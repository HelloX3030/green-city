#include "SdStorage.h"
#include "CloudUpload.h"
#include "UploadPolicy.h"
#include <Arduino.h>
#include <SD.h>
#include <SPI.h>
#include <atomic>
#include <esp_system.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <sys/time.h>

#if __has_include("quietnode_config.h")
#include "quietnode_config.h"
#else
#include "quietnode_config.example.h"
#endif

namespace {
constexpr uint32_t ROTATE_BYTES = 16 * 1024 * 1024;
constexpr unsigned OUTBOX_LIMIT = 1440; // At most 24 hours of minute windows.
constexpr size_t BUFFER_BYTES = 512;
struct RawSample {
    uint64_t uptime;
    int64_t utcMs;
    uint32_t sequence;
    uint32_t millivolts;
    bool valid;
};
struct MinutePacket { NoiseSummary summary; time_t startUtc; time_t endUtc; };
SPIClass sdSpi(FSPI);
SemaphoreHandle_t sdMutex = nullptr;
QueueHandle_t rawQueue = nullptr, minuteQueue = nullptr;
std::atomic<bool> healthy{false};
std::atomic<uint32_t> droppedRaw{0};
std::atomic<bool> verifyRequested{false};
char bootId[20], outbox[64], rawPath[96], minutePath[96];
File rawFile;
unsigned segment = 0, pendingFiles = 0;
uint32_t rawWritten = 0;
char rawBuffer[BUFFER_BYTES];
size_t rawUsed = 0;

struct SdLock {
    SdLock() { xSemaphoreTake(sdMutex, portMAX_DELAY); }
    ~SdLock() { xSemaphoreGive(sdMutex); }
};

void storageFailed(const char* operation) {
    healthy.store(false);
    Serial.printf("[sd] ERROR during %s; SD logging stopped; cloud uses RAM fallback. Reboot with a working card.\n", operation);
}

void recordPath(char* path, size_t size, int64_t timestamp, const char* extension) {
    snprintf(path, size, "%s/%012lld.%s", outbox, static_cast<long long>(timestamp), extension);
}

bool readRecord(const char* path, CloudMeasurement& m) {
    File f = SD.open(path, FILE_READ);
    if (!f) return false;
    uint8_t bytes[TELEMETRY_BYTES];
    const size_t size = f.size();
    const size_t count = f.read(bytes, sizeof(bytes));
    f.close();
    return count == sizeof(bytes) && decodeTelemetry(bytes, size, m);
}

void quarantine(const char* path) {
    char bad[128];
    snprintf(bad, sizeof(bad), "%s.bad-%08lx", path, static_cast<unsigned long>(esp_random()));
    Serial.printf("[sd] Quarantining incomplete/corrupt record: %s\n", path);
    if (!SD.rename(path, bad)) storageFailed("record quarantine");
}

// Recover complete temporary records after a reset; retain corrupt files as .bad.
void recoverOutbox() {
    File directory = SD.open(outbox);
    if (!directory || !directory.isDirectory()) { storageFailed("outbox open"); return; }
    File entry = directory.openNextFile();
    while (entry) {
        const String name = entry.name();
        const bool isFile = !entry.isDirectory();
        entry.close();
        char path[128];
        snprintf(path, sizeof(path), "%s/%s", outbox, name.c_str());
        if (isFile && (name.endsWith(".q") || name.endsWith(".tmp"))) {
            CloudMeasurement m{};
            if (!readRecord(path, m)) {
                quarantine(path);
            } else if (name.endsWith(".tmp")) {
                char ready[128]; recordPath(ready, sizeof(ready), m.timestamp, "q");
                if (!SD.exists(ready)) {
                    if (!SD.rename(path, ready)) storageFailed("temporary record recovery");
                } else {
                    // Preserve a redundant temp file without replaying it twice.
                    quarantine(path);
                }
            }
        }
        entry = directory.openNextFile();
    }
    directory.close();
    // Recount after renames: FAT directory iteration may revisit a renamed entry.
    pendingFiles = 0;
    directory = SD.open(outbox);
    entry = directory.openNextFile();
    while (entry) {
        if (!entry.isDirectory() && String(entry.name()).endsWith(".q")) ++pendingFiles;
        entry.close(); entry = directory.openNextFile();
    }
    directory.close();
}

bool persistRecord(const CloudMeasurement& m) {
    char path[128], temp[128];
    recordPath(path, sizeof(path), m.timestamp, "q");
    recordPath(temp, sizeof(temp), m.timestamp, "tmp");
    if (SD.exists(path)) {
        CloudMeasurement existing{};
        uint8_t a[TELEMETRY_BYTES], b[TELEMETRY_BYTES];
        encodeTelemetry(m, a);
        if (readRecord(path, existing)) {
            encodeTelemetry(existing, b);
            if (!memcmp(a, b, sizeof(a))) return true;
        }
        Serial.println("[sd] Conflicting outbox timestamp; preserving original, using RAM for new window");
        return false;
    }
    if (pendingFiles >= OUTBOX_LIMIT) {
        Serial.println("[sd] Outbox full (1440 windows); new window uses bounded RAM fallback");
        return false;
    }
    uint8_t bytes[TELEMETRY_BYTES]; encodeTelemetry(m, bytes);
    File f = SD.open(temp, FILE_WRITE);
    if (!f) { storageFailed("outbox create"); return false; }
    const bool written = f.write(bytes, sizeof(bytes)) == sizeof(bytes);
    f.flush(); f.close();
    CloudMeasurement check{};
    if (!written || !readRecord(temp, check) || !SD.rename(temp, path)) {
        storageFailed("outbox write/verify/rename");
        return false;
    }
    ++pendingFiles;
    Serial.printf("[sd] Minute durable; pending=%u\n", pendingFiles);
    return true;
}

bool openRawSegment() {
    snprintf(rawPath, sizeof(rawPath), "/quietnode/raw/%s-%03u.csv", bootId, segment++);
    rawFile = SD.open(rawPath, FILE_WRITE);
    if (!rawFile) return false;
    if (!rawFile.setBufferSize(512)) return false;
    const char* header = "sequence,uptime_ms,utc,millivolts,dba,valid\n";
    return rawFile.write(reinterpret_cast<const uint8_t*>(header), strlen(header)) == strlen(header);
}

bool flushRaw(bool sync) {
    if (rawUsed) {
        if (rawFile.write(reinterpret_cast<uint8_t*>(rawBuffer), rawUsed) != rawUsed) return false;
        rawUsed = 0;
    }
    if (sync) rawFile.flush();
    if (rawFile.size() >= ROTATE_BYTES) {
        rawFile.flush(); rawFile.close();
        if (!openRawSegment()) return false;
    }
    return true;
}

void formatUtc(int64_t utcMs, char* output, size_t size) {
    output[0] = 0;
    if (utcMs < 1767225600000LL) return;
    const time_t seconds = utcMs / 1000;
    struct tm utc; gmtime_r(&seconds, &utc);
    char date[24]; strftime(date, sizeof(date), "%Y-%m-%dT%H:%M:%S", &utc);
    snprintf(output, size, "%s.%03uZ", date, unsigned(utcMs % 1000));
}

void verifyReadback() {
    SdLock lock;
    if (!healthy.load() || !flushRaw(true)) {
        Serial.println("[sd] Verification failed: storage unavailable");
        return;
    }
    File reader = SD.open(rawPath, FILE_READ);
    if (!reader || reader.size() == 0) {
        Serial.println("[sd] Verification failed: raw CSV cannot be reopened");
        return;
    }
    char header[64]{};
    const size_t headerBytes = reader.readBytesUntil('\n', header, sizeof(header) - 1);
    header[headerBytes] = 0;
    if (strcmp(header, "sequence,uptime_ms,utc,millivolts,dba,valid")) {
        Serial.println("[sd] Verification failed: raw header mismatch");
        return;
    }
    const uint32_t size = reader.size();
    char tail[513]{};
    reader.seek(size > 512 ? size - 512 : 0);
    const size_t count = reader.read(reinterpret_cast<uint8_t*>(tail), 512);
    reader.close();
    tail[count] = 0;
    char* end = strrchr(tail, '\n');
    if (end) *end = 0;
    char* last = strrchr(tail, '\n');
    if (!last || !end || last + 1 == end) {
        Serial.println("[sd] Verification failed: no complete data row yet");
        return;
    }
    File minutes = SD.open(minutePath, FILE_READ);
    const size_t minuteBytes = minutes ? minutes.size() : 0;
    minutes.close();
    Serial.printf("[sd] VERIFIED readback raw=%s bytes=%lu minute_bytes=%u pending=%u\n",
                  rawPath, static_cast<unsigned long>(size), unsigned(minuteBytes), pendingFiles);
    Serial.printf("[sd] Last stored row: %s\n", last + 1);
}

void storageWorker(void*) {
    uint32_t lastFlush = millis(), lastStatus = millis();
    for (;;) {
        MinutePacket packet{};
        if (xQueueReceive(minuteQueue, &packet, 0) == pdTRUE) {
            const bool eligible = publishableWindow(packet.summary, packet.startUtc, packet.endUtc);
            CloudMeasurement m{static_cast<float>(packet.summary.laeq), packet.summary.maximum,
                               packet.summary.events, packet.endUtc};
            bool durable = false;
            if (healthy.load()) {
                SdLock lock;
                // Durable outbox first; no networking waits inside this mutex.
                if (eligible) durable = persistRecord(m);
                char line[256];
                const int length = snprintf(line, sizeof(line), "%llu,%lld,%lld,%lu,%lu,%lu,%lu,%lu,%.3f,%.3f,%lu,%u\n",
                    static_cast<unsigned long long>(esp_timer_get_time() / 1000),
                    static_cast<long long>(packet.startUtc >= 1767225600 ? packet.startUtc : 0),
                    static_cast<long long>(packet.endUtc >= 1767225600 ? packet.endUtc : 0),
                    static_cast<unsigned long>(packet.summary.durationMs),
                    static_cast<unsigned long>(packet.summary.samples), static_cast<unsigned long>(packet.summary.invalidSamples),
                    static_cast<unsigned long>(packet.summary.expectedSamples), static_cast<unsigned long>(packet.summary.maxSampleGapMs),
                    packet.summary.laeq, packet.summary.maximum, static_cast<unsigned long>(packet.summary.events), eligible);
                File minuteFile = healthy.load() ? SD.open(minutePath, FILE_APPEND) : File();
                if (minuteFile) minuteFile.setBufferSize(512);
                if (!minuteFile || length <= 0 || length >= int(sizeof(line)) ||
                    minuteFile.write(reinterpret_cast<const uint8_t*>(line), length) != size_t(length)) {
                    if (healthy.load()) storageFailed("minute CSV write");
                } else {
                    minuteFile.flush();
                }
                minuteFile.close();
            }
            if (eligible && !durable && !queueRamCloudMeasurement(m))
                Serial.println("[sd] LOSS: minute could not be saved or queued to RAM");
        }
        // Bound each batch so minute persistence is serviced regularly.
        for (unsigned i = 0; i < 16; ++i) {
            RawSample sample{};
            if (xQueueReceive(rawQueue, &sample, 0) != pdTRUE) break;
            if (!healthy.load()) { ++droppedRaw; continue; }
            char utc[32], line[128]; formatUtc(sample.utcMs, utc, sizeof(utc));
            const int length = snprintf(line, sizeof(line), "%lu,%llu,%s,%lu,%.2f,%u\n",
                static_cast<unsigned long>(sample.sequence), static_cast<unsigned long long>(sample.uptime), utc,
                static_cast<unsigned long>(sample.millivolts), sample.millivolts / 20.0f, sample.valid);
            SdLock lock;
            if (length <= 0 || length >= int(sizeof(line)) ||
                (rawUsed + length > sizeof(rawBuffer) && !flushRaw(false))) {
                storageFailed("sample buffer write"); ++droppedRaw; continue;
            }
            memcpy(rawBuffer + rawUsed, line, length); rawUsed += length; ++rawWritten;
        }
        if (healthy.load() && millis() - lastFlush >= 5000) {
            SdLock lock;
            if (!flushRaw(true)) storageFailed("raw CSV flush");
            lastFlush = millis();
        }
        if (verifyRequested.exchange(false)) verifyReadback();
        if (millis() - lastStatus >= 30000) {
            SdLock lock;
            Serial.printf("[sd] healthy=%u samples_buffered_or_written=%lu raw_dropped=%lu raw_bytes=%lu pending=%u\n",
                          healthy.load(), static_cast<unsigned long>(rawWritten),
                          static_cast<unsigned long>(droppedRaw.load()),
                          static_cast<unsigned long>(rawFile ? rawFile.size() : 0), pendingFiles);
            Serial.printf("[sd] heap=%u largest=%u worker_stack_free=%u\n", ESP.getFreeHeap(),
                          ESP.getMaxAllocHeap(), unsigned(uxTaskGetStackHighWaterMark(nullptr)));
            lastStatus = millis();
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
} // namespace

void beginSdStorage() {
    sdMutex = xSemaphoreCreateMutex();
    rawQueue = xQueueCreate(8, sizeof(RawSample)); // Eight seconds at the 1 Hz SD logging rate.
    minuteQueue = xQueueCreate(4, sizeof(MinutePacket));
    if (!sdMutex || !rawQueue || !minuteQueue) {
        Serial.println("[sd] Disabled: queue allocation failed; cloud remains available");
        return;
    }
    pinMode(PIN_SD_ENABLE, OUTPUT);
    digitalWrite(PIN_SD_ENABLE, LOW); // senseBox MCU-S2 SD power is active LOW.
    sdSpi.begin(PIN_SD_SCLK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
    if (!SD.begin(PIN_SD_CS, sdSpi, 4000000, "/sd", 2, false) || SD.cardType() == CARD_NONE) {
        Serial.println("[sd] No usable card detected. Use FAT32; no formatting attempted. Cloud continues with RAM queue.");
        return;
    }
    if (!SD.exists("/quietnode") && !SD.mkdir("/quietnode")) return storageFailed("root directory");
    if (!SD.exists("/quietnode/raw") && !SD.mkdir("/quietnode/raw")) return storageFailed("raw directory");
    if (!SD.exists("/quietnode/minutes") && !SD.mkdir("/quietnode/minutes")) return storageFailed("minute directory");
    // Isolate pending records by station. A different station never replays them.
    const char* station = strlen(QUIETNODE_BOX_ID) == 24 ? QUIETNODE_BOX_ID : "unconfigured";
    snprintf(outbox, sizeof(outbox), "/quietnode/outbox-%s", station);
    if (!SD.exists(outbox) && !SD.mkdir(outbox)) return storageFailed("outbox directory");
    snprintf(bootId, sizeof(bootId), "%08lx%08lx", static_cast<unsigned long>(esp_random()), static_cast<unsigned long>(esp_random()));
    snprintf(minutePath, sizeof(minutePath), "/quietnode/minutes/%s.csv", bootId);
    if (!openRawSegment()) return storageFailed("raw CSV create");
    File minuteFile = SD.open(minutePath, FILE_WRITE);
    if (minuteFile) minuteFile.setBufferSize(512);
    const char* header = "uptime_ms,start_utc_epoch,end_utc_epoch,duration_ms,valid,invalid,expected,max_gap_ms,laeq,lmax,events,upload_eligible\n";
    if (!minuteFile || minuteFile.write(reinterpret_cast<const uint8_t*>(header), strlen(header)) != strlen(header))
        return storageFailed("minute CSV create");
    rawFile.flush(); minuteFile.flush(); minuteFile.close();
    healthy.store(true);
    recoverOutbox();
    if (!healthy.load()) return;
    Serial.printf("[sd] Card detected: %llu MB; boot=%s; recovered_pending=%u\n",
                  static_cast<unsigned long long>(SD.cardSize() / 1024 / 1024), bootId, pendingFiles);
    Serial.printf("[sd] Raw CSV: %s; minute CSV: %s; flush=5s\n", rawPath, minutePath);
    if (xTaskCreate(storageWorker, "sd-storage", 4096, nullptr, 1, nullptr) != pdPASS)
        storageFailed("worker creation");
}

void logSdSample(uint32_t millivolts, bool valid) {
    static uint32_t sequence = 0;
    static uint32_t lastLogMs = millis() - 1000;
    const uint32_t now = millis();
    if (now - lastLogMs < 1000) return;
    lastLogMs += ((now - lastLogMs) / 1000) * 1000;
    ++sequence;
    if (!healthy.load()) return;
    struct timeval utc; gettimeofday(&utc, nullptr);
    RawSample sample{static_cast<uint64_t>(esp_timer_get_time() / 1000),
                     utc.tv_sec >= 1767225600 ? int64_t(utc.tv_sec) * 1000 + utc.tv_usec / 1000 : 0,
                     sequence, millivolts, valid};
    if (xQueueSend(rawQueue, &sample, 0) != pdTRUE) ++droppedRaw;
}

bool logSdSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc) {
    if (!healthy.load()) return false;
    MinutePacket packet{summary, startUtc, endUtc};
    if (xQueueSend(minuteQueue, &packet, 0) == pdTRUE) return true;
    Serial.println("[sd] Minute storage queue full; using RAM cloud fallback");
    return false;
}

size_t peekSdUploads(CloudMeasurement* records, size_t capacity) {
    if (!healthy.load() || !capacity) return 0;
    if (capacity > 3) capacity = 3;
    SdLock lock;
    if (!pendingFiles) return 0;
    File directory = SD.open(outbox);
    if (!directory) { storageFailed("outbox listing"); return 0; }
    String oldest[3];
    size_t selected = 0;
    File entry = directory.openNextFile();
    while (entry) {
        const String name = entry.name();
        if (!entry.isDirectory() && name.endsWith(".q")) {
            size_t at = 0;
            while (at < selected && oldest[at] < name) ++at;
            if (at < capacity) {
                if (selected < capacity) ++selected;
                for (size_t i = selected - 1; i > at; --i) oldest[i] = oldest[i - 1];
                oldest[at] = name;
            }
        }
        entry.close(); entry = directory.openNextFile();
    }
    directory.close();
    if (!selected) { pendingFiles = 0; return 0; }
    size_t count = 0;
    for (size_t i = 0; i < selected; ++i) {
        const String path = String(outbox) + "/" + oldest[i];
        if (readRecord(path.c_str(), records[count])) ++count;
        else { quarantine(path.c_str()); if (pendingFiles) --pendingFiles; }
    }
    return count;
}

bool acknowledgeSdUpload(const CloudMeasurement& m) {
    if (!healthy.load()) return false;
    SdLock lock;
    char path[128]; recordPath(path, sizeof(path), m.timestamp, "q");
    if (!SD.remove(path)) { storageFailed("accepted outbox removal"); return false; }
    if (pendingFiles) --pendingFiles;
    Serial.printf("[sd] Cloud acceptance recorded; pending=%u\n", pendingFiles);
    return true;
}

void requestSdVerification() {
    if (!healthy.load()) Serial.println("[sd] Verification unavailable: card not healthy/mounted");
    else verifyRequested.store(true);
}
