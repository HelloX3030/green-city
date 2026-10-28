#pragma once
#include "TelemetryRecord.h"
#include <cstdio>
#include <ctime>

// Bounded JSON encoding; IDs are validated before the uploader starts.
inline size_t formatCloudBatch(char* output, size_t capacity, const CloudMeasurement* batch,
                               size_t count, const char* laeqId, const char* maxId, const char* eventId) {
    if (capacity < 4 || !count || count > 3) return 0;
    size_t used = 1;
    output[0] = '[';
    for (size_t i = 0; i < count; ++i) {
        const time_t seconds = batch[i].timestamp;
        struct tm utc;
        if (!gmtime_r(&seconds, &utc)) return 0;
        char timestamp[24];
        if (!strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc)) return 0;
        const int written = snprintf(output + used, capacity - used,
            "%s{\"sensor\":\"%s\",\"value\":\"%.1f\",\"createdAt\":\"%s\"},"
            "{\"sensor\":\"%s\",\"value\":\"%.1f\",\"createdAt\":\"%s\"},"
            "{\"sensor\":\"%s\",\"value\":\"%lu\",\"createdAt\":\"%s\"}",
            i ? "," : "", laeqId, batch[i].laeq, timestamp,
            maxId, batch[i].maximum, timestamp,
            eventId, static_cast<unsigned long>(batch[i].events), timestamp);
        if (written <= 0 || size_t(written) >= capacity - used - 2) return 0;
        used += written;
    }
    output[used++] = ']'; output[used] = 0;
    return used;
}
