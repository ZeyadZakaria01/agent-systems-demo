# 10: Storyline, search-vs-memory triage and reinforcement precision

**What to build:** One storyline on the paper's Website Redesign example (a deadline that changes, Alice, a vendor delay, dependent topics). The checks, the triage and the chat runs all share it. The storyline questions run on every system. Each wrong answer is sorted into a search failure or a memory failure. Reinforcement precision is reported beside C6 clause 1. Spec: user stories 38–40; Implementation Decisions "Workload", "Reads used by checks".

**Blocked by:** 01 (C1 tracer bullet)

**Status:** resolved

- [x] The storyline has 20–30 events, each a `/v1` placement with the expected state after it. It has 10–15 questions, each labelled with a LongMemEval ability, a ground-truth answer and the topic that holds the answer.
- [x] MemState questions use the default stages and `top_k` 8; the baseline uses its top-10 query.
- [x] A question counts as answered when the read returns the labelled topic with the ground-truth value current. A wrong answer whose labelled topic was not returned is a search failure; one whose topic was returned with the wrong stored value is a memory failure. Search failures, memory failures and correct answers are counted per system.
- [x] Reinforcement precision is the salience increments to the labelled topic divided by all increments over the storyline questions. It is reported together with the number of questions whose labelled topic was bumped at all, plus a note that it equals Precision@k because every returned topic is bumped. It is not applicable on the baseline.
- [x] A suite test asserts a baseline search failure when the labelled topic falls outside the top 10.
- [x] Smoke run: a recorded upstream run prints the triage counts and reinforcement precision.
- [x] The drafted content is handed to the user for review (ticket 11).

## Comments

Merged to `gem-suite` as `5cd5c71`. Workload: `demo/workloads/storyline.py` (29 events, 15 questions); triage in `demo/workloads/triage.py`; tables in `demo/reporting/storyline.py`; draft `.scratch/gem-conformance-suite/storyline-draft.md`. Smoke run F20: upstream 15/15 correct, 0 search / 0 memory failures, reinforcement precision 0.125 = Precision@8. Ticket 11 is the human review of that draft.

- 2026-10-21, spec revision (this ticket stays resolved): the storyline stays duplicate-free (ticket 11). The baseline now answers with MiniLM top 8, not top 10 (ticket 20), and the storyline, triage and reinforcement precision also run on the reference GEM, both phases (ticket 30).
