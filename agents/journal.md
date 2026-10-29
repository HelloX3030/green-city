# Journal of the overnight agent chain

One entry per agent, appended by the agent itself, newest at the bottom. Also the place to record
what was tried and rejected, so the next agent does not try it again blindly. Format:

```
## Agent N · HH:MM–HH:MM · X points
Picked: the task, in one line, with why
Did: one line per commit, with the hash
Tried, rejected: what, and why it was dropped
Found, left for later: ideas and bugs seen but not done, most valuable first
State: make check / make test / make e2e green? anything broken or half done?
```

## Agent 1 · 02:18–
Picked: /sensors survives a slow or dead openSenseMap/UBA during the demo (serve stale while refreshing, keep last good values per box, pins and last values from history.json when the box list cannot be fetched), since the sensor pins are half the story and a 20–30 s wait or empty map in front of the jury is the worst case

_Orchestrator: the first agent 1 (02:18–02:22, picked "sensors that survive a slow or dead openSenseMap") was aborted by the owner to fix the budget probe. Its uncommitted edits to backend/main.py and backend/sensors.py are in `git stash list` as "agent-1 leftovers (orchestrator restart 02:22)", not on the branch; the task is open. The numbering starts again at 1._

## Agent 1 (restarted) · 02:23–02:33 · usage unknown (probe 429 at the end)
Picked: the open task above, finished from the stash (reviewed, applied, tested), then the card text for bubbles without a sensor
Did: 34173a1 sensors survive a slow or dead openSenseMap/UBA (warm on start, stale answer at once with refresh behind, last good values or last hour of history.json per box, pins from history.json without the box list), backend/test_sensors.py with a client that always fails
Did: d83fb5e no_data reasons for Hitze, Luft, Lärm all read "Kein …sensor im Umkreis von 800 m. Hier fehlt ein Sensor." (story step: a sensor goes there)
Tried, rejected: a separate "Hier fehlt ein Sensor" call-out in ClusterCard: the reason line already carries it, and "sendet noch keine Daten" (no_data with a sensor) must not get it
Found, left for later: (1) `desktop: first open` failed once in the full run (NoiseNode pin not within 15 s, the scenario took 47.8 s), green alone and in the next full run: load flake of four Chromes, not the backend (/sensors answered in 2 ms); (2) the local dev DB is full of e2e reports ("Baustelle ab 6 Uhr (phone)", 236 in one bubble), the deployed DB is not ours, but a screenshot for the pitch from localhost would show them; (3) the MapLibre attribution "i" sits as a black dot top left under the title on the phone, could be styled or moved; (4) the stash "agent-1 leftovers" is now on the branch and can be dropped
State: make test green (19), make e2e 39/39 green, make check not run (no app change); tree clean

## Agent 2 · 02:32–02:34 · usage unknown (probe 429)
Picked: nothing. `agents/usage.py` answered "usage unknown (HTTP 429), finish what is open, start nothing new" twice in a row, and agent 1 left nothing open
Did: only this entry
Tried, rejected: starting a task anyway: the verdict says not to, and the probe being blind is exactly the case it guards against
Found, left for later: the list from agent 1 is still the best next work: (1) the MapLibre attribution "i" as a black dot top left on the phone, (2) e2e reports flooding the local dev DB for pitch screenshots, (3) the `desktop: first open` load flake; the stash "agent-1 leftovers" can be dropped (left, since a drop cannot be undone)
State: nothing changed in app or backend; checks not run; tree clean

## Agent 3 · 02:33–02:35 · usage unknown (probe 429)
Picked: nothing. `agents/usage.py` answered "usage unknown (HTTP 429), finish what is open, start nothing new" twice, and nothing is open
Did: only this entry
Tried, rejected: starting agent 1's list anyway: the verdict rules it out while the probe is blind
Found, left for later: the probe has now been 429 for three agents in a row (02:32–02:35); the next agent could wait a few minutes before probing, in case the endpoint limits frequent calls. Work list unchanged from agent 2: (1) MapLibre attribution "i" black dot on the phone, (2) e2e reports flooding the local dev DB, (3) `desktop: first open` load flake
State: nothing changed in app or backend; checks not run; tree clean

## Agent 4 · 02:34–02:39 · usage unknown (probe 429)
Picked: nothing. `agents/usage.py` answered "usage unknown (HTTP 429), finish what is open, start nothing new" at 02:34 and again at 02:38 after a 3 min pause, and nothing is open
Did: only this entry
Tried, rejected: waiting before probing (agent 3's idea): a 3 min pause still got 429, so it is not just the agents probing too often; starting work anyway: the verdict rules it out
Found, left for later: the probe has been 429 for four agents (02:32–02:38), for the orchestrator/owner to look at (agents/ tooling is protected). backend/history.json shows as modified: the running backend writes sensor history into it, not an agent edit; left alone. Work list unchanged: (1) MapLibre attribution "i" black dot on the phone, (2) e2e reports flooding the local dev DB, (3) `desktop: first open` load flake
State: nothing changed in app or backend; checks not run; tree clean apart from history.json written by the backend

_Orchestrator: agent 4 ended with uncommitted changes, they are in `git stash list` as "agent-4 leftovers", not on the branch. Treat its task as not done unless its commits say otherwise._

## Agent 5 · 02:39–02:41 · usage unknown (probe 429)
Picked: nothing. `agents/usage.py` answered "usage unknown (HTTP 429), finish what is open, start nothing new" at 02:39, and nothing is open: the stash "agent-4 leftovers" is only backend/history.json (one line, written by the running backend, not agent work)
Did: only this entry
Tried, rejected: starting agent 1's list anyway: the verdict rules it out while the probe is blind
Found, left for later: probe 429 for five agents now (02:32–02:39), for the orchestrator/owner (agents/ tooling is protected). Both stashes can be dropped: "agent-1 leftovers" is on the branch (34173a1), "agent-4 leftovers" is backend-written history.json. Work list unchanged: (1) MapLibre attribution "i" black dot on the phone, (2) e2e reports flooding the local dev DB, (3) `desktop: first open` load flake
State: nothing changed in app or backend; checks not run; tree clean

## Agent 6 · 02:40–02:41 · usage unknown (probe 429)
Picked: nothing. `agents/usage.py` answered "usage unknown (HTTP 429), finish what is open, start nothing new" twice at 02:40, and nothing is open (tree clean, both stashes already judged: one on the branch, one backend-written history.json)
Did: only this entry
Tried, rejected: starting agent 1's list anyway: the verdict rules it out while the probe is blind
Found, left for later: probe 429 for six agents now (02:32–02:40); the chain spends its night on empty entries until the orchestrator/owner fixes the probe (agents/ tooling is protected). Work list unchanged: (1) MapLibre attribution "i" black dot on the phone, (2) e2e reports flooding the local dev DB, (3) `desktop: first open` load flake
State: nothing changed in app or backend; checks not run; tree clean

## Agent 7 · 02:41–02:43 · usage unknown (probe 429)
Picked: nothing. `agents/usage.py` answered "usage unknown (HTTP 429), finish what is open, start nothing new" twice (02:41, 02:42), and nothing is open (tree clean)
Did: only this entry
Tried, rejected: using the orchestrator's prompt header instead of the probe (it says 0.0 of 50 points, window 16 %, weekly 30 %): those numbers look frozen too, agent 1 is listed at 0.0 points for 3 commits and a full e2e run, so the header is as blind as the probe and no reason to override its verdict
Found, left for later: probe 429 for seven agents (02:32–02:42), and the header's point counts don't move either; for the orchestrator/owner (agents/ tooling is protected). Work list unchanged: (1) MapLibre attribution "i" black dot on the phone, (2) e2e reports flooding the local dev DB, (3) `desktop: first open` load flake
State: nothing changed in app or backend; checks not run; tree clean

## Agent 8 · 02:43–02:55 · ~2 points (probe at 02:48; 429 again at 02:47 and 02:54)
Picked: the MapLibre attribution "i" that sits as a black dot under the title on the phone (agent 1 list, item 1), because it is the first thing the jury sees on the map; the probe answered "fine" at 02:43 (first run 429, second run 17 % window), so work is allowed again. Then, after a "fine" at 02:48, item 2: e2e reports flooding the local DB
Did: 4c65b01 map credits: grey "i" in a glass circle instead of the black dot; opened, the credits sat behind pins (pins go up to z-index 100), the top-left control corner now has 101; first open checks the "i" opens the credits (OpenStreetMap) and closes again
Did: b09fe0e e2e collects every device token it uses (browser tokens on goto/close and before `page.forget()` clears the device, plus the hand-made e2e-group/other/live tokens) and withdraws their reports at the end via DELETE /reports/{id}; first run withdrew 79 (incl. old ones of the fixed e2e-group tokens), second run 7, /clusters stays at 18 bubbles / 353 reports run after run
Tried, rejected: deleting the ~350 older e2e reports already in backend/reports.db (e.g. "Baustelle ab 6 Uhr (phone)"): their tokens are gone with the old Chrome profiles, it would mean deleting rows by text in sqlite, which can't be undone; left for the owner. Committing the backend-written backend/history.json: reverted it instead, the backend rewrites it hourly
Found, left for later: (1) the old e2e reports in the local DB, if the owner wants a clean localhost for screenshots: something like `DELETE FROM reports WHERE message LIKE '%(phone)%' OR …`, after a backup; (2) `phone: zoomed out, Melden flies to my position` failed once with "Failed to fetch dynamically imported module /_app/env.js" (vite load flake under four Chromes, green in the next run), same family as agent 1's `desktop: first open` flake; a retry in `goto` when `__map` never appears would hide both; (3) the probe flips between 429 and answers within minutes, so it is worth asking it again rather than giving up after one 429
State: make check green, make test green, make e2e 39/39 green (second run; first run one vite load flake); tree clean

## Agent 9 · 03:01–
Picked: the e2e load flake (agent 8 list, item 2): `goto` navigates again when vite fails to load a module and `__map` never appears, so a full run is green on the first try and the next agents trust it; probe "fine" at 03:01 after 429s and one "network unreachable"
