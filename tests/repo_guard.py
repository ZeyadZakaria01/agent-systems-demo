"""What the suite must leave untouched in the repository it runs from: the shared config and this checkout's HEAD.
Branches are left out: other worktrees commit while the suite runs (the pre-commit hook runs it mid-commit)."""

import subprocess
from pathlib import Path


def _git_path(repo: Path, flag: str) -> Path:
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute", flag],
                         check=True, capture_output=True, text=True).stdout.strip()
    return Path(out)


def repo_fingerprint(repo: Path) -> dict[str, bytes]:
    return {
        "config": (_git_path(repo, "--git-common-dir") / "config").read_bytes(),
        "HEAD": (_git_path(repo, "--git-dir") / "HEAD").read_bytes(),
    }
