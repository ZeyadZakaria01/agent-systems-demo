# Demo shape and framing

Type: grilling
Status: resolved
Blocked by: 01

## Question

What does the demo consist of, what is the user's own contribution, and how is it framed for an audience that co-wrote the system?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- **Contribution**: the **GEM conformance suite**, a miniature of the trajectory benchmark GEM names as its first evaluation target (*Correctness and Evaluation* paragraph, §5), plus one small patch measured before and after. Scorecard columns: MemState upstream | MemState patched | last-write-wins baseline (ticket 21).
- **What the professor sees**: MemState running, Graph Explorer (`/ui/`) open while the harness drives `/v1`, field history and salience changing live; scorecard at the end. Lead with what holds (C1, append-path C4, the C6 bump), then gaps, each framed as a research question.
- **Evidence rule**: no gap enters the report or slides without a recorded reproducing run; each verdict stores a raw state snapshot.
- Upstream MemState is measured unmodified, black-box over HTTP.
- Deliverable form: Python scripts with a shared client and a runner printing a summary table.
