"""Evidence: one results directory per run, one snapshot per (system, check, fresh system), one `results.json`.

Layout: `<results_root>/<run id>/{results.json, scorecard.md, snapshots/<system>/<check>[--<tag>].json, logs/}`.
`capture()` runs when a system is closed (also after an error, and guarded: a dead server must not lose the
evidence); `write_snapshots()` runs once the check's verdicts are known. A snapshot holds: the system label and
`describe()` (URL, DB path, commit, engine line), start/finish timestamps, every scored transition (request,
response, timestamps, latency), the setup writes, reads and waits kept apart, the full stored state read after the
check (every topic including archived ones, plus edges), and the verdicts. Generic over rows and systems.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from demo.adapter import System
from demo.verdict import Verdict


@dataclass
class RunDir:
    id: str
    dir: Path
    runtime_dir: Path  # parent of this run's fresh server DBs (absolute, git-ignored)
    events: list[dict] = field(default_factory=list)  # server start/stop records

    @property
    def logs(self) -> Path:
        return self.dir / "logs"


def new_run_dir(results_root: Path, runtime_root: Path) -> RunDir:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id, n = stamp, 1
    while (results_root / run_id).exists() or (runtime_root / run_id).exists():
        n += 1
        run_id = f"{stamp}-{n}"
    run = RunDir(id=run_id, dir=(results_root / run_id).resolve(), runtime_dir=(runtime_root / run_id).resolve())
    run.dir.mkdir(parents=True)
    return run


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("′", "prime")).strip("-")  # C4' must not share C4's file


def snapshot_path(system_id: str, check_id: str, tag: str | None = None) -> str:
    return f"snapshots/{system_id}/{slug(check_id)}{'--' + slug(tag) if tag else ''}.json"


def capture(system_id: str, check_id: str, system: System, tag: str | None, started_at: str, finished_at: str) -> dict:
    """Everything a snapshot needs from one system, read now. Never raises: failures are recorded in the evidence."""
    try:
        describe, describe_error = system.describe(), None
    except Exception as e:
        describe, describe_error = {"system": system.label}, f"{type(e).__name__}: {e}"
    try:
        state, state_error = system.read_state(), None
    except Exception as e:  # the snapshot of a crashed check must still be written
        state, state_error = None, f"{type(e).__name__}: {e}"
    log = system.log
    return {
        "system": system_id,
        "label": system.label,
        "check": check_id,
        "tag": tag,
        "describe": describe,
        "describe_error": describe_error,
        "started_at": started_at,
        "finished_at": finished_at,
        "scored_transitions": log.of_kind("scored"),
        "setup_writes": log.of_kind("setup"),
        "reads": log.of_kind("read"),
        "waits": log.of_kind("wait"),
        "state": state,
        "state_error": state_error,
    }


def write_snapshots(run: RunDir, captured: list[dict], verdicts: list[Verdict]) -> list[str]:
    """Write one snapshot per captured system (each lists the check's verdicts), set the links on the verdicts."""
    paths = []
    for evidence in captured:
        rel = snapshot_path(evidence["system"], evidence["check"], evidence["tag"])
        path = run.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {**evidence, "rows": [v.row for v in verdicts], "verdicts": [v.to_dict() for v in verdicts]},
                indent=2,
                default=str,
            )
        )
        paths.append(rel)
    for v in verdicts:
        v.snapshots = list(paths)
    return paths


def write_results(run: RunDir, payload: dict) -> Path:
    path = run.dir / "results.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path
