# How the conformance suite runs MemState

Type: grilling
Status: resolved
Blocked by: 02

## Question

Does the harness score against a real server started by `scripts/run_memstate.sh` (waiting for the Reasoner's background effects with a timeout), or in-process via FastAPI `TestClient` with a real server only for the live show?

Recommendation so far: real server only: one code path, and what the professor watches is what gets scored.

## Answer

Resolved 2026-10-11 (recommendation accepted with the review, ticket 21): real server only, started by `scripts/run_memstate.sh`; the harness polls state until the Reasoner's background effects land, with a timeout, and logs that wait separately (it feeds the latency row).
