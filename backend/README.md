# backend

FastAPI + SQLite. Stores reports, returns clusters.

`make backend` from the repo root, or `uv run uvicorn main:app --reload --port 8000` here.

- `POST /reports` `{lat, lon, types: ["noise"|"heat"|"air"|"no_shade"|"other"], message?, author?}`
- `GET /reports?since=<iso>`
- `GET /clusters?days=14` – reports within 150 m grouped, with count and type counts

Docs at http://localhost:8000/docs
