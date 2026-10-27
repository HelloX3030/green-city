# HitzeKompass Heilbronn – who is unprotected when it gets hot, and where is the nearest cool spot?
**Topic:** Climate Change: Adaptation | **Expert lens:** public-health / Hitzeaktionsplan practitioner working with social-vulnerability data (WHO, UBA/BMUV heat guidance)

## The question
On a 35 °C day, which Kitas, care homes, playgrounds and bus stops in Heilbronn leave vulnerable people without shade, drinking water or a cool refuge within a 3-minute walk, and where should a frail person, a parent with a toddler or an outdoor worker go right now?

## Why it matters for Heilbronn
Heat is Germany's deadliest climate hazard (RKI: roughly 3,000 deaths per year, concentrated among over-75s, infants, the chronically ill and outdoor workers). Heilbronn lies in one of the warmest basins in Baden-Württemberg and must deliver a municipal Hitzeaktionsplan as Green Capital 2027. Artemis explains *where* heat is; nobody yet answers *who is exposed and what protects them*. Beneficiaries: care-home residents and carers, Kita staff deciding whether to go outside, people waiting at unshaded stops, and the Gesundheitsamt/Grünflächenamt, which gets a ranked list of cheap fixes (a fountain, a shade sail, a bench under a tree, a "Kühler Ort" sticker on a library) per Planungsbezirk, ready for the Hitzeaktionsplan and the Green City Dashboard.

## What we build (MVP for Thursday's demo)
- **Protection-gap map (city view):** every Kita, senior facility, playground, school and bus stop as a point, scored red/yellow/green by what exists within 150 m: shade (Baumkataster trees, OSM shelters), drinking water (OSM `drinking_water`/fountains), a seat, and a public cool indoor place within 300 m (library, church, pharmacy, supermarket).
- **Vulnerability weighting per Planungsbezirk:** share of 65+/80+ and 0-6 year olds (city open data), so a gap in an old-age district ranks higher. Output: "Top 15 cheapest fixes" table ("Bus stop X, Böckingen: no shade, nearest water 480 m, 1,200 residents 75+ within 500 m").
- **Cool-spot finder (citizen view, mobile):** one button "Mir ist heiß" shows the nearest shaded bench, fountain and cool room with a walking route that prefers tree-lined streets. Large type, German, three buttons, usable by an 80-year-old.
- **Heat-alert banner:** live DWD warning for warn cell "Stadt Heilbronn" via BrightSky; when active, the city view lists "facilities to call today".
- **Reality check:** two members ground-truth 10-15 red spots on Wednesday with photos, a senseBox MCU (temperature + brightness/UV as shade proxy) and the Aug-2026 heat-walk temperatures; shown as photo pop-ups.
- Delivered as a Green City Dashboard tile plus standalone Leaflet app.

## Data & sources
| Source | What it gives us | URL | Verified |
|---|---|---|---|
| Heilbronn Open Data: Baumkataster Jan 2026 (WGS84 shapefile) | every city tree = shade | https://opendata.heilbronn.de/sites/default/files/SHAPE_BKA_HN20260101_EPSG4326.zip | yes (link; attributes not inspected) |
| Heilbronn Open Data: Planungsbezirke WGS84 | district polygons | https://opendata.heilbronn.de/sites/default/files/SHAPE_KLGL_PB_EPSG4326_0.zip | yes |
| Heilbronn Open Data: Durchschnittsalter / Einwohnerdaten / Altersgruppen Planungsbezirke | vulnerability (age structure) | https://opendata.heilbronn.de/sites/default/files/DurchschnittsalterPlanungsbezirke.csv ; dataset `einwohnerdaten-auf-ebene-planungsbezirke` | yes / partly (age-group file not opened) |
| Heilbronn Open Data: Kinderbetreuung, Pflegeeinrichtungen | Kita/care context | https://opendata.heilbronn.de/dataset/kinderbetreuung-heilbronn | no: statistics only, no geolocated download found -> use OSM |
| OpenStreetMap via Overpass | kindergarten, social_facility (senior), nursing_home, playground, bus_stop+shelter, drinking_water, fountain, bench, library, pharmacy, supermarket | https://overpass-turbo.eu | no: HTTP 406 from our network; run in browser and export GeoJSON |
| DWD warnings via BrightSky | heat warnings, warn cell 808121000 | https://api.brightsky.dev/alerts?lat=49.14&lon=9.22 | yes (no alert today) |
| Heat-walk datalogger (Summer School 2026) | 61k GPS points `timestamp,lat,lon,temperature,humidity` | https://cloud.reedu.de/s/X9x2XE9a9xCxLm8 (WebDAV `datasets/alles.csv`, 7.7 MB) | yes, downloadable |
| senseBox:home (15 schools) | 24/7 temperature, 2.0 M rows | https://api.atrai.bike/collections/osem_home_data_heilbronn/items?f=json | yes |
| Haltestellen (TRIAS / Mobidata BW) | official stop list as OSM backup | opendata.heilbronn.de "Linienplan mit Haltestellen" | partly (listed, not called) |

## Technical plan
Stack: Python (geopandas/shapely) script -> static GeoJSON; Leaflet (or MapLibre) + vanilla JS/Vite on GitHub Pages, embedded as a Dashboard tile; BrightSky fetched client-side; routing via public OSRM. No backend.
Flow: `data/` -> `score.py` (150 m buffers, counts, age weights, ranking) -> `facilities.geojson`, `districts.geojson`, `coolspots.geojson` -> app with tabs Stadt / Bürger.
- **Tue evening:** agree scoring rules (shade = ≥3 trees or shelter within 150 m; water ≤150 m; cool room ≤300 m), download sources, run Overpass in browser, convert shapefiles. Non-coders: derive "Kühler Ort" criteria from UBA guidance, prepare field checklist.
- **Wed:** A+B scoring pipeline and ranking table; C+D Leaflet app, citizen view, alert banner; E (non-coder) field validation with photos and senseBox; F pitch, slides, plain-German UX copy, Dashboard tile PR.
- **Thu morning:** merge photos, freeze data, rehearse twice, test on a phone.

## Demo & pitch
Pitch: "Heat kills more people in Germany than any other weather. Heilbronn knows where its hot spots are, but not who stands in them. HitzeKompass scores every Kita, care home, playground and bus stop by shade, water and a cool refuge within three minutes, weights it by the old people and small children living nearby, and hands the city a ranked list of cheap fixes. For residents it is one button: 'Mir ist heiß'. Live-linked to DWD warnings, built on Heilbronn open data and OSM, ready as a Dashboard tile."
On screen: red/yellow/green city map; click Böckingen -> top-15 fix list; phone view, press the button, route to shaded bench and fountain; field photo of a red bus stop with measured temperature.
Criteria: Teamwork (six defined roles incl. field team); Innovation (first people-centred heat-protection score for a German mid-size city); Functionality (real data, live alerts, working route); Impact & Feasibility (feeds the Hitzeaktionsplan, fixes under 5k € each); UX (three-button senior view); Presentation (field photos make it tangible).

## Risks & fallbacks
- Overpass blocked on venue wifi -> overpass-turbo.eu export or Geofabrik BW extract.
- Kitas/care homes only from OSM -> state coverage honestly, let field team add missing ones.
- Shapefile lacks crown size -> use tree density.
- No heat warning in October -> "simulation mode" replaying a summer-2026 warning.
- Datalogger is one-day data -> illustration only, not part of the score.
- Routing too hard -> straight-line nearest cool spot.

## Stretch goals
- Hour-by-hour shadow sides of streets from sun position.
- "Hitzetelefon" call list for care homes in red zones during a warning.
- senseBox "Schattenwächter": battery MCU at a playground logging temp + UV for a week.
- Export fix list as Hitzeaktionsplan annex PDF.

## Why this doesn't overlap with other teams
Artemis explains the physics of heat islands; we take heat as given and look at people and protective infrastructure. Lo-bah and Jeshile do cycling routes/safety, Green Beez gamifies tree planting, our water colleague covers heavy rain. No registered team addresses vulnerable groups, cool spots or the city's heat-action decision list.
