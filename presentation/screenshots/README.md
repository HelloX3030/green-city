# Screenshots of the app for the slides

Phone size (390×844 at 3×), taken by `shoot.mjs` from a running dev server and backend
(`APP=http://localhost:5173 API=http://localhost:8000 node presentation/screenshots/shoot.mjs [name]`).
Taken from a copy of the local database with the test texts removed.

| File | Shows | Fits |
|---|---|---|
| `01-home.png` | map of the Innenstadt with bubbles, sensor pins, the NoiseNode, home sheet | any "the app" slide |
| `02-report-sheet.png`, `02b-report-sheet-filled.png` | Melden: the report sheet with all types, then filled in | slide 7 (replaces the old desktop shot) |
| `03-sent-card.png` | the answer card right after sending: status, reason, rank | slide 7, "the answer is the feature" |
| `04-sent-trash-hint.png` | a Müll report sent: "Sensor fehlt", reason "Kein Sensor misst Müll" | outlook: the same loop for anything a city can measure |
| `05-cluster-card.png` | the biggest bubble: reports, people, chips, status | any |
| `06-no-sensor-card.png` | "Sensor fehlt" with "Platz 1 von N Stellen ohne Sensor" | slide 8 |
| `06b-confirmed-card.png` | a bubble confirmed by the NoiseNode | slide 9 |
| `07-filter-sheet.png`, `07b-filter-map.png` | the Ebenen sheet with the filter "Nur Bestätigte" set, then the map with only those bubbles | filter / ranking slide |
| `08-layer-noise.png` | the city's noise map 2022 as a layer | slide 4 |
| `09-noisenode-7d.png`, `09b-noisenode-all.png`, `09c-noisenode-24h.png` | the NoiseNode sensor card with its chart | slide 9 ("graph of measurements") |
| `10-about.png` | the about sheet: name, three steps, statuses | slide 10 |
| `11-map-wide.png` | 1600×900 map overview, for a background | title or closing |
| `12-logo-leaf.png` | the leaf logo, transparent, 1024 px | slide 10 instead of "Heilbronn Meldet" |

The product name on slide 10 is "Sag's Heilbronn", as in the app. The NoiseNode chart before 28 Oct is the
demo week seeded by `backend/seed_noise.py`.
