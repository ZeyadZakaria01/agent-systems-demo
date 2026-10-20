# 31: Scorecard in three groups, claim column, probes section

**What to build:** The scorecard layout the revised spec and report §9.8 describe: one table in three groups (MemState: upstream, step 1, step 2, step 3 | Reference: phase 1, phase 2 | Baseline: versioned row), a *claimed by [P1]?* column on every row, a separate section for the probes of the proposed C1′ and C4′, two change chains, the merge as existence, MemState's limits stated with their numbers, and the latency note that never claims "no measurable difference" from one repeat. Spec: user stories 8, 9, 13, 45, 72–75; Implementation Decisions "Scorecard output"; suite audit F3, F5, F15, F18.

**Blocked by:** 20 (versioned-row baseline), 21 (verdict rules), 23 (case-level change table), 25 (C4′ probe), 26 and 27 (reference GEM)

**Status:** ready-for-agent

- [ ] `scorecard.md` and `results.json` show one table in three groups with the columns in order, each cell a verdict with its snapshot link and `(n case(s) n/a)` where cases were skipped. Rows: C1, C2(a), C2(b), C2(c), C2(d), C3, C4, C5 mechanism, C5 natural trajectory, C6 clause 1, C6 clause 2. C5's cell text states the declared bound beside the active count.
- [ ] The *claimed by [P1]?* column is filled for every row (§4 and §4.3: C1, C2, C4 by construction; C3 claimed by §4's opening, not in §4.3; C5, C6 under transitions; the probes not claimed). C2(a), C4, C5 and C6, empty in the first build, are filled (suite audit F15).
- [ ] The probes section, "probes of the proposed C1′ and C4′, outside [P1]'s claims", has the six time probes with two cells each (accepts dates; answers correctly given dates) and the C4′ probe. Case-level controls (the C4 update path, each probe's control date) are shown (suite audit F18).
- [ ] The change table has two chains, upstream → step 1 → step 2 → step 3 and phase 1 → phase 2, with the case-level lines of ticket 23.
- [ ] The merge is printed as existence with the natural random-ID count beside it, in `scorecard.md` as well as `results.json` (suite audit F5).
- [ ] MemState's limits are stated with their numbers: the 500-entry history cap (a correction uses two entries) and C5's 500-topic soft limit against 2,000 active topics (F10).
- [ ] A latency table from fewer than three repeats is labelled provisional and never prints "no measurable difference" (`demo/latency_tables.py:58-76`; suite audit F3); with three repeats the rule applies as before.
- [ ] The deviations table lists the reference GEM's parameters and declared simplifications (one-hop flagging over extension edges in either direction, restricted policy vocabulary, single archive threshold, revision after every ingest as MemState's Reasoner does, no LLM), the C6 clause 2 seeds (0.06 on the reference GEM, 0.03 and 0.01 on upstream) and the versioned row's settings.
- [ ] The summary line says "no regressions on the rows the suite checks" only when the change table shows no row worse at step 3 than at step 1.
- [ ] Suite tests render the layout from stand-in results: three groups, claim column present on every row, a provisional ramp table without the note, the merge existence line.
