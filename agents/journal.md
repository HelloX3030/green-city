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
