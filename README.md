# green-city

Citizens report where Heilbronn is too hot, too loud or the air is bad. We check it against sensor data. Where no data exists, a sensor goes there.

Green City Hackathon Heilbronn, 27–29 Oct 2026. https://hackathon.greencity.hn/

## Customer journey

1. Joe lives in Heilbronn. Something bugs him on his way home: heat, noise, dust.
2. He scans the QR code, opens the app, taps *Report*, picks the issue. Location comes from GPS. Done.
3. His report lands on the map. Reports nearby form a cluster.
4. The cluster is checked against historical sensor data: confirmed, unconfirmed, or no data.
5. No data? A sensor pack goes to a volunteer in that area. It streams live into the same map.
6. Joe opens the map again and sees: the city listened, and now it measures.

## Run

```
make setup   # once
make dev     # backend :8000 + app :5173, phone on same wifi: http://<laptop-ip>:5173
```

## Repo

- `app/` – the web app (branch `app`)
- `NoiseNode/` – senseBox firmware (branch `hardware`)
- `resources/` – hackathon slides, Heilbronn noise maps
- `notes.md` – local scratch, untracked

## Resources

- Hackathon site and data overview: https://hackathon.greencity.hn/resources
- senseBox:home data Heilbronn: https://api.atrai.bike/collections/osem_home_data_heilbronn/items?f=json
- senseBox:bike: https://api.atrai.bike / https://data.atrai.bike
- openSenseMap: https://opensensemap.org/ – API: https://docs.opensensemap.org/#api-Measurements-getLatestMeasurements
  - senseboxID bekommst du von der opensensemap, wenn du dort ein neues device registrierst
  - sowie eine sensorID, für jedes phänomen dass eine sensebox misst. dann kannst du auch einzelne sensoren direkt abfragen
  - Beispiel: https://opensensemap.org/explore/69bd6ceb867a8a00078d3c3f – letzte Messwerte als JSON: https://api.opensensemap.org/boxes/69bd6ceb867a8a00078d3c3f
- Heilbronn open data (trees, districts): https://opendata.heilbronn.de
- Noise maps (Lärmkartierung, modelled LDEN/LNight): `resources/103-101-16-B_*.pdf` – Anlage 1 road, 2 and 3 rail/other, Kartierungsergebnisse = summary
- Air quality station Heilbronn (LUBW/UBA): station DEBW015
