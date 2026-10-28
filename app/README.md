# app

SvelteKit + MapLibre. One page: map, one bottom sheet (report, cluster card, sensor card, layers).

Look: CARTO Positron basemap, glass surfaces, one green for actions. Colours and icons per report type, sensor kind and layer live in `src/lib/api.ts`, the icon paths in `src/lib/icons.ts`. Sensors and clusters are DOM markers (`.pin` styles in `Map.svelte`), trees, bike rides and the bubble discs are map layers.

One radius: 100 m (`CLUSTER_RADIUS_M` in `api.ts`, `RADIUS_M` in the backend) is the only circle in the app, always in metres on the ground. The report circle is it, every bubble's disc is it (faint from zoom 15, the selected one with a line and the single reports from 15.5), and the join rule is it: a report goes to the nearest bubble whose anchor is within 100 m, else it opens a new one. Anchors are the oldest report and never move, so bubbles stay put. Bubble size is the weight (halves every 7 days), the number is the count, the card says how many are from this week.

Title pill top left opens a short about sheet (three steps, status colours). Layout: one bottom sheet on phones, a 400 px card bottom-left from 600 px width, the map centre shifts away from it.

Reporting: Melden flies to the phone's position at zoom 16 if it comes within 2 s, else zooms to 15 where you are. Below zoom 15 the circle is grey and Melden disabled. The bubble the report would join gets a green ring and the hint says so, computed in the app with the backend's rule. Position denied or outside Heilbronn shows a toast. The map padding waits for a running animation, setPadding would cancel it.

Identity: no login. The app keeps a random token in localStorage (`deviceToken` in `api.ts`) and sends it as `X-Device` on every request, the backend turns it into a user on first contact. Clearing site data means a new user. The server says per bubble how many reports are mine: those bubbles get a green dot and the card says "Du und N andere". Right after sending the card says "Gemeldet" instead.

Testing: `make e2e` runs `e2e/run.mjs`, headless Chrome through the flows in `scenarios.md` at three screen sizes with emulated positions. Screenshots in `e2e/out/`. Run it before a commit, add flows for new features.

Map limits: city limit from opendata.heilbronn.de (`src/lib/boundary.json`, rebuild with `make boundary`). Outside the city a grey wash. The screen centre (crosshair in report mode) is clamped to the city polygon (`transformConstrain`), the view itself is free. Min zoom is where the city fills the screen (recomputed on resize and sheet changes), max zoom 18.

Context layers (layers button top right): UBA road noise map 2022 (raster straight from datahub.uba.de), city tree register (`static/trees.json`, rebuild with `make trees`), bike rides of the last 7 days from the backend, all-time PM2.5 of the Heilbronn senseBox:bikes on a 25 m grid (`static/pm.json`, rebuild with `make pm`, ~5 min of openSenseMap requests). The grid shows as dots below zoom 14.5 and as the real cells above. Thumbnails in the layer list (`static/thumbs/`) are screenshots of the map with that layer on.

`make app` from the repo root. `make build` writes static files to `build/`.

Backend defaults to `http://<same host>:8000`. Override with `VITE_API_URL` in `.env`.
