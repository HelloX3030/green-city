# Pausenluft – the School-Run Air Clock
**Topic:** Air quality | **Expert lens:** atmospheric scientist / low-cost PM sensor network & exposure specialist

## The question
When during the day and week is the air at Heilbronn's schools actually dirty, how much can we trust the cheap sensors that say so, and what should a school do with that at 7:45 on a Tuesday?

## Why it matters for Heilbronn
- Children are the most PM-sensitive group and spend 6-8 h/day at school; the school run (07:00-08:15, 12:30-13:30) coincides with the traffic and heating peaks. The 15 senseBox:home stations (mostly at schools) have never been analysed as an *exposure* dataset – only shown as live dots.
- The city runs the schools: a "when to ventilate / when to hold the break" recommendation is something the Schulamt can act on tomorrow at zero hardware cost – a reusable Green Capital 2027 tile.
- Low-cost optical sensors (SPS30) over-read at high humidity (fog, autumn mornings) and drift; without calibration against the LUBW reference the network is PR, not evidence. A per-station *trust score* makes it something city hall can cite.

## What we build (MVP for Thursday)
- A Green City Dashboard tile/subpage "Pausenluft" with a map of all ~8 live PM stations (schools + Innenstadt + OpenSpace + Sternwarte) plus the two LUBW stations.
- Per station: a 7-day x 24-h "air clock" heatmap of PM2.5 (and PM10) built from ~2 M rows since March 2026, with school-day phases (arrival, breaks, pick-up) overlaid and WHO 24-h guideline (15 µg/m³ PM2.5) as the colour threshold.
- "Now vs typical": current reading vs the station's typical value for this weekday/hour → "cleaner / normal / worse than usual".
- Ventilation advisor ("Lüftungsampel"): green/amber/red for the next 3 hours from outdoor PM trend, NO2 at the traffic station, DWD pollen forecast for the region, wind from Bright Sky. One sentence a teacher understands.
- Calibration panel: hourly Innenstadt box vs LUBW DEBW015 (2.6 km apart, both urban background) → scatter, bias, humidity dependence, simple per-station RH correction, and a 0-100 trust score shown next to every station.
- Indoor vs outdoor: the Justinus-Kerner-Gymnasium box is flagged *indoor* – compare it with the outdoor Innenstadt box 2.4 km away to show infiltration and the effect of windows.

## Data & sources
| Source | What it gives us | URL | Verified |
|---|---|---|---|
| senseBox:home (atrai OGC API) | 2,012,544 rows, ~1-min PM1/2.5/4/10 (SPS30), T, RH, P; 14 boxes tagged GreenCityHN, 7-8 reporting today | https://api.atrai.bike/collections/osem_home_data_heilbronn/items?f=json&limit=1000&offset=N | yes (schema + box list) |
| openSenseMap API | box metadata (exposure indoor/outdoor, sensor type), live values, 5 more outdoor PM boxes in HN (Festplatz, THW, Neckargartach, KI-Pavillon, experimenta Forum) | https://api.opensensemap.org/boxes?grouptag=GreenCityHN | yes |
| UBA/LUBW reference, DEBW015 Heilbronn (station id 226) | hourly PM10, PM2.5, NO2, validated | https://luftdaten.umweltbundesamt.de/api/air-data/v3/measures/json?station=226&component=9&scope=2&date_from=...&date_to=...&time_from=1&time_to=24 | yes (data up to today 11:00) |
| UBA/LUBW DEBW152 Weinsberger Str.-Ost (id 353), traffic | hourly NO2 (41 µg/m³ today); no PM via API | same, station=353&component=5 | yes |
| DWD pollen forecast | daily 8-species index, region "Hohenlohe/mittlerer Neckar" | https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json | yes |
| Bright Sky (DWD) | wind, RH, rain, hourly | https://api.brightsky.dev/weather?lat=49.14&lon=9.22 | yes |
| Sensor.Community live | 6 SDS011 PM sensors in HN bbox as extra validation points | https://data.sensor.community/airrohr/v1/filter/box=49.10,9.15,49.20,9.30 | yes (live); archive CSV not reachable from here |

Not verified: full-history pagination speed of the atrai API (2 M rows at limit=1000 = ~2000 calls; test a bigger `limit` or ask re:edu for a dump), and whether any box has data from New Year/heating season 2025 (boxes were created March 2026, so fireworks are likely out).

## Technical plan
Stack: Python (pandas, requests) → one Parquet/CSV of hourly means per box → static JSON → vanilla JS + Leaflet + Plotly/Chart.js page, dropped into the Green-City-Dashboard repo as a tile (or standalone GitHub Pages as fallback).
Architecture: `fetch.py` (atrai + UBA + pollen + Bright Sky) → `process.py` (hourly resampling, RH flag >85 %, per-box linear calibration vs DEBW015, weekday-hour climatology, trust score) → `data/*.json` → frontend reads JSON, no backend needed.
- Tue evening: split roles; data person starts bulk download (run overnight); frontend person scaffolds the tile with fake JSON; analyst pulls UBA hourly series.
- Wed: morning – hourly dataset done, calibration scatter + trust scores; afternoon – air-clock heatmaps and advisor logic wired to real JSON; designer finalises layout and colour thresholds; non-coders write station texts, interview a teacher/parent, prepare slides.
- Thu morning: polish, record a backup video, rehearse pitch twice.
Roles (4-6): 1 data engineer, 1 analyst (calibration), 1-2 frontend, 1 designer/UX (also builds the tile styling), 1 storyteller/pitch + school contact (non-coder).

## Demo & pitch
60-s pitch: "Every morning 15 senseBoxes at Heilbronn schools measure what children breathe – and nobody looks at the pattern. We did. At the Innenstadt and the school stations PM2.5 peaks exactly at drop-off, and on foggy mornings the cheap sensors exaggerate it by X %. Pausenluft shows every school its own air clock, tells teachers when opening the windows helps and when it hurts, and gives the city a trust score for each sensor, calibrated against the LUBW station. It runs on data that already exists and costs nothing to keep."
On screen: map → click a school → air clock heatmap with the morning stripe → Lüftungsampel for the next 3 h → calibration scatter with R² and trust score.
Criteria: Teamwork (roles incl. non-coders), Innovation (temporal exposure + calibration, not another live map), Technical (2 M-row pipeline + reference comparison), Impact/Feasibility (actionable for Schulamt, zero cost, dashboard-ready), UX (one tile, one sentence per school), Presentation (concrete numbers, teacher quote).

## Risks & fallbacks
- Bulk download too slow → use 3-4 stations (Innenstadt, Wolf-von-Gemmingen, Schulgarten, OpenSpace) and 2 months of data; ask organisers for a dump.
- Many school boxes offline since March → honest "station silent since …" badge; this is itself a finding for the city.
- Calibration shows poor agreement (likely R² 0.5-0.8 at 2.6 km) → present it as the trust score, not a failure.
- Dashboard integration blocked → standalone page + screenshot of tile mock.

## Stretch goals
- Deploy one senseBox MCU-S2 + SPS30 from the hardware table at the venue entrance and show it joining the network live.
- Weekly email/PDF "Luftbericht" per school; automatic weekly re-run via GitHub Actions.
- NO2 proxy: correlate school PM morning peaks with the Weinsberger Str. NO2 traffic signal.

## Why this doesn't overlap with other teams
Lo-bah.png and Jeshile use the *mobile bike* PM data to rank routes/streets for cyclists. Pausenluft uses only the *stationary* 24/7 stations, targets children and teachers (not cyclists), focuses on *time of day* and *sensor trustworthiness* against the LUBW reference, and produces a ventilation recommendation rather than a route. No other team touches calibration, pollen, indoor/outdoor or schools.
