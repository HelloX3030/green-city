# app

SvelteKit + MapLibre. One page: map, report sheet, cluster card, sensor card.

Context layers (chips under the title): UBA road noise map 2022 (raster straight from datahub.uba.de), city tree register (`static/trees.json`, rebuild with `make trees`), bike rides of the last 7 days from the backend.

`make app` from the repo root. `make build` writes static files to `build/`.

Backend defaults to `http://<same host>:8000`. Override with `VITE_API_URL` in `.env`.
