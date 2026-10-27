# Gap2035 – Heilbronn's Roof & Heat Gap Map
**Topic:** Climate Change: Mitigation | **Expert lens:** senior energy-systems / municipal climate-action engineer (Klimaschutzkonzepte, building energy, PV potential, district heating)

## The question
Heilbronn wants to be climate-neutral by 2035. Its heat plan (KWP 2023/25) counts ~1,800 GWh/a of heat demand, 75 % natural gas, plus coal-based district heat; roof PV is ~80 MWp installed vs. ~440 MWp potential. **Where exactly is the gap – per district and per building – and what is the single best next step for the people living in each house?**

## Why it matters for Heilbronn
- The KWP and Klimaschutz-Masterplan exist only as 130-page PDFs; residents cannot see whether *their* street is in one of the 13 Wärmenetz-Eignungsgebiete or whether their roof is worth PV.
- 98 % of emissions come from businesses and households, so city hall's main lever is triggering private decisions. A per-address "do this next" tool is the citizen-facing layer the Stabsstelle Klimaschutz lacks (it already funds PV grants and heat-pump advice).
- A district-level gap tracker (installed vs. potential, pace of new registrations) delivers the monitoring the council mandated in 2022 and fits the Green City Dashboard.

## What we build (MVP for Thursday)
- **Interactive map (MapLibre)** of all Heilbronn building footprints, coloured by estimated roof-PV potential (kWp) computed from footprint area (and roof orientation/pitch where LoD2 is obtainable).
- **Overlay of the 13 Wärmenetz-Eignungsgebiete** digitised from the KWP PDF (GeoJSON), with a short per-area explainer.
- **Overlay of existing PV** from the Marktstammdatenregister, aggregated per PLZ/Stadtteil (count, MWp, registrations per year).
- **Address lookup: "My house – next step"**: type an address → roof PV estimate (kWp, kWh/a, t CO2/a), "you are in / outside a heat-network area" → recommendation (connect to network / heat pump / insulate first), links to the city's grant and the Energieatlas calculator.
- **Gap2035 dashboard tile** (greencity.hn style): installed vs. potential PV per district, yearly additions, "at today's pace the roof potential is reached in year X".

## Data & sources
| Source | What it gives us | URL | Verified |
|---|---|---|---|
| Kommunale Wärmeplanung Heilbronn (PDF 2023, rev. 2025) | Heat demand 1,797 GWh/a, 75 % gas, 19,031 buildings by chimney-sweep data, 13 named Eignungsgebiete with maps | https://www.heilbronn.de/fileadmin/daten/stadtheilbronn/formulare/umwelt_mobilitaet/energie/Waerme/2025_Bericht_kwp_heilbronn_compressed.pdf | yes (PDF read; no GIS download, polygons must be traced) |
| Klimaschutz-Masterplan Fortschreibung (DS 287/2022), KLIMAfit brochure | 2035 target, sector shares, measure list | https://www.heilbronn.de/fileadmin/daten/stadtheilbronn/formulare/umwelt_mobilitaet/klimaschutz/DS_287_2022_Fortschreibung_Klimaschutzmasterplan.pdf | yes (exists) |
| Marktstammdatenregister | All PV units: capacity, commissioning date, PLZ/Gemeinde, coordinates for larger units; ~5,600 units / ~80 MWp in Heilbronn | https://www.marktstammdatenregister.de/MaStR/Einheit/Einheiten/OeffentlicheEinheitenuebersicht (filter Gemeinde, CSV export) or `pip install open-mastr` | partly (export exists; Heilbronn figure from a third-party summary) |
| OSM building footprints (Overpass) | Footprint polygons, building type, levels | https://overpass-turbo.eu/ | yes |
| LGL BW Open GeoData: LoD2 / Hausumringe | Roof geometry (pitch, orientation) for real PV estimates | https://opengeodata.lgl-bw.de/ | **not verified** (portal is JS-only; licence/LoD2 availability unconfirmed – treat as stretch) |
| Energieatlas BW Solardachkataster | Official per-roof PV suitability (web app only) | https://www.energieatlas-bw.de/sonne/dachflachen/solarpotenzial-auf-dachflachen | partly (no WFS/download found) – use to calibrate and link out |
| PVGIS API | Yield (kWh/kWp/a) for Heilbronn by orientation | https://re.jrc.ec.europa.eu/api/v5_3/PVcalc | yes (public API) |
| MobiData BW | E-charging stations BW, "Kfz und Verkehrsbelastung Heilbronn" CSV | https://mobidata-bw.de/dataset/?q=heilbronn | yes (stretch only) |
| opendata.heilbronn.de | 17 "Umwelt und Klima" datasets; no energy dataset found | https://opendata.heilbronn.de/ | partly (no energy data confirmed) |

## Technical plan
**Stack:** Python (GeoPandas, Shapely, requests) for the pipeline → static GeoJSON/PMTiles; frontend plain HTML + MapLibre GL + a small Nominatim/Photon geocoder call; dashboard tile as a React component for the Green-City-Dashboard repo. No backend needed – everything is precomputed and served statically (GitHub Pages).

**Architecture:** `pipeline/` (fetch OSM → compute kWp = area × 0.35 usable × 0.2 kWp/m² × orientation factor; join MaStR per PLZ; load traced Eignungsgebiete) → `data/*.geojson` → `web/` (map + address lookup) and `tile/` (KPI charts).

**Tue evening:** repo + data fetch (Overpass, MaStR CSV, PVGIS yield table); non-coders start tracing the 13 areas in geojson.io and extracting KWP/Masterplan numbers.
**Wed:** pipeline finished by noon; map with three layers; address lookup + recommendation logic; dashboard tile; pitch storyboard.
**Thu morning:** polish, test 5 real addresses, record fallback screencast, rehearse pitch.

**Roles (4-6):** 1-2 data/pipeline, 1-2 frontend/map, 1 "domain + content" (trace polygons, grant info, recommendation texts, calibration against Energieatlas), 1 design/pitch (tile layout, slides, 60-s pitch). Non-coders own the polygon tracing, content and pitch.

## Demo & pitch
**60-s pitch:** "Heilbronn wants to be climate-neutral by 2035, but 75 % of its heat is gas and only ~18 % of its roof-solar potential is built. The plans exist – as PDFs. Gap2035 turns them into a map: type your address, see whether you'll get district heat or should plan a heat pump, and what your roof could produce. For the city it's a live gap tracker per district, built on open data, ready for the Green City Dashboard."
**On screen:** map zoomed to Kernstadt with heat-network areas → type a Böckingen address → card with kWp, t CO2, recommendation → switch to dashboard tile with the gap bar per district.
**Criteria:** Teamwork (clear roles incl. non-coders); Innovation (first citizen-facing merge of KWP + MaStR + roof potential); Functionality (live lookup, real numbers); Impact & Feasibility (ties directly to the council's 2035 monitoring mandate, continuable by Stabsstelle Klimaschutz); UX (one question, one answer); Presentation (concrete address story).

## Risks & fallbacks
- **LoD2 not obtainable** → footprint-area heuristic only, calibrated against ~10 roofs in the Energieatlas; state it honestly.
- **MaStR CSV export caps rows** → use `open-mastr` bulk download overnight on one laptop, or aggregate by PLZ from the web filter.
- **Polygon tracing too slow** → trace the 5 largest areas first, label the rest by centroid.
- **Geocoder rate limits** → preload addresses from OSM `addr:*` tags; demo on a fixed list.

## Stretch goals
- Heat-pump suitability score per building (building age class from OSM/Zensus, density).
- E-charging coverage vs. car density per district (MobiData BW + Heilbronn Kfz CSV) as a mobility-emissions tile.

## Why this doesn't overlap with other teams
Purely energy/buildings: no routing, cycling safety, traffic lights or tree gamification; Artemis explains microclimate, we map heating systems and roof PV. Mobility appears only as an optional charging-coverage emissions tile.
