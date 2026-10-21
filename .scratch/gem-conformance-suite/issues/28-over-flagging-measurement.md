# 28: Over-flagging measurement on one chain

**What to build:** A measurement with no verdict: a transitive walk over extension edges, run on one chain scenario that holds one anti-trap (a dependent that does not actually change), reporting flags raised against flags needed. It serves report §5.5 ("how many hops") and StateMem's over-propagation cost. The reference GEM's default stays one hop; the transitive walk with a visited set is a mode used only here. Spec: user story 68; Implementation Decisions "Stricter check pass criteria" (over-flagging measurement); ticket "Reference GEM design" item 1.

**Blocked by:** 24 (stricter C3 and C2(c)), 26 (reference GEM phase 1)

**Status:** resolved

- [x] The scenario is one chain A ← B ← C ← D joined by extension edges. D's value does not depend on the updated field of A (the anti-trap). The scenario file labels which dependents need revision (B and C).
- [x] The reference GEM runs it twice, with one-hop propagation and with the transitive walk, and reports for each: flags raised, flags needed, flags missed, flags not needed. Hand-worked [INFERENCE]: one hop raises B only (misses C); the transitive walk raises B, C and D (D not needed).
- [x] The result is a measurement beside the C3 row, not a verdict, in `scorecard.md` and `results.json`.
- [x] A suite test asserts the counts on the reference GEM. No MemState system is measured (none propagates, F17).

## Comments

2026-10-21: Built on `gs-28-over-flagging`. Scenario `demo/scenarios/over_flagging_chain.json` (A Website Redesign, B Launch Milestone, C Press Briefing, D Catering Order; edges B→A, C→B, D→C, extension; update A's Deadline; labels B, C needed, D not). `ReferenceGem(propagation="transitive")` is a mode (default `one_hop`, validated against `PROPAGATIONS`) that walks extension edges with a visited set; the only change in `reference_gem.py` is the constructor argument, `_flag_targets` (called from `_apply_policies`) and the `describe()` parameter string, none in the valid-time internals. `demo/over_flagging.py` builds the chain on any adapter and counts raised/needed/missed/not-needed; `demo/checks/over_flagging.py` is a no-verdict (`not-scored`), `on_scorecard=False` row `Over-flagging`, `systems=("reference-gem",)`: one hop on the system as opened, transitive on a `ReferenceGem` it builds itself. `demo/over_flagging_tables.py` renders the table after the storyline in `scorecard.md` (`run.py`); the numbers are in the verdict's `measurements["over_flagging"]`, hence `results.json`.

Measured (matches the hand-worked [INFERENCE]): one hop raises B (raised 1, needed 2, missed 1 = C, not needed 0); transitive raises B, C, D (raised 3, needed 2, missed 0, not needed 1 = D). `tests/test_over_flagging.py` (8 tests) pins both, the cycle case, the labels, the table. Full suite 300 passed.

For ticket 30: register the reference GEM under id `reference-gem` (the check's `systems=`; `REFERENCE_GEM_ID` in `demo/checks/over_flagging.py`) or change that constant; the check opens its transitive instance itself, outside the session's snapshot. Ticket 29: `_flag_targets` is a new seam (one-hop vs walk).
