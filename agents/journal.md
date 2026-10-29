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
