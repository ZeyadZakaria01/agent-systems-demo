# 30: Reference GEM workloads and windows

**What to build:** The workloads that run on the reference GEM, and the two windows counted in interactions. The reference GEM runs the C1–C6 checks, the time probes, the C4′ probe, the storyline with its triage and reinforcement precision, and the merge revision and dependent-topic staleness windows. It does not run the latency ramps (in-process milliseconds are not comparable with an HTTP server; the ramps measure the engine swap and the patch) or the chat runs (it has no LLM chat). Spec: user stories 30, 63; Implementation Decisions "Stricter check pass criteria" (windows), "Runner"; ticket "Reference GEM design" items 5 and 8.

**Blocked by:** 10 (storyline), 26 and 27 (reference GEM), 21 (verdict rules)

**Status:** resolved

- [x] The runner runs the reference GEM, both phases, in-process on every check, time probe and the storyline, and skips the latency ramps and chat runs on it; the scorecard shows no latency or chat cell for it.
- [x] The storyline runs with MiniLM and top 8. Triage (search failures, memory failures, correct) and reinforcement precision are reported per phase. Expected [INFERENCE]: 15/15 correct; precision 1/8 (every returned topic is bumped).
- [x] The merge revision window is measured in interactions (duplicate-creating ingest → merge visible), median and range over 20 repetitions. The dependent-topic staleness window is measured in interactions (A's update → B's flag visible on a read); expected [INFERENCE] 0, because the flag is raised in the same transition.
- [x] C5's verdict text states β = 500 beside the active count at 2,000 topics (about 400 expected [INFERENCE]).
- [x] Suite tests assert the window counts with revision running after every ingest, and the storyline counts.

## Comments

2026-10-21: Built on `gs-30-ref-gem-workloads`. `demo/systems/registry.py` registers `reference-gem-p1` and `reference-gem-p2` (labels "reference GEM (phase N)", in-process, after `step3`, before `baseline`; `SystemSpec.latency=False`). `REFERENCE_GEM_IDS` in `demo/checks/over_flagging.py` is now both ids. Windows are counted in interactions where `read_state()["interactions"]` exists (`demo/workloads/windows.py::interactions`; `MergeOutcome.window_interactions`, C3 `Pair.window_interactions`); seconds otherwise. Tests: `tests/systems/test_reference_gem_workloads.py` (registry, both windows 0 over 20 repetitions, pre-merge window, storyline 15/15 and 1/8 on both phases, C5-2 text, runner, latency table exclusion).

Smoke: `python -m demo.run --systems reference-gem-p1,reference-gem-p2 --results-root /tmp/t30-results` (in-process, 38 s, no error verdict): both windows "median 0 interactions" (merge range 0-0 over 20 repetitions); storyline 15/15 correct, reinforcement precision 0.125 on both phases; C5-2: 1604 archived and 396 active at n=2000 "against declared bound 500 topics (β)"; no latency table. Chat: chat runs are recordings (`runs/recordings/`, upstream), never opened on a system id, so the reference GEM has no chat cell. The scorecard table has no reference GEM column yet: its columns are ticket 31's (the rows read "—" until `Column`s list `reference-gem-p1`/`-p2`); the windows, storyline, reinforcement and over-flagging tables already show both systems.
