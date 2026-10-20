# 07: C6 clause 1 and clause 2

**What to build:** Two C6 rows, each quoting its clause wording. Clause 1 checks that retrieval raises the salience of what it returns. Clause 2 checks that a reinforced topic leaves forgetting eligibility. Over-reinforcement and salience durability are recorded as observations, not verdicts. Spec: user stories 14, 27; report §9.4; Implementation Decisions "Reads used by checks".

**Blocked by:** 01 (C1 tracer bullet)

**Status:** resolved

- [x] Clause 1 confirms that each retrieval raises the salience of the topics it returns, and records whether unrelated candidates rise too (observation: over-reinforcement).
- [x] Clause 2 ingests a field-less topic at salience 0.03 and queries it until it passes 0.05, then scores whether it left forgetting eligibility. A field write that resets salience is recorded as a durability observation.
- [x] Salience checks account for the +0.1 that the suite's own reads add to every returned topic.
- [x] Both rows quote the clause wording. Reinforcement precision appears beside clause 1 without a verdict once ticket 10 supplies it.
- [x] The suite's tests assert, on the baseline, that both clauses fail with unchanged salience.
- [x] Smoke run: a recorded upstream run prints both rows and their observations, with snapshots.

## Comments

Merged as `4344039`; reviewed and fixed in `16f2bd5` (C6-2 gives `partial`, not not-scored, when the control is not archived; user's question on this verdict was cancelled, `partial` is the default taken). Smoke F15, C6-2 re-recorded.

- 2026-10-21, spec revision (this ticket stays resolved), ratified by the user: C6 clause 2 stops at the first forgetting pass; when the control is not archived the row is `not-scored` ("forgetting was not shown to run"), not `partial`. Clause 1 gains an as-of salience case. Both are ticket 22. Upstream's recorded `pass` is unaffected (F15).
