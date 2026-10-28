# app

SvelteKit + MapLibre. One page: map, one bottom sheet (report, cluster card, sensor card, layers).

Look: CARTO Positron basemap, glass surfaces, one green for actions. Colours and icons per report type, sensor kind and layer live in `src/lib/api.ts`, the icon paths in `src/lib/icons.ts`. Sensors and clusters are DOM markers (`.pin` styles in `Map.svelte`), trees, bike rides and the 100 m discs of the bubbles are map layers. A bubble's disc is faint from zoom 15 up, the selected one has a line and shows the single reports from 15.5.

Title pill top left opens a short about sheet (three steps, status colours). Layout: one bottom sheet on phones, a 400 px card bottom-left from 600 px width, the map centre shifts away from it.

Reporting: Melden flies to the phone's position at zoom 16 if it comes within 2 s, else zooms to 15 where you are. The circle is the 100 m cluster radius on the ground (`CLUSTER_RADIUS_M`, same as the backend), it grows with the zoom. Below zoom 15 the circle is grey and Melden disabled. The bubble a report would join (nearest within 100 m, the backend rule) gets a green ring and the hint says so. Position denied or outside Heilbronn shows a toast. The map padding waits for a running animation, setPadding would cancel it.

Testing: `make e2e` runs `e2e/run.mjs`, headless Chrome through the flows in `scenarios.md` at three screen sizes with emulated positions. Screenshots in `e2e/out/`. Run it before a commit, add flows for new features.

Map limits: city limit from opendata.heilbronn.de (`src/lib/boundary.json`, rebuild with `make boundary`). Outside the city a grey wash. The screen centre (crosshair in report mode) is clamped to the city polygon (`transformConstrain`), the view itself is free. Min zoom is where the city fills the screen (recomputed on resize and sheet changes), max zoom 18.

Context layers (layers button top right): UBA road noise map 2022 (raster straight from datahub.uba.de), city tree register (`static/trees.json`, rebuild with `make trees`), bike rides of the last 7 days from the backend, all-time PM2.5 of the Heilbronn senseBox:bikes on a 25 m grid (`static/pm.json`, rebuild with `make pm`, ~5 min of openSenseMap requests). The grid shows as dots below zoom 14.5 and as the real cells above. Thumbnails in the layer list (`static/thumbs/`) are screenshots of the map with that layer on.

`make app` from the repo root. `make build` writes static files to `build/`.

Backend defaults to `http://<same host>:8000`. Override with `VITE_API_URL` in `.env`.
