# 10: Storyline, search-vs-memory triage and reinforcement precision

**What to build:** One storyline on the paper's Website Redesign example (a deadline that changes, Alice, a vendor delay, dependent topics). The checks, the triage and the chat runs all share it. The storyline questions run on every system. Each wrong answer is sorted into a search failure or a memory failure. Reinforcement precision is reported beside C6 clause 1. Spec: user stories 38–40; Implementation Decisions "Workload", "Reads used by checks".

**Blocked by:** 01 (C1 tracer bullet)

**Status:** ready-for-agent

- [ ] The storyline has 20–30 events, each a `/v1` placement with the expected state after it. It has 10–15 questions, each labelled with a LongMemEval ability, a ground-truth answer and the topic that holds the answer.
- [ ] MemState questions use the default stages and `top_k` 8; the baseline uses its top-10 query.
- [ ] A question counts as answered when the read returns the labelled topic with the ground-truth value current. A wrong answer whose labelled topic was not returned is a search failure; one whose topic was returned with the wrong stored value is a memory failure. Search failures, memory failures and correct answers are counted per system.
- [ ] Reinforcement precision is the salience increments to the labelled topic divided by all increments over the storyline questions. It is reported together with the number of questions whose labelled topic was bumped at all, plus a note that it equals Precision@k because every returned topic is bumped. It is not applicable on the baseline.
- [ ] A suite test asserts a baseline search failure when the labelled topic falls outside the top 10.
- [ ] Smoke run: a recorded upstream run prints the triage counts and reinforcement precision.
- [ ] The drafted content is handed to the user for review (ticket 11).
