# Scenarios

The one radius (100 m, report circle, bubble discs, join rule) and its zoom floor 15 are what most report-mode checks below assert.

What `node e2e/run.mjs` drives through headless Chrome, with the position emulated (in the city, in Stuttgart, denied) and three screen sizes (360×640, 768×1024, 1440×900). Run it before every commit that touches the app, needs the dev server and the backend running. Screenshots land in `e2e/out/`, look at them, the checks only catch what they assert.

Per size
- first open: home sheet with Melden, NoiseNode pin on the map
- zoomed out to 11, Melden: flies to my position at zoom 16, circle green, Melden enabled
- send a report (Zu laut): "Gemeldet" card with "Du …", the bubble gets the green dot, close, home sheet back
- tap a bubble at zoom 15: cluster card ("n Meldungen", "Du und …" since one is mine, no "diese Woche" when all are fresh), bubble highlighted, its 100 m disc drawn, the faint discs of the others only from zoom 15
- Meine Meldungen from the home sheet: the sent report is listed with type, time, bubble size and status, a Zurückziehen button; tap on it from zoom 12 flies to its bubble at 16 with the card
- layers: Lärmkarte, Messräder, Feinstaub on at zoom 11 and 16, legend shows
- about sheet via the title pill, open and close

Phone only
- Melden with position outside Heilbronn: toast "Du bist außerhalb von Heilbronn", zooms in where it is
- Melden with position denied: toast "Standort nicht verfügbar", zooms in where it is
- report mode at zoom 15 and 16: the circle is 64 px, then 128 px (100 m on the ground), hint stays below the dot
- report mode with the centre on a bubble: bubble has a green ring, hint "Kommt zu den … Meldungen hier dazu", 150 m further: no ring, plain hint
- zoom out in report mode: circle grey, hint "Näher ranzoomen", Melden disabled, enabled again after zooming in
- drag past the city edge six times: centre stays inside the city limit, no jump after release
- jump far outside at zoom 8: centre snaps to the city limit, zoom is the min zoom, the whole city is on screen
- withdraw: Zurückziehen asks "Wirklich?", the second tap removes the row, the server has one report less, toast "Meldung zurückgezogen"
- device token: with it `/clusters` marks my bubbles (`mine`) and `/reports/mine` lists my reports, without it nothing is mine and `/reports/mine` is refused; 32 chars in localStorage, same token and same user after a reload, a cleared storage is a new user with no marked bubbles, a report without the header is refused
- backend unreachable: "Server nicht erreichbar" after the next poll, gone when it is back

Not covered, check by hand on a phone
- pinch zoom and rotation lock
- real GPS accuracy and the time until the position comes
- the sensor card for the NoiseNode (needs the live box)
- dark mode, once it exists

New feature: add its flows here and to `e2e/run.mjs` in the same commit.
