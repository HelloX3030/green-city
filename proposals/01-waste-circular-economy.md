# Noch gut! HN – the reuse-first waste guide
**Topic:** Waste & Circular economy | **Expert lens:** head of strategy, municipal Abfallwirtschaftsbetrieb (circular economy, citizen science, open data)

## The question
Heilbronn residents throw 172.7 kg of Rest-/Sperrmüll per person per year into the grey bin (2023), the same as Stuttgart and far above neighbouring Landkreise (109-143 kg). **For any item I want to get rid of, what is the nearest option to repair, donate or share it before it becomes Restmüll, and how much waste and money would Heilbronn save if people used those options?**

## Why it matters for Heilbronn
- The city's Abfall-ABC answers only "which bin?". Reuse offers (Reparier Café, experimenta Maker Space, Gildecenter, second-hand, give boxes) exist but are scattered across sub-pages; nobody sees them at the moment of throwing away.
- From 2026 Rest-/Biomüll is billed per emptying via a bin chip: every kilo diverted saves households money, a built-in incentive.
- City hall: fulfils the KrWG avoidance mandate, gives the Entsorgungsbetriebe a plug-in reuse layer for Abfall-ABC/app, yields a Green Capital 2027 tile. Beneficiaries: residents (cheaper), social enterprises (more donations/repairs), city (less Restmüll to incinerate).

## What we build (MVP for Thursday's demo)
- **Item search ("Toaster", "Sofa", "Kinderrad")** over ~500 scraped Abfall-ABC entries, each mapped to a 4-step **reuse ladder**: Repair -> Donate/Sell/Share -> Recycle -> Dispose, with nearest location, hours and distance on a Leaflet map.
- **Location layer**: 7 Recyclinghöfe (official site), curated reuse directory (Reparier Café HN, experimenta Maker Space, Gildecenter, charity shops) and OSM POIs (`shop=second_hand|charity`, `amenity=give_box|public_bookcase`, `craft=shoemaker|tailor|electronics_repair`, `service:bicycle:repair=yes`).
- **Impact tile**: Sankey "Where does Heilbronn's waste go?" (Statistisches Landesamt 2023: 46.5 kt total -> 22.3 kt Rest-/Sperrmüll of which 18.8 kt incinerated, 7.2 kt Bio, 17.1 kt Wertstoffe) plus a kg/person comparison bar vs. Stuttgart, Ludwigsburg, Region.
- **Savings calculator**: slider "I divert X kg/week" -> smaller bin/fewer emptyings -> EUR/year from the fee table; tonnes if 10 % of households did the same.
- **"Gerettet" counter**: one-tap "repaired/donated instead" logging, public aggregate (seeded).
- Deliverable: static web app on GitHub Pages; impact tile as iframe/page for greencity.hn.

## Data & sources
| Source | What it gives us | URL | Verified |
|---|---|---|---|
| Abfall-ABC, Abfallwirtschaft Stadt Heilbronn | A-Z items with official Entsorgungsweg; server-rendered HTML, letter pages via `tx_heilbronn_content[letter]=A` | https://abfallwirtschaft.heilbronn.de/abfall-abc | yes (structure; scraping untested) |
| Recyclinghöfe page | 7 sites, addresses, opening hours, accepted materials | https://abfallwirtschaft.heilbronn.de/abfallentsorgung/abfallannahme/recyclinghoefe | yes |
| Abfallvermeidung page | Named local reuse offers: Reparier Café HN (Senioren für Andere), Reparier Café experimenta, Aufbaugilde/Gildecenter | https://abfallwirtschaft.heilbronn.de/abfallvermeidung | yes (no addresses/hours -> curate manually) |
| City Abfallbilanz | 2022-2025 totals: 2025 = 51,763 t (30,539 t Verwertung / 21,224 t Beseitigung); fraction split only as images | https://abfallwirtschaft.heilbronn.de/abfallbilanz | yes |
| Statistisches Landesamt BW, Kommunales Abfallaufkommen 2023 | Stadtkreis Heilbronn: 360.7 kg/E total; 172.7 kg/E Rest-/Sperrmüll; 55.5 kg/E Bio; 132.5 kg/E Wertstoffe; Papier 6,961 t, Glas 2,338 t, Metall 1,249 t; Schadstoffe 107 t; same for all Kreise | https://www.statistischebibliothek.de/mir/servlets/MCRFileNodeServlet/BWHeft_derivate_00027893/3651_23001.pdf | yes (pdftotext works) |
| opendata.heilbronn.de "Abfallgebühren 2022" | CSV: container type, size, rhythm, EUR/year; CC BY 4.0; DKAN API | https://opendata.heilbronn.de/node/2057 (CSV: /sites/default/files/2022_ABFALL_ABFALLGEBUEHREN.CSV) | yes (2022 prices; 2026 chip tariff must be added by hand) |
| OpenStreetMap via Overpass | Second-hand, charity, repair crafts, give boxes, bookcases, recycling points | https://overpass-turbo.eu | partly (query drafted; all public Overpass servers were at capacity during check -> use Geofabrik BW extract as fallback) |
| Abfallbilanz BW 2024 incl. Restmüllanalyse | Share of avoidable fractions in the grey bin (statewide proxy) | https://um.baden-wuerttemberg.de (PDF linked from city page) | no (not opened) |
| Green City Dashboard repo | Tile integration target (Next.js/Tailwind inferred, not documented) | https://github.com/reedu-reengineering-education/Green-City-Dashboard | partly |

Not found: Depotcontainer coordinates as open data; Heilbronn-specific Restmüll composition; machine-readable Abfallkalender/API.

## Technical plan
Stack: Python (requests + BeautifulSoup) scraper -> `items.json` / `places.geojson`; static front end (Vite, vanilla JS or React), Leaflet, Fuse.js search, Plotly Sankey; GitHub Pages; optional Supabase/FastAPI endpoint for the counter (fallback: seeded JSON).

- **Tue evening**: agree item-to-ladder rules (e.g. Elektrokleingerät -> repair, donate, Recyclinghof); scrape Abfall-ABC + Recyclinghöfe; run Overpass; map skeleton; non-coders phone Gildecenter and Reparier Café for hours.
- **Wed**: search + ladder cards + map (2 devs); Sankey, kg/E comparison, fee calculator (1 data person); UX, icons, mobile (designer); 20-30 curated reuse places + item mapping in a shared sheet, add missing POIs to OSM (2 non-coders). Evening: integrate, test with 5 strangers at OpenSpace.
- **Thu morning**: bug-fix, demo data, pitch rehearsal, package tile, one-page handover for Entsorgungsbetriebe.

## Demo & pitch
60-second pitch: "Every Heilbronner bins 173 kg a year, among the highest in the region, and from 2026 every emptying costs money. What if the city's own Abfall-ABC said 'repair or donate here' before it says 'Restmüll'? Noch gut! HN takes 500 official entries, adds Heilbronn's repair cafés, second-hand and give-away points, and shows the nearest on a map. Our Sankey shows where 46,500 tonnes go today; our calculator shows what a household saves. It runs as a website and a Green City Dashboard tile, ready for the Entsorgungsbetriebe to plug in."
On screen: type "Bürostuhl" -> ladder card (Gildecenter pickup, Recyclinghof Plus last), map pin; Sankey tile; savings slider; "Gerettet" counter ticks.
Criteria: Teamwork (coder/curator split, OSM edits by non-coders); Innovation (reuse ladder on official data + 2026 tariff incentive); Functionality (search, map, charts work); Impact & Feasibility (official data, named operator, continuation via Abfall-ABC/app); UX (one search box, mobile-first); Presentation (live demo, one strong number).

## Risks & fallbacks
- Abfall-ABC scraping blocked or messy -> copy the ~500 entries manually from the "Alle" page into a sheet (2 people, 1 h).
- Overpass down (seen today) -> Geofabrik Baden-Württemberg .pbf + osmium/pyrosm, or hand-curated 30 places.
- 2026 tariff not public -> use 2022 CSV, label clearly as "2022 prices".
- Counter backend too much -> static seeded counter, state the real version as next step.

## Stretch goals
- QR placard per Recyclinghof linking to "before you dump it".
- Photo-to-item classification (phone camera -> Abfall-ABC entry) with a small vision model.
- Export of the curated reuse directory as a CC BY dataset to opendata.heilbronn.de.
- Event layer: Reparier Café dates from reparatur-initiativen.de.

## Why this doesn't overlap with other teams
Mojorigo senses glass-container fill levels for logistics; we never touch containers, sensors or pickup routes. We work upstream of the bin: what to do with an item before disposal, where the tonnage goes, what households save. No bike, heat, tree or traffic data.
