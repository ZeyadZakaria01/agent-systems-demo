"""Live mode: drive a MemState server that is ALREADY running, so the Graph Explorer can be watched while checks run.

`python -m demo.run --mode live --url http://127.0.0.1:8765 [--as upstream] [--step] [--delay N] [--checks ...]`

What differs from recorded mode (`demo/run.py`):
- The runner never starts or stops a server and takes no lock (the presenter started the server and owns it).
- One database for the whole run, not a fresh one per check. To keep the checks apart, every title a check writes is
  suffixed ` [live <check id> <HHMMSS of the run>]` (and `--<tag>` inside `ctx.fresh_system(tag)`; the time keeps a
  second run against the same server from duplicating the first run's titles), so the Reasoner's exact-title
  duplicate detection never merges topics of two checks. A check that forces a fixed topic id collides when two
  checks force the same id (the server answers 500; the verdict is `error`), and a check that writes an EMPTY title
  (stored `untitled`) can still be merged with another's; neither is rewritten.
- Pace: `--delay N` sleeps N seconds after every write or query (visible in the Graph Explorer); `--step` waits for
  Enter instead. State reads for the snapshot are not paced.
- Everything is labelled live: verdicts carry system `live`, `results.json` has `"mode": "live"`, the scorecard file
  is `scorecard-live.md` headed "LIVE", every printed line starts with `[LIVE]`.
- Output goes to `demo/results-live/<run id>/`, never to the recorded results; the runner refuses a results root
  inside the recorded one. A live run is never part of the scorecard of record.
- `--as` says which system the server is, for the checks' `systems=` filter (default `upstream`; a patch server is
  `step1`, ...). Nothing is verified against it: the server decides.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from demo.checks import Check, natural_key
from demo.client import MemStateSystem, System, utc_now
from demo.deviations import DEVIATIONS
from demo.evidence import RunDir, capture, new_run_dir, slug, write_results, write_snapshots
from demo.paths import REPO_ROOT, RESULTS_ROOT
from demo.failures import detail as _detail, errored as _errored
from demo.scorecard import Column, counts, render_scorecard
from demo.session import Session
from demo.latency_tables import render_latency
from demo.storyline_tables import render_storyline
from demo.verdict import Verdict

LIVE = "live"
RESULTS_ROOT_LIVE = REPO_ROOT / "demo" / "results-live"
BANNER = "LIVE RUN - not a result of record; one shared database, titles suffixed per check."


class LiveError(RuntimeError):
    pass


def suffixed(title: str, scope: str) -> str:
    """The title a check's topic gets in the shared live database; empty titles stay empty (see module doc)."""
    return f"{title} [live {scope}]" if title else title


class LiveSystem(MemStateSystem):
    """A MemState server the suite did not start: titles are scoped to the check, every step may pause."""

    def __init__(self, label: str, base_url: str, scope: str, pace: Callable[[str], None]) -> None:
        super().__init__(label, base_url)
        self.scope = scope
        self.pace = pace

    def _scoped(self, params: dict) -> dict:
        params = dict(params)
        if isinstance(params.get("title"), str):
            params["title"] = suffixed(params["title"], self.scope)
        return params

    def ingest(self, request: dict) -> dict:
        response = super().ingest(request)
        scoped = self._scoped(request) if request.get("placement") == "new_topic" else request
        target = scoped.get("title") or str(request.get("topic_id", ""))[:8]
        self.pace(f"ingest {request.get('placement')} {target!r} "
                  f"fields {[f'{f.get('name')}={f.get('value')!r}' for f in request.get('fields') or []]}")
        return response

    def query(self, request: dict) -> dict:
        response = super().query(request)
        self.pace(f"query {request.get('q')!r} stages {request.get('stages')} -> "
                  f"{[c['title'] for c in response['candidates']]}")
        return response

    def setup_write(self, action: str, *, label: str, **params) -> dict | None:
        response = super().setup_write(action, label=label, **params)
        self.pace(f"setup {action}")
        return response

    # Titles are scoped in the transport methods, below the log; the pause is in the public methods, above it, so
    # `--delay`/`--step` never enter a recorded `latency_ms` or `finished_at`.
    def _ingest(self, request: dict) -> dict:
        return super()._ingest(self._scoped(request) if request.get("placement") == "new_topic" else request)

    def _setup_write(self, action: str, params: dict) -> dict | None:
        return super()._setup_write(action, self._scoped(params) if action in ("create_topic", "patch_topic") else params)

    def _describe(self) -> dict:
        return {**super()._describe(), "live": True, "title_scope": self.scope}


@dataclass
class LiveResult:
    dir: Path
    verdicts: list[Verdict]
    scorecard: str


def preflight(url: str) -> dict:
    """The server must be up and report its DB; a live run never starts one."""
    try:
        health = httpx.get(f"{url}/health/graph", timeout=10)
        health.raise_for_status()
        topics = httpx.get(f"{url}/api/ui/topics", params={"include_archived": True}, timeout=30)
        topics.raise_for_status()
    except httpx.HTTPError as e:
        raise LiveError(f"no MemState server answering at {url} ({type(e).__name__}: {e}); live mode never starts "
                        "one: start it with scripts/run_memstate.sh on a fresh DB, then pass --url") from e
    return {"url": url, "db_path": health.json().get("path"), "topics_before": len(topics.json()["topic_ids"])}


def make_pace(delay: float, step: bool, log: Callable[[str], None], wait: Callable[[str], None] | None = None,
              sleep: Callable[[float], None] = time.sleep) -> Callable[[str], None]:
    def pace(what: str) -> None:
        log(f"  {what}")
        if step:
            (wait or _wait_for_enter)("  [LIVE] step done; press Enter for the next step (Ctrl-D: run on) ")
        elif delay > 0:
            sleep(delay)
    return pace


def _wait_for_enter(prompt: str) -> None:
    print(prompt, end="", flush=True)  # the prompt has no newline: flush or a piped terminal shows nothing
    sys.stdin.readline()


def run_live(url: str, checks: list[Check], results_root: Path, command: str, as_system: str = "upstream",
             delay: float = 0, step: bool = False, log: Callable[[str], None] = lambda m: print(m, flush=True),
             wait: Callable[[str], None] | None = None, sleep: Callable[[float], None] = time.sleep,
             connect: Callable[[str, Callable[[str], None]], System] | None = None) -> LiveResult:
    """`connect(scope, pace)` builds the system a check works on (default: a `LiveSystem` on `url`; tests pass others)."""
    url = url.rstrip("/")
    if RESULTS_ROOT.resolve() in (results_root.resolve(), *results_root.resolve().parents):
        raise LiveError(f"live results must not go under the recorded results ({RESULTS_ROOT}); use another --results-root")
    server = preflight(url) if connect is None else {"url": url, "db_path": None, "topics_before": 0}
    log(f"[LIVE] {BANNER}")
    log(f"[LIVE] server {url} (DB {server['db_path']}, {server['topics_before']} topics before); never started or stopped here")
    run = new_run_dir(results_root, results_root)
    started = utc_now()
    verdicts: list[Verdict] = []
    applicable = [c for c in checks if c.applies_to(as_system)]
    rows = sorted((r for c in applicable for r in c.rows if r.on_scorecard), key=lambda r: natural_key(r.id))
    column = Column(f"live ({url})", (LIVE,))
    pace = make_pace(delay, step, lambda m: log(f"[LIVE] {m}"), wait, sleep)

    def save(complete: bool) -> str:
        scorecard = f"**{BANNER}**\n\n" + render_scorecard(rows, (column,), verdicts)
        if storyline := render_storyline(verdicts):
            scorecard += "\n\n" + storyline
        if latency := render_latency(verdicts):
            scorecard += "\n\n" + latency
        (run.dir / "scorecard-live.md").write_text(scorecard + "\n")
        write_results(run, {
            "run_id": run.id, "mode": "live", "label": BANNER, "complete": complete, "command": command,
            "started_at": started, "finished_at": utc_now(), "server": server, "as_system": as_system,
            "delay_s": delay, "step": step, "checks": [c.id for c in applicable],
            "rows": [{"id": r.id, "claim": r.claim, "control": r.control} for r in rows],
            "verdicts": [{**v.to_dict(), "mode": "live"} for v in verdicts],
            "counts": {column.header: counts(column, rows, verdicts)},
            "deviations": [d.__dict__ for d in DEVIATIONS],
        })
        return scorecard

    for check in applicable:
        log(f"[LIVE] {check.id}: running")
        verdicts += _run_check(run, check, connect or (lambda scope, pace: LiveSystem(f"live {url}", url, scope, pace)), pace)
        save(False)
    scorecard = save(True)
    return LiveResult(dir=run.dir, verdicts=verdicts, scorecard=scorecard)


def _run_check(run: RunDir, check: Check, connect: Callable, pace: Callable[[str], None]) -> list[Verdict]:
    def open_system(tag: str | None):
        scope = check.id if tag is None else f"{check.id}--{slug(tag)}"
        return _live_cm(connect(f"{scope} {run.id[9:15]}", pace))

    session = Session(open_system, lambda system, tag, t0, t1: capture(LIVE, check.id, system, tag, t0, t1))
    notes: list[str] = []
    try:
        try:
            verdicts = check.execute(session)
        except Exception as e:
            verdicts = _errored(check, LIVE, _detail(e))
    finally:
        try:
            session.close()
        except Exception as e:
            notes.append(f"cleanup after the check failed: {type(e).__name__}: {e}")
    for v in verdicts:
        v.system = LIVE
        v.observations.extend(["live run: one shared database, titles suffixed per check", *notes])
    write_snapshots(run, session.captured, verdicts)
    return verdicts


class _live_cm:
    """Context manager over a `LiveSystem`: closes the HTTP client only; the server is not ours to stop."""

    def __init__(self, system: System) -> None:
        self.system = system

    def __enter__(self) -> System:
        return self.system

    def __exit__(self, *exc) -> None:
        close = getattr(self.system, "close", None)
        if close is not None:
            close()
