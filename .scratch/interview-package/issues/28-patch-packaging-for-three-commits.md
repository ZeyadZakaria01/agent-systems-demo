# Patch packaging for the three-commit patch on LadybugDB

Type: grilling
Status: resolved
Blocked by: 24

## Question

[Patch packaging](18-patch-packaging.md) decided one commit on Kuzu. Report §9.5 now has three commits on LadybugDB. How is that packaged and run?

- Worktree branch with three commits exported as a format-patch series; file names under `patches/`.
- Where `ladybug` is installed (root venv beside `kuzu`, or a separate venv) and how `scripts/run_memstate.sh --patched` selects it.
- Which commits get a scored run: the port-only commit as an identical-verdicts check, the bitemporal commit, the merge commit; which of these are scorecard columns.
- How ADR 0004 (Kuzu pinned at 0.11.3) is amended for the patched column; DB files are not interchangeable between engines.

## Answer

Resolved 2026-10-20 (Q1–Q5 accepted; Q4 revised once). Facts: none of [Patch packaging](18-patch-packaging.md)'s plan was built (no `MemState-patched/`, no `patches/`, no `--patched` flag); the only LadybugDB copy is the scratch `.runtime/ms-ladybug/`; `memstate` is an editable install of `MemState/src`, so `PYTHONPATH` selects a copy (F11); "kuzu" appears 61 times in 16 MemState files; no upstream test touches merging; `test_topic_fields.py:39` uses non-date `valid_from` strings (`"t0"`…`"t4"`).

- **Q1, packaging.** Branch `bitemporal` in the `MemState-patched/` worktree, three commits on `945d7c4`, exported with `git format-patch` as `patches/0001-port-to-ladybugdb.patch`, `0002-bitemporal-field-histories.patch`, `0003-merge-by-valid-time.patch`; re-exported whenever a commit changes; README gives the rebuild commands. `.runtime/ms-ladybug/` is discarded. A public GitHub fork (usable for a PR to the authors) may be added later; the patch files apply to it unchanged. Rejected: one combined patch (loses per-commit runs), vendored copy, runtime override, git bundle (not reviewable).
- **Q2, commit 1.** The import line in `kuzu_adapter.py` plus the `pyproject.toml` dependency (`kuzu>=0.11.0` → `ladybug==0.21.2`); no renames (16 files would change and the "engine swap changes nothing" claim would be harder to check). MemState's README keeps its two Kuzu mentions; our README and the commit message say LadybugDB.
- **Q3, install and selection.** Root venv with both engines. `scripts/run_memstate.sh --patched` sets `PYTHONPATH=MemState-patched/src`; default DB folders are named per engine (`.runtime/memstate-kuzu-<ts>/`, `memstate-ladybug-<ts>/`); the script prints the engine and source folder that loaded, and recorded runs keep that line. MemState's repo now uses this repo's `.githooks/` (`git -C MemState config core.hooksPath`, done 2026-10-20; worktrees share it).
- **Q4, scored runs.** The conformance suite (the scored checks, merge ×20 and the C5 archive verdict) runs on upstream, the baseline and each of the three commits; the chat case and the dated merge case run on commit 3 only (Time probes and their controls); latency is decided in [Reinforcement precision and the engine latency ramps](29-reinforcement-precision-and-latency-ramps.md). The scorecard's patch column is commit 3; a per-commit table lists the rows whose verdict changed. Commit 1 must match upstream verdict for verdict (merge counts vary with random IDs: 10/20 vs 8/20, F9/F11). Commit 1 → 2 is the clean measure of Zep's model on MemState (same engine); commit 3 is incremental on commit 2. MemState's 39 tests pass unedited at every commit: a `valid_from` that does not parse as a date keeps arrival order. Commits 2 and 3 add developer tests in the patched copy, for coding errors only.
- **Q5, decision records.** New [ADR 0006](../../../docs/adr/0006-patch-on-ladybugdb-upstream-on-kuzu.md) (patch on LadybugDB, upstream on Kuzu); ADR 0004 points to it; ADR 0001 now names the bitemporal extension.
- **README.** Layout row and the submodule paragraph updated now; the run commands (`--patched`, engine-named folders) change when the script gains the flag.

Applied: report §9.5 Structure and §9.8; README; ADRs 0001, 0004, 0006; map; comments on tickets 29 and 30.
