# Scenarios

What `node e2e/run.mjs` drives through headless Chrome, with the position emulated (in the city, in Stuttgart, denied) and three screen sizes (360×640, 768×1024, 1440×900). Run it before every commit that touches the app, needs the dev server and the backend running. Screenshots land in `e2e/out/`, look at them, the checks only catch what they assert.

Per size
- first open: home sheet with Melden, NoiseNode pin on the map
- zoomed out to 11, Melden: flies to my position at zoom 16, circle green, Melden enabled
- send a report (Zu laut): "Gemeldet" card, close, home sheet back
- tap a bubble at zoom 15: cluster card, bubble highlighted
- layers: Lärmkarte, Messräder, Feinstaub on at zoom 11 and 16, legend shows
- about sheet via the title pill, open and close

Phone only
- Melden with position outside Heilbronn: toast "Du bist außerhalb von Heilbronn", zooms in where it is
- Melden with position denied: toast "Standort nicht verfügbar", zooms in where it is
- zoom out in report mode: circle grey, hint "Näher ranzoomen", Melden disabled, enabled again after zooming in
- drag past the city edge six times: centre stays inside the city limit, no jump after release
- jump far outside at zoom 8: centre snaps to the city limit, zoom is the min zoom, the whole city is on screen
- backend unreachable: "Server nicht erreichbar" after the next poll, gone when it is back

Not covered, check by hand on a phone
- pinch zoom and rotation lock
- real GPS accuracy and the time until the position comes
- the sensor card for the NoiseNode (needs the live box)
- dark mode, once it exists

New feature: add its flows here and to `e2e/run.mjs` in the same commit.
