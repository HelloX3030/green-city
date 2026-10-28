#include "TelemetryRecord.h"
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
    CloudMeasurement original{63.9f, 89.6f, 3, 1793145600};
    uint8_t record[TELEMETRY_BYTES];
    encodeTelemetry(original, record);
    CloudMeasurement restored{};
    assert(decodeTelemetry(record, sizeof(record), restored));
    assert(restored.timestamp == original.timestamp && restored.laeq == original.laeq &&
           restored.maximum == original.maximum && restored.events == original.events);
    // Every truncated length must be rejected after a torn SD write.
    for (size_t length = 0; length < sizeof(record); ++length)
        assert(!decodeTelemetry(record, length, restored));
    // Detect corruption anywhere in the header, measurement or checksum.
    for (size_t byte = 0; byte < sizeof(record); ++byte) {
        record[byte] ^= 1;
        assert(!decodeTelemetry(record, sizeof(record), restored));
        record[byte] ^= 1;
    }
    original.timestamp = 0;
    encodeTelemetry(original, record);
    assert(!decodeTelemetry(record, sizeof(record), restored));
    original.timestamp = 1793145600;
    original.laeq = NAN;
    encodeTelemetry(original, record);
    assert(!decodeTelemetry(record, sizeof(record), restored));
    original.laeq = 90; original.maximum = 60;
    encodeTelemetry(original, record);
    assert(!decodeTelemetry(record, sizeof(record), restored));
    std::puts("Telemetry persistence checks passed");
}
