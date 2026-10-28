# app

SvelteKit + MapLibre. One page: map, one bottom sheet (report, cluster card, sensor card, layers).

Look: CARTO Positron basemap, glass surfaces, one green for actions. Colours and icons per report type, sensor kind and layer live in `src/lib/api.ts`, the icon paths in `src/lib/icons.ts`. Sensors and clusters are DOM markers (`.pin` styles in `Map.svelte`), trees and bike rides are map layers.

Map limits: city limit from opendata.heilbronn.de (`src/lib/boundary.json`, rebuild with `make boundary`). Inside nothing shows, outside a grey wash fades in while you drag and the map springs back on release. Zoom 11 to 18, hard stop a little beyond the city bbox.

Context layers (layers button top right): UBA road noise map 2022 (raster straight from datahub.uba.de), city tree register (`static/trees.json`, rebuild with `make trees`), bike rides of the last 7 days from the backend, all-time PM2.5 of the Heilbronn senseBox:bikes on a 25 m grid (`static/pm.json`, rebuild with `make pm`, ~5 min of openSenseMap requests). The grid shows as dots below zoom 14.5 and as the real cells above. Thumbnails in the layer list (`static/thumbs/`) are screenshots of the map with that layer on.

`make app` from the repo root. `make build` writes static files to `build/`.

Backend defaults to `http://<same host>:8000`. Override with `VITE_API_URL` in `.env`.
