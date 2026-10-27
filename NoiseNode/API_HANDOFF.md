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

## Current measurement meaning and limitations

The cloud channel currently contains an **instantaneous prototype sound-level
reading**, not a minute LAeq. Firmware samples every 125 ms but uploads only
**one valid reading per boot**, after NTP obtains UTC. A reset starts another
one-shot upload. Failed uploads retain that reading in RAM for retry; a power
cycle loses unsent data. This is not yet a continuous cloud feed.

Local Serial output includes approximate energy-based minute LAeq, maximum
sampled level, distinct-event count and sampling diagnostics. Those summaries
are not uploaded yet. They will require separate registered sensor channels
and periodic transmission. See README.md for calculation and coverage details.

The complete measurement system has not been reference-calibrated. Readings
are unsuitable for certified or legally enforceable noise assessments. No
intelligible audio is recorded or transmitted. The map's outdoor label is
station metadata, not evidence that this initial home test was outdoors.

Station upload tokens and Wi-Fi credentials are local secrets and are not
needed by dashboard developers. They remain outside tracked source files.
