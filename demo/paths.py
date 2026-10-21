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
RESULTS_ROOT = REPO_ROOT / "demo" / "results"
RECORD_ROOT = REPO_ROOT / "demo" / "record"  # tracked: the run of record, copied from RESULTS_ROOT
RUN_SCRIPT = REPO_ROOT / "scripts" / "run_memstate.sh"
# The machine-wide one-server lock, held by every run and script that starts a server (demo/server_lock.py).
SERVER_LOCK = SHARED_ROOT.parent / f"{SHARED_ROOT.name}-wt" / "server.lock"
