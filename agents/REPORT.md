# Report of the night, 29 Oct 2026 (02:18–06:34)

## TL;DR

- **Better now:** the demo flow on the phone is smoother. A first open no longer throws 500s. The map still shows bubbles when the Carto basemap is down. A spot without a sensor now says "Sensor fehlt" and gives its rank, as the pitch tells it. "Kein Schatten" is checked against the Baumkataster. iOS no longer zooms in when you tap a text field. Enter sends on the phone keyboard. Long bubble cards fold after five texts. The app has a real home-screen icon.
- **Do this before the demo:** the local DB `backend/reports.db` still holds about 90 old e2e test texts ("Baustelle ab 6 Uhr (phone/tablet/desktop)") plus "kek" and "kek2". "kek"/"kek2" show on the 55-report "Sensor fehlt" card at the Hauptbahnhof, which is the demo's heat spot. The others now sit behind "Alle N Texte zeigen". No agent deleted them because it can't be undone. If the demo runs on this DB: make a backup, then `DELETE FROM reports WHERE message LIKE 'Baustelle ab 6 Uhr (%' OR message IN ('kek','kek2');`.
- **Check by hand on a real phone (only measured in headless Chrome so far):** 1. Tap "Ein Satz dazu" on iOS: the page must not zoom. 2. Press Enter on the keyboard: it should send. 3. "Zum Home-Bildschirm" should show the green leaf. 4. The green Android address bar from theme-color `#3a7d5c`: change it to `#ededeb` in `app/src/app.html` if it looks too heavy.
- **Known rough edge:** the dev backend (`make backend`, `--reload`) can hang for minutes after a backend file changes while a phone holds `/events` open. Don't edit backend files during the demo.
- **Checks:** I ran `make check` (0 errors, 0 warnings) and `make test` (29/29 OK) myself at about 06:37. I did not run `make e2e` (not enough time left). Agent 37's full run was 44/44 green at 06:28, and no app or backend code has changed since 06:23 (114fb2a).

## What changed (most valuable for the demo first)

How each change was verified comes from the journal unless I say otherwise. "e2e" means a new or tightened check in `app/e2e/run.mjs`, and a full `make e2e` was green after the change.

1. **No 500s on a new phone's first open** (64bb534). `/me` and `/reports/mine` arrive together, and both tried to create the device: `UNIQUE devices.token`, 31 times in backend.log. Now `INSERT OR IGNORE` and the first request's user is reused. Verified with test_db and live with 20 tokens × 4 parallel requests, all 200.
2. **Sensors survive a slow or dead openSenseMap/UBA** (34173a1). They are fetched on start, a stale answer is served at once while the refresh runs behind it, a dead box keeps its last values, and the pins come from history.json. Verified with test_sensors.
3. **Map works without the basemap** (c7e4ec3). If Carto's style.json fails, or takes 15 s, the map falls back to a plain background and bubbles and pins still come. Before, the map stayed grey and empty; this happened once at 02:24. Verified by an e2e that blocks basemaps.cartocdn.com.
4. **The "Sensor fehlt" beat** (d83fb5e, f0bf68a, 051b615). A bubble with no sensor nearby shows a readable "Sensor fehlt" pill instead of a light grey "Keine Daten". The reason says "Hier fehlt ein Sensor", and a line says "Platz 1 von 8 Stellen ohne Sensor, nach Meldungen", which leads to the ask for the next sensors. Verified by e2e on all sizes.
5. **Kein Schatten is checked against the Baumkataster** (4d93428, 6bfb981). Fewer than 10 city trees within 100 m → Bestätigt; otherwise Unbestätigt with the count. Adds `backend/trees.json` (808 KB), because the docker context of the backend can't see app/static. The threshold of 10 is a judgement call. The about sheet now says what is actually compared. Verified with 5 tests in test_status and e2e.
6. **Reporting on the phone** (2ae57cb, a187aed, 834be51, 705d900, f9d5122, d59b959):
   - Inputs are 16 px, so iOS doesn't zoom in.
   - Enter sends a report, saves the name and links the code. A busy flag stops a double claim.
   - The crosshair dot no longer garbles the joined bubble's number.
   - A message of only spaces is stored as no text. This is fixed in both backend and app, with a backend test.
   - When the filter hides the new bubble, a toast says "Gemeldet, vom Filter ausgeblendet".
7. **Bubble card readability** (123e032, 1ba921b, bd4fa9f, d4e31c0, 1fcabbc, 3feaa28, 2ea380f, 225223b):
   - The card shows five texts and "Alle N Texte zeigen". The biggest card had ~90 texts and pushed "Hier auch melden" far down.
   - New lines "und N Meldungen ohne Text" and "Du und 146 andere Personen".
   - No-break spaces keep "vor 53 min", "letzte …" and units like dB(A) together at 360 px.
8. **Map numbers and credits** (5d7bda6, fff535b, 4c65b01). A sensor pin no longer hides a bubble's number; the number moves to a badge. The black MapLibre dot under the title is now a grey "i" that opens above the pins.
9. **Sensor card** (42fa383, 49d5c13, d6ca33a, 114fb2a):
   - The header says "Messwert vor 1 h" instead of "live · vor 1 h", or "offline · letzter Wert vor 3 Tagen".
   - Tapping the Temperatur or PM2,5 tile switches the chart.
   - The PM2,5 chart no longer shows a "-3,3" tick.
   - "Sensor fehlt" no longer breaks over two lines in Meine Meldungen (58f2704).
10. **Page metadata and icon** (41500b4, fe95f17). `lang="de"` (Chrome on Android stopped offering to translate), a title, the leaf favicon instead of the Svelte logo, apple-touch-icon and 192/512 PNGs, and a web manifest with no `display` mode, so the app opens in the browser as before. Verified by e2e: the icons load as PNGs of the right size.
11. **More trustworthy e2e** (b09fe0e, b73de3d, 32caa4e, 4acff73, 40981cc):
    - e2e withdraws its own test reports, even after a run that died.
    - It retries a page load that vite broke.
    - A scenario now fails on console errors and failed requests to the app or the backend, not only on uncaught exceptions.
    - A flaky pin tap is fixed.
    - Scenarios went from 39 to 44.

Size: 33 files, +1061/−86 (5767321..HEAD), plus the journal commits.

## Tried and rejected

- **Deleting the old e2e reports from the DB:** their device tokens are lost, so it would mean deleting rows by text in SQLite, which can't be undone. Left for you (see TL;DR).
- **`maximum-scale=1` against the iOS zoom:** it blocks pinch-zoom (accessibility). The 16 px inputs fix the cause instead.
- **`display: "standalone"` in the manifest:** it changes the back button and link behaviour, and there was no real phone to test on.
- **`--timeout-graceful-shutdown 2` for the reload hang:** it could not be verified (starting a test uvicorn was denied), so it was reverted.
- **PM10 in the sensor chart:** it needs a PM10 history refetch upstream (a minute or more per box) that rewrites the tracked history.json. Too risky this close to the demo.
- **Moving the credits "i" off the edge of the "22" bubble:** the only free corner is under the title. The overlap is harmless and depends on the map position.
- **Hiding the "−" zoom button that peeks above tall sheets:** it only shows in narrow desktop windows; real phones hide the zoom buttons.
- **A longer filter toast text:** it ran under the Ebenen button at 360 px.
- **A 15 s e2e load timeout:** it would restart slow but working cold loads; 30 s plus an early retry on vite errors is used instead.
- **Starting work while `agents/usage.py` was blind (429):** the budget rule says "start nothing new". This cost agents 2–7 and 36–40 their turns.

## Open ends and suggestions (by value for the demo)

1. **Clean the junk texts from `backend/reports.db`** if the demo uses this DB: 2 min (command in the TL;DR, back up first).
2. **Check the four points on a real phone** (TL;DR): 5 min.
3. **Run `make e2e` once more before you leave**, about 3 min. Don't edit app files while it runs: vite's reload breaks scenarios. Seeing "loading again" in the output is normal.
4. **Add `--timeout-graceful-shutdown 2`** to the uvicorn line of `make backend`, then test that an edit reloads while a browser is open: 10 min. Only matters if you edit the backend live.
5. **PM10 chart:** 30+ min including a history refetch. After the demo.
6. **`display: "standalone"`** for a home-screen app without an address bar: 15 min including a phone test.
7. **Fix `agents/usage.py`, which returned HTTP 429 most of the night**, for the next chain. Agents worked in short "fine" windows between 429s.

## How the night went

All 40 agents ended "finished"; none was killed. Points are as the stats recorded them: most agents show 0 because the probe was blind. The counts were frozen until about 02:42, so agent 1's work is not counted.

| # | time | pts | $ | commits | result |
|---|---|---|---|---|---|
| 1 | 02:23–02:32 | 0 | 1.00 | 3 | sensors resilient, Sensor-fehlt reason |
| 2–7 | 02:32–02:42 | 0 | 1.19 | 6 | probe 429, journal only |
| 8 | 02:42–02:55 | 2 | 1.28 | 4 | credits "i", e2e cleans up |
| 9 | 02:55–03:04 | 0 | 0.65 | 3 | e2e load retry |
| 10 | 03:04–03:08 | 0 | 0.89 | 3 | first-open 500 fix |
| 11 | 03:08–03:25 | 2 | 1.86 | 6 | bubble numbers, units, time column |
| 12 | 03:25–03:36 | 0 | 1.26 | 4 | basemap fallback, "Personen" |
| 13 | 03:36–03:41 | 0 | 1.03 | 3 | Sensor fehlt pill |
| 14 | 03:41–03:48 | 0 | 0.85 | 4 | time no-break |
| 15 | 03:48–03:56 | 1 | 0.80 | 3 | crosshair dot |
| 16 | 03:56–04:04 | 1 | 0.73 | 3 | sensor header |
| 17 | 04:04–04:19 | 1 | 2.01 | 3 | Baumkataster for shade |
| 18 | 04:19–04:30 | 0 | 0.83 | 3 | about sheet |
| 19 | 04:30–04:37 | 1 | 0.83 | 3 | 16 px inputs |
| 20 | 04:37–04:49 | 0 | 1.51 | 5 | no-breaks, e2e token file |
| 21 | 04:49–04:54 | 1 | 0.93 | 3 | rank without sensor |
| 22 | 04:54–05:12 | 0 | 1.25 | 3 | lang=de, favicon |
| 23 | 05:12–05:16 | 1 | 0.78 | 3 | home-screen icons |
| 24 | 05:16–05:24 | 0 | 0.88 | 3 | e2e fails on console errors |
| 25 | 05:24–05:29 | 0 | 0.60 | 3 | "ohne Text" count |
| 26 | 05:29–05:34 | 1 | 0.79 | 3 | fold texts at five |
| 27 | 05:34–05:40 | 0 | 1.15 | 3 | filtered Gemeldet toast |
| 28 | 05:40–05:44 | 1 | 0.50 | 3 | "Meldungen ohne Text" |
| 29 | 05:44–05:53 | 0 | 0.95 | 3 | trim blank messages |
| 30 | 05:53–06:00 | 0 | 0.76 | 3 | Enter sends |
| 31 | 06:00–06:05 | 1 | 0.83 | 3 | Enter in Meine Meldungen |
| 32 | 06:05–06:12 | 0 | 0.97 | 3 | tiles switch chart |
| 33 | 06:12–06:19 | 1 | 0.54 | 3 | flaky pin tap in e2e |
| 34 | 06:19–06:24 | 0 | 0.57 | 3 | PM2,5 scale at 0 |
| 35–40 | 06:24–06:33 | 0 | 1.93 | 7 | checks, e2e 44/44, journal only |

**Total:** 14.0 of 50 points, about $30.15, 02:18–06:34 (about 4 h 15 min).

**Stashes (not applied):** both can be dropped.
- `stash@{1}` "agent-1 leftovers": `backend/main.py` and `backend/sensors.py`, already on the branch as 34173a1.
- `stash@{0}` "agent-4 leftovers": a one-line change to `backend/history.json` that the running backend wrote, not agent work.

**What I verified myself:** `make check` and `make test`, the git log and diff stat, the stash contents (by stat). Everything else is from the journal and `agents/run/stats.json`.
