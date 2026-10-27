# QuietNode: first openSenseMap upload

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
Without configuration the sensor and LED still work; cloud upload is disabled.

## Build and demonstrate

From this folder:

```sh
pio run
pio device list
pio run --target upload --upload-port /dev/ttyACM0
pio device monitor --port /dev/ttyACM0 --baud 115200
```

Replace `/dev/ttyACM0` with the detected USB serial device.

The firmware connects to Wi-Fi, synchronises UTC using NTP and captures the
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
The main loop schedules the existing 250 ms readings using `millis()` and
yields between readings. Wi-Fi and TLS still share the ESP32-S2's CPU, so
this is not a guarantee of exact sampling intervals. No statistics assume
uniform sampling in this first upload test.

Next steps after a confirmed real upload: 125 ms acquisition, LED smoothing,
minute-level energy-based LAeq / sampled maximum / distinct event counts,
and bounded buffering for periodic uploads. No audio is recorded or sent.
