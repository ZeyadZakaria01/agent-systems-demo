# 32: Run-of-record folder and the upstream tests at every step

**What to build:** The run of record lives in the repository. `runs/results/` is git-ignored, yet report §9.2 and §9.8 promise snapshot links, so the recorded run is copied into a tracked `runs/record/<run-id>/`. The same command runs MemState's 39 upstream tests at upstream and at each patch step and records the counts, so "the 39 tests pass unedited at every commit" has a run behind it. Spec: user story 76; Implementation Decisions "Run of record"; ticket "Close the suite audit's design gaps" item 6 (suite audit A13, A14).

**Blocked by:** 15 (patch step 3), 31 (scorecard layout)

**Status:** resolved

- [x] After a recorded run, a final step copies the scorecard, `results.json` and the snapshots into `runs/record/<run-id>/`, which is tracked (not git-ignored). Databases stay in `.runtime/`, and `results.json` cites their absolute paths.
- [x] The recorded command runs MemState's 39 upstream tests against upstream (`MemState/`, left byte-for-byte unmodified: no bytecode, cache or egg-info changes) and against `MemState-patched/` at each step, and records passed, failed and total per system in `results.json` and the scorecard. A step on which any of the 39 fails is flagged.
- [x] The scorecard's snapshot links point into `runs/record/<run-id>/`.
- [x] The README says where the run of record lives and how it is produced.
- [x] Smoke run: the folder is produced from a smoke run, `git status` shows it as trackable, and the test counts appear for upstream and every step that exists.

## Comments

2026-10-21: Built on `gs-32-run-of-record-folder`. `demo/reporting/record.py` (`record_run`, `--record` on `demo.run`, `python -m demo.reporting.record <dir>`) copies `scorecard.md`, `results.json`, `snapshots/` to `runs/record/<run id>/` (tracked; refuses to overwrite). Snapshot links were already run-relative, so they resolve inside the record. `demo/systems/upstream_tests.py` counts the 39 (junit XML; `PYTHONDONTWRITEBYTECODE`, `-p no:cacheprovider`, report in a temp dir); `SystemSpec.unit_tests` runs it after each MemState system's checks while the step is checked out; counts in `results.json` `upstream_tests` and the scorecard's "MemState's 39 upstream tests" table; a failing step (or total != 39) is flagged. Smoke (findings F30): upstream, step 1, 2, 3 all 39/0/39; `find MemState -newer` empty; the smoke record was not committed (empty `runs/record/` would not track; the folder showed as untracked, not ignored). For ticket 19: pass `--record` on the run of record; commit `runs/record/<id>/` afterwards; test runs add ~3 s upstream and ~12 s per step. `tests/reporting/test_run_of_record.py`.

