# Repeats and forgetting test

Type: grilling
Status: resolved
Blocked by: 03

## Question

How many times is each measurement run, and how is forgetting (C5) tested given that MemState's forget scan only starts at 500 topics?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- Deterministic tests once; the merge test ×20 with random ids (report the violation rate). LLM work is one recorded chat run, n=1 (revised from ×3, ticket 21).
- Forgetting: a generated ramp of topics (100 / 250 / 500 / 1000, 2000 if timings allow) for the two C5 verdicts and the latency row (ticket 21), **and** cheaper targeted tests: salience erasure by a field write, three-duplicate merge, merge into an archived topic.
