# Hörbronn – the 24-hour noise clock
**Topic:** Noise | **Expert lens:** senior acoustics engineer / environmental-noise researcher (low-cost sensor networks, EU Environmental Noise Directive, ESP32 + I2S mics)

## The question
The official Lärmkartierung shows *where* Heilbronn is loud as a modelled yearly average (Lden/Lnight, road/tram/industry only). It cannot say *when* (night trucks, 7 am rush, Friday nightlife, construction), who sits next to it (schools, Kitas, hospitals), or what it does to people. **Hörbronn** asks: at the city's eight official hotspots, what does a real 24-hour day sound like, who is exposed, and how many residents are highly annoyed or lose sleep?

## Why it matters for Heilbronn
- Heilbronn (~130k) is a legal Ballungsraum; its Stufe-IV mapping (2022, schall.tech) found trigger values exceeded "along practically all larger roads" and named 8 hotspots: Südstraße (515 residents > 65 dB Lden, 282 > 70), Karlsruher Str./Weststraße, Wilhelmstraße, Mannheimer/Weinsberger Str., Paulinenstraße, Neckartalstraße, Neckarsulmer Str., Wilhelm-Leuschner-Str. The Lärmaktionsplan Stufe IV (consultation 2024) proposes Tempo 30 on some streets and had to drop others for bus timetables.
- The plan is updated every 5 years on model output alone; the city has no measured noise data. Cheap time-resolved measurements plus a WHO 2018 health translation give the Deputy Mayor evidence for night-time Tempo 30, construction-hour rules or nightlife management.
- Beneficiaries: ~3,900 residents in the 8 hotspot areas, nearby schools/Kitas, and the Umweltamt, which keeps the sensor kit and a greencity.hn tile.

## What we build (MVP for Thursday)
- **3–5 DIY sound-level loggers**: senseBox MCU-S2 + INMP441 I2S MEMS mic (3 wires), computing A-weighted LAeq,1s on-device and uploading 1-minute LAeq/Lmax/L10/L90 over Wi-Fi (openSenseMap or own tiny API). Housed in a yoghurt cup with foam windscreen, battery-powered, taped to windows/balconies at 2–3 hotspots, 1 nightlife spot (Allee/Kaiserstraße area), 1 quiet control (park).
- **Noise walks**: phones (phyphox / NoiseCapture) log GPS-tagged levels along hotspot streets at rush hour, lunch and late evening, cross-calibrated against the loggers.
- **Map + "noise clock" dashboard tile**: hotspot segments (digitised from the official PDF), OSM sensitive receptors within 100 m, live/recorded 24-h profile per site, and a health panel (% highly annoyed, % highly sleep-disturbed per hotspot, WHO 2018) with a "night levels −3 dB (Tempo 30)" slider.
- One sensor running live at the venue during the pitch.

## Data & sources
| Source | What it gives us | URL | Verified |
|---|---|---|---|
| Betroffenheitsanalyse Lärmkartierung Stufe IV (DS 223/2023, schall.tech) | 8 hotspots, residents per Lden/Lnight class, DTV per street (e.g. 35,500 Kfz/24 h), conflict maps as PDF annexes | https://www.heilbronn.de/fileadmin/daten/stadtheilbronn/formulare/umwelt_mobilitaet/laerm/laermaktionsplan_stufe_IV/Betroffenheitsanalyse_2023/223_2023_DS_223_2023_Anlage_Betroffenheitsanalyse.pdf | yes (text extracted) |
| LUBW Lärmkartierung geodata / WMS | Lden/Lnight rasters | https://www.lubw.baden-wuerttemberg.de (Lärmkartierung) | **no** – LUBW 2022 layers cover only *outside* agglomerations; no Heilbronn WMS found. We digitise the 8 segments by hand (30 min) |
| Open Data Heilbronn: KFZ-Zählstelle Karlsruher Str./Theresienstraße; Baustellen 2021–2023 (CSV); HNV GTFS/TRIAS | traffic volume at hotspot 1, construction sites, tram timetable to attribute Stadtbahn events | https://opendata.heilbronn.de/dataset/kfz-z%C3%A4hlstelle-karlsruher-stra%C3%9Fe-theresienstra%C3%9Fe , https://opendata.heilbronn.de/dataset/bauma%C3%9Fnahmen-baustellen | partly (datasets exist; columns/geo not checked) |
| OSM via Overpass | roads, schools, Kitas, hospitals, care homes, playgrounds, bars/clubs | https://overpass-turbo.eu | yes |
| WHO Environmental Noise Guidelines 2018 | %HA = 78.927 − 3.1162·Lden + 0.0342·Lden²; %HSD = 19.4312 − 0.9336·Lnight + 0.0126·Lnight²; limits 53/45 dB | https://www.who.int/europe/publications/i/item/9789289053563 | yes (from expert knowledge) |
| senseBox MCU-S2 | ESP32-S2 with Wi-Fi, 2× I2C, UART, 3 digital/analog I/O | https://sensebox.de/en/products-boards | partly – **no official microphone exists**; I2S on the free GPIOs is plausible (S2 has an I2S peripheral) but unverified on this board |
| Open-source LAeq firmware (ikostoski esp32-i2s-slm) | A-weighted dB from INMP441/ICS-43434 on ESP32 | https://github.com/ikostoski/esp32-i2s-slm | partly – written for ESP32, needs S2/Arduino-ESP32 3.x I2S driver port |

## Technical plan
Stack: Arduino-ESP32 firmware (I2S → A-weighting IIR → LAeq) → HTTP POST to openSenseMap (free map/API) or a 50-line FastAPI + SQLite; phones export CSV; Python (pandas/geopandas) for Overpass joins and WHO formulas; MapLibre/Leaflet front end as a greencity.hn tile (React) with a static fallback.

- **Tue evening**: pick sites, source 5 INMP441 mics (someone's drawer / local shop; else phones). Flash first logger, verify I2S on S2, calibrate loggers against one phone app (offset only). Deploy logger #1 overnight at a Südstraße or Wilhelmstraße window (team member / friend). Start digitising hotspots and run Overpass queries.
- **Wed**: build and deploy 3–4 more loggers; noise walks at 7:30, 13:00, 22:00; backend + map + noise clock; health panel; collect photos and 2–3 resident quotes.
- **Thu morning**: pull 36 h of data, finalise charts, live sensor at venue, pitch rehearsal.
- **Roles (4–6)**: 2 hardware (firmware, wiring, enclosures, calibration), 1–2 data/web (GeoJSON, Overpass, WHO panel, tile), 1 non-coder field lead (site access, deployments, noise walks, interviews), 1 design/pitch (story, visuals, slides; can be non-coder).

## Demo & pitch
60 s: "Heilbronn's noise map is a yearly average computed in an office. We put ears on the street. In 36 hours our 3-euro microphones at the city's official hotspots show that Südstraße is louder at 5 am than the model assumes, that night trucks dominate, and that 500 residents and two Kitas sit in the red zone. Our noise clock tells the Umweltamt when Tempo 30 would help – and how many people would sleep better."
On screen: map with hotspots, receptors and pulsing live level from the venue sensor; the 24-h noise clock for each site; WHO health panel with the "−3 dB" slider.
Criteria: Teamwork (hardware/data/field/pitch split); Innovation (time-resolved + health lens, nobody measures noise here); Technical execution (working devices + live tile); Impact & feasibility (plugs into the 5-year LAP cycle, kit costs < 30 €, can be left with the Umweltamt); UX (one clock, one map, one slider); Presentation (live sound → live number on screen).

## Risks & fallbacks
- I2S port to the S2 fails → RMS dBFS + fixed offset without A-weighting; or phones only (phyphox "Audio Amplitude", NoiseCapture) as fixed loggers in a window.
- No mics obtainable → laptop/phone loggers; the dashboard and health analysis stand on the official data alone.
- Accuracy ±3–5 dB → state it; we compare sites and times, not legal compliance.
- Rain/wind → foam windscreen, under an eave, cup opening downwards.
- Little data → show it honestly; the pipeline is the product.

## Stretch goals
- On-phone sound classification (YAMNet) to tag traffic vs voices vs construction vs tram.
- Night event counter (> 80 dB Lmax, trucks/motorbikes) with tram timetable cross-check.
- Push loggers to sensor.community/openSenseMap for a permanent public feed; one-click "Lärmbeschwerde" letter with the resident's own data.

## Why this doesn't overlap with other teams
It uses no senseBox:bike data, ranks no routes, scores no streets for cycling safety, and touches neither heat, trees, bins nor traffic lights. It is the only proposal built on the regulatory noise dataset plus a self-built measurement device, and the only one with a health outcome.
