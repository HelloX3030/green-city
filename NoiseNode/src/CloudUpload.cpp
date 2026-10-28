#include "CloudUpload.h"
#include "OpenSenseMapRootCA.h"
#include "UploadPolicy.h"
#include "SdStorage.h"
#include "CloudPayload.h"
#include <atomic>
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
using Measurement = CloudMeasurement;
std::atomic<bool> uploadsPaused{false};
QueueHandle_t measurements = nullptr;
constexpr uint32_t RETRY_MS = 60000;
constexpr UBaseType_t QUEUE_CAPACITY = 27; // Plus at most three in-flight RAM records.
constexpr size_t BATCH_SIZE = 3;

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
    uint32_t lastConnectionAttempt = millis(), lastUploadEnd = 0, waitMs = 0;
    uint32_t failureBackoff = RETRY_MS;
    bool attemptedUpload = false, wasConnected = false, fromSd = false;
    Measurement batch[BATCH_SIZE]{};
    size_t count = 0;
    Serial.println("[cloud] Periodic uploader started; SD outbox preferred; <=1 request/minute, up to 3 windows/request");

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
            WiFi.reconnect(); lastConnectionAttempt = now;
        }
        if (connected && time(nullptr) >= 1767225600 && !uploadsPaused.load() &&
            (!attemptedUpload || now - lastUploadEnd >= waitMs)) {
            if (!count) {
                count = peekSdUploads(batch, BATCH_SIZE);
                fromSd = count != 0;
                if (!fromSd) {
                    while (count < BATCH_SIZE && xQueueReceive(measurements, &batch[count], 0) == pdTRUE) ++count;
                }
            }
            if (count) {
                attemptedUpload = true;
                char payload[1200];
                const size_t used = formatCloudBatch(payload, sizeof(payload), batch, count,
                    QUIETNODE_LAEQ_SENSOR_ID, QUIETNODE_LMAX_SENSOR_ID, QUIETNODE_EVENTS_SENSOR_ID);
                if (!used) {
                    Serial.println("[cloud] Payload buffer too small; retaining batch");
                    lastUploadEnd = millis(); waitMs = RETRY_MS;
                    continue;
                }
                WiFiClientSecure tls;
                tls.setCACert(OPEN_SENSE_MAP_ROOT_CA);
                tls.setHandshakeTimeout(10);
                HTTPClient http;
                http.setConnectTimeout(10000); http.setTimeout(10000);
                const String url = String("https://api.opensensemap.org/boxes/") + QUIETNODE_BOX_ID + "/data";
                int status = -1;
                uint32_t serverWait = 0;
                if (http.begin(tls, url)) {
                    const char* headers[] = {"Retry-After"}; http.collectHeaders(headers, 1);
                    http.addHeader("Content-Type", "application/json");
                    http.addHeader("Authorization", QUIETNODE_ACCESS_TOKEN);
                    status = http.POST(String(payload));
                    serverWait = retryAfterMs(http.header("Retry-After"));
                }
                if (status < 0) {
                    char error[128]{};
                    const int tlsError = tls.lastError(error, sizeof(error));
                    Serial.printf("[cloud] Transport: %s; TLS=%d %s; heap=%u largest=%u\n",
                        HTTPClient::errorToString(status).c_str(), tlsError, error, ESP.getFreeHeap(), ESP.getMaxAllocHeap());
                }
                http.end(); lastUploadEnd = millis();
                Serial.printf("[cloud] POST result=%d windows=%u source=%s worker_stack_free=%u\n",
                    status, unsigned(count), fromSd ? "SD" : "RAM", unsigned(uxTaskGetStackHighWaterMark(nullptr)));
                if (status >= 200 && status < 300) {
                    for (size_t i = 0; i < count; ++i) {
                        Serial.printf("[cloud] Accepted window_epoch=%lld LAeq=%.1f Lmax=%.1f events=%lu\n",
                            static_cast<long long>(batch[i].timestamp), batch[i].laeq, batch[i].maximum,
                            static_cast<unsigned long>(batch[i].events));
                        if (fromSd && !acknowledgeSdUpload(batch[i]))
                            Serial.println("[cloud] SD acknowledgement failed; record may replay after reboot");
                    }
                    count = 0; failureBackoff = RETRY_MS;
                    waitMs = serverWait > RETRY_MS ? serverWait : RETRY_MS;
                } else {
                    waitMs = serverWait > failureBackoff ? serverWait : failureBackoff;
                    failureBackoff = retryDelayMs(failureBackoff);
                    Serial.printf("[cloud] Retaining batch; retry in %lu seconds\n", static_cast<unsigned long>(waitMs / 1000));
                    if (status == 401 || status == 403 || status == 404)
                        Serial.println("[cloud] Check station token and sensor IDs in local configuration");
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

} // namespace

bool cloudUploadConfigured() {
    return strlen(QUIETNODE_WIFI_SSID) && validId(QUIETNODE_BOX_ID) &&
           validId(QUIETNODE_LAEQ_SENSOR_ID) && validId(QUIETNODE_LMAX_SENSOR_ID) &&
           validId(QUIETNODE_EVENTS_SENSOR_ID) && strlen(QUIETNODE_ACCESS_TOKEN) &&
           strcmp(QUIETNODE_LAEQ_SENSOR_ID, QUIETNODE_LMAX_SENSOR_ID) &&
           strcmp(QUIETNODE_LAEQ_SENSOR_ID, QUIETNODE_EVENTS_SENSOR_ID) &&
           strcmp(QUIETNODE_LMAX_SENSOR_ID, QUIETNODE_EVENTS_SENSOR_ID);
}

void beginCloudUpload() {
    if (!cloudUploadConfigured()) {
        Serial.println("[cloud] Disabled: configure Wi-Fi, station and all three minute sensor IDs");
        return;
    }
    measurements = xQueueCreate(QUEUE_CAPACITY, sizeof(Measurement));
    if (!measurements) {
        Serial.println("[cloud] Disabled: RAM allocation failed");
        return;
    }
    if (xTaskCreate(uploadWorker, "cloud-upload", 9216, nullptr, 1, nullptr) != pdPASS) {
        Serial.println("[cloud] Disabled: worker creation failed");
        vQueueDelete(measurements);
        measurements = nullptr;
    }
}

bool offerCloudSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc) {
    if (logSdSummary(summary, startUtc, endUtc)) return true;
    if (!measurements) return false;
    if (!publishableWindow(summary, startUtc, endUtc)) {
        Serial.println("[cloud] Skipping incomplete window or unavailable/discontinuous UTC; see minute diagnostics");
        return false;
    }
    return queueRamCloudMeasurement({static_cast<float>(summary.laeq), summary.maximum, summary.events, endUtc});
}

bool queueRamCloudMeasurement(const CloudMeasurement& measurement) {
    if (!measurements) return false;
    if (xQueueSend(measurements, &measurement, 0) != pdTRUE) {
        Serial.println("[cloud] RAM queue full: dropping NEW window; existing queued/in-flight windows retained");
        return false;
    }
    Serial.printf("[cloud] Minute queued; depth=%u\n",
                  static_cast<unsigned>(uxQueueMessagesWaiting(measurements)));
    return true;
}

void setCloudUploadPaused(bool paused) {
    uploadsPaused.store(paused);
    Serial.println(paused ? "[cloud] Uploads paused; acquisition and storage continue" : "[cloud] Uploads resumed");
}
