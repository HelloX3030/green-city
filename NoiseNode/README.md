# QuietNode

senseBox MCU-S2 / ESP32-S2, Arduino and PlatformIO. DFRobot SEN0232 signal →
**IO6 / GPIO6 (A6)**, + → 3.3V, − → GND. Onboard WS2812: GPIO1.
The preserved sensor conversion is `dBA = analogReadMilliVolts(A6) / 20.0`.
Serial runs at **115200 baud**. No audio is recorded or transmitted.

## Minute statistics and display

Firmware schedules 125 ms readings using `millis()` without catch-up samples.
The LED uses an exponential smoother (alpha 0.25) independently of statistics:
green below 50, yellow from 50 to below 65, orange from 65 through 80, red above
80 dBA. Invalid readings turn the LED off. These are illustrative categories.

Every approximately 60 seconds, Serial prints:

- `approx_LAeq`: `10 * log10(mean(10^(Li/10)))` over valid scheduled readings.
- `sampled_Lmax`: highest valid sampled level, not certified acoustic peak.
- `events`: distinct onsets at or above 80 dBA, rearmed at or below 75 dBA.
  A sustained event crossing a window boundary is counted only at its onset.
- Valid/invalid/expected sample counts, actual duration, maximum sampling gap,
  and uptime in milliseconds. Empty windows report unavailable values.

Event thresholds are constants in `src/main.cpp`. Invalid readings do not
rearm the detector. Sensor readings outside 30–130 dBA are excluded.

The sample energy average approximates equally spaced readings. Local results
with gaps describe only available samples. The uploader rejects incomplete
windows instead of pretending they represent a full minute. No missing data
is replaced with zero. This complete system has not been reference-calibrated
and is unsuitable for certified or legally enforceable noise assessments.

## Configure

Copy `include/quietnode_config.example.h` to `include/quietnode_config.h` if
the local file does not already exist. The latter is gitignored. Fill in:

- Wi-Fi SSID/password: 2.4 GHz, without a browser login.
- Station ID and device upload access token (not account password or JWT).
- Three separate sensor IDs on your custom station:

| Local config key | openSenseMap title | Unit |
|---|---|---|
| `QUIETNODE_LAEQ_SENSOR_ID` | `LAeq_1min` | dB(A) |
| `QUIETNODE_LMAX_SENSOR_ID` | `Lmax_1min` | dB(A) |
| `QUIETNODE_EVENTS_SENSOR_ID` | `EventCount_1min` | count |

Use type SEN0232 for each. Add them through your logged-in openSenseMap
account; the device token cannot change station metadata. Keep the original
Sound Level channel as the initial instantaneous test; the periodic firmware
does not write minute statistics into it. `QUIETNODE_SENSOR_ID` is retained
in local configuration only for reference. Missing Wi-Fi/configuration disables
the uploader; local readings and statistics still work.

## Build and run

```sh
pio run
pio device list
pio run --target upload --upload-port /dev/ttyACM0
pio device monitor --port /dev/ttyACM0 --baud 115200
```

Use the detected USB runtime port. The uploader starts only with all three
valid, distinct sensor IDs. NTP obtains UTC. Each uploaded timestamp marks
the **end** of its measurement window. A window is eligible only when:

- UTC is available at both boundaries and advances consistently (within 2 s).
- Its duration is 60000–60125 ms with 480 valid out of 480 expected samples.
- It has no invalid samples and no sample gap above 250 ms.

The first boot window is normally skipped while NTP synchronises; expect the
first upload after roughly two minutes. A clock jump or incomplete window is
logged and omitted. No false historical timestamps are generated.

## Buffering and recovery

HTTPS runs in a separate FreeRTOS task with 10 s connection/read/handshake
timeouts. Sampling shares the single CPU with networking, so exact cadence
is not guaranteed; minute coverage checks detect incomplete sampling.

A FIFO holds **30 minute summaries** in RAM, including the oldest during its
upload attempt. Only 2xx responses remove items. Full queues reject the newest
window with an explicit log, preserving the existing backlog. Power loss or
reset loses queued data; persistent storage is not implemented.

Each request contains all three measurements with the original end timestamp.
Normal operation sends one request per complete minute. A backlog drains at
most once per 5 s after successful requests. Failure retry delays increase from
60 s to 120, 240, 480 and 900 s, capped at 900 s. A `Retry-After` header can
extend the delay (seconds or HTTP date, capped at seven days). Wi-Fi reconnects
automatically, with explicit retry attempts every 30 s. Status 401/403/404
logs a configuration hint; failures retain the FIFO's oldest window.

A lost response can cause a retry of an already accepted timestamp. Consumers
should identify records by sensor ID plus timestamp rather than summing
repeated fetches. Before-NTP windows, incomplete windows, resets and FIFO
overflow can all create gaps. See Serial diagnostics; never interpret a gap
as silence or zero events.

## API and security

Verified against https://docs.opensensemap.org/ and the official server:
https://github.com/sensebox/openSenseMap-API/blob/master/packages/api/lib/controllers/measurementsController.js.

`POST https://api.opensensemap.org/boxes/<boxId>/data`, JSON array of
`{sensor, value, createdAt}` objects. `Authorization` contains the raw station
token, without a Bearer prefix. IDs are 24 lowercase hexadecimal characters.
The documented request maximum is 2500 values; our payload contains three.
The documentation does not establish a numerical production upload-frequency
limit, so the retry policy is a client choice, not a claimed API quota.

TLS verifies the server with the included ISRG Root X1 trust anchor; the live
chain was checked on 2026-10-27. Never use `setInsecure()`. The root may need
updating if the service changes certificate authorities. No secrets are logged
or committed. See `API_HANDOFF.md` for public endpoints and channel status.

## Native checks

```sh
g++ -std=c++11 -Wall -Wextra -Werror -I include test/native/noise_aggregator_test.cpp -o /tmp/quietnode-aggregator-test
/tmp/quietnode-aggregator-test
g++ -std=c++11 -Wall -Wextra -Werror -I include test/native/upload_policy_test.cpp -o /tmp/quietnode-upload-test
/tmp/quietnode-upload-test
```
