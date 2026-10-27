# QuietNode public data handoff

First hardware upload verified on **28 October 2026, 00:19:15 CET**
(`2026-10-27T23:19:15.000Z`). The ESP32 uploaded directly over Wi-Fi/HTTPS;
the latest-value and historical APIs both returned **66.8 dB(A)**.

- Station: NoiseNode
- Public map: https://opensensemap.org/explore/6ae0d7aa4bc0370008dba0f7
- senseBoxID: `6ae0d7aa4bc0370008dba0f7`
- Sound Level sensorID: `6ae0d7aa4bc0370008dba0f8`
- Unit: `dB(A)`; hardware: DFRobot SEN0232 on senseBox MCU-S2, GPIO6.

## Read data

No credentials are needed for these public GET requests.

Latest reading:

```sh
curl 'https://api.opensensemap.org/boxes/6ae0d7aa4bc0370008dba0f7/sensors/6ae0d7aa4bc0370008dba0f8'
```

The response contains metadata and a `lastMeasurement` object. Verified excerpt:

```json
{"lastMeasurement":{"createdAt":"2026-10-27T23:19:15.000Z","value":"66.8"}}
```

Historical query (verified to return the same reading):

```sh
curl 'https://api.opensensemap.org/boxes/6ae0d7aa4bc0370008dba0f7/data/6ae0d7aa4bc0370008dba0f8?from-date=2026-10-27T23%3A00%3A00Z&to-date=2026-10-28T00%3A00%3A00Z&format=json&download=false'
```

This returns an array containing `createdAt`, `value` and `location`. Values
are strings; parse them as numbers. Timestamps are UTC. Display local times
using an explicit timezone such as Europe/Berlin. A missing or stale reading
means no new measurement is available; never convert that to zero.

API reference: https://docs.opensensemap.org/#api-Measurements-getData

## Initial channel meaning and limitations

The original cloud channel contains an **instantaneous prototype sound-level
reading**, not a minute LAeq. Its first-upload firmware sent one value per
boot. The new periodic firmware uses separate minute channels and leaves this
original channel untouched. Do not treat its last value as a live feed.

## Periodic channels (live and hardware-verified)

| Channel | Sensor ID | Unit | Meaning |
|---|---|---|---|
| LAeq_1min | `6ae1349f00df8f00089ecc14` | dB(A) | Approximate energy average of a complete minute of 125 ms samples |
| Lmax_1min | `6ae1349f00df8f00089ecc16` | dB(A) | Maximum sampled level in that minute; not certified peak SPL |
| EventCount_1min | `6ae1349f00df8f00089ecc18` | count | Onsets >=80 dBA, rearmed <=75 dBA, counted once across boundaries |

Use the latest/history endpoint patterns above with the IDs in this table. All three readings in
a request share a UTC timestamp labelling the end of the window. Normal cadence
is one upload per minute after NTP establishes time. Only complete windows with
480 valid samples are published. The first minute after boot is usually omitted.
A gap means unavailable data, not zero. Failed uploads retain up to 30 windows
in RAM; overflow drops the newest and resets lose the queue. Consumers should
identify records using sensor ID plus timestamp. Sampling diagnostics remain
on Serial. See README.md for exact eligibility rules and recovery policy.

The periodic firmware was flashed and verified on 28 October 2026. Two
consecutive windows were accepted with HTTP 201 and retrieved from the public
history endpoint for all three channels:

| Window end (UTC) | LAeq_1min | Lmax_1min | EventCount_1min |
|---|---|---|---|
| 2026-10-27T23:34:46Z | 63.9 | 66.9 | 0 |
| 2026-10-27T23:35:46Z | 66.3 | 89.6 | 1 |

These correspond to 00:34:46 and 00:35:46 CET on 28 October. Both windows
contained 480/480 valid samples, with no invalid readings; maximum sample gaps
were 130 ms and 125 ms. The RAM queue returned to zero after each upload.
Normal periodic operation is verified. Prolonged outage/reconnection, queue
capacity exhaustion and overnight operation have not yet been hardware-tested.

Example live LAeq history query:

```sh
curl 'https://api.opensensemap.org/boxes/6ae0d7aa4bc0370008dba0f7/data/6ae1349f00df8f00089ecc14?format=json&download=false'
```

For Lmax and events, substitute their IDs from the table. The default history
query covers the last 48 hours. Use explicit UTC from-date/to-date parameters
for a fixed period, as in the earlier historical example.

The complete measurement system has not been reference-calibrated. Readings
are unsuitable for certified or legally enforceable noise assessments. No
intelligible audio is recorded or transmitted. The map's outdoor label is
station metadata, not evidence that this initial home test was outdoors.

Station upload tokens and Wi-Fi credentials are local secrets and are not
needed by dashboard developers. They remain outside tracked source files.
