# RegenCheck Heilbronn
**Topic:** Water | **Expert lens:** senior urban hydrologist / stormwater & sponge-city engineer (municipal SRRM projects, LUBW data, citizen-science sensors)

## The question
How much rain actually falls on *my* street in Heilbronn, how often does it reach heavy-rain (Starkregen) thresholds, and where does the water pool when it does?

## Why it matters for Heilbronn
- Heavy rain is the water risk with the shortest warning time. BW funds municipal Starkregenrisikomanagement (70 %), but hazard maps are model output nobody validates with observations; residents get no street-level answer to "did it rain hard here?"
- Benefits: residents (cellars, underpasses, allotments), schools with senseBoxes, Tiefbauamt/Entwässerung (validation points), fire brigade (post-event totals).
- City hall gets a free rain-event catalogue since 2016, a crowd-validated "water pooled here" layer to hold against its hazard maps, and a dashboard tile running on public APIs at zero cost.

## What we build (MVP for Thursday's demo)
- **Live tile "Rain in the last 2 h"**: DWD RADOLAN 5-min radar (1 km grid) via Bright Sky, summed per Stadtteil polygon, coloured by DWD warning thresholds (15/25/40 mm·h⁻¹; 20/35/60 mm·6 h⁻¹). Leaflet map + animated frames.
- **Event catalogue 2016-2026**: hourly DWD station data (Heilbronn/Neckar, id 15547) -> list of all hours/6-h windows above thresholds, per year, per season; compare to the SRGK scenario intensities (36 / 48 / 128 mm·h⁻¹) to show how close reality has come.
- **Street-level check**: click an address -> rain last 2 h / 24 h, biggest event in 10 years, nearest receiving stream (OSM: Böllinger Bach, Lein, Schozach, Sulm, Neckar).
- **"Wasser stand hier" citizen layer**: one-tap report (location, depth category, photo optional) stored as GeoJSON; shown as pins; exportable CSV for the city.
- **senseBox rain gauge**: ToF distance sensor over a straight-walled container = water column in mm, every 5 min to openSenseMap; tile shows "radar pixel X mm vs our gauge Y mm".

## Data & sources
| source | what it gives us | URL | verified |
|---|---|---|---|
| Bright Sky `/radar` (DWD RADOLAN RV) | 5-min precipitation grid, 1 km, last 2 h (+ nowcast frames) | https://api.brightsky.dev/radar?lat=49.14&lon=9.22&distance=5000 | yes (25 frames, 11×11 grid returned today; nowcast: partly) |
| Bright Sky `/weather` | hourly DWD obs incl. precipitation since 2016-10 for station Heilbronn/Neckar (dwd 15547) | https://api.brightsky.dev/weather?lat=49.14&lon=9.22&date=2016-10-01 | yes |
| Open-Meteo | hourly precipitation forecast + probability, 16 days | https://api.open-meteo.com/v1/forecast?latitude=49.14&longitude=9.22&hourly=precipitation,precipitation_probability | yes |
| PEGELONLINE (WSV) | Neckar level, 15-min, gauge "Heilbronn Schleuse UP" (uuid f77df170-…), also Lauffen, Horkheim | https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/HEILBRONN%20SCHLEUSE%20UP/W/measurements.json?start=P10D | yes (impounded reach: level barely moves, use as context only) |
| LUBW HVZ | flood forecasts/warnings Neckar incl. Lauffen, Rockenau | https://www.hvz.baden-wuerttemberg.de/ | partly (site yes, no public JSON API found) |
| OSM via Overpass | Stadtteil polygons, waterways, culverts, drinking-water points | https://overpass-turbo.eu/ | partly (Overpass unreachable from my sandbox; tags are standard) |
| opendata.heilbronn.de | drinking-water hardness/analysis CSV 2019-20; public water supply since 2010 (Statistik BW table) | https://opendata.heilbronn.de/dataset/wasserversorgung-und-wasserqualit%C3%A4t-der-stadt-heilbronn ; https://www.statistik-bw.de/Umwelt/Wasser/22025035.tab?R=KR121&form=csv | yes (dataset pages); CSV content not opened |
| Stadt Heilbronn Starkregengefahrenkarte | official hazard map to compare citizen reports against | not found online | **no** – ask organisers / Tiefbauamt whether a WMS or PDF exists |
| openSenseMap | storage + API for our senseBox gauge | https://docs.opensensemap.org/ | yes (documented) |

## Technical plan
Stack: Python (requests, pandas, shapely) fetch/aggregate job -> static GeoJSON; frontend as a Green City Dashboard tile (React/Leaflet, fork https://github.com/reedu-reengineering-education/Green-City-Dashboard) or plain Vite+Leaflet; citizen reports via tiny FastAPI/Supabase endpoint (GitHub-hosted JSON for the demo); senseBox MCU-S2 + ToF, Arduino sketch posting to openSenseMap.

- **Tue evening**: pull radar + 10-year station CSV, Stadtteil polygons via Overpass Turbo, agree thresholds; hardware pair wires ToF gauge.
- **Wed**: map tile (radar overlay, polygon sums, address search); catalogue charts; report form + storage; gauge logging live, calibrate by pouring known mm; non-coders draft pitch, test UX with people at OpenSpace.
- **Thu morning**: polish, embed in dashboard fork, rehearse, record 30-s backup capture.

Roles (4-6): 1 data/backend, 1-2 frontend/map, 1 hardware, 1 UX/pitch (non-coder: threshold explainer, form wording, slides), 1 QA & outreach (ask Tiefbauamt/fire brigade for the hazard map).

## Demo & pitch
60-s pitch: "Heavy rain is Heilbronn's fastest water risk, yet no resident can see what fell on their street. RegenCheck turns the DWD radar into a street-level rain meter, lists every heavy-rain hour since 2016, and lets citizens pin where water actually pooled — the validation data the city's hazard maps are missing. Our senseBox gauge proves the radar numbers. It runs on free public APIs and can go live on greencity.hn tomorrow."
On screen: animated radar -> click Böckingen -> "12 mm in 2 h, 4th heaviest since 2016" -> exceedance timeline -> citizen pins near Böllinger Bach -> live gauge next to radar value. Pour water into the gauge on stage: tile updates.
Criteria: Teamwork (roles incl. hardware + non-coders); Innovation (radar + citizen validation + ground truth, not a weather widget); Functionality (live APIs, working sensor); Impact & Feasibility (public data, SRRM-relevant, continuable by city/schools); UX (one question, one click); Presentation (live pour).

## Risks & fallbacks
- Radar API outage -> cached frames; Open-Meteo as substitute.
- Dry demo days -> replay mode with stored frames of a past event (Bright Sky `date` param).
- Overpass slow -> download polygons once, commit GeoJSON.
- ToF noise -> average 20 readings, narrow container; fallback manual reading.
- No official hazard map -> ship without it; citizen layer still valuable.

## Stretch goals
- Nowcast alert when a Stadtteil will exceed 15 mm/h within 60 min.
- Groundwater levels from LUBW UDO next to rain.
- Soil-moisture sensor on a second senseBox (infiltration vs runoff).
- Rain-barrel/cistern calculator per roof area from the event catalogue (water-use angle).

## Why this doesn't overlap with other teams
No team touches rain, radar, Neckar or flooding. Artemis explains heat islands (sealing from a thermal angle); we use no sealing data at all, only rain and where it drains. Bike teams use senseBox:bike mobility data; we use DWD/WSV APIs and a self-built rain gauge.
