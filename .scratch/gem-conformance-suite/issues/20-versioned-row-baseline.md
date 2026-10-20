# 20: Versioned-row baseline

**What to build:** The baseline becomes a versioned row, replacing the last-write-wins row of ticket 01 (clean cutover, no second baseline). It is MAFBench's concrete solution (versioned fact stores with multi-version concurrency control, write-ahead logging and conflict resolution, `2602.03128v2.md:568`), so "database guarantees are necessary but not sufficient" is tested against what the benchmark asks for. It sits behind the same system adapter, in-process. Expected [INFERENCE]: it gives C1, C2's atomic commit and current-value rule, and C4; it lacks declarative policies (C2(c)), dependency tracking (C3), forgetting (C5) and reinforcement (C6), each scored `absent` and confirmed by a probe. Spec: user stories 44, 45, 55, 61, 62; Implementation Decisions "Baseline (versioned row)", "Expected verdicts"; tickets "Answer the challenge list" item 4, "Revise the spec…" follow-up.

**Blocked by:** 01 (C1 tracer bullet)

**Status:** ready-for-agent

- [ ] `demo/baseline.py` is a versioned row: an append-only history per (title, field) with the time each value was recorded, one transaction per write (all fields of a write apply, or none), in-process. The last-write-wins row, its top-10 query and its "no history" behaviour are removed.
- [ ] It accepts the ingest shape but **rejects empty and `null` values**, like a NOT NULL / CHECK constraint: the write returns `Rejected` and nothing is saved (the whole write, since a write is one transaction).
- [ ] A second `new_topic` with an existing title appends to that topic's history, so no merge ever occurs. It has no salience (reads return none), archived flag, edges or valid-time dates; each missing capability is confirmed by a probe so the rows can read `absent` (ADR 0002). A read returns the latest recorded value and changes nothing.
- [ ] It exposes `current` and the history with recorded times through `read_topic`, and answers a `recorded_at` read from its history. `describe()["accepts"]` is true for `recorded_at` only; `valid_from`, `invalid_at` and `valid_at` are false.
- [ ] Its query embeds with MiniLM and returns the top 8. The deviations table lists the versioned row's settings instead of the old top-10 survey setting.
- [ ] The suite's tests run every check in-process against it and assert the verdicts "Expected verdicts" lists for the versioned row: C1 pass; C2(a) n/a, so not-scored (no merge occurs; the test shows the check's arrangement cannot be met); C2(b) pass; C2(c) absent; C2(d) pass; C3 absent; C4 pass (merge and forgetting cases n/a; empty and `null` writes rejected); C5 mechanism and natural trajectory absent; C6 clause 1 and clause 2 absent; all six time probes absent; C4′ absent. They also assert the observations a reader relies on: the rejected empty and `null` writes with nothing saved, and salience reading none.
- [ ] The tests of resolved tickets 01, 04, 05, 06, 07, 08, 09 and 10 that pinned the old baseline's verdicts are updated to the versioned row's; none pins a MemState verdict.
- [ ] A suite test asserts a storyline search failure on the versioned row when the labelled topic falls outside the top 8.
