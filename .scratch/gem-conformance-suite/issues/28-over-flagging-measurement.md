# 28: Over-flagging measurement on one chain

**What to build:** A measurement with no verdict: a transitive walk over extension edges, run on one chain scenario that holds one anti-trap (a dependent that does not actually change), reporting flags raised against flags needed. It serves report §5.5 ("how many hops") and StateMem's over-propagation cost. The reference GEM's default stays one hop; the transitive walk with a visited set is a mode used only here. Spec: user story 68; Implementation Decisions "Stricter check pass criteria" (over-flagging measurement); ticket "Reference GEM design" item 1.

**Blocked by:** 24 (stricter C3 and C2(c)), 26 (reference GEM phase 1)

**Status:** ready-for-agent

- [ ] The scenario is one chain A ← B ← C ← D joined by extension edges. D's value does not depend on the updated field of A (the anti-trap). The scenario file labels which dependents need revision (B and C).
- [ ] The reference GEM runs it twice, with one-hop propagation and with the transitive walk, and reports for each: flags raised, flags needed, flags missed, flags not needed. Hand-worked [INFERENCE]: one hop raises B only (misses C); the transitive walk raises B, C and D (D not needed).
- [ ] The result is a measurement beside the C3 row, not a verdict, in `scorecard.md` and `results.json`.
- [ ] A suite test asserts the counts on the reference GEM. No MemState system is measured (none propagates, F17).
