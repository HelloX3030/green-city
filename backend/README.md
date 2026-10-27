# backend

FastAPI + SQLite. Stores reports, returns clusters.

```
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- `POST /reports` `{lat, lon, types: ["noise"|"heat"|"air"|"no_shade"|"other"], message?, author?}`
- `GET /reports?since=<iso>`
- `GET /clusters?days=14` – reports within 150 m grouped, with count and type counts

Docs at http://localhost:8000/docs
