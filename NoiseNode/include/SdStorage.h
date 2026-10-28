#pragma once
#include "NoiseAggregator.h"
#include "TelemetryRecord.h"
#include <time.h>

void beginSdStorage();
void logSdSample(uint32_t millivolts, bool valid);
// Asynchronous: returns true if queued for the storage worker, not yet durable.
bool logSdSummary(const NoiseSummary& summary, time_t startUtc, time_t endUtc);
// Called only by the cloud worker; SD mutex is never held during HTTPS.
size_t peekSdUploads(CloudMeasurement* measurements, size_t capacity);
bool acknowledgeSdUpload(const CloudMeasurement& measurement);

// Queue a readback check for the storage worker (never blocks sampling).
void requestSdVerification();
