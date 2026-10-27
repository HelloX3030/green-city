#pragma once
#include <cmath>
#include <cstdint>

struct NoiseSummary {
    uint32_t durationMs;
    uint32_t samples;
    uint32_t invalidSamples;
    uint32_t expectedSamples;
    uint32_t maxSampleGapMs;
    uint32_t events;
    double laeq;
    float maximum;
};

// Energy average of equally scheduled sound-level samples. Timing/coverage
// diagnostics accompany every result so gaps are never silently zero-filled.
class NoiseAggregator {
public:
    static constexpr uint32_t WINDOW_MS = 60000;
    static constexpr uint32_t SAMPLE_MS = 125;

    explicit NoiseAggregator(float eventThreshold = 80.0f, float rearmThreshold = 75.0f)
        : eventThreshold_(eventThreshold), rearmThreshold_(rearmThreshold) {}

    void begin(uint32_t now) { windowStart_ = now; }

    bool closeWindow(uint32_t now, NoiseSummary& result) {
        const uint32_t elapsed = now - windowStart_;
        if (elapsed < WINDOW_MS) return false;
        result = {elapsed, samples_, invalid_, elapsed / SAMPLE_MS,
                  maxGap_, events_, samples_ ? 10.0 * std::log10(energy_ / samples_) : NAN,
                  samples_ ? maximum_ : NAN};
        windowStart_ = now;
        energy_ = 0;
        samples_ = invalid_ = events_ = maxGap_ = 0;
        maximum_ = 0;
        // Preserve event state across windows: a sustained event counts once.
        return true;
    }

    void add(uint32_t now, float decibels, bool valid) {
        if (havePrevious_) {
            const uint32_t gap = now - previousSample_;
            if (gap > maxGap_) maxGap_ = gap;
        }
        previousSample_ = now;
        havePrevious_ = true;
        if (!valid || !std::isfinite(decibels) || decibels < 30 || decibels > 130) {
            ++invalid_;
            return;
        }
        energy_ += std::pow(10.0, decibels / 10.0);
        ++samples_;
        if (decibels > maximum_) maximum_ = decibels;
        if (!eventActive_ && decibels >= eventThreshold_) {
            ++events_;
            eventActive_ = true;
        } else if (eventActive_ && decibels <= rearmThreshold_) {
            eventActive_ = false;
        }
    }

private:
    uint32_t windowStart_ = 0, previousSample_ = 0;
    uint32_t samples_ = 0, invalid_ = 0, events_ = 0, maxGap_ = 0;
    double energy_ = 0;
    float maximum_ = 0;
    float eventThreshold_, rearmThreshold_;
    bool eventActive_ = false, havePrevious_ = false;
};
