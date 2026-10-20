# Patch packaging

Type: grilling
Status: resolved
Blocked by: 07

## Question

How does the patched MemState sit beside the unmodified upstream?

Options on the table: a git worktree `MemState-patched/` on a branch with one commit, run via `run_memstate.sh --patched` (PYTHONPATH); a runtime override that swaps the merge function at server start; a GitHub fork.

Recommendation so far: git worktree (reviewable diff, upstream untouched; can become a PR later). The worktree belongs to MemState's own repo, so it needs `core.hooksPath` pointing at this repo's `.githooks/`.

## Answer

Resolved 2026-10-11 (recommendation accepted with the review, ticket 21): git worktree `MemState-patched/` on its own branch with one commit, started via `scripts/run_memstate.sh --patched` (PYTHONPATH to the worktree's `src/`). Set `core.hooksPath` for MemState's repo to this repo's `.githooks/` before committing in the worktree.

Amended 2026-10-12: `MemState/` is now a git submodule pinned at `945d7c4`, so the worktree's branch lives inside this repo's `.git/modules/MemState` and cannot be pushed upstream. `MemState-patched/` is git-ignored here; the patch is committed in this repo as `patches/0001-history-preserving-merge.patch` (`git format-patch`), which reproduces the patched copy on a fresh worktree.

**Superseded in part 2026-10-19 by [Report v2 redraws the demo](23-report-v2-redraws-the-demo.md):** three commits on LadybugDB instead of one on Kuzu; reopened as [Patch packaging for the three-commit patch on LadybugDB](28-patch-packaging-for-three-commits.md). The worktree, `--patched` flag and hooks setup stand.
