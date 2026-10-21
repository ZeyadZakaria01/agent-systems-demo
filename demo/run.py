"""The runner: `python -m demo.run`, recorded mode (below) or `--mode live` against a running server (`demo/live.py`:
`--url`, `--as`, `--delay`, `--step`).

Recorded mode: per system, per check, a fresh database (a server started with `scripts/run_memstate.sh` for MemState
systems, stopped when the check ends; the baseline in-process); results go to `demo/results/<run id>/`.
A run that starts a server (a MemState system, or `--chat`) holds the machine-wide lock for its whole length
(`demo/server_lock.py`), also when started under `flock .../server.lock`, which the commands below keep:

    flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline

Flags: `--systems a,b` (default: every system that exists; `step1`..`step3` need that many commits on `bitemporal`),
`--checks C1,...` (row or check ids, default all),
`--ramp-repeats N` (C5 latency ramps, default 1 while building, 3 for the run of record),
`--record` (final step: copy the scorecard, `results.json` and snapshots to the tracked `demo/record/<run id>/`),
`--chat` (after the systems: record both chat runs, `bad-merge` on upstream and `two-weeks` on step 3, into this run's
folder; Ollama and the proxy are started for them and stopped after, also when they were running), `--recordings DIR`
(where the chat recordings are read and written, default `demo/recordings/`), `--list`, `--results-root DIR`. After each MemState system's checks the runner runs MemState's 39 upstream tests
(`demo/upstream_tests.py`: upstream in `MemState/`, a step in the patched copy while it is checked out) and records the
counts. The scorecard is followed by the per-step change table (`demo/changes.py`) once
upstream or a patch step was measured. The printed output ends with a block that pastes into `docs/findings.md`.

Failure handling: a check that raises, a system that cannot open (server did not start, setup failed) or a server
that dies mid-check gives `error` verdicts (with the evidence that could still be captured) and the run goes on;
`results.json` and `scorecard.md` are rewritten after every check (`"complete": false` until the end), so an
interrupted run keeps what it collected. Each system's `setup`/`teardown` hooks (`demo/systems.py`) bracket its checks.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from demo import chat_run, live
from demo.adapter import utc_now
from demo.changes import CHAIN, REFERENCE_CHAIN, change_table_payload, regression_summary, render_change_tables
from demo.checks import Check, discover, natural_key
from demo.deviations import DEVIATIONS
from demo.chat_recording import RECORDINGS_ROOT, latest_per_case, render_chat_cases, results_payload
from demo.evidence import RunDir, new_run_dir, write_results
from demo.failures import detail as _detail, errored as _errored, run_check
from demo.latency_tables import with_latency
from demo.paths import RECORD_ROOT, REPO_ROOT, RESULTS_ROOT, SERVER_LOCK, SHARED_ROOT
from demo.scorecard import (COLUMNS, SCOPE_NOTE, Column, claimed_by_p1, counts, render_deviations, render_limits,
                            render_merge_existence, render_probes, render_scorecard)
from demo.over_flagging_tables import render_over_flagging
from demo.storyline_tables import render_storyline
from demo.record import record_run
from demo.server_lock import server_lock
from demo.systems import SYSTEMS, SystemSpec
from demo.upstream_tests import render_upstream_tests
from demo.verdict import Verdict, measured
from demo.windows import render_windows


@dataclass
class RunResult:
    dir: Path
    verdicts: list[Verdict]
    scorecard: str  # scorecard table, then the deviations table
    findings_block: str
    chat_errors: list[str] = field(default_factory=list)  # chat cases the run asked for and could not record


ChatRecorder = Callable[[RunDir, Path], "chat_run.Recorded"]  # (this run's folder, the recordings folder) -> what it recorded


def run_recorded(systems: list[str], checks: list[Check], results_root: Path, command: str,
                 run_day: date | None = None, columns: tuple[Column, ...] = COLUMNS,
                 runtime_root: Path | None = None, registry: dict[str, SystemSpec] | None = None,
                 recordings_dir: Path | None = None, record_chats: ChatRecorder | None = None,
                 log=print) -> RunResult:
    registry = registry or SYSTEMS
    run_day = run_day or date.today()
    run = new_run_dir(results_root, runtime_root or SHARED_ROOT / ".runtime" / "gem-suite")
    recordings_dir = recordings_dir or RECORDINGS_ROOT
    chats = latest_per_case(recordings_dir)  # what existed at the start; a run that records chats re-reads after them
    chat_errors: list[str] = []
    started = utc_now()
    verdicts: list[Verdict] = []
    test_counts: dict[str, dict] = {}  # system id -> upstream-test counts (or {"error": ...})
    rows = sorted((r for c in checks for r in c.rows if r.on_scorecard), key=lambda r: natural_key(r.id))

    def save(complete: bool) -> str:
        # only scorecard rows: a Storyline-only run still has upstream verdicts, which must not print an empty table
        scored = [v for v in verdicts if any(r.id == v.row for r in rows)]
        windows = render_windows(verdicts)
        scorecard = render_scorecard(rows, columns, verdicts)
        if measured(scored, CHAIN):  # the claim is about the patch steps; a run without them says nothing of regressions
            scorecard += "\n\n" + regression_summary(rows, scored)
        if any(r.probe for r in rows):
            scorecard += "\n\n" + render_probes(rows, columns, scored)
        if merge := render_merge_existence(rows, columns, scored):
            scorecard += "\n\n" + merge
        if windows:
            scorecard += f"\n\n### Staleness windows\n\n{windows}"
        if change_tables := render_change_tables(rows, scored):  # one per chain; a baseline-only run has none
            scorecard += "\n\n" + change_tables
        if storyline := render_storyline(verdicts):
            scorecard += "\n\n" + storyline
        if over_flagging := render_over_flagging(verdicts):
            scorecard += "\n\n" + over_flagging
        if chat_cases := render_chat_cases(chats):  # recorded chat runs (ticket 17), replayed from demo/recordings/
            scorecard += "\n\n" + chat_cases
        scorecard = with_latency(scorecard, verdicts)
        if tests := render_upstream_tests(test_counts, {s: registry[s].label for s in test_counts}):
            scorecard += "\n\n" + tests
        scorecard += "\n\n" + render_limits()
        scorecard += "\n\n" + SCOPE_NOTE + "\n\n### Deviations\n\n" + render_deviations()
        (run.dir / "scorecard.md").write_text(scorecard + "\n")
        write_results(run, {
            "run_id": run.id, "mode": "recorded", "complete": complete, "command": command,
            "run_day": run_day.isoformat(), "started_at": started, "finished_at": utc_now(),
            "systems": systems, "checks": [c.id for c in checks],
            "columns": [{"header": c.title, "group": c.group, "system": c.system} for c in columns],
            "rows": [{"id": r.id, "claim": r.claim, "control": r.control, "probe": r.probe,
                      "claimed_by_p1": claimed_by_p1(r)} for r in rows],
            "verdicts": [v.to_dict() for v in verdicts],
            "counts": {c.system: counts(c, [r for r in rows if not r.probe], verdicts) for c in columns},
            "change_tables": {"memstate": change_table_payload(rows, scored, CHAIN),
                              "reference": change_table_payload(rows, scored, REFERENCE_CHAIN)},
            "regression_summary": regression_summary(rows, scored) if measured(scored, CHAIN) else None,
            "upstream_tests": test_counts,
            "servers": run.events,
            "deviations": [d.__dict__ for d in DEVIATIONS],
            "chat_cases": results_payload(chats), "chat_errors": chat_errors,
        })
        return scorecard

    for system_id in systems:
        spec = registry[system_id]
        applicable = [c for c in checks if c.applies_to(system_id)]
        if not applicable:
            continue
        try:
            setup_error = None
            if spec.setup is not None:
                try:
                    spec.setup(run)
                except Exception as e:
                    setup_error = _detail(e)
            if setup_error is not None:
                log(f"[{system_id}] setup failed")
                for check in applicable:
                    verdicts += _errored(check, system_id, f"setup of {system_id} failed: {setup_error}")
                save(False)
                continue
            for check in applicable:
                log(f"[{system_id}] {check.id}: running")
                verdicts += _run_one(run, spec, check, run_day)
                save(False)
            if spec.unit_tests is not None:  # before teardown: a step is still checked out
                log(f"[{system_id}] upstream tests: running")
                try:
                    test_counts[system_id] = spec.unit_tests().to_dict()
                except Exception as e:
                    test_counts[system_id] = {"error": _detail(e)}
                save(False)
        finally:
            if spec.teardown is not None:
                try:
                    spec.teardown(run)
                except Exception as e:  # recorded, not fatal: the next system's setup starts from its own state
                    run.events.append({"system": system_id, "teardown_error": _detail(e)})
                    log(f"[{system_id}] teardown failed: {e}")
    if record_chats is not None:  # after every server of the suite is down: Ollama has the GPU to itself
        log("[chat] recording both chat runs")
        try:
            chat_errors += record_chats(run, recordings_dir).errors
        except Exception as e:  # e.g. the proxy bypass, a half-running Ollama: the suite's results are kept
            chat_errors.append(_detail(e))
        chats = latest_per_case(recordings_dir)
    scorecard = save(True)
    return RunResult(dir=run.dir, verdicts=verdicts, scorecard=scorecard,
                     findings_block=findings_block(run, command, verdicts), chat_errors=chat_errors)


def _run_one(run: RunDir, spec: SystemSpec, check: Check, run_day: date) -> list[Verdict]:
    def open_system(tag: str | None):
        return spec.open(check.id if tag is None else f"{check.id}--{tag}", run)

    return run_check(run, check, spec.id, open_system, run_day)


def needs_server_lock(systems: list[str], chat: bool) -> bool:
    """A MemState system (its upstream tests are counted) or a chat run starts a server; in-process systems do not."""
    return chat or any(SYSTEMS[s].unit_tests is not None for s in systems)


def pasteable_command(argv: list[str]) -> str:
    """The command that reproduces this run: working directory, lock and interpreter included."""
    return f"cd {REPO_ROOT} && flock {SERVER_LOCK} {sys.executable} -m demo.run {shlex.join(argv)}".rstrip()


def _observation_text(o) -> str:
    """An observation is a dict: its `summary`, else its `name` (the full dict lives in results.json)."""
    return str(o.get("summary") or o.get("name") or "(structured observation, see results.json)")


def _cases_text(cases) -> str:
    """Every case for short rows; for rows with 7+ cases a tally plus only the cases that did not hold."""
    def one(c) -> str:
        return f"{c.name}: {'n/a' if c.held is None else 'held' if c.held else 'BROKE'} ({c.observation})"
    if len(cases) <= 6:
        return "; ".join(one(c) for c in cases)
    tally = (f"{len(cases)} cases: held {sum(c.held is True for c in cases)}, "
             f"BROKE {sum(c.held is False for c in cases)}, n/a {sum(c.held is None for c in cases)}")
    rest = [one(c) for c in cases if c.held is not True]
    return tally + (f"; not held: {'; '.join(rest)}" if rest else "")


def findings_block(run: RunDir, command: str, verdicts: list[Verdict]) -> str:
    """Markdown for `docs/findings.md`: command, DB paths, key output per verdict."""
    lines = [f"Run ({date.today().isoformat()}): `{command}` (recorded mode; results `{run.dir}`).", ""]
    dbs = [f"`{e['db_path']}` ({e['system']}, {e['check']}; {e['engine_line']}; commit {e['commit']})"
           for e in run.events if "db_path" in e]
    lines.append("DB paths: " + ("; ".join(dbs) if dbs else "none (in-process systems only)") + ".")
    lines += ["", "Key output:", ""]
    for v in verdicts:
        held = _cases_text(v.cases)
        extra = f" error: {v.error.splitlines()[0]}" if v.error else ""
        links = " ".join(f"`{p}`" for p in v.snapshots) or "none"
        lines.append(f"- {v.row} on {v.system}: **{v.verdict}**{extra}"
                     + (f" - {held}" if held else "") + f" [snapshots {links}]")
        scalars = ", ".join(f"{k}={val}" for k, val in v.measurements.items() if not isinstance(val, (list, dict)))
        if scalars:
            lines.append(f"  - measurements: {scalars}")
        lines += [f"  - observation: {_observation_text(o)}" for o in v.observations]
    return "\n".join(lines)


def _select(ap: argparse.ArgumentParser, available: list[Check], spec: str | None) -> list[Check]:
    if not spec:
        return available
    wanted = {w.strip().lower() for w in spec.split(",")}
    checks = [c for c in available if wanted & {r.id.lower() for r in c.rows} | ({c.id.lower()} & wanted)]
    missing = wanted - {r.id.lower() for c in checks for r in c.rows}
    if missing:
        ap.error(f"unknown check(s) {sorted(missing)}; known rows: {[r.id for c in available for r in c.rows]}")
    return checks


def _main_live(ap: argparse.ArgumentParser, args, available: list[Check], argv: list[str]) -> int:
    if not args.url:
        ap.error("--mode live needs --url (the server is started by you, never by the runner)")
    if args.systems:
        ap.error("--systems is for recorded mode; live mode drives the one server at --url (--as picks the check filter)")
    if args.as_system not in SYSTEMS or args.as_system == "baseline":
        ap.error(f"--as must be a MemState system id; known: {[s for s in SYSTEMS if s != 'baseline']}")
    try:
        result = live.run_live(args.url, _select(ap, available, args.checks), args.results_root or live.RESULTS_ROOT_LIVE,
                               shlex.join(["python", "-m", "demo.run", *argv]), as_system=args.as_system,
                               delay=args.delay, step=args.step)
    except live.LiveError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"\n## LIVE scorecard ({live.BANNER})\n")
    print(result.scorecard)
    print(f"\n[LIVE] Results: {result.dir}/results.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="python -m demo.run", description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=["recorded", "live"], default="recorded")
    ap.add_argument("--systems", help=f"comma-separated system ids; known: {', '.join(SYSTEMS)} (default: all; a patch "
                                         "step fails unless bitemporal holds exactly three commits)")
    ap.add_argument("--checks", help="comma-separated row or check ids (default: all)")
    ap.add_argument("--results-root", type=Path, help="default demo/results (recorded) or demo/results-live (live)")
    live_group = ap.add_argument_group("live mode (--mode live; see demo/live.py)")
    live_group.add_argument("--url", help="the running MemState server to drive, e.g. http://127.0.0.1:8765 (required)")
    live_group.add_argument("--as", dest="as_system", default="upstream", help="system id the server is, for the checks' filter")
    live_group.add_argument("--delay", type=float, default=0, help="seconds to pause after every write or query")
    live_group.add_argument("--step", action="store_true", help="wait for Enter after every write or query")
    ap.add_argument("--ramp-repeats", type=int, default=1,
                    help="times to run each C5 latency ramp (1 while building, 3 for the run of record)")
    ap.add_argument("--chat", action="store_true",
                    help="after the systems, record both chat runs (bad-merge on upstream, two-weeks on step 3) into "
                         "this run's folder; starts Ollama and the proxy and stops them (needs the machine lock)")
    ap.add_argument("--recordings", type=Path, default=RECORDINGS_ROOT,
                    help="the chat recordings folder: read for the scorecard, written by --chat (default demo/recordings)")
    ap.add_argument("--record", action="store_true",
                    help="final step: copy scorecard.md, results.json and snapshots/ to the tracked demo/record/<run id>/")
    ap.add_argument("--list", action="store_true", help="list checks and systems, then exit")
    args = ap.parse_args(argv)
    import demo.ramp as ramp
    ramp.REPEATS = max(1, args.ramp_repeats)

    available = discover()
    if args.list:
        for c in available:
            for r in c.rows:
                print(f"{r.id}{' (control)' if r.control else ''}: runs on {c.systems or 'all systems'}")
        print("systems:", ", ".join(SYSTEMS))
        return 0
    if args.mode == "live":
        if args.chat:
            ap.error("--chat is for recorded mode: the chat runs start their own servers")
        return _main_live(ap, args, available, argv)
    systems = args.systems.split(",") if args.systems else list(SYSTEMS)
    unknown = [s for s in systems if s not in SYSTEMS]
    if unknown:
        ap.error(f"unknown system(s) {unknown}; known: {list(SYSTEMS)}")
    checks = _select(ap, available, args.checks)
    results_root = args.results_root or RESULTS_ROOT
    command = pasteable_command(argv)
    # the recordings cite their snapshots by the folder the run ends in: demo/record/ when it is recorded, else here
    link_root = RECORD_ROOT if args.record else results_root
    chats = (lambda run, recordings: chat_run.record_chats(run, recordings, link_root, command)) if args.chat else None
    with server_lock() if needs_server_lock(systems, args.chat) else nullcontext():
        result = run_recorded(systems, checks, results_root, command, recordings_dir=args.recordings,
                              record_chats=chats)
    print("\n## Scorecard\n")
    print(result.scorecard)
    print(f"\nResults: {result.dir}/results.json\n")
    if args.record:
        print(f"Run of record: {record_run(result.dir, RECORD_ROOT)}\n")
    print("## Paste into docs/findings.md\n")
    print(result.findings_block)
    for error in result.chat_errors:
        print(f"error: chat run not recorded: {error}", file=sys.stderr)
    return 1 if result.chat_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
