#pragma once
#include "NoiseAggregator.h"
#include "TelemetryRecord.h"
#include <time.h>

// Periodic HTTPS uploads run separately from sensor sampling.
void beginCloudUpload();
// Minute diagnostics go to SD; complete windows use a durable SD outbox or RAM fallback.
// A true result means queued for processing, not necessarily flushed yet.
bool offerCloudSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc);

// Storage failure fallback: bounded RAM queue; may be lost on reset.
bool queueRamCloudMeasurement(const CloudMeasurement& measurement);

// Serial maintenance controls, used for outage/replay checks without changing Wi-Fi.
void setCloudUploadPaused(bool paused);
