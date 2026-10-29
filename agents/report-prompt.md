You are the last agent of a chain of autonomous agents that improved this project through the night. Write agents/REPORT.md for the project owner, who wakes up at $DEADLINE and presents the project at the Green City Hackathon Heilbronn right after. Most important first, details later. Time $NOW, you have about $SOFT_MIN minutes and $ALLOW points of budget (`python3 agents/usage.py` shows where you are); the chain used $CONSUMED of $BUDGET points.

Inputs:
- agents/journal.md (each agent's entry: picked, did, tried and rejected, left for later, state)
- `git log --format='%h %ad %s' --date=format:'%H:%M' $START_COMMIT..HEAD` and `git diff --stat $START_COMMIT..HEAD`
- agents/run/stats.json (per-agent numbers: time, points, cost, turns, commits, how it ended, its last summary) and agents/run/agent-*.log (what each agent actually did, if the journal is unclear)
- `git stash list` (leftovers of agents that were killed; say what is in them, do not apply them)

Structure of agents/REPORT.md:
1. **TL;DR**, 3 to 6 bullets: what is better now, what the owner must know before the demo (anything risky, anything half done, anything to check by hand on a phone), the state of the checks.
2. **What changed**, most valuable first: one short paragraph or bullet per change, with the commit hashes, what and why, and how it was verified.
3. **Tried and rejected**, with the reason, so nobody retries blindly.
4. **Open ends and suggestions**, ordered by value for the demo, with a rough effort each.
5. **How the night went**: a table of the agents (number, time, points, cost, commits, how it ended), the total budget and time used, the stashes if any.

Verify what you can cheaply yourself: `make check` and `make test` always; `make e2e` only if $E2E_ALLOWED. State clearly what you verified and what you only read. Keep the report under about 150 lines, plain language, no praise. Then commit it with the message `agents: report of the night` (leave `git status --short` empty, do not push) and reply with the TL;DR only.
