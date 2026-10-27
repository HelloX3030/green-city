#pragma once
#include "NoiseAggregator.h"
#include <time.h>

// Periodic HTTPS uploads run separately from sensor sampling.
void beginCloudUpload();
// Complete minute windows are retained in a bounded RAM FIFO until accepted.
// Returns false if disabled, invalid/incomplete, UTC unavailable, or FIFO full.
bool offerCloudSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc);
