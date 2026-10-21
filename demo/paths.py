"""Repo locations. Git-ignored state (venv, embedding cache, MemState/, .runtime/) lives in the main checkout."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _shared_root() -> Path:
    common = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(common).parent


# The main checkout; equals REPO_ROOT outside a linked worktree (same resolution as scripts/run_memstate.sh).
SHARED_ROOT = _shared_root()
RUNS_ROOT = REPO_ROOT / "runs"  # every run's output; results/ and results-live/ are git-ignored, the rest is tracked
RESULTS_ROOT = RUNS_ROOT / "results"
RESULTS_ROOT_LIVE = RUNS_ROOT / "results-live"
RECORD_ROOT = RUNS_ROOT / "record"  # the run of record, copied from RESULTS_ROOT
RECORDINGS_ROOT = RUNS_ROOT / "recordings"  # chat recordings of record
RUN_SCRIPT = REPO_ROOT / "scripts" / "run_memstate.sh"
# The machine-wide one-server lock, held by every run and script that starts a server (demo/systems/server_lock.py).
SERVER_LOCK = SHARED_ROOT.parent / f"{SHARED_ROOT.name}-wt" / "server.lock"
