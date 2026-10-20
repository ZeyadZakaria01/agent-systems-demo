# Reference GEM: show the time gap is in the conditions, not the prototype

Type: grilling
Status: resolved

## Question

Upstream MemState fails several conditions (C2(a), C3, C4, C5-2; F17, F18, F21, F22) as well as the time probes (F19). The objection to the demo is therefore "the time cases fail only because the prototype is incomplete". Should the demo first complete the conditions, and where: inside the real MemState server, or in a separate model?

## Answer

Resolved 2026-10-20 with the user.

- **Option chosen: MemTX's method.** MemTX compares against small reimplementations of each published system, "each implements only what its paper claims, with deliberate absences declared", and runs the authors' official MemState through the same interface "as a check on ours" (`docs/papers/2607.23929v2.md:170`). Its own MemState baseline (`MemTX/src/baselines/gem_memstate_manager.py`, 267 lines) does **not** satisfy the six conditions: it has no topics, no salience, no decay, no edges or propagation, no merge, and hard-coded rather than declarative checks. So we copy the method, not that code.
- **A reference GEM is added to the suite.** It is our own in-process system built to the paper's definitions of C1–C6, behind the suite's existing system adapter, like the baseline. It is scored in two phases:
  - **Phase 1, reference GEM:** expected to pass C1–C6 and fail the time probes (one time axis; C1 = most recent value).
  - **Phase 2, reference GEM + Zep's four timestamps:** expected to pass C1–C6 and the time probes. It uses the same bitemporal rules as the real patch (report §9.5, ADR 0005).
- **What this changes about the claim.** It moves from "the published prototype gets the time cases wrong" to "a system built to all six conditions gets them wrong, so the gap is in the conditions (report §5.7), and Zep's model closes it without breaking C1–C6".
- **The real-MemState patch stays as planned.** Port, bitemporal histories, merge by valid time: build tickets 02, 12–15. It shows the same fix on the authors' system, which answers "the reference model is a toy". Upstream stays measured unmodified.
- **Rejected:** completing C2(c), C3 and C5 inside the real MemState server. That means three research-sized features (a policy language, LLM-driven repair, decay) built into its LLM-driven Reasoner, and a claim tied to one prototype's code.
- **Scope of the reference GEM:**
  - C5 and C6 follow the paper's full wording: salience bumped on every read, decay with disuse, archiving below a threshold, archived topics readable by id.
  - C2(c) and C3 are deliberately simplified and declared as such in the report.
  - C5-2 passes by design (upstream fails it, F22). Reinforcement precision stays 1/8, because C6's wording bumps every returned topic.
- **Preconditions agreed:**
  1. The C3 and C2(c) checks get stricter pass criteria before the reference GEM is scored. Otherwise "passes all six" means only "passes our absence probes".
  2. Every simplification is declared in the report.
  3. The real-MemState patch is kept.
- **Interview line to prepare:** "You built it to fail." Answer: it is built to the paper's definitions; its failure follows from C1's wording, which is the finding.

Expectations above are reasoning [INFERENCE]; nothing is built or run.

Open design details: [Reference GEM design: scope per condition, stricter checks, scorecard place](38-reference-gem-design.md). Spec and build tickets: [Revise the spec and build tickets for the reference GEM and the suite audit](39-revise-spec-for-reference-gem-and-audit.md). ADR: `docs/adr/0007-reference-gem-beside-memstate.md`. Glossary: "Reference GEM".

## Comments

- 2026-10-20, *superseded in part* by [Answer the challenge list](40-answer-the-challenge-list.md):
  - **Phases.** Phase 1 is built once, on the **kindest reading** of Definition 4: a value's timestamp is when it became true, and "current" is judged at the question date. Expected [INFERENCE]: it passes T1, T2, T3 and T6, and fails T4 (no end date) and T5 (no second timestamp). Upstream MemState stands for the arrival-time reading. Phase 2 is "reference GEM + C1′ (report §9.5 rules)", not "+ Zep's four timestamps".
  - **Claim.** The claim is now: "Definition 4 does not say what its one timestamp means, and no reading of it handles all six time stories. C1′ is an **amendment**: one clarification and two additions (end date, recorded time). The model is the standard bitemporal one, in the form Zep uses; our contribution is the read rule and its tests."
  - **Wording.** Results are worded "passes the suite's checks, with declared simplifications".
  - **Interview line.** "You built it to fail" is now answered by: phase 1 gets every date and the kindest reading, and still fails T4 and T5, because the paper's entries have no place for an end date or a second time.
