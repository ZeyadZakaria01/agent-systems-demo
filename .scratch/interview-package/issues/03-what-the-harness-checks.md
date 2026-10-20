# What the conformance suite checks

Type: grilling
Status: resolved
Blocked by: 02

## Question

Which correctness conditions does the harness test, against what ground truth, at which level (state or answer), through which write path, and on what workload?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- **Conditions**: all six; C1 and C4 act as controls that should pass. MemState's own 39 unit tests touch only C1 and append-path C4.
- **Ground truth**: the paper's three levels (current value per unit over time; dependent units after each update; active footprint per interaction count) plus provenance trails (C4) and salience trails (C6).
- **Level**: state-level checks are primary; one answer-level contrast case (after the bad merge, an answer can look right while state violates C2/C4), produced by one recorded Ollama chat run and graded by hand, labelled n=1. Cloud-vs-local comparison and the LLM judge are future work (revised, ticket 21).
- **Write path**: `/v1/ingest` and `/v1/query` produce the verdicts; the single chat run is scored separately (chat-created topics have no embedding, salience lives at a different level).
- **Workload**: one shared storyline (~20–30 events, 10–15 questions) encoded as `/v1` placements; the chat run uses 2–3 of its questions. Questions labelled with LongMemEval's five abilities; LongMemEval itself is motivation only.
