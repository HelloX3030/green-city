#include "NoiseAggregator.h"
#include <cassert>
#include <cmath>
#include <cstdio>

int main() {
    NoiseSummary result;
    NoiseAggregator energy;
    energy.begin(0);
    energy.add(0, 40, true);
    energy.add(125, 60, true);
    assert(!energy.closeWindow(59999, result));
    assert(energy.closeWindow(60000, result));
    assert(std::abs(result.laeq - 57.03291378) < 0.00001);
    assert(result.maximum == 60 && result.samples == 2);
    assert(result.expectedSamples == 480); // Missing samples remain visible.

    NoiseAggregator events;
    events.begin(0);
    events.add(0, 80, true);
    events.add(125, 90, true);
    events.add(250, 76, true); // Above rearm threshold: same event.
    assert(events.closeWindow(60000, result));
    assert(result.events == 1);
    events.add(60000, 90, true); // Sustained event crosses the window boundary.
    events.add(60125, 75, true);
    events.add(60250, 80, true);
    assert(events.closeWindow(120000, result));
    assert(result.events == 1);
    assert(result.maxSampleGapMs == 59750);

    NoiseAggregator invalid;
    invalid.begin(0);
    invalid.add(0, 0, false);
    invalid.add(125, NAN, true);
    assert(invalid.closeWindow(60000, result));
    assert(result.samples == 0 && result.invalidSamples == 2);
    assert(std::isnan(result.laeq) && std::isnan(result.maximum));
    invalid.add(60125, 50, true);
    assert(invalid.closeWindow(120000, result));
    assert(result.samples == 1 && result.invalidSamples == 0);
    assert(std::abs(result.laeq - 50) < 0.00001);

    NoiseAggregator rollover;
    rollover.begin(UINT32_MAX - 30000);
    rollover.add(UINT32_MAX - 100, 50, true);
    rollover.add(24, 50, true);
    assert(rollover.closeWindow(29999, result));
    assert(result.durationMs == 60000 && result.maxSampleGapMs == 125);
    std::puts("NoiseAggregator checks passed");
}
