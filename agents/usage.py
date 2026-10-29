#!/usr/bin/env python3
"""Session budget probe for the overnight agent chain.

Prints the Claude subscription usage (5-hour session window, weekly window) and, while a run is
active, how much of the run's budget and of the current agent's allowance is used, with a verdict.

    python3 agents/usage.py          # human-readable, one line per thing
    python3 agents/usage.py --json   # the same as JSON

The orchestrator (run.py) imports probe() and advance() from here, so both see the same numbers.
"""
import copy
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, 'run', 'state.json')
CRED = os.path.expanduser('~/.claude/.credentials.json')
URL = 'https://api.anthropic.com/api/oauth/usage'


def probe():
    """One sample of the subscription usage. Raises after three failed attempts."""
    tok = json.load(open(CRED))['claudeAiOauth']['accessToken']
    req = urllib.request.Request(URL, headers={
        'Authorization': 'Bearer ' + tok, 'anthropic-beta': 'oauth-2025-04-20', 'Accept': 'application/json'})
    err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
            break
        except Exception as e:  # network blip, token refresh in flight
            err = e
            time.sleep(2 + 3 * attempt)
    else:
        raise RuntimeError(f'usage endpoint unreachable: {err}')
    fh, wk = d.get('five_hour') or {}, d.get('seven_day') or {}
    return {
        'session_percent': fh.get('utilization'),
        'session_resets_at': fh.get('resets_at'),
        'weekly_percent': wk.get('utilization'),
        'weekly_resets_at': wk.get('resets_at'),
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }


def advance(state, sample):
    """Fold a sample into the state: consumed points grow by the utilization delta. A drop in the
    utilization is the 5-hour window turning over, then everything in the new window counts as ours.
    resets_at is not used for that: it is unreliable (microsecond jitter, sometimes missing)."""
    u, r = sample.get('session_percent'), sample.get('session_resets_at')
    if u is None:
        return state
    last_u = state.get('last_util')
    if last_u is None:
        pass
    elif float(u) < float(last_u):
        state['consumed'] = state.get('consumed', 0.0) + float(u)
    else:
        state['consumed'] = state.get('consumed', 0.0) + float(u) - float(last_u)
    state['last_util'], state['last_resets_at'] = float(u), r
    state['weekly'] = sample.get('weekly_percent')
    state['sampled_at'] = sample.get('fetched_at')
    return state


def load_state():
    try:
        return json.load(open(STATE))
    except (OSError, ValueError):
        return None


def save_state(state):
    tmp = STATE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)


def local(iso):
    """'2026-10-29T02:40:00+00:00' -> '03:40' in local time."""
    try:
        return datetime.fromisoformat(iso).astimezone().strftime('%H:%M')
    except Exception:
        return '?'


def summary(state, sample):
    """What usage.py prints: numbers and a verdict for the running agent."""
    now = datetime.now(timezone.utc)
    out = {'session_percent': sample['session_percent'], 'session_resets_at': sample['session_resets_at'],
           'weekly_percent': sample['weekly_percent']}
    lines = [f"session window: {sample['session_percent']} % used, resets {local(sample['session_resets_at'] or '')}",
             f"weekly window: {sample['weekly_percent']} %"]
    if not state or state.get('finished'):
        lines.append('no run active')
        out['verdict'] = 'no run active'
        return out, lines
    st = advance(copy.deepcopy(state), sample)
    budget, reserve = st['budget'], st['reserve']
    consumed = st['consumed']
    deadline = datetime.fromisoformat(st['deadline'])
    mins_left = (deadline - now).total_seconds() / 60
    out.update(consumed=round(consumed, 1), budget=budget, reserve=reserve,
               remaining=round(budget - consumed, 1), deadline=st['deadline'], minutes_left=round(mins_left))
    lines.append(f"run budget: {consumed:.1f} of {budget} points used, {budget - consumed:.1f} left "
                 f"({reserve} of them reserved for the final report)")
    lines.append(f"deadline: {deadline.astimezone().strftime('%H:%M')} local, {mins_left:.0f} min left for the whole chain")
    if st.get('weekly_ceiling') and sample['weekly_percent'] is not None and sample['weekly_percent'] >= st['weekly_ceiling']:
        lines.append(f"weekly window at the ceiling of {st['weekly_ceiling']} %")
    a = st.get('agent')
    verdict = 'fine'
    if a:
        used = consumed - a['start_consumed']
        mins = (now - datetime.fromisoformat(a['start_time'])).total_seconds() / 60
        out['agent'] = {'n': a['n'], 'points_used': round(used, 1), 'allowance': a['allowance'],
                        'minutes_used': round(mins), 'soft_minutes': a['soft_minutes'], 'hard_minutes': a['hard_minutes']}
        lines.append(f"agent {a['n']}: {used:.1f} of {a['allowance']} points used, {mins:.0f} of {a['soft_minutes']} min used "
                     f"(killed at {a['hard_minutes']} min or {a['allowance'] + st.get('grace_points', 0)} points)")
        if consumed >= budget - reserve or mins_left <= st.get('report_minutes', 15) + 2:
            verdict = 'STOP now: commit what is green or revert it, finish the journal entry, reply with your summary'
        elif used >= a['allowance'] or mins >= a['soft_minutes']:
            verdict = 'WRAP UP: allowance used, finish within a few minutes, commit or revert, journal, summary'
        elif used >= 0.75 * a['allowance'] or mins >= 0.75 * a['soft_minutes']:
            verdict = 'finish what is open, start nothing new'
    if sample['weekly_percent'] is not None and st.get('weekly_ceiling') and sample['weekly_percent'] >= st['weekly_ceiling']:
        verdict = 'STOP now: weekly ceiling reached, commit what is green or revert it, journal, summary'
    out['verdict'] = verdict
    lines.append('verdict: ' + verdict)
    return out, lines


def main():
    try:
        sample = probe()
    except Exception as e:
        print(f'usage unknown ({e}); treat it as "finish what is open, start nothing new"')
        return 1
    out, lines = summary(load_state(), sample)
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
