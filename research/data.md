# Data sources, verified 2026-10-27

Note: `context.md` from the earlier pass did not exist (scratchpad was empty); everything below was collected fresh.

## 1. Inventory

| Source | URL | Gives | Verified | App use |
|---|---|---|---|---|
| senseBox:home HN (atrai OGC) | `api.atrai.bike/collections/osem_home_data_heilbronn/items?f=json&limit=N&offset=M` | 2,012,544 Points: Temperature, Rel. Humidity, Pressure, Illuminance, UV Intensity, PM1/2.5/4/10, boxName/boxId/createdAt; ~8 boxes; 2026-04 to 2026-10, 1-min. `bbox`/`datetime`/`sortby` ignored → page by offset | yes, works | historical check heat/humidity/PM/light/UV |
| senseBox:bike (atrai) | `api.atrai.bike/collections/osem_bike_data/items?f=json&bbox=9.1,49.1,9.3,49.2` | 1,474,744 Points: Temperature, Humidity, PM1-10, Overtaking Distance, Speed, Surface_*; 2025-12 to 2026-10 | yes, works | historical check PM along streets |
| atrai derived HN layers | `.../collections/{danger_zones_PM_heilbronn,speed_map_heilbronn,traffic_flow_heilbronn,bumpy_roads_heilbronn,overtaking_distance_heilbronn}/items?f=json` | danger_zones_PM: 183,030 Points `Risk Index`; others LineStrings per OSM segment | yes, works | map layer (PM risk heatmap) |
| data.atrai.bike | `https://data.atrai.bike` | React SPA, no API | yes, SPA | none |
| openSenseMap | `api.opensensemap.org/boxes?bbox=9.1,49.1,9.3,49.2&format=json`; `/boxes/{id}/sensors`; `/boxes/{id}/data/{sensorId}?from-date=&to-date=` | 71 boxes in bbox, ~9 outdoor live today (Innenstadt `69bd6ceb867a8a00078d3c3f`, Schulgarten, GreenCity OpenSpace, KI-Pavillon, THW, Neckargartach, Festplatz, Sternwarte); 5-min values since 2026-03 (1,901 rows/7 d). Team NoiseNode `6ae0d7aa4bc0370008dba0f7`, sensor `…dba0f8` dB(A), 0 readings | yes, works | live pin + history |
| Birdiary | `wiediversistmeingarten.org/api/station`; `/api/station/{id}` | 183 stations, 9 near HN (Open Space Heilbronn live today); lat/lng, lastEnvironment temp/humidity, bird counts per day. `/api` root = 404, no environment-history endpoint | yes, works | live pin (biodiversity) |
| Mobile Datalogger (Summerschool) | `cloud.reedu.de/s/X9x2XE9a9xCxLm8` → WebDAV `cloud.reedu.de/public.php/webdav/datasets/alles.csv` (user = share token) | CSV `timestamp,latitude,longitude,temperature,humidity,gps_speed`; walks 2026-09-02 (Wartberg, Neckar, Innenstadt); 7.7 MB | yes, works | seed heat-walk layer |
| Bright Sky (DWD) | `api.brightsky.dev/current_weather?lat=49.14&lon=9.22`; `/alerts?lat&lon`; `/weather?lat&lon&date&last_date` | current obs; alerts (none today); hourly history. DWD Heilbronn 15547 wind-only since 2016; temp/humidity fall back to Obersulm-Willsbach 03734 (10 km, since 2010) | yes, works | weather context + heat-day history |
| Open-Meteo | `api.open-meteo.com/v1/forecast?…&current=temperature_2m,uv_index`; `archive-api.open-meteo.com/v1/archive`; `air-quality-api.open-meteo.com/v1/air-quality` | model values, not measured: temp, RH, UV index, PM10/PM2.5/NO2, EAQI; hourly archive | yes, works | weather/UV context |
| UBA air quality | `luftdaten.umweltbundesamt.de/api/air-data/v3/measures/json?date_from=…&time_from=1&date_to=…&time_to=24&station=DEBW015&component={1,3,5,9}&scope=2` (old host 301s) | DEBW015 Heilbronn (49.1655, 9.2248), urban background, since 1979; hourly PM10(1), O3(3), NO2(5), PM2.5(9); 2016 tested; latest 16:00 today; `/airquality/json` = index | yes, works | historical check air quality |
| OpenData Heilbronn (DKAN) | `opendata.heilbronn.de/data.json` (follow 302), `/api/3/action/package_list` | 140 datasets. Baumkataster shapefile EPSG4326 (zip 1.4 MB); Planungsbezirke shapefile EPSG4326 (101 KB); Stadtkreisgrenze GeoJSON; `KlimadatenKalendarjahr.csv` 1961– (heisse Tage, Tropennächte) | yes, works | map layer trees/districts; heat-day history |
| Noise: UBA Lärmkartierung 2022 | `datahub.uba.de/server/rest/services/VeLa/LK/MapServer` — raster: `/export?bbox={x1,y1,x2,y2}&bboxSR=3857&imageSR=3857&size=512,512&layers=show:4210&format=png32&transparent=true&f=image`; vector: `/4210/query?…&f=geojson` | Layer 4210 LK_BLR_road_Den (Lden 55-59…>75, roadsInAgglomeration) covers Heilbronn centre (125,806 px in test tile); 4220 night, 5210 rail, 7210 industry. GeoJSON = 5 state-wide MultiPolygons, 10 MB | yes, works | map layer modelled noise |
| Noise: LUBW INSPIRE WMS | `rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/GDI/INSPIRE_Gesundheit_Laerm/MapServer/WMSServer` | 2017, main roads outside agglomerations; 0 features in HN centre | yes, empty for HN | none |
| Noise: city PDFs | `resources/103-101-16-B_*.pdf`; 2022 Stufe IV report on heilbronn.de | PDF only; no WMS/GeoJSON on GovData or geoportal.heilbronn.de | yes, PDF only | fallback |
| Basemaps | `tiles.openfreemap.org/styles/{liberty,positron}`; `basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json`; `tile.openstreetmap.org/{z}/{x}/{y}.png`; `demotiles.maplibre.org/style.json` | all no-key, CORS `*`. Protomaps and MapTiler → 403 without key | yes, works | basemap |
| Overpass | `overpass.osm.ch/api/interpreter` | overpass-api.de, lz4, kumi, private.coffee, mail.ru unreachable from sandbox; osm.ch 200, CORS `*` | yes, osm.ch only | OSM POIs |
| Green City Dashboard, Smart City Data Library, MobiData BW, DWD Open Data, Beehive Grafana | greencity.hn; data-library.smartcity.hn (empty SPA); mobidata-bw.de; opendata.dwd.de | on hackathon page | unverified | none |

## 2. Gaps (historical measurement data in Heilbronn)

- Temperature: no gap (UBA none; DWD via Obersulm since 2010; senseBox:home in-city since 2026-03).
- Humidity: no gap (same sources as temperature).
- Air quality: no gap (UBA DEBW015 since 1979; senseBox PM since 2026-03).
- Noise: GAP — zero measured history; only modelled Lden/Lnight 2022; NoiseNode has 0 readings.
- Light: partial — Illuminance only since 2026-03 (senseBox:home), nothing earlier.
- UV: partial — UV Intensity since 2026-03, UV Index field null; Open-Meteo is model only.

## 3. Cheap impressive layers

1. Road noise Lden 2022 — UBA datahub `export` PNG, MapLibre raster source `tiles: [".../export?bbox={bbox-epsg-3857}&…layers=show:4210…"]`.
2. Trees — Baumkataster shapefile → GeoJSON (convert once, ogr2ogr/mapshaper), circle or heatmap layer.
3. PM danger zones — atrai `danger_zones_PM_heilbronn` GeoJSON (Risk Index), heatmap layer.

## 4. CORS

- Direct from browser (`Access-Control-Allow-Origin: *`): api.atrai.bike, api.opensensemap.org, wiediversistmeingarten.org/api, api.brightsky.dev, open-meteo (all 3 hosts), overpass.osm.ch, OpenFreeMap, CARTO, OSM tiles.
- Reflects Origin (works in browser): datahub.uba.de, rips-gdi.lubw.
- No ACAO header seen → proxy or fetch at build time: luftdaten.umweltbundesamt.de, opendata.heilbronn.de, cloud.reedu.de WebDAV.

## 5. Snippets

senseBox:home item (`api.atrai.bike/...osem_home_data_heilbronn/items?f=json&limit=1`):
```json
{"type":"Feature","geometry":{"type":"Point","coordinates":[9.11055,49.143947]},
 "properties":{"boxId":"69bd6c0f867a8a00078becd4",
  "boxName":"SenseBox Eichbottschule Leingarten",
  "createdAt":"2026-04-25T09:12:29.121",
  "Temperature":18.7,"Rel. Humidity":41.79,"Pressure":997.56,
  "Illuminance":952,"UV Intensity":196.88,"UV Index":null,
  "Finedust PM1":6.05,"Finedust PM2.5":6.4,"Finedust PM10":6.4}}
// top level: "numberMatched":2012544
```

openSenseMap latest (`api.opensensemap.org/boxes/69bd6ceb867a8a00078d3c3f/sensors`):
```json
{"_id":"69bd6ceb867a8a00078d3c3f","sensors":[
 {"_id":"69bd6ceb867a8a00078d3c40","title":"Temperatur","unit":"°C",
  "lastMeasurement":{"value":"16.6","createdAt":"2026-10-27T17:01:54.887Z"}},
 {"_id":"69bd6ceb867a8a00078d3c46","title":"PM25","unit":"µg/m³", ...}]}
// history: /boxes/{id}/data/{sensorId}?from-date=…&to-date=…&format=json
// → [{"value":"16.6","location":[9.221977,49.142487,165],"createdAt":"…"}]
```
