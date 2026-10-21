# 11: Review the storyline content

**What to build:** The user reads the drafted storyline before the recorded run, then approves it or asks for edits: the events, their expected states, the questions, the ability labels, the ground-truth answers and the answer topics. Spec: Implementation Decisions "Workload" ("The user reviews the drafted content before the recorded run").

**Blocked by:** 10 (storyline)

**Status:** resolved

- [x] The user has read every event and question with its labels and ground truth.
- [x] Requested edits are applied and the approval is recorded under `## Comments`.

## Comments

- 2026-10-20, user review, part 1 (accepted):
  - Q06, Q08, Q09 and Q15 are relabelled knowledge update (each answer is the latest single write), so the storyline asks knowledge update 11 and information extraction 4. Temporal reasoning and multi-session reasoning are not asked: time validity is tested by the time probes and the "two weeks ago" chat run, and multi-session reasoning is not measured.
  - E20's reason is now "promoted after the homepage prototype".
  - No abstention question: it has no answer topic, so triage cannot sort it. The report says so (§9.2).
  - The bad-merge chat run shows the "looks right" outcome (see ticket 17).
  - Applied in `demo/workloads/storyline.py` and `demo/reporting/storyline_draft.py`; draft regenerated; `pytest -q` 151 passed.
  - **Still open:** whether the scored storyline itself contains the re-explained duplicate, or stays duplicate-free (upstream and the baseline both 15/15, F20). Approval waits on that answer.
- 2026-10-20, user review, part 2 (**approved**): the scored storyline stays **duplicate-free**, so the code is unchanged. The merge damage is shown by the C4 check and the bad-merge chat run (ticket 17); it is a prototype bug, not a gap in the conditions. With a clean storyline, "every system 15/15, yet their stored state differs" is visible at a glance. Decided in the wayfinder ticket "Answer the challenge list" (S11).
