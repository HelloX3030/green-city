# backend

FastAPI + SQLite. Stores reports, returns clusters with a sensor-data verdict, proxies live sensors.

`make backend` from the repo root, or `uv run uvicorn main:app --reload --port 8000` here.

- `POST /reports` `{lat, lon, types: ["noise"|"heat"|"air"|"no_shade"|"other"], message?, author?}`
- `GET /reports?since=<iso>`
- `GET /clusters?days=14` – reports within 150 m grouped; `count` raw, `weight` with decay (a report halves every 7 days), `dominant` type by weight, `status` confirmed / unconfirmed / no_data for it, `reason` one line in German
- `GET /sensors` – live values of the outdoor openSenseMap boxes in Heilbronn (incl. our NoiseNode) and UBA station DEBW015, cached 60 s
- `GET /bikes` – GeoJSON lines of the senseBox:bike rides (grouptag heilbronn) in the last 7 days with mean PM2.5 per ride, cached 10 min

Docs at http://localhost:8000/docs

## Status rules (status.py)

Nearest sensor within 800 m, daily values since March 2026:

- heat: ≥ 5 days with max ≥ 30 °C → confirmed
- air: ≥ 10 days with PM2.5 mean > 15 µg/m³ (WHO) → confirmed; UBA station as fallback within 3 km. A bike ride within 150 m in the last 7 days adds its PM2.5 to the reason, and turns no_data into unconfirmed
- noise: NoiseNode days with mean ≥ 55 dB(A) → confirmed; no readings → no_data
- no_shade: always no_data

## history.json

Daily statistics per box, from `api.opensensemap.org/statistics/descriptive` (1–2 min per call) and the UBA API.
Committed as a snapshot so a fresh start has data. The server refreshes entries older than 24 h in the background.
Rebuild by hand: `uv run python history.py`.
