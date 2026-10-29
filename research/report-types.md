# More report types: what fits our principle, and what to do with one day left

Written 2026-10-28. Companion to `complaints.md` (demand numbers) and `data.md` (data sources).

## 0. The principle, stated once

Sag's Heilbronn is not a Mängelmelder. The city's Mängelmelder takes an *incident* (a broken lamp, a dumped sofa), routes it to an Amt, and a worker fixes it in about 10 days. It works: ~13,800 reports by Nov 2025 (Stimme 21.11.2025), ~20 a day.

We take a *condition* (it is loud here, hot here, the air is bad here): something no worker can fix on a ticket, and that the city only acts on if it is **measured**. Our loop:

1. a person says how a place feels,
2. we check the feeling against data that already exists,
3. where no data exists, a sensor goes there,
4. the person gets an answer card (the 57 % re-report effect, FixMyStreet study).

A new report type is a good fit when all four hold:

| Test | Question |
|---|---|
| Demand | Do people feel it, and is there no button for it today? |
| Condition | Is it recurring and place-bound, not a one-off a worker clears? |
| Check | Is there data in Heilbronn *today* we can hold the cluster against? |
| Sensor | Is there a cheap sensor that closes the gap where the check says "no data"? |

Trash and potholes, our first two ideas, fail the *condition* test as plain incidents. Both come back in, though, as conditions (see 2 and 5 below).

## 1. Candidates, scored

Data columns are what is actually reachable now (verified in `data.md` and re-probed today against api.atrai.bike).

| # | Citizen wording | Demand | Check in HN today | Sensor that closes the gap | Fit |
|---|---|---|---|---|---|
| 1 | **Zu eng überholt** (unsicher mit dem Rad) | 77 % of ADFC Fahrradklima-Test 2024 respondents say cars pass too close; Überholabstand graded 4.6 nationally | atrai `overtaking_distance_heilbronn`: 1,389 road segments with mean overtaking distance in cm, counts per distance band, from senseBox:bike ToF sensor. Legal minimum in town is 150 cm (StVO §5). Sample: Saarlandstraße 108 cm | senseBox:bike, already 29 in the city, ~10 rides/day | **High. Zero hardware, hard legal threshold, nobody else has this layer.** |
| 2 | **Holprige Straße / kaputter Radweg** | Straße und Verkehr is #2 in the HN Mängelmelder; potholes are #1 on FixMyStreet UK | atrai `bumpy_roads_heilbronn`: 9,600 segments with Roughness / Normalized Roughness from the bike accelerometer, with number of boxes that rode it | senseBox:bike; or the phone itself (Boston Street Bump: <10 % false positives, 5–10 m location) | **High. Same code path as 1.** The single pothole stays a Mängelmelder ticket; we answer "this street is among the roughest 10 % the bikes measured". |
| 3 | **Kein Schatten / zu wenig Grün** (exists, but has no check) | 89 % value green access; HN green volume 1.96 m³/m², worst in BW | OpenData HN Baumkataster (shapefile, EPSG 4326): trees within 100 m vs. city median. Today `no_shade` answers "Kein Sensor misst Schatten" | Soil-moisture probes on street trees (Karlsruhe, Bamberg, Pirmasens run them); Gieß den Kiez code is MIT and reused by Leipzig and Magdeburg | **High for the jury, cheap.** Turns our weakest status line into a real check. |
| 4 | **Gestank / Geruch** | Smell Pittsburgh (CMU, 2016–) proved citizen smell reports line up with PM monitors and even predict smell events | Falls onto the existing `air` check: PM2.5 history + the last bike pass | Same as air; VOC sensor (BME680) on the NoiseNode later | **Medium.** Cheapest possible add (a chip that maps to `air`), low novelty. |
| 5 | **Mülleimer immer voll** | #1 everywhere: HN Müll und Abfall ~5,450 reports (Stimme, via search summary, unverified), Mängelmelder.de 37 % | None | Ultrasonic fill-level sensors: Hannover 20 bins (LoRaWAN), Flensburg 35, Mannheim 98 underground containers, Dortmund 92 Bigbelly for 367 k€ | **Medium as outlook, low to build.** The condition version ("this bin overflows every weekend") is a real smart-waste use case, but we have no data and no sensor, and the incident version competes with the Mängelmelder. |
| 6 | **Zu schnell / zu viel Verkehr / Poser** | City reply in the Lärmaktionsplan: Poser and Gewerbelärm fall outside the EU directive, so nobody measures them | None that is honest: atrai `speed_map_heilbronn` is **bike** speed, not car speed. Do not sell it as traffic | Telraam window counter, 60–80 €, counts cars/bikes/pedestrians and car speed; ADFC Berlin and DLR run them | **Medium.** The best "a sensor goes there" story after noise, but every answer today is "no data". |
| 7 | **Zu dunkel hier** (Angstraum) | Beleuchtung is #3 in the HN Mängelmelder (~2,050, same caveat); Münster surveys Angsträume by hand | senseBox:home Illuminance since 2026-03, but at 8 fixed boxes, not at the dark corner | A lux sensor is already on the senseBox; 2 € on the NoiseNode | **Medium.** Demand real, check thin; a free upgrade of our hardware story. |
| 8 | **Land unter nach Regen** | Starkregen is the climate-adaptation topic; Pfarrkirchen, Ergoldsbach run sensor alarms | Bright Sky hourly rain for "it rained X mm that day" | Gully level sensors (Redbridge ~100, Dublin 50) | **Low now.** Seasonal, nobody reports it at a demo. |
| 9 | **Keine Vögel / tote Natur** | Niche | Birdiary: 9 stations near HN, Open Space live | Birdiary box | **Low.** Fun pin, not a report type. |

## 2. Proposal

### Build today: "Unterwegs mit dem Rad" (types 1 and 2)

Two new types in one group, both checked against bike layers we already know how to fetch, zero hardware, one new backend module. This is the demo line *"the same loop works for mobility"*, and it is the one place where we hold a feeling against a **legal number**.

Backend, one file `roads.py`:
- at startup fetch `overtaking_distance_heilbronn` (1,389) and `bumpy_roads_heilbronn` (9,600) as GeoJSON LineStrings, cache them like `history.json`;
- `nearest_segment(lat, lon, layer, max_m=40)` by point-to-segment distance, reuse `distance_m`;
- status rules in `status.py`:
  - `close_pass`: segment found and mean < 150 cm → confirmed, *"Messräder: N Überholvorgänge auf der Saarlandstraße, im Schnitt 108 cm. Erlaubt sind 150 cm."*; mean ≥ 150 → unconfirmed; no segment → no_data *"Hier kam noch kein Messrad vorbei."*;
  - `rough_road`: Normalized Roughness in the top 20 % of all segments → confirmed, *"Unter den 20 % holprigsten Straßen, die die Räder gemessen haben (N Fahrten)."*; else unconfirmed; none → no_data.
- the layers are all-time aggregates with no date, so the reason says "gemessen" without a time span.

App: two chips with icons, filter chips in the Ebenen sheet, the card and the runner scenario as for the other types. The `bikes.py` live rides already draw the bikes on the map, so the "sensor goes there" step is visibly the bike.

Estimate: 2–3 h backend plus app plus runner. Touches `status.py`, `main.py` ReportType and the type list in the app. The other agent should know before anyone edits the enum.

### Build if time is left: a real check for `no_shade` (type 3)

Convert the Baumkataster once to GeoJSON (ogr2ogr or mapshaper, it is 1.4 MB zipped), count trees within 100 m, compare with the city median. Status line: *"12 Bäume im Umkreis von 100 m, Stadtmittel 31. Hier fehlt Grün."* Half a day at most, mostly the one-off conversion. It gives the Green City jury the green type a real answer and ties heat and shade together.

### Say, don't build: one outlook slide, "Dasselbe Prinzip"

One row per type, four columns: Gefühl → Daten → Sensor → Antwort.

- Müll: "immer voll" → none → fill-level sensor (Hannover, Flensburg, Mannheim) → "wird seit Mai bedarfsgerecht geleert".
- Verkehr / Poser: "zu laut, zu schnell" → none, outside the EU directive → Telraam am Fenster → "an 5 von 7 Abenden über 30 km/h".
- Angstraum: "zu dunkel" → none → lux on the NoiseNode → "nachts unter 5 lx, Stadtmittel 15".
- Bäume: "vertrocknet" → Baumkataster + DWD rain → soil moisture → "Gießbedarf, seit 14 Tagen trocken".
- Starkregen: "Land unter" → rain history → gully sensor → warning before the next one.

The sentence for the slide: *"The Mängelmelder has 13 buttons for things a worker fixes in ten days. We add the buttons for things you can only fix once you measure them."*

### Cheap goodwill: hand incidents to the city

When someone picks *Sonstiges* and the text contains Müll, Sperrmüll, Laterne, Schlagloch, show a line under the sent card: *"Das ist ein Fall für den Mängelmelder der Stadt"* with a link to heilbronn.mängelmelder.de. We don't compete, we route. Fifteen minutes.

### Don't do

- Trash or potholes as incident reports with photo. Duplicates a working city tool in front of a city jury, and we have no verification data for either.
- Selling the atrai speed map as car speed. It is the bikes' own speed.
- A fifth environmental type nobody will tap during the demo (flooding, birds).

## 3. Caveats

- Mängelmelder per-category counts (Müll ~5,450, Straße ~4,420, Beleuchtung ~2,050) come from a search summary of a paywalled Stimme article; only the 13,800 total (Nov 2025) and the 9,000 headline (Nov 2024) were seen directly. Use "about 14,000, Müll first, Straße second" on stage.
- Overtaking and roughness layers are aggregated over all rides, with "Number of Boxes" per segment often 1 or 2. Say "Messräder haben gemessen", not "repräsentativ".
- No accuracy figure for the senseBox:bike overtaking detector was published (FOSS4G 2024 paper says accuracy "will be addressed"). The Sensors 2025 "SenseBike" paper is a different system.
- Heilbronn's own ADFC Fahrradklima-Test grades were not looked up (they sit in the interactive map PDF at fkt.adfc.de); the 77 % and 4.6 are national.

## 4. Sources

- Heilbronn Mängelmelder: heilbronn.de/rathaus/kontakt/maengelmelder.html (13 categories); Stimme 22.11.2024 (>9,000); Stimme 21.11.2025 (13,800); werdenktwas.de 25.11.2020 (launch, six main groups)
- Mängelmelder.de Jahresauswertung 2024: static.werdenktwas.de/domain/190/fs/Statistik/Jahresauswertung_2024.pdf
- atrai layers: api.atrai.bike/collections/{overtaking_distance_heilbronn,bumpy_roads_heilbronn,speed_map_heilbronn,traffic_flow_heilbronn}/items?f=json (probed 2026-10-28)
- senseBox:bike: sensebox.de/en/products-bike; FOSS4G 2024 academic track talk XMAGHX; ARPHA Proceedings 6:135-140
- ADFC Fahrradklima-Test 2024: fkt.adfc.de/ueber-den-fkt/vergangene-fahrradklima-test-durchgaenge/ergebnisse-2024; verbandsbuero.de summary (77 %, 4.6)
- Street Bump: boston.gov/departments/new-urban-mechanics/street-bump; CNN 16.02.2012; ScienceDirect S0198971517301333 (5–10 m)
- Smell Pittsburgh: arxiv.org/abs/1912.11936 (Hsu et al., ACM TiiS 2020); smellpgh.org
- Smart waste: enercity.de press 2021 (Hannover); kommune21.de (Flensburg); smartmannheim.de (Mannheim); nordstadtblogger.de (Dortmund, 367 k€); smart-city-dialog.de/wissen/massnahmen/smart-waste
- Telraam: telraam.net; civitas.eu/solutions-and-tools/telraam-wecount-traffic-counting (60–80 €); ADFC Berlin and DLR press 22.03.2022
- Trees: citylab-berlin.org/en/projects/giessdenkiez; wochenblatt-reporter.de (Karlsruhe soil sensors); infranken.de (Bamberg); rheinpfalz.de (Pirmasens)
- Angsträume: oparl.stadt-muenster.de/bodies/0001/downloadfiles/00579880.pdf (Münster survey); heidelberg.de Angsträume hotline
- Flooding: pfarrkirchen.de onboarding FAS (Schachtsensoren); kommunal.de (Ergoldsbach); redbridge.gov.uk gully sensors (May 2023); smartdublin.ie
