"""Repo locations. Git-ignored state (venv, embedding cache, MemState/, .runtime/) lives in the main checkout."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _shared_root() -> Path:
    common = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return Path(common).parent


# The main checkout; equals REPO_ROOT outside a linked worktree (same resolution as scripts/run_memstate.sh).
SHARED_ROOT = _shared_root()
RESULTS_ROOT = REPO_ROOT / "demo" / "results"
RUN_SCRIPT = REPO_ROOT / "scripts" / "run_memstate.sh"
# The machine-wide one-server lock every run that starts a server is wrapped in (the runner never takes it itself).
SERVER_LOCK = SHARED_ROOT.parent / f"{SHARED_ROOT.name}-wt" / "server.lock"
