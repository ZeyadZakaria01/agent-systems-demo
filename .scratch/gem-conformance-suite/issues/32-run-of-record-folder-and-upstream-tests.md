# 32: Run-of-record folder and the upstream tests at every step

**What to build:** The run of record lives in the repository. `demo/results/` is git-ignored, yet report §9.2 and §9.8 promise snapshot links, so the recorded run is copied into a tracked `demo/record/<run-id>/`. The same command runs MemState's 39 upstream tests at upstream and at each patch step and records the counts, so "the 39 tests pass unedited at every commit" has a run behind it. Spec: user story 76; Implementation Decisions "Run of record"; ticket "Close the suite audit's design gaps" item 6 (suite audit A13, A14).

**Blocked by:** 15 (patch step 3), 31 (scorecard layout)

**Status:** ready-for-agent

- [ ] After a recorded run, a final step copies the scorecard, `results.json` and the snapshots into `demo/record/<run-id>/`, which is tracked (not git-ignored). Databases stay in `.runtime/`, and `results.json` cites their absolute paths.
- [ ] The recorded command runs MemState's 39 upstream tests against upstream (`MemState/`, left byte-for-byte unmodified: no bytecode, cache or egg-info changes) and against `MemState-patched/` at each step, and records passed, failed and total per system in `results.json` and the scorecard. A step on which any of the 39 fails is flagged.
- [ ] The scorecard's snapshot links point into `demo/record/<run-id>/`.
- [ ] The README says where the run of record lives and how it is produced.
- [ ] Smoke run: the folder is produced from a smoke run, `git status` shows it as trackable, and the test counts appear for upstream and every step that exists.
