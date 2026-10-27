#include "CloudUpload.h"
#include "OpenSenseMapRootCA.h"
#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include <freertos/FreeRTOS.h>
#include <freertos/event_groups.h>
#include <freertos/queue.h>

#if __has_include("quietnode_config.h")
#include "quietnode_config.h"
#else
#include "quietnode_config.example.h"
#endif

namespace {
struct Measurement {
    float decibels;
    time_t timestamp;
};
QueueHandle_t measurements = nullptr;
EventGroupHandle_t state = nullptr;
constexpr EventBits_t CAPTURE_ENABLED = BIT0;
constexpr uint32_t RETRY_MS = 60000;

bool validId(const char* id) {
    if (strlen(id) != 24) return false;
    for (size_t i = 0; i < 24; ++i) {
        if (!((id[i] >= '0' && id[i] <= '9') ||
              (id[i] >= 'a' && id[i] <= 'f'))) return false;
    }
    return true;
}

void uploadWorker(void*) {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(QUIETNODE_WIFI_SSID, QUIETNODE_WIFI_PASSWORD);
    configTime(0, 0, "pool.ntp.org", "time.cloudflare.com");
    uint32_t lastConnectionAttempt = millis();
    uint32_t lastUploadAttempt = 0;
    bool attemptedUpload = false;
    bool wasConnected = false;
    bool pending = false;
    Measurement measurement{};

    for (;;) {
        const uint32_t now = millis();
        const bool connected = WiFi.status() == WL_CONNECTED;
        if (connected != wasConnected) {
            Serial.println(connected ? "[cloud] Wi-Fi connected; waiting for UTC if needed"
                                     : "[cloud] Wi-Fi disconnected");
            wasConnected = connected;
        }
        if (!connected && now - lastConnectionAttempt >= 30000) {
            Serial.println("[cloud] Retrying Wi-Fi");
            WiFi.reconnect();
            lastConnectionAttempt = now;
        }
        if (!pending && xQueueReceive(measurements, &measurement, 0) == pdTRUE) {
            pending = true;
            Serial.println("[cloud] Captured one measurement; retained in RAM until accepted");
        }
        if (pending && connected &&
            (!attemptedUpload || now - lastUploadAttempt >= RETRY_MS)) {
            attemptedUpload = true;
            lastUploadAttempt = now;
            struct tm utc;
            gmtime_r(&measurement.timestamp, &utc);
            char timestamp[24];
            strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
            char payload[180];
            snprintf(payload, sizeof(payload),
                     "[{\"sensor\":\"%s\",\"value\":\"%.1f\",\"createdAt\":\"%s\"}]",
                     QUIETNODE_SENSOR_ID, measurement.decibels, timestamp);

            WiFiClientSecure tls;
            tls.setCACert(OPEN_SENSE_MAP_ROOT_CA);
            tls.setHandshakeTimeout(10);
            HTTPClient http;
            http.setConnectTimeout(10000);
            http.setTimeout(10000);
            const String url = String("https://api.opensensemap.org/boxes/") +
                               QUIETNODE_BOX_ID + "/data";
            int status = -1;
            if (http.begin(tls, url)) {
                http.addHeader("Content-Type", "application/json");
                http.addHeader("Authorization", QUIETNODE_ACCESS_TOKEN);
                status = http.POST(String(payload));
            }
            Serial.printf("[cloud] POST result: %d (%.1f dBA at %s)\n",
                          status, measurement.decibels, timestamp);
            http.end();
            if (status >= 200 && status < 300) {
                Serial.println("[cloud] Upload accepted. One-shot test complete; sampling continues.");
                break;
            }
            Serial.println("[cloud] Upload failed; keeping sample and retrying in at least 60 seconds");
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    // Leave the loop first so HTTP/TLS destructors release their resources.
    vTaskDelete(nullptr);
}
} // namespace

void beginCloudUpload() {
    if (!strlen(QUIETNODE_WIFI_SSID) || !validId(QUIETNODE_BOX_ID) ||
        !validId(QUIETNODE_SENSOR_ID) || !strlen(QUIETNODE_ACCESS_TOKEN)) {
        Serial.println("[cloud] Disabled: fill include/quietnode_config.h to enable one-shot upload");
        return;
    }
    measurements = xQueueCreate(1, sizeof(Measurement));
    state = xEventGroupCreate();
    if (!measurements || !state) {
        Serial.println("[cloud] Disabled: RAM allocation failed");
        if (measurements) vQueueDelete(measurements);
        if (state) vEventGroupDelete(state);
        measurements = nullptr;
        state = nullptr;
        return;
    }
    xEventGroupSetBits(state, CAPTURE_ENABLED);
    if (xTaskCreate(uploadWorker, "cloud-upload", 12288, nullptr, 1, nullptr) != pdPASS) {
        Serial.println("[cloud] Disabled: worker creation failed");
        vQueueDelete(measurements);
        vEventGroupDelete(state);
        measurements = nullptr;
        state = nullptr;
    }
}

void offerCloudMeasurement(float decibels) {
    if (!state || !(xEventGroupGetBits(state) & CAPTURE_ENABLED)) return;
    const time_t utcNow = time(nullptr);
    // Reject unsynchronised clocks and out-of-range sensor readings.
    if (utcNow < 1767225600 || decibels < 30.0f || decibels > 130.0f) return;
    Measurement measurement{decibels, utcNow};
    if (xQueueSend(measurements, &measurement, 0) == pdTRUE) {
        xEventGroupClearBits(state, CAPTURE_ENABLED);
    }
}
