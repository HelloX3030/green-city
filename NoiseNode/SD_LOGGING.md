# SD logging and persistent upload recovery

The onboard senseBox MCU-S2 slot is used with FAT32. No formatting is performed.
Only files beneath `/quietnode` are created or managed by this firmware.
SD power is active LOW on GPIO9; SPI uses SCK12, MISO13, MOSI11 and CS10,
following the installed senseBox board variant and the manufacturer's example:
https://docs.sensebox.de/docs/hardware/sd/.

## Files on the card

| Path | Contents |
|---|---|
| `/quietnode/raw/<boot-id>-000.csv` | One reading per second, including invalid sensor voltages |
| `/quietnode/minutes/<boot-id>.csv` | All minute statistics, timing/coverage diagnostics and upload eligibility |
| `/quietnode/outbox-<station-id>/<epoch>.q` | Checksummed minute awaiting cloud acceptance |

Boot IDs keep sessions separate. Raw files rotate at approximately 16 MiB.
Old raw/minute files are never automatically deleted. Copy them to your computer
by powering the board off, removing the card and using a card reader.

The sound sensor still runs at 125 ms and uses all valid readings for statistics.
Only the SD raw archive is downsampled to 1 Hz to reserve memory for TLS.

Raw CSV columns are `sequence,uptime_ms,utc,millivolts,dba,valid`. The voltage is
ADC millivolts, dBA retains two decimals, and valid is 0/1 for the sensor range.
UTC uses ISO 8601 with milliseconds; before the clock is set the field is empty.
Uptime and sequence remain usable without Wi-Fi. Sequence numbers restart in
each boot file; gaps reveal dropped logging records. No audio is stored.

Minute CSV stores uptime, UTC start/end as epoch seconds (0 when unavailable),
actual window duration, valid/invalid/expected counts, max gap, LAeq, maximum,
events and a 0/1 upload-eligibility flag. Empty-window floating values may be
`nan`; do not convert them to zero. Incomplete or un-timestamped windows remain
in this CSV even though they are not uploaded.

## Buffering and durability

A separate FreeRTOS worker drains a 8-sample RAM queue (~8 s at 1 Hz) into a 512-byte
write buffer. Writes are grouped and raw data is flushed every five seconds.
The sampling loop only enqueues records without waiting on SD I/O. File
stream buffers are limited to 512 bytes and the mount to two open files to
leave enough contiguous RAM for certificate-verified TLS. SD/network
workers share the MCU's CPU; sampling diagnostics still determine cloud
eligibility. Queue overflow is reported through `raw_dropped` and sequence gaps.

A separate 4-entry queue hands minute results to the worker. An enqueued
minute is **not durable yet**. The worker writes each eligible summary to a
32-byte versioned binary temporary record, flushes/closes it, verifies its CRC
by reopening it, then renames it to `.q`. `[sd] Minute durable` marks completion.
The uploader prefers up to three oldest ready SD records per request, using
each original window timestamp and the configured three sensor channels. It
spaces requests by at least 60 seconds, including when catching up a backlog.

Only after a cloud 2xx does it remove that ready record. Minute CSV remains as
an archive after acknowledgement. On boot, valid `.q` files are replayed and
complete `.tmp` records recovered. Truncated/corrupt records are retained under
`.bad-...` names with a diagnostic instead of being sent as valid measurements.
The native record checks cover round trips, every truncated length and
corruption at every byte position.

The outbox is capped at 1440 records (~24 h of complete minutes). If full or
unwritable, new eligible minutes use the existing bounded 30-window cloud RAM
queue; overflow is logged. A missing card or detected SD write error leaves
cloud operation available through that RAM queue. Reboot with a working card
to restore SD logging; hot insertion/removal is not supported. Already saved
outbox records are not erased merely because the card stops working.

A reset loses RAM-only records and the latest unflushed raw data (normally
up to five seconds, potentially more during a stalled card). FAT32 and SD
controllers cannot guarantee atomicity under abrupt power loss; filesystem
corruption is still possible. A cloud response lost before acknowledgement
can cause replay of the same sensor/timestamp; consumers should deduplicate
on those two fields. Do not change the configured metric channels while
records are pending. Outboxes are isolated by station ID.

## Serial maintenance commands

Send a newline after each command at 115200 baud:

- `sd verify`: flush, reopen and read back the current raw CSV; prints its path,
  size and last complete stored row. Reports minute file size and pending count.
- `cloud pause`: hold uploads while sampling and SD recording continue.
- `cloud resume`: resume uploads. Pause state is not retained across a reboot.
- `reboot`: restart the MCU. Buffered data may be lost; use after `sd verify`
  when deliberately testing recovery.

Every 30 seconds, `[sd]` diagnostics report storage health, raw sample count,
dropped samples, current file size and pending record count. No Wi-Fi password
or upload token is written to CSV or printed by these commands.

## Hardware validation

Verified on 28 October 2026 with the inserted **3781 MiB card**:

- Card mounted and raw CSV was flushed, reopened and read back on the MCU.
- A real minute ending `2026-10-27T23:48:25Z` was held on SD, recovered after
  an MCU reboot and a physical power cycle, then retrieved from all three
  public cloud histories: LAeq **69.7**, maximum **86.9**, events **7**.
- The initial larger logger exhausted TLS heap. The current compromise keeps
  acquisition/statistics at 125 ms, SD archive at 1 Hz, small queues, two open
  files maximum, and 512-byte file buffers. Recovery succeeded with certificate
  verification enabled; no insecure HTTPS fallback was used.
- Rapid catch-up requests triggered HTTP 429; the final uploader batches up
  to three windows per request and waits at least 60 seconds after each request.
- Every truncated record length and a flipped bit at every record byte were
  rejected by native CRC/format tests. Batched JSON parsing and buffer bounds
  were checked natively too.

Abrupt power-cut filesystem corruption, a physically full card, the 1440-file
outbox cap and an overnight endurance run have not been hardware-tested.

Final 1 Hz SD build: two fresh SD-backed windows ending **00:05:05Z** and
**00:06:05Z** on 28 October 2026 were accepted with HTTP 201. Both had
480/480 valid sensor samples, zero invalid readings and no dropped SD records;
maximum sample gaps were 130 ms and 125 ms. SD pending count returned to zero.
The second window was independently read from all public channels: LAeq 63.8,
maximum 66.3, events 0. Cloud task minimum free stack was 4280 bytes; SD worker
minimum observed free stack was 856 bytes. This is a short functional test,
not an overnight endurance result.
