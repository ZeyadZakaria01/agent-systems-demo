# 29: Mutation tests: one broken reference GEM per condition

**What to build:** The checks are tested against deliberately broken versions of the reference GEM, so that "passes the suite's checks" means the checks can fail a wrong system (ticket "Reference GEM design" item 10; challenge list S1). The same authors write the checks and build the reference GEM; this is the guard. The mutants live in the tests. Spec: user story 69; Implementation Decisions "Mutation tests".

**Blocked by:** 22 (revised checks), 24 (stricter checks), 25 (C4′ probe), 26 and 27 (reference GEM)

**Status:** resolved

- [x] One mutant per condition, each built by overriding one behaviour of the reference GEM: C1 returns the oldest entry as current; C2(a) merge keeps the earlier write as current; C2(b) commits the first field before validating the second; C2(c) ignores policies added at runtime; C3 also flags association-linked topics; C4 deletes overflow beyond 500 instead of archiving it; C5 has no decay; C6 reads do not raise salience; C4′ accepts a source message but stores none; C1′ (phase 2) ignores `invalid_at`; C1′ (phase 2) answers "believed on" from the current history.
- [x] Each check gives a non-pass verdict on its targeted row, as the table in the spec states: fail C1; not pass C2(a); fail C2(b); fail C2(c); not pass C3 (control case breaks); not pass C4 (cap case); fail C5 natural trajectory; fail C6 clause 1; fail the C4′ probe; fail T4; fail T5.
- [x] Rows not targeted by a mutant keep their unmutated verdict, except where the break causes the change; the controls (C1 update path, each probe's control date) still pass.
- [x] A test also asserts the unmutated reference GEM passes every one of these checks, so the mutants are shown to differ from it in the one behaviour only.
- [x] A check that does not catch its mutant is fixed before the reference GEM's results are recorded.

## Comments

2026-10-21: `tests/systems/test_mutants.py` (25 tests, ~4 min, in-process): eleven mutants as subclasses overriding one seam each (`_valid_entry`, `_merge`, `_transact`, `_apply_policies`, `_neighbours`, `_cap`, `_effective`, `_bump`, `_propose`, `_live`). Every targeted row gives its table verdict (fail for C1, C2(b), C2(c), C5-2, C6-1, C4′, T4, T5; not pass for C2(a), C3, C4). C5's "natural trajectory" is row C5-2; C5-1 (seeded mechanism) correctly still passes with no decay. Unmutated phase 1/2 pass every row (T4/T5 absent in phase 1; Over-flagging is a measurement). Untargeted rows keep verdicts except rows the break causes, pinned per mutant: C1 (every row reading a current value: C2(a), C2(d), C4, T1-T3, T6), C2(b)→C2(c) (relies on atomic rejection), C5→C6-2 (needs decay), C6→C6-1/C6-2 clause 2. Controls still pass. No check failed to catch its mutant, so no check fix was needed.
