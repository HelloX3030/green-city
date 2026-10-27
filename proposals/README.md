# Green City Hackathon Heilbronn 2026 – Project Proposals

Seven proposals, one per Green Capital topic, each written from the perspective of a simulated domain expert.
They are deliberately non-overlapping (by topic, by primary dataset and by target user) and were checked against the
ideas already registered by other teams on hackathon.greencity.hn/teams (heat-island explanation, green bike routing,
glass-container fill level, tree-planting gamification, cycling-safety ranking, traffic-light waiting times).

| # | Proposal | Topic | Core question | Primary data (verified?) | Hardware on site | Target user |
|---|----------|-------|---------------|--------------------------|------------------|-------------|
| 1 | [Noch gut! HN](01-waste-circular-economy.md) | Waste & Circular economy | Where can I repair / donate this instead of binning it? | City Abfall-ABC (scraped, verified), Recyclinghöfe, StaLa waste statistics (verified), OSM reuse POIs (partly) | no | Households, Entsorgungsbetriebe |
| 2 | [RegenCheck Heilbronn](02-water.md) | Water | How much rain just fell on my street, and where does it pool? | DWD RADOLAN radar via Bright Sky (verified live), 10 y hourly DWD station data (verified), citizen reports | ToF rain gauge | Residents, Tiefbauamt |
| 3 | [Hörbronn](03-noise.md) | Noise | How loud are the city's 8 official noise hotspots over 24 h, and who lives next to them? | Lärmaktionsplan hotspots from city PDF (verified), self-built loggers, phone noise walks, OSM receptors | DIY I2S mic loggers (mic unverified) | Residents, Lärmaktionsplan authors |
| 4 | [Pausenluft](04-air-quality.md) | Air quality | What do schoolchildren breathe during arrival, breaks and pick-up, and when should teachers ventilate? | senseBox:home 2 M rows (verified), LUBW reference station API (verified), DWD pollen (verified) | no | Schools, parents |
| 5 | [Second Opinion](05-biodiversity-land-use.md) | Biodiversity & Land use | Is the city's automated bird and bee census actually right? | Birdiary API incl. validated labels (verified), beehive Postgres + 12.7k labelled crops (verified), Baumkataster (verified) | no | Birdiary / re:edu, Umweltamt |
| 6 | [Gap2035](06-climate-mitigation.md) | Climate mitigation | How far is each district from its roof-PV and heat-network potential, and what is my house's next step? | Kommunaler Wärmeplan PDF (verified), MaStR (partly), OSM footprints (verified), LoD2 (unverified) | no | Homeowners, Klimaschutzmanagement |
| 7 | [HitzeKompass](07-climate-adaptation.md) | Climate adaptation | Which Kitas, care homes, playgrounds and bus stops lack shade, water and a cool room nearby? | Baumkataster + Planungsbezirke + age data (verified), OSM amenities (unverified), DWD heat warnings (verified) | optional UV/temp ground-truthing | Vulnerable residents, Hitzeaktionsplan |

## Suggested pick order

Ranked for a 4–6 person team with ~1.5 build days, weighting jury criteria (originality, execution, impact, demo) and how much of the data is already confirmed reachable.

1. **HitzeKompass (7)** – highest impact and feasibility combination. All city datasets verified, direct hook into the Hitzeaktionsplan the city must write for 2027, a clear "Top 15 cheapest fixes" deliverable for the Deputy Mayor pitch, and a mobile view that demos well. Main risk is OSM amenity coverage; fallback is the field team adding points.
2. **Second Opinion (5)** – strongest originality. The hook ("the city's bird AI thinks Heilbronn is full of North American chickadees") is a ready-made pitch opener, every dataset was verified live, and it exploits the two unclaimed assets (birdhouses, beehive videos). Slightly weaker on "helps residents directly", strong on "helps the project continue".
3. **Pausenluft (4)** – most scientifically solid. 2 M rows of real data, a reference-station calibration nobody else will do, and a concrete ventilation advice for 15 schools. Risk is bulk-download speed; ask the organisers for a dump on Tuesday evening.
4. **Hörbronn (3)** – most hackathon-spirited (build sensors, collect your own data) and the only noise entry. Depends on sourcing 3–5 INMP441 microphones tonight and getting I2S working on the MCU-S2; the phone-app fallback keeps it alive.
5. **RegenCheck (2)** – great live demo (pour water on the gauge, tile updates) and verified radar API, but heavy rain is a hard sell in late October and the citizen layer needs a small backend.
6. **Gap2035 (6)** – highest policy relevance, but the most unverified inputs (LoD2 roofs, MaStR totals) and manual polygon tracing of 13 areas eat into build time.
7. **Noch gut! HN (1)** – very feasible and useful, lowest technical wow; good choice if the team is mostly non-coders.

## Notes shared by several experts

- Overpass API was unreachable or at capacity from the sandbox today; plan to export from overpass-turbo.eu in a browser or use the Geofabrik Baden-Württemberg extract.
- opendata.heilbronn.de is DKAN, not CKAN: there is a DCAT catalog.xml and per-dataset JSON, but no CKAN API.
- The Green City Dashboard repo has no documented "how to add a tile"; it is a Next.js app. Ask a re:edu mentor on Tuesday how tiles are contributed, or ship a standalone page plus a tile mock.
- The Baumkataster shapefile is Latin-1 encoded.
