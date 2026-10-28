#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>

struct CloudMeasurement {
    float laeq;
    float maximum;
    uint32_t events;
    int64_t timestamp;
};

// Fixed, versioned little-endian record. No compiler padding is written to SD.
constexpr size_t TELEMETRY_BYTES = 32;
inline uint32_t telemetryCrc(const uint8_t* bytes, size_t count) {
    uint32_t crc = 0xffffffff;
    for (size_t i = 0; i < count; ++i) {
        crc ^= bytes[i];
        for (int bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}
inline void putTelemetry32(uint8_t* p, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) p[i] = (value >> (8 * i)) & 255;
}
inline uint32_t getTelemetry32(const uint8_t* p) {
    uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= uint32_t(p[i]) << (8 * i);
    return value;
}
inline void encodeTelemetry(const CloudMeasurement& m, uint8_t* bytes) {
    static_assert(sizeof(float) == 4, "32-bit IEEE float required");
    putTelemetry32(bytes, 0x31514e51); // QNQ1
    putTelemetry32(bytes + 4, 1);
    putTelemetry32(bytes + 8, uint32_t(m.timestamp));
    putTelemetry32(bytes + 12, uint32_t(uint64_t(m.timestamp) >> 32));
    uint32_t bits;
    std::memcpy(&bits, &m.laeq, 4); putTelemetry32(bytes + 16, bits);
    std::memcpy(&bits, &m.maximum, 4); putTelemetry32(bytes + 20, bits);
    putTelemetry32(bytes + 24, m.events);
    putTelemetry32(bytes + 28, telemetryCrc(bytes, 28));
}
inline bool decodeTelemetry(const uint8_t* bytes, size_t size, CloudMeasurement& m) {
    if (size != TELEMETRY_BYTES || getTelemetry32(bytes) != 0x31514e51 ||
        getTelemetry32(bytes + 4) != 1 ||
        getTelemetry32(bytes + 28) != telemetryCrc(bytes, 28)) return false;
    m.timestamp = int64_t(uint64_t(getTelemetry32(bytes + 8)) |
                          (uint64_t(getTelemetry32(bytes + 12)) << 32));
    uint32_t bits = getTelemetry32(bytes + 16); std::memcpy(&m.laeq, &bits, 4);
    bits = getTelemetry32(bytes + 20); std::memcpy(&m.maximum, &bits, 4);
    m.events = getTelemetry32(bytes + 24);
    return m.timestamp >= 1767225600 && m.timestamp < 4102444800LL &&
           std::isfinite(m.laeq) && std::isfinite(m.maximum) &&
           m.laeq >= 30 && m.laeq <= 130 && m.maximum >= m.laeq - 0.01f && m.maximum <= 130;
}
