# Scenarios

The one radius (100 m, report circle, bubble discs, join rule) and its zoom floor 15 are what most report-mode checks below assert.

What `node e2e/run.mjs` drives through headless Chrome, with the position emulated (in the city, in Stuttgart, denied) and three screen sizes (360×640, 768×1024, 1440×900), in four Chromes at once: one per size, one for the phone-only flows below. They share the backend, so checks against the API wait until both agree. Run it before every commit that touches the app, needs the dev server and the backend running. Screenshots land in `e2e/out/`, look at them, the checks only catch what they assert.

Per size
- first open: home sheet with Melden, NoiseNode pin on the map, map credits closed as a small grey "i" under the title, a tap opens them (OpenStreetMap …)
- zoomed out to 11, Melden: flies to my position at zoom 16, circle green, Melden enabled
- send a report (Zu laut, with a text): "Gemeldet" card with "Du …" (and "deine 2. Meldung hier heute" from the second one today), my text first in the list with a "Du" tag, the Zu-laut chip ringed, a "Nochmal melden" button, the bubble gets the green dot, close, home sheet back
- tap a bubble at zoom 15: cluster card (headline "n Meldungen", below it "Du und N andere" with N the other people since one is mine, no "diese Woche" when all are fresh, my report marked "Du" in the list, button "Nochmal melden" since I reported here today), the number on the bubble is the report count of the API, bubble highlighted, its 100 m disc drawn, the faint discs of the others only from zoom 15; type chips (icon and reports) when the bubble has more than one type or I reported here, the ones I named ringed in their colour, a tap on one filters the texts to that type and says "Zu laut · 3 Meldungen"; the sheet is at most 72 % of the screen high, with many texts it scrolls and the button at the end comes into view
- Meine Meldungen from the home sheet: the sent report is listed with type, time, bubble size and status, a Zurückziehen button; tap on it from zoom 12 flies to its bubble at 16 with the card
- layers: Lärmkarte, Messräder, Feinstaub on at zoom 11 and 16, legend shows
- filters in the Ebenen sheet: only "Zu laut" leaves the bubbles with noise reports, numbered by them; "mindestens 3" drops the small ones; "die letzten 30 Tage" refetches with that window; "Nur Bestätigte"; while set the layers button has a dot and the home sheet shows the filter line with an ×; "Zurücksetzen" or the × brings everything back, the choice survives a reload
- sensor card on a sensor the API has history for: the chart with the readout (latest value and time), "Alles" draws another line than "7 Tage", a touch on the chart reads the value under the finger with a cursor line
- about sheet via the title pill, open and close

Phone only
- Melden with position outside Heilbronn: toast "Du bist außerhalb von Heilbronn", zooms in where it is
- Melden with position denied: toast "Standort nicht verfügbar", zooms in where it is
- report mode at zoom 15 and 16: the circle is 64 px, then 128 px (100 m on the ground), hint stays below the dot
- a sensor under a bigger bubble: at zoom 15 the NoiseNode pin lies inside the runner's bubble, a tap on it opens the sensor card, small pins sit above big ones
- report mode with the centre on a bubble: bubble has a green ring, hint "Kommt zu den … Meldungen hier dazu", 150 m further: no ring, plain hint
- zoom out in report mode: circle grey, hint "Näher ranzoomen", Melden disabled, enabled again after zooming in
- drag past the city edge six times: centre stays inside the city limit, no jump after release
- jump far outside at zoom 8: centre snaps to the city limit, zoom is the min zoom, the whole city is on screen
- withdraw: Zurückziehen asks "Wirklich?", the second tap removes the row, the server has one report less, toast "Meldung zurückgezogen"
- account: Name angeben → Speichern sets the name on the server and the sheet; Anderes Gerät verknüpfen shows a 6-char code, a wrong code typed here gives the toast, a second device claims the code through the API and this one comes back to the list by itself (polls /me while the code is shown) with the other's report and "(2)" devices
- zoomed out to 12: bubbles that overlap merge (a `.group` bubble), the numbers on screen still add up to the reports of all API clusters, a tap on a group zooms in (at least a level, fitBounds on its members) where the numbers add up again
- live: a report sent from another device shows up on the bubble within 2.5 s while the event stream is up (the poll alone would take up to a minute)
- device token: with it `/clusters` marks my bubbles (`mine`) and `/reports/mine` lists my reports, without it nothing is mine and `/reports/mine` is refused; 32 chars in localStorage, same token and same user after a reload, a cleared storage is a new user with no marked bubbles, a report without the header is refused
- backend unreachable: "Server nicht erreichbar" after the next poll, gone when it is back

Not covered, check by hand on a phone
- pinch zoom and rotation lock
- real GPS accuracy and the time until the position comes
- the sensor card for the NoiseNode (needs the live box), its chart once it has a few days
- dark mode, once it exists

New feature: add its flows here and to `e2e/run.mjs` in the same commit.
