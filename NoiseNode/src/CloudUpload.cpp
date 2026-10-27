#include "CloudUpload.h"
#include "OpenSenseMapRootCA.h"
#include "UploadPolicy.h"
#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

#if __has_include("quietnode_config.h")
#include "quietnode_config.h"
#else
#include "quietnode_config.example.h"
#endif

namespace {
struct Measurement {
    float laeq;
    float maximum;
    uint32_t events;
    time_t timestamp;
};
QueueHandle_t measurements = nullptr;
constexpr uint32_t RETRY_MS = 60000;
constexpr UBaseType_t QUEUE_CAPACITY = 30;

bool validId(const char* id) {
    if (strlen(id) != 24) return false;
    for (size_t i = 0; i < 24; ++i) {
        if (!((id[i] >= '0' && id[i] <= '9') ||
              (id[i] >= 'a' && id[i] <= 'f'))) return false;
    }
    return true;
}

uint32_t retryAfterMs(const String& header) {
    // Retry-After can be seconds or an HTTP date (bounded to seven days).
    if (!header.length()) return 0;
    bool digits = true;
    for (size_t i = 0; i < header.length(); ++i) {
        if (header[i] < '0' || header[i] > '9') digits = false;
    }
    int64_t seconds = 0;
    if (digits) {
        seconds = strtoll(header.c_str(), nullptr, 10);
    } else {
        struct tm utc{};
        if (strptime(header.c_str(), "%a, %d %b %Y %H:%M:%S GMT", &utc)) {
            // configTime keeps the process timezone at UTC.
            seconds = mktime(&utc) - time(nullptr);
        }
    }
    // Keep millis() comparisons safe; cap unusually long server delays at 7 days.
    if (seconds <= 0) return 0;
    if (seconds > 604800) seconds = 604800;
    return static_cast<uint32_t>(seconds * 1000);
}

void uploadWorker(void*) {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(QUIETNODE_WIFI_SSID, QUIETNODE_WIFI_PASSWORD);
    configTime(0, 0, "pool.ntp.org", "time.cloudflare.com");
    uint32_t lastConnectionAttempt = millis();
    uint32_t lastUploadEnd = 0;
    uint32_t waitMs = 0;
    uint32_t failureBackoff = RETRY_MS;
    bool attemptedUpload = false;
    bool wasConnected = false;
    Serial.println("[cloud] Periodic uploader started; RAM queue capacity: 30 minute windows");

    for (;;) {
        const uint32_t now = millis();
        const bool connected = WiFi.status() == WL_CONNECTED;
        if (connected != wasConnected) {
            Serial.println(connected ? "[cloud] Wi-Fi connected; waiting for valid UTC windows"
                                     : "[cloud] Wi-Fi disconnected; queued windows retained");
            wasConnected = connected;
        }
        if (!connected && now - lastConnectionAttempt >= 30000) {
            Serial.println("[cloud] Retrying Wi-Fi");
            WiFi.reconnect();
            lastConnectionAttempt = now;
        }
        Measurement measurement{};
        if (connected && (!attemptedUpload || now - lastUploadEnd >= waitMs) &&
            xQueuePeek(measurements, &measurement, 0) == pdTRUE) {
            attemptedUpload = true;
            struct tm utc;
            gmtime_r(&measurement.timestamp, &utc);
            char timestamp[24];
            strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
            char payload[480];
            snprintf(payload, sizeof(payload),
                     "[{\"sensor\":\"%s\",\"value\":\"%.1f\",\"createdAt\":\"%s\"},"
                     "{\"sensor\":\"%s\",\"value\":\"%.1f\",\"createdAt\":\"%s\"},"
                     "{\"sensor\":\"%s\",\"value\":\"%lu\",\"createdAt\":\"%s\"}]",
                     QUIETNODE_LAEQ_SENSOR_ID, measurement.laeq, timestamp,
                     QUIETNODE_LMAX_SENSOR_ID, measurement.maximum, timestamp,
                     QUIETNODE_EVENTS_SENSOR_ID, static_cast<unsigned long>(measurement.events), timestamp);

            WiFiClientSecure tls;
            tls.setCACert(OPEN_SENSE_MAP_ROOT_CA);
            tls.setHandshakeTimeout(10);
            HTTPClient http;
            http.setConnectTimeout(10000);
            http.setTimeout(10000);
            const String url = String("https://api.opensensemap.org/boxes/") +
                               QUIETNODE_BOX_ID + "/data";
            int status = -1;
            uint32_t serverWait = 0;
            if (http.begin(tls, url)) {
                const char* headers[] = {"Retry-After"};
                http.collectHeaders(headers, 1);
                http.addHeader("Content-Type", "application/json");
                http.addHeader("Authorization", QUIETNODE_ACCESS_TOKEN);
                status = http.POST(String(payload));
                serverWait = retryAfterMs(http.header("Retry-After"));
            }
            http.end();
            lastUploadEnd = millis();
            Serial.printf("[cloud] POST result=%d window_end=%s LAeq=%.1f Lmax=%.1f events=%lu\n",
                          status, timestamp, measurement.laeq, measurement.maximum,
                          static_cast<unsigned long>(measurement.events));
            if (status >= 200 && status < 300) {
                // Only this worker removes items; the main loop only appends.
                xQueueReceive(measurements, &measurement, 0);
                // Live windows arrive once/minute; recover a backlog at most
                // once per 5 seconds instead of accumulating it indefinitely.
                waitMs = serverWait > 5000 ? serverWait : 5000;
                failureBackoff = RETRY_MS;
                Serial.printf("[cloud] Minute accepted; queued=%u\n",
                              static_cast<unsigned>(uxQueueMessagesWaiting(measurements)));
            } else {
                waitMs = serverWait > failureBackoff ? serverWait : failureBackoff;
                failureBackoff = retryDelayMs(failureBackoff);
                Serial.printf("[cloud] Retaining window; retry in %lu seconds; queued=%u\n",
                              static_cast<unsigned long>(waitMs / 1000),
                              static_cast<unsigned>(uxQueueMessagesWaiting(measurements)));
                if (status == 401 || status == 403 || status == 404) {
                    Serial.println("[cloud] Check station token and sensor IDs in local configuration");
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
} // namespace

void beginCloudUpload() {
    if (!strlen(QUIETNODE_WIFI_SSID) || !validId(QUIETNODE_BOX_ID) ||
        !validId(QUIETNODE_LAEQ_SENSOR_ID) || !validId(QUIETNODE_LMAX_SENSOR_ID) ||
        !validId(QUIETNODE_EVENTS_SENSOR_ID) || !strlen(QUIETNODE_ACCESS_TOKEN) ||
        !strcmp(QUIETNODE_LAEQ_SENSOR_ID, QUIETNODE_LMAX_SENSOR_ID) ||
        !strcmp(QUIETNODE_LAEQ_SENSOR_ID, QUIETNODE_EVENTS_SENSOR_ID) ||
        !strcmp(QUIETNODE_LMAX_SENSOR_ID, QUIETNODE_EVENTS_SENSOR_ID)) {
        Serial.println("[cloud] Disabled: configure Wi-Fi, station and all three minute sensor IDs");
        return;
    }
    measurements = xQueueCreate(QUEUE_CAPACITY, sizeof(Measurement));
    if (!measurements) {
        Serial.println("[cloud] Disabled: RAM allocation failed");
        return;
    }
    if (xTaskCreate(uploadWorker, "cloud-upload", 12288, nullptr, 1, nullptr) != pdPASS) {
        Serial.println("[cloud] Disabled: worker creation failed");
        vQueueDelete(measurements);
        measurements = nullptr;
    }
}

bool offerCloudSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc) {
    if (!measurements) return false;
    if (!publishableWindow(summary, startUtc, endUtc)) {
        Serial.println("[cloud] Skipping incomplete window or unavailable/discontinuous UTC; see minute diagnostics");
        return false;
    }
    Measurement measurement{static_cast<float>(summary.laeq), summary.maximum,
                            summary.events, endUtc};
    if (xQueueSend(measurements, &measurement, 0) != pdTRUE) {
        Serial.println("[cloud] RAM queue full: dropping NEW window; existing 30 retained");
        return false;
    }
    Serial.printf("[cloud] Minute queued; depth=%u\n",
                  static_cast<unsigned>(uxQueueMessagesWaiting(measurements)));
    return true;
}
