# Revise the conformance-suite spec

Type: task
Status: resolved
Blocked by: 25, 26, 27, 28, 29

## Question

Bring `.scratch/gem-conformance-suite/spec.md` in line with report §9 (v2) and the resolutions of the tickets that block this one: scorecard columns with the §4.3 claim, the E4 row folded into C4, paired controls, the five time probes, the three-commit LadybugDB patch, the new measurements. Set its `Status:` back to `ready-for-agent` when done.

## Comments

- 2026-10-20, from [Time probes and their controls](27-time-probes-and-controls.md): six time probes, not five; see its Answer.
- 2026-10-20, from [Patch packaging for the three-commit patch on LadybugDB](28-patch-packaging-for-three-commits.md): the suite runs on upstream, the baseline and each commit, with a per-commit table of changed verdicts; commit 1 is compared verdict for verdict, not count for count. Check for the spec: `TopicFields.cap_history` (exercised by `MemState/tests/test_topic_fields.py:37-42`) trims field history to a cap, which may drop entries against C4 [INFERENCE: not run]; decide whether C4 gets a history-cap case.

## Answer

Resolved 2026-10-20. `.scratch/gem-conformance-suite/spec.md` rewritten to report §9 and tickets 25–29; `Status: ready-for-agent`.

- Five systems (upstream, steps 1–3, baseline); scorecard [P1]'s claim | upstream | patch (step 3) | baseline, plus a per-step change table (step 1 compared verdict for verdict).
- Rows: C1, C2(a–c), C3, C4 (empty/`null` write folded in, ex-E4), C5 ×2, C6 ×2, six time probes; controls include each probe's control date; over-blocking recorded.
- Time-probe stories, story shift, as-of moment and scoring as in Time probes and their controls; dated merge case on step 3.
- Storyline questions carry an answer topic: search-vs-memory triage and reinforcement precision (Precision@k, no verdict).
- Latency ramps on upstream and each step, 1 run while building, 3 at the end; step 3 also times as-of reads.
- Patch steps 1–3 specified from Bitemporal history model and API; packaging, `--patched`, engine-named DBs from Patch packaging.
- Chat runs: bad-merge on upstream, "two weeks ago" on step 3, both recorded and replayable.
- Decided here: C4 gets a history-cap case (501 updates; is the first value still there?), since `cap_history` keeps the newest 500 entries [INFERENCE]; the run decides the case.
- Build plan: two days, eight subagent slices, step 2 on the critical path.

README status line updated.
