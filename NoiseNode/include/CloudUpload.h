#pragma once

// Starts a network worker. Captures one valid, UTC-timestamped measurement
// per boot, retries failures, then stops uploading after success.
void beginCloudUpload();
void offerCloudMeasurement(float decibels);
