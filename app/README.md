# app

SvelteKit + MapLibre. One page: map, one bottom sheet (report, cluster card, sensor card, layers).

Look: CARTO Positron basemap, glass surfaces, one green for actions. Colours and icons per report type, sensor kind and layer live in `src/lib/api.ts`, the icon paths in `src/lib/icons.ts`. Sensors and clusters are DOM markers (`.pin` styles in `Map.svelte`), trees and bike rides are map layers.

Context layers (layers button top right): UBA road noise map 2022 (raster straight from datahub.uba.de), city tree register (`static/trees.json`, rebuild with `make trees`), bike rides of the last 7 days from the backend.

`make app` from the repo root. `make build` writes static files to `build/`.

Backend defaults to `http://<same host>:8000`. Override with `VITE_API_URL` in `.env`.
