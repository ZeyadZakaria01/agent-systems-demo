# 07: C6 clause 1 and clause 2

**What to build:** Two C6 rows, each quoting its clause wording. Clause 1 checks that retrieval raises the salience of what it returns. Clause 2 checks that a reinforced topic leaves forgetting eligibility. Over-reinforcement and salience durability are recorded as observations, not verdicts. Spec: user stories 14, 27; report §9.4; Implementation Decisions "Reads used by checks".

**Blocked by:** 01 (C1 tracer bullet)

**Status:** ready-for-agent

- [ ] Clause 1 confirms that each retrieval raises the salience of the topics it returns, and records whether unrelated candidates rise too (observation: over-reinforcement).
- [ ] Clause 2 ingests a field-less topic at salience 0.03 and queries it until it passes 0.05, then scores whether it left forgetting eligibility. A field write that resets salience is recorded as a durability observation.
- [ ] Salience checks account for the +0.1 that the suite's own reads add to every returned topic.
- [ ] Both rows quote the clause wording. Reinforcement precision appears beside clause 1 without a verdict once ticket 10 supplies it.
- [ ] The suite's tests assert, on the baseline, that both clauses fail with unchanged salience.
- [ ] Smoke run: a recorded upstream run prints both rows and their observations, with snapshots.
