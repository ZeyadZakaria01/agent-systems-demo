# 30: Reference GEM workloads and windows

**What to build:** The workloads that run on the reference GEM, and the two windows counted in interactions. The reference GEM runs the C1–C6 checks, the time probes, the C4′ probe, the storyline with its triage and reinforcement precision, and the merge revision and dependent-topic staleness windows. It does not run the latency ramps (in-process milliseconds are not comparable with an HTTP server; the ramps measure the engine swap and the patch) or the chat runs (it has no LLM chat). Spec: user stories 30, 63; Implementation Decisions "Stricter check pass criteria" (windows), "Runner"; ticket "Reference GEM design" items 5 and 8.

**Blocked by:** 10 (storyline), 26 and 27 (reference GEM), 21 (verdict rules)

**Status:** ready-for-agent

- [ ] The runner runs the reference GEM, both phases, in-process on every check, time probe and the storyline, and skips the latency ramps and chat runs on it; the scorecard shows no latency or chat cell for it.
- [ ] The storyline runs with MiniLM and top 8. Triage (search failures, memory failures, correct) and reinforcement precision are reported per phase. Expected [INFERENCE]: 15/15 correct; precision 1/8 (every returned topic is bumped).
- [ ] The merge revision window is measured in interactions (duplicate-creating ingest → merge visible), median and range over 20 repetitions. The dependent-topic staleness window is measured in interactions (A's update → B's flag visible on a read); expected [INFERENCE] 0, because the flag is raised in the same transition.
- [ ] C5's verdict text states β = 500 beside the active count at 2,000 topics (about 400 expected [INFERENCE]).
- [ ] Suite tests assert the window counts with revision running after every ingest, and the storyline counts.
