# Ratify verdict rules set during the build

Type: grilling
Status: resolved
Blocked by: —

## Question

The build (branch `gem-suite`, worktree `/home/zeyad/work/agent-systems-demo-wt/integration`) settled two verdict rules without the user. Both change scorecard cells, so they need an answer before the build ticket "Run of record" records the scorecard:

1. **C6 clause 2 when the control is not archived.** The never-read control topic is still live after the filler topics, so no forgetting pass was shown to run. The build grades the row `partial` (reinforcement held, forgetting not demonstrated). The user's question was cancelled, so this is the recommended default and has not been ratified. The alternative is `fail`. Evidence: `docs/journal.md` on `gem-suite`, entry "Ticket 07 review: C6-2 returned not-scored…"; `tests/test_c6.py::test_clause_2_is_partial_when_the_control_shows_no_forgetting_pass_ran`.
2. **Not-scored when no case applies.** The spec reserves not-scored for C2(b)'s "neither outcome" rule (spec, "Verdict model"). The build's `from_cases` also returns not-scored when no case applied, and it marks verdicts resting on fewer cases than were run with `(n case(s) n/a)`, for example the baseline's C1 cell `pass (1 case n/a)`. Ratify the broader rule and amend the spec, or narrow the code to the spec. Evidence: `docs/journal.md` on `gem-suite`, the ticket 01 review entry; `tests/test_verdict.py::test_a_verdict_resting_on_fewer_cases_than_were_run_says_so_in_its_scorecard_cell`.
3. **C2(b) when the ingest succeeds and reports the invalid edge applied.** Upstream lands here (F17: ingest succeeds, reports `edge:<id>` applied, no edge stored). The check scores it `not-scored` with a soundness observation, but story 21 gives this outcome no verdict and report §9.4 says "a fail contradicts a stated claim". Options: `fail` (a reported write that did not happen breaks C2's soundness), or `not-scored` (atomicity untestable with this input). Audit: [suite-audit-vs-spec.md](../assets/suite-audit-vs-spec.md) F14; [suite-audit-vs-report.md](../assets/suite-audit-vs-report.md) A11.
4. **T5 (as-of) when both answers are identical.** The check scores `absent` even on a system that advertises `recorded_at`, so a buggy step 2 would read "not implemented" (ADR 0002) instead of `fail`. Proposed rule: `absent` only when the system does not accept `recorded_at`; otherwise `fail`. Audit: suite-audit-vs-spec.md F7; suite-audit-vs-report.md A15.
5. **Missing time capability: `fail` or `absent`.** Upstream has no valid-time option, yet T1–T4 and T6 score `fail` while T5 scores `absent`, on the same probe evidence (F19: `accepts_valid_time: false`). The glossary defines `fail` as "implements the capability … but behaves incorrectly", which would make these `absent` (ADR 0002). Choose deliberately, and keep it consistent with item 4. Source: [challenge list](../assets/challenge-conditions-baseline-suite-probes.md) T2, and S3 (the reason ADR 0002 gives for `absent` concerns how it reads to the paper's author).

## Answer

Resolved 2026-10-20 with the user.

- **Item 2 (decided): a verdict rests only on the cases that could run.** A case that needs a capability belonging to another condition is n/a. The scorecard cell says how many cases were skipped (`pass (1 case n/a)`, baseline C1, F13). If no case could run, the verdict is `not-scored`. This differs from `absent`, which means the whole condition's capability is missing, confirmed by a probe (ADR 0002). The spec's "Verdict model" gets this sentence, and the build's `Verdict.from_cases` already does it.
- **Item 3 (decided): C2(b) switches its input.** The edge to a missing topic never reaches atomicity: `add_related_edge` is a `MATCH … MERGE` that silently creates nothing (`graph_store.py:1081-1088`), so nothing fails mid-write (F17). The new input is one `new_topic` with a valid field and a second field whose `ref_topic_id` points to a missing topic. That field is validated mid-write (`graph_store.py:450-452`). On upstream it gives HTTP 400 with the topic and first field stored: a partial commit, **`fail`** (F23, measured on `gem-suite`). The edge case stays as a separate soundness observation: "an edge reported applied is not stored". My first recommendation (`fail` on the edge input) was wrong and is recorded in the journal.
- **Consequences, not separate decisions:**
  - **Item 1 (C6 clause 2, control not archived):** under item 2 the target's survival cannot be judged when no forgetting pass ran, so the row is **`not-scored`**, with the observation "forgetting was not shown to run". Forgetting that never runs is C5's failure (C5-2). The recorded upstream row is unaffected: its control was archived, so `pass` (F15).
  - **Items 4 and 5 (time probes):** these follow from "Answer the challenge list" (two cells per probe: "accepts dates" and "answers correctly given dates"; upstream "cannot express") and from ADR 0002. A probe scores **`absent`** when the system does not accept the date the probe needs, confirmed by the schema probe. It scores **`fail`** when the system accepts the date and answers wrong. So T5 is `absent` only when `recorded_at` is not accepted. Upstream reads `absent` on all six probes. Reference GEM phase 1 is expected [INFERENCE] to read `absent` on T4 (no end date) and T5 (no recorded time).
- **For the spec revision ("Revise the spec and build tickets for the reference GEM and the suite audit"):**
  - the verdict-model sentence;
  - the C2(b) input and the edge observation;
  - the C6-2 not-scored rule;
  - the per-probe absent/fail rule;
  - a per-probe date-capability test. Today `demo/memstate_system.py:97-102` requires both `valid_from` and `invalid_at`, so a system accepting only a start date would get no dates at all.
