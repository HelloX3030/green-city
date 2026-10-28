#pragma once
#include "NoiseAggregator.h"
#include "TelemetryRecord.h"
#include <time.h>

// Periodic HTTPS uploads run separately from sensor sampling.
void beginCloudUpload();
// True when Wi-Fi, station, token and three distinct minute sensor IDs are configured.
bool cloudUploadConfigured();
// Minute diagnostics use SD only in local-only builds; cloud uploads use the RAM queue.
// A true result means queued for processing, not necessarily flushed yet.
bool offerCloudSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc);

// Storage failure fallback: bounded RAM queue; may be lost on reset.
bool queueRamCloudMeasurement(const CloudMeasurement& measurement);

// Serial maintenance controls, used for outage/replay checks without changing Wi-Fi.
void setCloudUploadPaused(bool paused);
