# backend

FastAPI + SQLite. Stores reports, returns clusters with a sensor-data verdict, proxies live sensors.

`make backend` from the repo root, or `uv run uvicorn main:app --reload --port 8000` here.

Every request may carry `X-Device: <32-64 chars>`, the app's random token. `users` is a row per person, `devices` maps tokens to users, created on first contact. Writes and `/reports/mine` need the header, `/clusters` uses it for `mine` if present. Old reports with an `author` id are mapped to a user on start, the id works as a token.

- `GET /me` – `{id, name, created_at, devices}` of the caller; `PATCH /me {name}` sets the name, the whole account in v00
- `POST /me/link` – `{code, expires_at}`, a 6-char code valid 10 min; `POST /me/claim {code}` on another device makes it this user, its reports so far come along (its old user row goes)
- `POST /reports` `{lat, lon, types: ["noise"|"heat"|"air"|"no_shade"|"other"], message?}`, needs `X-Device`
- `GET /reports?since=<iso>`
- `GET /reports/mine` – the caller's reports, newest first, needs `X-Device`
- `DELETE /reports/{id}` – withdraw one of the caller's reports, 404 for anyone else's
- `GET /clusters?days=14` – reports grouped: the oldest report anchors a cluster, later reports within 100 m of an anchor join it, anchors never move, `id` is the anchor's report id; `points` the member positions `[lat, lon, type]`; `count` raw, `people` distinct users, `recent` of the last 7 days, `mine` from the caller's device (0 without `X-Device`), `weight` with decay: one voice per person and day, halving every 7 days, `types` reports per type, ordered by voices so the first is the type most people name (a person naming two types in a day is one voice for each), `dominant` that first type, `status` confirmed / unconfirmed / no_data for it, `reason` one line in German
- `GET /sensors` – live values of the outdoor openSenseMap boxes in Heilbronn (incl. our NoiseNode) and UBA station DEBW015, cached 60 s
- `GET /sensors/{id}/history` – per phenomenon (temp, pm25, noise) `daily` since March and `hourly` of the last 7 days as sorted `[time, value]` lists, from history.json; 404 for an unknown id
- `GET /clusters/{id}/reports?days=14` – the reports of one bubble, the caller's own first (`mine`, needs `X-Device`), then the others, newest first; no author
- `GET /events` – server-sent events: `event: reports` whenever a report is sent, withdrawn or moves by a claim, `event: ping` every 25 s as a keep-alive. The app refetches on it and polls only once a minute while the stream is up.
- `GET /bikes` – GeoJSON lines of the senseBox:bike rides (grouptag heilbronn) in the last 7 days with mean PM2.5 per ride, cached 10 min. Points outside the city bbox are dropped.

Docs at http://localhost:8000/docs. `make test` runs the unit tests (clustering, db, api).

## Status rules (status.py)

Nearest sensor within 800 m, daily values since March 2026:

- heat: ≥ 5 days with max ≥ 30 °C → confirmed
- air: ≥ 10 days with PM2.5 mean > 15 µg/m³ (WHO) → confirmed; UBA station as fallback within 3 km. A bike ride within 150 m in the last 7 days adds its PM2.5 to the reason, and turns no_data into unconfirmed
- noise: NoiseNode days with mean LAeq ≥ 55 dB(A) → confirmed; no readings → no_data. Per phenomenon the channel that reported last is used, so the dead `Sound Level` channel loses against `LAeq_1min`
- no_shade: always no_data

## history.json

Daily statistics per box since March, from `api.opensensemap.org/statistics/descriptive` (1–2 min per call) and the UBA API, plus hourly ones of the last 7 days (fast). Temperature is the max per window, PM2.5 and noise the mean.
Committed as a snapshot so a fresh start has data. The server refreshes daily entries older than 24 h and hourly ones every hour in the background.
Rebuild by hand: `uv run python history.py`.
