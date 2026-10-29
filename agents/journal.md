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
