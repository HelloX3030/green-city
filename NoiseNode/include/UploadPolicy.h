#pragma once
#include "NoiseAggregator.h"
#include <cstdint>
#include <cstdlib>

// Upload only complete, uniformly scheduled windows with valid UTC throughout.
// Calendar timestamps label the END of each window.
inline bool publishableWindow(const NoiseSummary& s, int64_t startUtc, int64_t endUtc) {
    const int64_t errorMs = (endUtc - startUtc) * 1000 - s.durationMs;
    return startUtc >= 1767225600 && endUtc >= startUtc &&
           std::llabs(errorMs) <= 2000 && s.durationMs >= 60000 && s.durationMs <= 60125 &&
           s.expectedSamples == 480 && s.samples == s.expectedSamples &&
           s.invalidSamples == 0 && s.maxSampleGapMs <= 250 &&
           std::isfinite(s.laeq) && std::isfinite(s.maximum);
}

inline uint32_t retryDelayMs(uint32_t previousMs) {
    return previousMs >= 450000 ? 900000 : previousMs * 2;
}
