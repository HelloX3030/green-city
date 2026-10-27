#include "UploadPolicy.h"
#include <cassert>
#include <cstdio>

int main() {
    const int64_t start = 1793145600;
    NoiseSummary s{60000, 480, 0, 480, 125, 3, 65.5, 80};
    assert(publishableWindow(s, start, start + 60));
    assert(!publishableWindow(s, 0, start + 60));
    assert(!publishableWindow(s, start, start + 120));
    assert(!publishableWindow(s, start, start - 60));
    s.samples = 479;
    assert(!publishableWindow(s, start, start + 60));
    s.samples = 480;
    s.invalidSamples = 1;
    assert(!publishableWindow(s, start, start + 60));
    s.invalidSamples = 0;
    s.maxSampleGapMs = 500;
    assert(!publishableWindow(s, start, start + 60));
    s.maxSampleGapMs = 125;
    s.laeq = NAN;
    assert(!publishableWindow(s, start, start + 60));
    uint32_t delay = 60000;
    const uint32_t expected[] = {120000, 240000, 480000, 900000, 900000};
    for (uint32_t value : expected) {
        delay = retryDelayMs(delay);
        assert(delay == value);
    }
    std::puts("Upload policy checks passed");
}
