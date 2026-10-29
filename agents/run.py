#!/usr/bin/env python3
"""Overnight chain of Opus agents on this repo. See agents/README.md.

One agent at a time: it gets the situation (time, budget, previous agents, the owner's notes),
picks its own task, verifies, commits, writes the journal. The orchestrator samples the
subscription usage every minute, kills an agent past its hard limits, stashes leftovers, keeps the
dev servers up, and ends with a report agent plus its own final checks.
"""
import argparse
import copy
import json
import os
import shutil
import signal
import socket
import string
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(HERE, 'run')
sys.path.insert(0, HERE)
from usage import probe, advance, load_state, save_state, STATE  # noqa: E402

LOG = None
CURRENT = {'proc': None}


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if LOG:
        LOG.write(line + '\n')
        LOG.flush()


def sh(cmd, check=True, **kw):
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, **kw)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def parse_deadline(s):
    """'07:00' is the next time it is 07:00; an ISO datetime is taken as is."""
    if len(s) == 5 and s[2] == ':':
        now = datetime.now().astimezone()
        d = now.replace(hour=int(s[:2]), minute=int(s[3:]), second=0, microsecond=0)
        if d <= now:
            d += timedelta(days=1)
        return d
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.astimezone()


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


class Servers:
    """backend :8000 and app :5173, each in its own process group, logs in agents/run/."""

    def __init__(self, enabled):
        self.enabled = enabled
        self.procs = {}

    def start(self, name, cmd, port):
        if port_open(port):
            log(f'{name}: port {port} already in use, leaving it to whoever runs it')
            return
        out = open(os.path.join(RUN, f'{name}.log'), 'a')
        self.procs[name] = subprocess.Popen(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                                            start_new_session=True)
        for _ in range(120):
            if port_open(port):
                log(f'{name}: up on :{port}')
                return
            time.sleep(0.5)
        log(f'{name}: not up on :{port} after 60 s, see agents/run/{name}.log')

    def ensure(self):
        if not self.enabled:
            return
        for name, cmd, port in (('backend', ['make', '-s', 'backend'], 8000), ('app', ['make', '-s', 'app'], 5173)):
            p = self.procs.get(name)
            if p and p.poll() is not None:
                log(f'{name}: exited with {p.returncode}, restarting')
                del self.procs[name]
            if not port_open(port):
                self.start(name, cmd, port)

    def stop(self):
        for name, p in self.procs.items():
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for name, p in self.procs.items():
            try:
                p.wait(15)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
        self.procs = {}


def readable(event, f):
    """One stream-json event -> lines of the human log."""
    ts = datetime.now().strftime('%H:%M:%S')
    t = event.get('type')
    if t == 'system' and event.get('subtype') == 'init':
        f.write(f"[{ts}] session {event.get('session_id')} model {event.get('model')}\n")
        return
    msg = event.get('message') if isinstance(event.get('message'), dict) else None
    content = msg.get('content') if msg else None
    if not isinstance(content, list):
        return
    for b in content:
        kind = b.get('type')
        if kind == 'text' and b.get('text', '').strip():
            f.write(f"[{ts}] {b['text'].strip()}\n")
        elif kind == 'tool_use':
            inp = b.get('input') or {}
            short = inp.get('command') or inp.get('file_path') or inp.get('pattern') or inp.get('url') \
                or inp.get('description') or inp.get('prompt') or json.dumps(inp)[:200]
            f.write(f"[{ts}] > {b.get('name')}: {str(short).strip()[:300]}\n")
        elif kind == 'tool_result':
            c = b.get('content')
            if isinstance(c, list):
                c = ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
            first = str(c or '').strip().splitlines()[:1]
            mark = '!' if b.get('is_error') else '<'
            f.write(f"[{ts}] {mark} {first[0][:200] if first else ''}\n")
    f.flush()


def run_claude(prompt, name, model, settings_json, deadline, state, hard_minutes, kill_points, servers):
    """Run one headless agent, poll usage every minute, kill past the hard limits.
    Returns (result dict or None, how it ended, points used)."""
    log_path = os.path.join(RUN, f'{name}.log')
    cmd = ['claude', '-p', '--model', model, '--output-format', 'stream-json', '--verbose',
           '--permission-mode', 'dontAsk', '--setting-sources', 'project', '--settings', settings_json]
    err = open(log_path + '.err', 'a')
    proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                            text=True, start_new_session=True)
    proc.stdin.write(prompt)
    proc.stdin.close()
    CURRENT['proc'] = proc
    result = {}

    def reader():
        with open(log_path, 'a') as f:
            f.write(f"\n===== {name} started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    f.write(line[:500] + '\n')
                    continue
                if ev.get('type') == 'result':
                    result.update(ev)
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] result: {ev.get('subtype')} "
                            f"turns={ev.get('num_turns')} cost=${ev.get('total_cost_usd', 0):.2f}\n")
                else:
                    readable(ev, f)

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    started = time.time()
    start_consumed = state['consumed']
    last_probe = time.time()
    ended = 'finished'
    while proc.poll() is None:
        time.sleep(5)
        if time.time() - last_probe >= 60:
            last_probe = time.time()
            try:
                advance(state, probe())
                save_state(state)
            except Exception as e:
                log(f'usage probe failed: {e}')
        used = state['consumed'] - start_consumed
        mins = (time.time() - started) / 60
        mins_left = (deadline - datetime.now().astimezone()).total_seconds() / 60
        reason = None
        if state['consumed'] >= state['budget']:
            reason = f"budget ceiling reached ({state['consumed']:.1f} of {state['budget']} points)"
        elif used >= kill_points:
            reason = f'agent used {used:.1f} points, kill at {kill_points}'
        elif mins >= hard_minutes:
            reason = f'agent ran {mins:.0f} min, kill at {hard_minutes}'
        elif mins_left <= 1:
            reason = 'deadline reached'
        elif state.get('weekly') is not None and state.get('weekly_ceiling') and state['weekly'] >= state['weekly_ceiling']:
            reason = f"weekly ceiling reached ({state['weekly']} %)"
        if reason:
            log(f'{name}: killing: {reason}')
            ended = 'killed: ' + reason
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(30)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            break
    th.join(10)
    err.close()
    CURRENT['proc'] = None
    try:
        advance(state, probe())
        save_state(state)
    except Exception as e:
        log(f'usage probe failed: {e}')
    if result:
        with open(os.path.join(RUN, f'{name}.json'), 'w') as f:
            json.dump(result, f, indent=1)
        if result.get('is_error') or result.get('subtype') != 'success':
            ended = f"error: {result.get('subtype')} {str(result.get('result', ''))[:200]}"
    elif ended == 'finished':
        ended = f'exited with {proc.returncode} and no result'
    return result, ended, state['consumed'] - start_consumed


def git_status():
    return sh(['git', 'status', '--porcelain'], check=False)


def tidy(name, n):
    """Stash what an agent left uncommitted and tell the next agent in the journal."""
    if not git_status():
        return False
    sh(['git', 'stash', 'push', '-u', '-m', f'{name} leftovers'], check=False)
    if git_status():  # something stash could not take, drop it rather than ship it
        sh(['git', 'checkout', '--', '.'], check=False)
        sh(['git', 'clean', '-fd', '--', 'app/src', 'backend', 'research', 'agents/journal.md'], check=False)
    with open(os.path.join(HERE, 'journal.md'), 'a') as f:
        f.write(f"\n_Orchestrator: agent {n} ended with uncommitted changes, they are in `git stash list` as "
                f"\"{name} leftovers\", not on the branch. Treat its task as not done unless its commits say otherwise._\n")
    sh(['git', 'add', 'agents/journal.md'])
    sh(['git', 'commit', '-q', '-m', f'agents: agent {n} left uncommitted work, stashed'])
    log(f'{name}: leftovers stashed')
    return True


def prev_table(state):
    rows = state.get('agents', [])
    if not rows:
        return '  (none, you are the first)'
    out = []
    for a in rows:
        s = (a.get('summary') or '').strip().replace('\n', ' / ')
        out.append(f"  - agent {a['n']} {a['start']}–{a['end']}: {a['points']:.1f} points, {a['commits']} commit(s), "
                   f"{a['ended']}. Summary: {s[:400] or '(none)'}")
    return '\n'.join(out)


def final_checks():
    out = []
    for target in ('check', 'test'):
        r = subprocess.run(['make', '-s', target], cwd=ROOT, text=True, capture_output=True)
        tail = '\n'.join((r.stdout + r.stderr).strip().splitlines()[-3:])
        out.append(f"- `make {target}`: {'green' if r.returncode == 0 else 'FAILED'}\n```\n{tail}\n```")
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--deadline', default='07:00', help='HH:MM local (next occurrence) or ISO datetime')
    ap.add_argument('--budget', type=float, default=50, help='points of the 5-hour window the chain may use in total')
    ap.add_argument('--reserve', type=float, default=3, help='points kept for the report agent')
    ap.add_argument('--agent-points', type=float, default=12, help='soft allowance per agent')
    ap.add_argument('--grace-points', type=float, default=4, help='an agent is killed this far past its allowance')
    ap.add_argument('--agent-minutes', type=int, default=40, help='soft allowance per agent')
    ap.add_argument('--grace-minutes', type=int, default=15, help='an agent is killed this far past its minutes')
    ap.add_argument('--min-agent-minutes', type=int, default=12, help='no new agent with less than this left')
    ap.add_argument('--min-agent-points', type=float, default=4, help='no new agent with less than this left')
    ap.add_argument('--report-minutes', type=int, default=15)
    ap.add_argument('--weekly-ceiling', type=float, default=80, help='stop when the weekly window reaches this')
    ap.add_argument('--model', default='opus')
    ap.add_argument('--branch', default='agents-improvement')
    ap.add_argument('--max-agents', type=int, default=99)
    ap.add_argument('--no-servers', action='store_true', help='do not start backend and app')
    ap.add_argument('--fresh', action='store_true', help='forget a previous unfinished run')
    ap.add_argument('--dry-run', action='store_true', help='print the first prompt, start nothing')
    args = ap.parse_args()

    global LOG
    os.makedirs(RUN, exist_ok=True)
    LOG = open(os.path.join(RUN, 'orchestrator.log'), 'a')
    deadline = parse_deadline(args.deadline)
    settings = json.load(open(os.path.join(HERE, 'settings.json')))
    settings_json = json.dumps(settings)
    notes_path = os.path.join(ROOT, 'notes.md')
    notes = open(notes_path).read().strip() if os.path.exists(notes_path) else '(notes.md is missing)'
    worker_tpl = string.Template(open(os.path.join(HERE, 'worker-prompt.md')).read())
    report_tpl = string.Template(open(os.path.join(HERE, 'report-prompt.md')).read())

    # preflight
    if not shutil.which('claude'):
        sys.exit('claude is not on PATH')
    branch = sh(['git', 'branch', '--show-current'])
    if branch != args.branch:
        sys.exit(f'on branch {branch}, expected {args.branch} (--branch to override)')
    if git_status() and not args.dry_run:
        sys.exit('working tree is not clean, commit or stash first:\n' + git_status())
    sample = probe()
    log(f"usage now: session {sample['session_percent']} % (resets {sample['session_resets_at']}), "
        f"weekly {sample['weekly_percent']} %")

    state = None if args.fresh else load_state()
    if state and state.get('finished'):
        state = None
    if state:
        log(f"resuming run started {state['started_at']}, {state['consumed']:.1f} points consumed, "
            f"{len(state['agents'])} agents done")
        state['deadline'] = deadline.isoformat()
    else:
        state = {'started_at': datetime.now().astimezone().isoformat(timespec='seconds'),
                 'start_commit': sh(['git', 'rev-parse', '--short', 'HEAD']),
                 'deadline': deadline.isoformat(), 'budget': args.budget, 'reserve': args.reserve,
                 'grace_points': args.grace_points, 'report_minutes': args.report_minutes,
                 'weekly_ceiling': args.weekly_ceiling, 'consumed': 0.0, 'agents': [], 'agent': None,
                 'finished': False}
    state['weekly_ceiling'] = args.weekly_ceiling
    advance(state, sample)
    if not args.dry_run:
        save_state(state)
    log(f"deadline {deadline.strftime('%Y-%m-%d %H:%M')}, budget {args.budget} points (reserve {args.reserve}), "
        f"start commit {state['start_commit']}, model {args.model}")

    def situation(n, soft_min, hard_min, allow):
        now = datetime.now().astimezone()
        return dict(N=n, NOW=now.strftime('%H:%M'), DEADLINE=deadline.strftime('%H:%M'),
                    MIN_LEFT=f"{(deadline - now).total_seconds() / 60:.0f}", SOFT_MIN=soft_min, HARD_MIN=hard_min,
                    ALLOW=f'{allow:g}', KILL_POINTS=f'{allow + args.grace_points:g}',
                    CONSUMED=f"{state['consumed']:.1f}", BUDGET=f'{args.budget:g}',
                    REMAINING=f"{args.budget - state['consumed']:.1f}", RESERVE=f'{args.reserve:g}',
                    SESSION_PCT=state.get('last_util'), WEEKLY_PCT=state.get('weekly'),
                    PREV_TABLE=prev_table(state), NOTES=notes, START_COMMIT=state['start_commit'],
                    E2E_ALLOWED='there are more than 10 minutes left' if soft_min > 10 else 'never, there is no time')

    if args.dry_run:
        print(worker_tpl.substitute(situation(len(state['agents']) + 1, args.agent_minutes,
                                              args.agent_minutes + args.grace_minutes, args.agent_points)))
        print('\n----- settings -----\n' + json.dumps(settings, indent=1)[:1500] + ' ...')
        return

    servers = Servers(not args.no_servers)
    stopping = {'now': False}

    def on_signal(signum, frame):
        if stopping['now'] and CURRENT.get('proc'):
            log(f'signal {signum} again, killing the running agent')
            try:
                os.killpg(CURRENT['proc'].pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            return
        log(f'signal {signum}, stopping after this agent (again to kill it now)')
        stopping['now'] = True
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    failures = 0
    try:
        while not stopping['now']:
            servers.ensure()
            n = len(state['agents']) + 1
            now = datetime.now().astimezone()
            mins_left = (deadline - now).total_seconds() / 60
            remaining = args.budget - state['consumed'] - args.reserve
            why = None
            if n > args.max_agents:
                why = f'max agents {args.max_agents} reached'
            elif remaining < args.min_agent_points:
                why = f"budget used ({state['consumed']:.1f} of {args.budget} points, {args.reserve} reserved)"
            elif mins_left - args.report_minutes < args.min_agent_minutes:
                why = f'{mins_left:.0f} min left, {args.report_minutes} needed for the report'
            elif state.get('weekly') is not None and state['weekly'] >= args.weekly_ceiling:
                why = f"weekly window at {state['weekly']} %"
            elif failures >= 2:
                why = 'two agents in a row ended in an error'
            if why:
                log('no more worker agents: ' + why)
                break
            soft_min = int(min(args.agent_minutes, mins_left - args.report_minutes))
            hard_min = int(min(soft_min + args.grace_minutes, mins_left - args.report_minutes / 2))
            allow = round(min(args.agent_points, remaining), 1)
            name = f'agent-{n}'
            state['agent'] = {'n': n, 'allowance': allow, 'start_consumed': state['consumed'],
                              'start_time': now.isoformat(timespec='seconds'), 'soft_minutes': soft_min,
                              'hard_minutes': hard_min}
            save_state(state)
            head_before = sh(['git', 'rev-parse', 'HEAD'])
            log(f'{name}: start, {soft_min} min (kill {hard_min}), {allow} points (kill {allow + args.grace_points}), '
                f"{state['consumed']:.1f} consumed so far, {mins_left:.0f} min to the deadline")
            prompt = worker_tpl.substitute(situation(n, soft_min, hard_min, allow))
            result, ended, points = run_claude(prompt, name, args.model, settings_json, deadline, state,
                                               hard_min, allow + args.grace_points, servers)
            commits = int(sh(['git', 'rev-list', '--count', f'{head_before}..HEAD'], check=False) or 0)
            stashed = tidy(name, n)
            usage = (result or {}).get('usage') or {}
            rec = {'n': n, 'start': now.strftime('%H:%M'), 'end': datetime.now().strftime('%H:%M'),
                   'minutes': round((time.time() - now.timestamp()) / 60), 'points': round(points, 1),
                   'cost_usd': round((result or {}).get('total_cost_usd') or 0, 2),
                   'turns': (result or {}).get('num_turns'),
                   'tokens_out': usage.get('output_tokens'), 'tokens_in': (usage.get('input_tokens') or 0)
                   + (usage.get('cache_creation_input_tokens') or 0) + (usage.get('cache_read_input_tokens') or 0),
                   'commits': commits, 'ended': ended, 'stashed': stashed,
                   'session_id': (result or {}).get('session_id'),
                   'denials': [d.get('tool_input', {}).get('command') or d.get('tool_name')
                               for d in (result or {}).get('permission_denials') or []][:20],
                   'summary': (result or {}).get('result') or ''}
            state['agents'].append(rec)
            state['agent'] = None
            save_state(state)
            with open(os.path.join(RUN, 'stats.json'), 'w') as f:
                json.dump(state['agents'], f, indent=1)
            failures = failures + 1 if ended.startswith('error') or ended.startswith('exited') else 0
            log(f"{name}: {ended}; {points:.1f} points, ${rec['cost_usd']}, {rec['turns']} turns, {commits} commit(s)"
                + (f", denied: {rec['denials']}" if rec['denials'] else ''))

        # the report
        now = datetime.now().astimezone()
        mins_left = (deadline - now).total_seconds() / 60
        allow = round(max(0.0, args.budget - state['consumed']), 1)
        report_path = os.path.join(HERE, 'REPORT.md')
        if allow >= 1 and mins_left >= 3:
            soft_min = int(max(3, min(args.report_minutes, mins_left - 1)))
            state['agent'] = {'n': len(state['agents']) + 1, 'allowance': allow, 'start_consumed': state['consumed'],
                              'start_time': now.isoformat(timespec='seconds'), 'soft_minutes': soft_min,
                              'hard_minutes': soft_min + 5}
            save_state(state)
            servers.ensure()
            log(f'report agent: start, {soft_min} min, {allow} points')
            prompt = report_tpl.substitute(situation(len(state['agents']) + 1, soft_min, soft_min + 5, allow))
            result, ended, points = run_claude(prompt, 'report', args.model, settings_json, deadline, state,
                                               soft_min + 5, allow + 1, servers)
            log(f'report agent: {ended}, {points:.1f} points')
            if sh(['git', 'status', '--porcelain', '--', 'agents/REPORT.md', 'agents/journal.md'], check=False):
                sh(['git', 'add', 'agents/REPORT.md', 'agents/journal.md'], check=False)
                sh(['git', 'commit', '-q', '-m', 'agents: report of the night (committed by the orchestrator)'], check=False)
            if git_status():
                sh(['git', 'stash', 'push', '-u', '-m', 'report leftovers'], check=False)
            state['agent'] = None
        else:
            log(f'no budget or time for a report agent ({allow} points, {mins_left:.0f} min)')
        if not os.path.exists(report_path):
            with open(report_path, 'w') as f:
                f.write('# Report of the night\n\nNo report agent ran (budget or time was gone). '
                        'See agents/journal.md and `git log` for what happened.\n')
        with open(report_path, 'a') as f:
            f.write(f"\n\n## Verification by the orchestrator, {datetime.now().strftime('%H:%M')}\n\n"
                    f"{final_checks()}\n\nAgents: {len(state['agents'])}, budget used "
                    f"{state['consumed']:.1f} of {args.budget} points, start commit {state['start_commit']}, "
                    f"head {sh(['git', 'rev-parse', '--short', 'HEAD'])}.\n")
        sh(['git', 'add', 'agents/REPORT.md', 'agents/journal.md'], check=False)
        if sh(['git', 'status', '--porcelain', 'agents/REPORT.md', 'agents/journal.md'], check=False):
            sh(['git', 'commit', '-q', '-m', 'agents: final checks appended to the report'], check=False)
        if git_status():
            sh(['git', 'stash', 'push', '-u', '-m', 'end-of-run leftovers'], check=False)
        state['finished'] = True
        save_state(state)
        log(f"done: {len(state['agents'])} agents, {state['consumed']:.1f} points, report in agents/REPORT.md")
    finally:
        servers.stop()
        LOG.close()


if __name__ == '__main__':
    main()
