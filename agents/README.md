# Overnight agent chain

`python3 agents/run.py` runs Opus agents on this repo one after the other until a deadline or a token
budget is reached, then a last agent writes `agents/REPORT.md`. Each agent picks its own task from
the state of the repo, the git history and `agents/journal.md`, where every agent records what it
did, tried and rejected. The permission settings in `settings.json` say what an agent may do (no
push, no deploy, no kill, no edits outside app/backend/research/journal).

```
python3 agents/run.py                       # deadline 07:00, 50 points of the 5-hour window
python3 agents/run.py --deadline 06:30 --budget 40 --agent-minutes 30
python3 agents/run.py --dry-run             # print the first prompt and the settings, start nothing
python3 agents/usage.py                     # where the budget and the current agent stand
tail -f agents/run/orchestrator.log         # what the chain is doing
tail -f agents/run/agent-3.log              # what agent 3 is doing
```

Budget: "points" are percentage points of the subscription's 5-hour session window, read from the
same endpoint the `/usage` command uses; consumption is summed across window resets, so 50 points
means half a session's worth no matter when the window turns over. Everything the account uses
while the chain runs counts, including your own sessions. A weekly ceiling (`--weekly-ceiling`,
default 80 %) stops the chain so the rest of the week is not burned.

Per agent: a soft allowance in minutes and points goes into the prompt; `usage.py` tells the agent
where it stands and gives a verdict (fine / finish what is open / wrap up / stop). The orchestrator
kills an agent that runs past the hard limits and stashes what it left uncommitted (`git stash list`),
noting it in the journal for the next agent.

Files in `agents/run/` (ignored by git): `state.json`, `stats.json`, `orchestrator.log`,
`agent-N.log` (readable transcript), `agent-N.json` (the result with usage), `backend.log`,
`app.log`. The agents' Claude sessions persist, `claude --resume <session_id>` opens one.
