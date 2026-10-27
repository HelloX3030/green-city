# QuietNode: offline monitoring and first openSenseMap upload

This firmware reads the DFRobot SEN0232 on **IO6 / GPIO6 (A6)** and displays
its approximate A-weighted level using the onboard NeoPixel on GPIO1.
Signal → IO6, + → 3.3V, − → GND. Serial runs at **115200 baud**.
The existing conversion is `dBA = analogReadMilliVolts(A6) / 20.0`.

## Configure locally

1. Register a **custom station** at https://opensensemap.org/.
2. For this first test, add a channel named **Sound level**, unit **dB(A)**,
   sensor type **SEN0232**. This is an instantaneous prototype reading,
   not LAeq or a certified noise measurement. Use an appropriate public
   station location; do not publish precise residential coordinates.
3. Copy `include/quietnode_config.example.h` to `include/quietnode_config.h`
   if the local file does not already exist.
4. Fill in the Wi-Fi SSID/password, station ID, sensor ID and station upload
   access token. Both IDs must be 24 lowercase hexadecimal characters.
   Use a 2.4 GHz network without a captive portal. The token is the station's
   access token, not your account password or account JWT.

`quietnode_config.h` is gitignored. Do not paste secrets into tracked files.
Leave the Wi-Fi SSID empty to run offline. Sensor readings, LED feedback and
minute summaries work without a network; cloud upload is disabled.

## Build and demonstrate

From this folder:

```sh
pio run
pio device list
pio run --target upload --upload-port /dev/ttyACM0
pio device monitor --port /dev/ttyACM0 --baud 115200
```

Replace `/dev/ttyACM0` with the detected USB serial device.

When configured, the firmware connects to Wi-Fi, synchronises UTC using NTP and captures the
first in-range reading (30–130 dBA) after time is available. It uploads that
**one measurement per boot**, including its original UTC timestamp. A 2xx
response logs `One-shot test complete`; sampling and LED feedback continue.
Resetting the board starts a fresh one-shot test.

Failures retain the same measurement in a single RAM slot and retry no more
frequently than once per minute. A reset loses that slot. HTTP 401/403 usually
means a wrong token; 404 suggests a wrong station ID. Negative result codes
indicate a transport/TLS error. No credentials are printed to Serial.

Verify the value and timestamp using:

```text
https://api.opensensemap.org/boxes/YOUR_BOX_ID/sensors/YOUR_SENSOR_ID
```

Check `lastMeasurement` against the serial log. HTTP acceptance alone is not
a completed hardware demonstration: confirm the public reading too.

## API and implementation notes

Checked 2026-10-27 against https://docs.opensensemap.org/ and the official
server implementation at
https://github.com/sensebox/openSenseMap-API/blob/master/packages/api/lib/controllers/measurementsController.js.

The request is `POST https://api.opensensemap.org/boxes/<boxId>/data`, with
`Content-Type: application/json` and the raw station token in `Authorization`
(no `Bearer` prefix). The server implementation returns 201 when saved.

```json
[{"sensor":"YOUR_SENSOR_ID","value":"54.2","createdAt":"2026-10-27T16:00:00Z"}]
```

The documentation specifies at most 2500 values per request. It does not
publish a numerical upload-frequency limit; the inspected route/default
configuration did not establish a production limit either. The one-minute
retry spacing is our conservative policy, not a claimed API quota.

TLS verifies the server against the included **ISRG Root X1** certificate;
the live API certificate chain was verified against this root on 2026-10-27.
Never use `setInsecure()`. Trust anchors may need updating if the service
changes its certificate authority.

Networking runs in a separate FreeRTOS task with connection/read timeouts.
The main loop schedules 125 ms readings using `millis()` and yields between
readings. Wi-Fi and TLS still share the ESP32-S2's CPU, so this is not a
guarantee of exact sampling intervals. No audio is recorded or sent.

## Offline demonstration

No Wi-Fi is required. Every valid sample updates the LED through an exponential
smoother (alpha 0.25); the original readings feed the statistics and Serial.
The illustrative LED ranges are green below 50, yellow from 50 to below 65,
orange from 65 through 80, and red above 80 dBA. Invalid sensor voltages turn
the LED off and are excluded from statistics.

Every approximately 60 seconds, Serial prints a `[minute]` summary:

- `approx_LAeq`: `10 * log10(mean(10^(Li/10)))` over valid scheduled readings.
- `sampled_Lmax`: maximum valid sampled level, not certified acoustic peak.
- `events`: distinct onsets at or above 80 dBA; another event requires a
  reading at or below 75 dBA first. A sustained event crossing a window
  boundary is counted only in the window where it started. Invalid samples
  cannot rearm the event detector.
- Valid, invalid and expected sample counts, actual window duration, maximum
  gap between sampled readings, and uptime in milliseconds.

Thresholds are configurable using `EVENT_THRESHOLD_DBA` and `EVENT_REARM_DBA`
in `src/main.cpp`. LED smoothing never changes the event or LAeq input.

LAeq uses an equal-sample energy average, approximating uniform 125 ms
sampling. Compare valid/invalid/expected counts and maximum gaps before
interpreting a window. Gaps and invalid samples reduce coverage; they are
never replaced with zeros. The reported result is for available samples,
not an estimate of the missing interval. A long stall produces an extended
window with its actual duration, not invented empty minute records. Empty
windows report unavailable levels and events. These are prototype metrics.

Without NTP, windows have **uptime**, not trustworthy calendar timestamps.
Offline summaries are currently Serial-only; they are not queued for later
cloud upload. The network integration remains a one-shot instantaneous
reading test. After a real upload is verified, periodic minute uploads will
need separate sensor channels and a bounded queue.

Native calculation checks (from this folder):

```sh
g++ -std=c++11 -Wall -Wextra -Werror -I include test/native/noise_aggregator_test.cpp -o /tmp/quietnode-aggregator-test
/tmp/quietnode-aggregator-test
```
