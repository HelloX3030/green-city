# Second Opinion: fact-checking Heilbronn's birds and bees
**Topic:** Biodiversity & Land use | **Expert lens:** urban ecologist / ornithologist with applied-ML background (citizen-science monitoring, camera-trap classifiers)

## The question
Heilbronn already runs an automated wildlife census (Birdiary feeders, OpenSpace beehives), but **can anyone trust it?** The feeder AI's number-one "species" in Heilbronn is *Poecile atricapillus*, the Black-capped Chickadee, a North American bird (1,085 hits at OpenSpace, 3,853 in Sontheim), followed by Carolina Chickadee, Anhinga, Mockingbird and Great-tailed Grackle. Only ~594 of ~14,200 visits were ever human-checked. So: **which birds and how many bees are really active in Heilbronn, and how does weather drive them?**

## Why it matters for Heilbronn
- Green Capital 2027 will be judged on evidence; a city dashboard showing American chickadees is an embarrassment waiting to happen. We turn existing public investment (15 stations, 3 hives, a LoRaWAN weather station) into numbers city hall can quote.
- A plausibility-checked species list plus activity-vs-weather curves is what the Grünflächenamt needs for feeding guidance, pollinator planting and heat-stress mitigation for urban fauna.
- Beneficiaries: city ecology office, schools hosting stations (corrected "my station" page), beekeepers, and Birdiary itself (we send corrections upstream).

## What we build (MVP for Thursday)
- **Bird fact-check pipeline** (Python): pull all Heilbronn movements via `/station/{id}?movements=500&movementsOffset=K`; (1) flag taxa outside a Central-European whitelist, (2) train a re-mapper on the 594 validated movements using the full detection score vector + perch weight (grams) + month/hour, (3) optional BirdNET second opinion on the `.wav` attached to each movement.
- **Corrected census tile** for greencity.hn (Next tile or standalone Leaflet page): per station raw vs. corrected counts, daily activity vs. temperature/humidity (143k env readings at OpenSpace alone), confidence traffic light per species.
- **Hive Pulse**: tiny CNN (<1 min on CPU) on the 12,716 labelled 32x32 crops (background / bee_motion / bee_slow), slid over the 9 recording sessions → bee-traffic index per session, plotted against the hive weather station (temp, light, wind, rain) pulled live from Grafana's Postgres via `/api/ds/query`.
- **Habitat ring**: Baumkataster (43,031 city trees with species, girth, crown) → tree count and species diversity within 150 m of each station.
- **Validation sprint**: non-coders label 200+ unvalidated clips in a simple form → new training labels + a correction file for Birdiary.

## Data & sources
| Source | What it gives us | URL | Verified |
|---|---|---|---|
| Birdiary API | `/station`, `/station/{id}?movements=N&movementsOffset=K`, `/movement/{id}`, `/statistics/{id}`, `/environment/{id}`; movement = detections[score], weight, video, audio (wav ~500 KB), temp/RH, `validation` if human-checked | https://wiediversistmeingarten.org/api | yes (10 stations ≤30 km, 6 with data, 14.2k movements) |
| Birdiary starter notebook | fetch/paging code | https://github.com/reedu-reengineering-education/Heilbronn-Hacksite/blob/main/public/birdiary_starter.ipynb | yes |
| Beehive Grafana | Postgres tables `data`, `sensors`, `beehives`; 2.75M rows since 2025-06-13; 3 hives (Dragino S31 temp/RH, D23 brood probes), SenseCAP weather (temp, RH, wind, rain, UV, light, pressure); anonymous SQL via POST `/api/ds/query` | https://beehive-grafana-production.up.railway.app | yes |
| Bee videos share | `traindata_20260916.tar.gz` (3 classes, 12,716 crops), 9 session tarballs (0.6-53 MB), README on RGB-ghost recording | https://cloud.reedu.de/s/YkHckREGAM89z9m (WebDAV `public.php/webdav`, user = share token) | yes |
| Baumkataster Heilbronn | Shapefile WGS84, 2025 + 2026 editions, dl-by-de/2.0; fields BAUM_NR, STADTTEIL, STRASSE, TYP, DEU_TEXT, WIS_TEXT, ST_UMFANG, KRONE_DM | https://opendata.heilbronn.de/dataset/baumkataster | yes |
| BirdNET (`pip install birdnet`) | audio species ID; code MIT, model CC BY-NC-SA (OK for research) | https://pypi.org/project/birdnet | partly (not yet run on Birdiary wavs) |
| Green City Dashboard repo | tile framework (Next.js inferred, Docker) | https://github.com/reedu-reengineering-education/Green-City-Dashboard | partly (no tile how-to in README) |
| Open-Meteo / DWD | weather backfill for stations without env data | https://open-meteo.com | no |

Not verified: whether feeder wavs contain usable bird song; exact tile contribution process for greencity.hn.

## Technical plan
Stack: Python (pandas, scikit-learn, PyTorch/Keras, birdnet, GeoPandas), Grafana HTTP for Postgres, Leaflet/MapLibre + Chart.js (or Next tile). Architecture: `fetch/` → `data/*.parquet` → `models/` (remapper, bee CNN) → `build_site.py` emits static JSON → front end. Everything cached so the demo never depends on live APIs; GitHub Pages fallback.
- **Tue evening**: fork notebook; dump all HN movements, statistics, environment; pull Grafana history hourly; download bee tarballs; agree whitelist.
- **Wed**: A+B remapper + hold-out evaluation (accuracy before/after); C bee CNN + traffic index; D front end, map, tree rings; E+F (non-coders) validation form, label 200 clips, pick the 10 "hall of shame" clips, draft pitch.
- **Thu morning**: wire JSON into front end, freeze data, rehearse twice, open Birdiary issue/PR with correction table.

## Demo & pitch
Pitch: "Heilbronn's smart feeders say our most common bird is a North American chickadee. Second Opinion re-labels 14,000 bird visits using the 594 that humans checked, counts bee traffic from OpenSpace's own hive footage, and wraps every station in its tree-register context. Result: a corrected, weather-aware census for greencity.hn, and a correction file going back to Birdiary."
On screen: station map raw vs. corrected; one "chickadee" clip beside its corrected label; accuracy jump on hold-out; bee-traffic curve rising with light, dropping in rain; tree ring.
Criteria: Teamwork (everyone labels); Innovation (first plausibility layer on a live citizen-science network; birds+bees+trees on one page); Technical execution (two trained models, three live APIs); Impact & Feasibility (fixes data the city already pays for, upstream PR); UX (traffic-light confidence, one page); Presentation (the chickadee punchline).

## Risks & fallbacks
- Too few validated examples per species → collapse to 6 feeder guilds (tits, sparrows, finches, corvids, pigeons, other).
- BirdNET finds nothing in feeder audio → drop it (optional).
- Bee session frames hard to window → report CNN confusion matrix on labelled crops only.
- Grafana blocked on demo day → cached Parquet.
- Shapefile is Latin-1 → `encoding='latin1'`.

## Stretch goals
Diff Baumkataster 2025 vs 2026 near stations; weekly retraining from new validations; senseBox MCU + microphone running BirdNET-Lite at a station; push corrections via Birdiary's validation endpoint.

## Why this doesn't overlap with other teams
No tree planting, adoption or gamification (Green Beez); no routing, heat islands, bike or traffic data; nobody has claimed the Birdiary or beehive datasets. The tree register is only a static habitat-context layer around sensor stations.
