# 23: Case-level change table

**What to build:** The per-step change table lists the cases whose outcome changed between steps, beside each row's verdict. Step 3 fixes only the merge case of C4, so C4 reads `partial` on both steps; the table must still show "merge keeps history: broken → fixed". The table works on any chain of systems, so ticket 31 can use it for both chains. Spec: user story 13; Implementation Decisions "Scorecard output"; ticket "Close the suite audit's design gaps" item 2 (suite audit F2).

**Blocked by:** 03 (per-step runs and change table), 21 (verdict rules)

**Status:** resolved

- [x] The change table takes a chain of systems and, per row, shows each system's verdict (changed cells marked) and, for each step in the chain, the cases whose outcome changed, for example `C4: partial → partial · merge keeps history: broken → fixed`. Rows with no case change list nothing.
- [x] Case identity is stable across systems: a case has an id in the check, so a case n/a on one system and held on the next is shown as `n/a → held`.
- [x] Step 1 is still compared with upstream verdict for verdict. Counts from random-ID tests are shown but not compared.
- [x] `demo/reporting/changes.py` is generic over the chain, so the second chain (phase 1 → phase 2) needs no change.
- [x] Suite tests with stand-in systems assert a row whose verdict is unchanged but whose case outcomes changed, and a row with no change.
- [x] Smoke run: upstream, step 1 and step 2 or 3 (whichever exists) print the table with case-level lines.

## Comments

2026-10-21: `Case` gained `id` (defaults to `name`; C4 sets explicit ids) and `compare` (False for C2a's random-ID repetitions: their held counts print, no case-by-case compare). `demo/reporting/changes.py`: `case_changes_per_step` + `- step N cases: C4: partial → partial · <case>: broken → fixed (vs <baseline>)` lines, from the same baseline as the cell's verdict; a broken→held case reads `fixed`, a case missing on one side `n/a`; rows without a case change print nothing. `results.json` `change_table.case_changes` carries the same. Generic over the chain (tested with a `phase1`/`phase2` chain). Tests in `tests/reporting/test_changes.py`.
Smoke: `flock ... python -m demo.run --systems upstream,step1 --checks C1,C4,T1,T2,T3` prints the table; only step 1 exists and it changes no case on those rows (storage-only), so no case line appears. Case lines shown by rendering upstream's recorded verdicts against the in-process `baseline` as a two-system chain: `baseline cases: C4: partial → pass · history survives a merge: broken → n/a · … · version_field with null does not replace April 20: broken → fixed`. Re-run with step 2/3 once they exist. Departure: smoke's case-line evidence is the upstream→baseline chain, not a step 2/3 run (none exists).

2026-10-21 (after merging ticket 22/24): C2(a) is now one existence case plus the natural random-id count, so `Case.compare` was dropped; the count is read from `measurements["natural_count"]` and printed as `random-ID count 10/20 → 3/20 (shown, not compared)` when it differs. C4 cases carry ids (`update`, `merge`, `forgetting`, `empty-string`, `null`, `cap`). Smoke on real systems: `flock ... python -m demo.run --systems upstream,step1,step2 --checks C1,C4,T1,T2,T3` printed `- step 2 cases: T1: absent → pass · today: … -> 'April 20': n/a → held · … · history intact: …: n/a → held (vs step 1)` for T1–T6; step 1 vs upstream: no change, C4 partial on all three with no case change (so no C4 line). Case-level lines on a verdict-unchanged row are covered by the stand-in tests (C4 `partial → partial · … broken → fixed`).
