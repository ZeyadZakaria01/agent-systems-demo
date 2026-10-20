"""The steps of the bitemporal patch: one commit each on branch `bitemporal` of the shared `MemState-patched/` worktree.

`PatchRepo.steps()` resolves them with `git rev-list --reverse <upstream commit>..bitemporal` (oldest first, so
step 1 is the first commit on top of upstream). `checkout_step(n)` checks one out detached after refusing a dirty
worktree; `return_to_branch()` goes back to `bitemporal` (the runner's `teardown` hook calls it, also after an error).
Step N is whatever the Nth commit is: until the patch is complete there are fewer than three, and the steps that
exist are the ones measured (`demo/systems.py` registers `step1`..`step3`; a step that does not exist fails its
setup with the commit count; the patch is meant to have exactly three).

Callers hold the machine-wide server lock (a checkout swaps the code a running server would load). "Dirty" means
tracked files modified or staged (what a checkout can clobber or refuse; untracked files do not count) or a rebase,
merge, cherry-pick, revert or bisect in progress. A setup that refuses leaves the worktree exactly where it was, and
so does its teardown; once a setup completed the checkout (even when HEAD was already at the step) its teardown
returns to `bitemporal`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from demo.paths import SHARED_ROOT

UPSTREAM_COMMIT = "945d7c4"
PATCH_BRANCH = "bitemporal"
PATCH_WORKTREE = SHARED_ROOT / "MemState-patched"


IN_PROGRESS = ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")


class StepError(RuntimeError):
    pass


@dataclass(frozen=True)
class PatchRepo:
    path: Path = PATCH_WORKTREE
    base: str = UPSTREAM_COMMIT
    branch: str = PATCH_BRANCH

    def _git(self, *args: str) -> str:
        r = subprocess.run(["git", "-C", str(self.path), *args], capture_output=True, text=True)
        if r.returncode != 0:
            raise StepError(f"`git -C {self.path} {' '.join(args)}` failed ({r.returncode}): "
                            f"{(r.stderr or r.stdout).strip()}")
        return r.stdout.strip()

    def steps(self) -> list[str]:
        """Full commit hashes, step 1 first."""
        return self._git("rev-list", "--reverse", f"{self.base}..{self.branch}").split()

    def step_commit(self, n: int) -> str:
        steps = self.steps()
        if not 1 <= n <= len(steps):
            raise StepError(f"step {n} does not exist: {self.branch} has {len(steps)} commit(s) on top of "
                            f"{self.base} ({', '.join(c[:7] for c in steps) or 'none'})")
        return steps[n - 1]

    def check_clean(self) -> None:
        for name in IN_PROGRESS:
            marker = Path(self._git("rev-parse", "--path-format=absolute", "--git-path", name))
            if marker.exists():
                raise StepError(f"{self.path} has a git operation in progress ({name}); finish or abort it before "
                                "measuring a step")
        dirty = self._git("status", "--porcelain", "--untracked-files=no")
        if dirty:
            raise StepError(f"{self.path} has uncommitted changes to tracked files; refusing to check out a step "
                            f"over them (commit or stash them first):\n{dirty}")

    def head(self) -> str:
        return self._git("rev-parse", "HEAD")

    def position(self) -> tuple[str, str]:
        """(HEAD commit, branch name; empty when detached): what a checkout can change."""
        return self.head(), self._git("branch", "--show-current")

    def checkout_step(self, n: int) -> str:
        """Check step `n` out detached and return its full hash."""
        commit = self.step_commit(n)
        self.check_clean()
        self._git("checkout", "--detach", commit)
        if self.head() != commit:
            raise StepError(f"checked out step {n} but HEAD is {self.head()}, expected {commit}")
        return commit

    def return_to_branch(self) -> None:
        self._git("checkout", self.branch)
