# Verdict scale and unimplemented conditions

Type: grilling
Status: resolved
Blocked by: 03

## Question

How are conditions scored when MemState has no machinery for them (C3, the policy half of C2)?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- Verdict scale: **pass / partial / fail / absent**. `fail` is reserved for features MemState implements incorrectly; `absent` means "capability not implemented, confirmed by a probe run". Summaries count them separately.
- **C3**: probe run (two topics linked with `kind="extension"`, update one, check the other) scored `absent`.
- **C2** splits three ways: superseded value returned as current → merge test (real pass/fail); atomic commit (Algorithm 1 line 12) → one `/v1/ingest new_topic` with valid fields plus an edge to a non-existent topic id, outcomes defined in ticket 21; declarative policies → `absent` (`Policies` is six numeric knobs).
- **C5** and **C6** each get two verdicts (mechanism vs natural trajectory; clause 1 vs clause 2), defined in ticket 21.
- Rejected: scoring absent features as `fail` (outcome fixed in advance, inflates the fail count, reads as a gotcha to the author).
