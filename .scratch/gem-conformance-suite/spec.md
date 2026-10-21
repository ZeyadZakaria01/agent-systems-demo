# Spec: GEM conformance suite and the bitemporal patch

Status: ready-for-agent

Source of the design: report §9 (`docs/report/gem-limitations-and-directions.md`) and the resolved tickets on the wayfinder map (`.scratch/interview-package/map.md`), in particular "Bitemporal history model and API", "Time probes and their controls", "Patch packaging for the three-commit patch on LadybugDB", "Reinforcement precision and the engine latency ramps", "Reference GEM: show the time gap is in the conditions", "Reference GEM design", "Ratify verdict rules set during the build", "Close the suite audit's design gaps" and "Answer the challenge list". Terms follow `GLOSSARY.md`. ADRs: 0001 (MemState measured unmodified over HTTP), 0002 (`absent` for unimplemented capabilities), 0003 (thinking off via proxy), 0004 (Kuzu pinned at 0.11.3 for upstream), 0005 (corrections keep and copy, narrowed: ordinary updates store no end date), 0006 (patch on LadybugDB, upstream on Kuzu), 0007 (a reference GEM beside MemState).

## Problem Statement

The GEM paper defines memory correctness as a property of the trajectory (C1–C6) but reports no measurements, and MemState's 39 tests cover only C1 and the append path of C4. In front of the paper's author, the user must show which conditions MemState meets as published, which it gets wrong, and which it does not implement, each backed by a recorded run on a fresh database; what MemState adds over a versioned database row; whether the time failures belong to the prototype or to the conditions, which needs a system built to the paper's definitions (the reference GEM); and a contribution of their own, measured before and after: C1′, an amendment of C1 (one clarification, two additions: an end date and a recorded time), in the standard bitemporal form Zep uses, added to MemState's field histories on LadybugDB. Recorded probes exist (findings F7–F24, `scripts/probe_memstate.py`); the suite's first tickets (01–11, 16) are built, the patch beyond step 1 and the reference GEM are not. The interview demo and report §9.7–§9.8 depend on it.

## Solution

A **GEM conformance suite**: state-level checks that drive a memory system only through GEM operators (`/v1/ingest`, `/v1/query`), read back what it stores (current values, field histories with timestamps and provenance, salience, archived flags, edges) and give each scorecard row a verdict: pass, partial, fail, absent or not-scored. It runs on seven systems:

- **upstream**: MemState at `945d7c4` on Kuzu 0.11.3, unmodified, over HTTP;
- **step 1, step 2, step 3**: the three commits of the patched copy on LadybugDB 0.21.2: (1) port, (2) bitemporal field histories and C1′ queries, (3) merge by valid time;
- **reference GEM, phase 1 and phase 2**: our own in-process system built to the paper's definitions of C1–C6, with declared simplifications (ADR 0007). Phase 1 reads Definition 4 on the kindest reading (a value's one timestamp is when it became true; "current" is judged at the asked date among non-archived entries; no end date, no recorded time). Phase 2 is phase 1 plus C1′ (report §9.5);
- **baseline**: a versioned row (append-only history with recorded time, one transaction per write, in-process, MiniLM, top 8).

Every in-process system retrieves with MiniLM and top 8. The scorecard is **one table in three groups**: **MemState** (upstream, step 1, step 2, step 3) | **Reference** (phase 1, phase 2) | **Baseline** (versioned row), with a *claimed by [P1]?* column. The time probes and the C4′ probe sit in their own section, "probes of the proposed C1′ and C4′, outside [P1]'s claims", with two cells per probe. The change table has two chains, upstream → step 1 → step 2 → step 3 and phase 1 → phase 2, and each row also lists the cases whose outcome changed between steps. Step 1 → step 2 holds the engine constant and isolates the effect of the time model on MemState; phase 1 → phase 2 isolates C1′ on a system that meets the conditions.

Beside the verdicts the suite records: the merge result as existence with the natural random-ID count (10/20) beside it, the merge revision window and dependent-topic staleness window (seconds on MemState, interactions on the reference GEM), search-vs-memory triage of the storyline questions, reinforcement precision for C6, the over-flagging measurement of a transitive walk on one chain, and latency ramps on upstream and each step (not on the reference GEM). Two recorded Ollama chat runs (n=1 each, graded by Sonnet and a blind reviewer agent (hand grading dropped by the user 2026-10-21), replayable, MemState only): the bad-merge contrast on upstream, and the "two weeks ago" case on step 3. A live mode drives a running server so the Graph Explorer shows histories and salience changing during the interview. The run of record is copied to a tracked `runs/record/<run-id>/`, and MemState's 39 upstream tests are run at upstream and at each step.

The reference GEM's result is worded "passes the suite's checks, with declared simplifications", never "satisfies C1–C6". Because the same authors write the checks and build the reference GEM, the stricter checks, the parameters and every system's expected verdict are written in this spec before the build, and each check is run against one deliberately broken reference GEM that it must catch.

## User Stories

**Running**

1. As the presenter, I want one command that runs the suite on all seven systems and prints the scorecard and the change tables, so that the evidence of record needs no manual steps.
2. As the presenter, I want each check run against a server started on a fresh absolute database, so that every verdict meets the evidence rule.
3. As the presenter, I want the runner to stop each server when its check finishes, so that the laptop never holds two servers or a stale database lock.
4. As the presenter, I want the runner to select step 1, 2 or 3 by checking out that commit in `MemState-patched/` before starting the server, so that every step is measured from the same branch without copies.
5. As the presenter, I want a live mode that drives an already running server, so that Prof. Mansour can watch field histories and salience change in the Graph Explorer.
6. As the presenter, I want live-mode verdicts labelled live and kept apart from recorded results, so that the scorecard of record comes only from fresh-database runs.
7. As the presenter, I want a replay mode that renders both chat recordings with no server or GPU, so that interview day does not depend on the laptop's GPU.

**Scorecard**

8. As the presenter, I want rows for C1, C2(a) superseded value, C2(b) atomicity, C2(c) declarative policies, C2(d) the superseded read on the lapsed-override story, C3, C4, C5 mechanism, C5 natural trajectory, C6 clause 1 and C6 clause 2, plus a separate section of probes of the proposed C1′ and C4′ (the six time probes and the C4′ probe), so that each clause is scored against its exact wording and the proposed refinements are not scored against the paper's claims.
9. As the presenter, I want a *claimed by [P1]?* column that states [P1]'s claim for every row (§4 and §4.3: C1, C2, C4 by construction; C3 claimed by §4's opening but not listed in §4.3; C5, C6 under transitions; the time probes and the C4′ probe not claimed, because they probe proposed refinements; ADR 0002 cites `MemState/README.md:5`, "NOT Full Implementation"), so that each verdict is read against the paper's own claim and `absent` is not read as a failure against it. The first build left the claim empty for C2(a), C4, C5 and C6; every row gets one.
10. As the presenter, I want each cell to show a verdict and link to its raw-state snapshot, so that any verdict can be audited live.
11. As the presenter, I want fails and absences counted separately, so that missing capabilities read as open research rather than defects (ADR 0002).
12. As the presenter, I want the controls (C1, the update path of C4, and each time probe's control date) marked as controls, so that the suite shows it can detect a pass and catches over-blocking.
13. As the presenter, I want the per-step change table to compare step 1 with upstream verdict for verdict, and to list beside each row the cases whose outcome changed (for example `C4: partial → partial · merge keeps history: broken → fixed`), with the natural random-ID merge count shown but not compared, so that chance variation (stale value current 10/20 on Kuzu vs 8/20 on LadybugDB, F9) is not read as an engine effect, and a step that fixes one case of a row is visible although the row's verdict does not change.
14. As the presenter, I want the C6 rows to quote the clause wording and show reinforcement precision beside clause 1 without a verdict, so that the gap between C6's wording and its motivation is visible without grading the author on a rule he did not write.

**Evidence**

15. As a reviewer, I want every verdict to save its requests and responses, the full state it read (every topic including archived ones, plus edges), timestamps, the DB path, the system label, the MemState commit and the engine line printed by the run script, so that it can be reproduced and cited in `docs/findings.md`.
16. As a reviewer, I want every setup write labelled and kept apart from scored transitions, so that no verdict rests on an editor-endpoint edit.
17. As a reviewer, I want every `absent` verdict to carry the probe run that confirmed the absence, so that no absence is asserted from reading code.
18. As the author of `docs/findings.md`, I want each recorded run to print the command, DB path and key output in pasteable form, so that new findings meet the evidence rule.

**Condition checks** (report §9.4)

19. As a reviewer, I want C1 to store `Deadline: March 15`, update it to `April 20` through `/v1/ingest version_field`, and confirm a default query returns only April 20 and a temporal query the full history.
20. As a reviewer, I want C2(a) to create two same-title topics where the one to be dropped holds the newer value, trigger the Reasoner's merge, and check which value is current, repeated 20 times with random topic IDs and distinct titles, and reported as **existence** (does the merge make the superseded value current in the arranged case?), not as a rate; the natural count on random IDs, without the arranged order (upstream: 10/20, F9), is shown beside it and not compared between systems.
21. As a reviewer, I want C2(b) to send one `/v1/ingest new_topic` with a valid first field and a second field whose `ref_topic_id` points to a missing topic (`graph_store.py:450-452` validates it mid-write), and classify the outcome: an error with the topic or the first field persisted is a partial commit (fail; upstream, F23); a refusal with nothing stored holds; neither (the missing reference is accepted) means atomicity is not testable with this input (not-scored). The earlier input, an edge to a missing topic, stays as a separate soundness observation: an edge reported applied is not stored (upstream, F17), never a verdict.
22. As a reviewer, I want C2(c) declarative policies probed and scored absent when the system exposes no way to add a policy (only numeric knobs); where a policy can be added at runtime, the stricter check (story 65) decides.
23. As a reviewer, I want C3 to link B → A with an extension edge (and a second pair A → B), update A, and read B before and after revision, so that propagation is probed as in F7; where the system flags dependents, the stricter check (story 64) decides.
24. As a reviewer, I want C4 to verify that a field history survives a value update, a merge and **real forgetting** with provenance intact (never an editor archive write), and that `version_field` with `""` and separately with `null` does not replace April 20 (rejection with April 20 current holds; an empty current value breaks the case). The forgetting case is n/a where a topic with fields cannot be forgotten through the system's own operations (upstream: any field write resets salience to 1.0, F24); on the reference GEM it runs through the reference GEM's own decay.
25. As a reviewer, I want C4 to include a history-cap case: 501 writes to one field (one `new_topic` and 500 `version_field`), then check whether the first value is still readable, so that the 500-entry cap (`TopicFields.cap_history`, `graph_store.py` `max_history=500`) is decided by a run: upstream drops the oldest (F21); the reference GEM archives the overflow instead of deleting it (readable by id) and is expected to pass [INFERENCE].
26. As a reviewer, I want the C5 mechanism verdict to ramp past the 500-topic trigger with a field-less topic ingested at `salience=0.01` and check whether it is archived (`partial` if only the count gate fires), and the natural-trajectory verdict to count archived topics at each ramp step with no setup. C5 counts topics, not history entries, and the verdict text states the system's declared bound beside the active count (upstream: the 500-topic soft limit against 2,000 active topics, F10, F22; reference GEM: declared β = 500 against its active count).
27. As a reviewer, I want C6 clause 1 to confirm each retrieval raises the salience of the topics it returns and record whether unrelated candidates rise too, and also that an as-of read (`valid_at` / `recorded_at`) raises salience (a case that is n/a where the system accepts no dates); and I want clause 2 to seed a topic at 0.03 on MemState and query it until it passes 0.05, stopping at the **first forgetting pass**, where the never-read control must be archived and the read topic must not be. If the control is not archived, no pass was shown to run, so the row is not-scored with the observation "forgetting was not shown to run" (that is C5's failure, not C6's). A field write resetting salience is recorded as a durability observation.
28. As a reviewer, I want the merge extras (three topics sharing one title; an active topic merged into an archived duplicate; whether upstream deletes the dropped topic) run and recorded, so that MemState's "not what is permanently erased" promise is cited only after a run.
29. As a reviewer, I want background effects awaited by polling state with a timeout, each wait logged apart from client latency, so that asynchronous revision is not misread as absent.
30. As a reviewer, I want the merge revision window (duplicate-creating ingest → merge visible, median and range over the 20 repetitions) and the dependent-topic staleness window reported: in seconds on MemState (the dependent window "unbounded (C3 absent)", citing the C3 run), and **in interactions** on the reference GEM (report §6.8 defines the window as "the time, or number of transitions").

**Time probes** (report §9.6; "Time probes and their controls")

31. As a reviewer, I want each time probe told as a dated story and asked on its story "today" plus at least one other date, one of which is the control, using the stories in Implementation Decisions, so that a wrong answer and a rejected legitimate update are both caught; the stories are ours, motivated by Zep and StateMemBench, and results assume correct dates (a best case).
32. As a reviewer, I want each story shifted so its "today" falls on the run day, the "today" question asked as a plain read with no date, and the other dates asked as as-of reads, so that the default path is exercised against the real server clock.
33. As a reviewer, I want a system that accepts none of the dates a probe needs to receive the same writes in the same order with no dates and to answer every asked date with the same plain read, so that the comparison isolates the time model and the system is never called wrong for what it cannot express.
34. As a reviewer, I want each story on its own topic and fresh database per system, apart from the storyline, so that a failure is attributable to the time logic.
35. As a reviewer, I want the as-of probe's "believed on Feb 10" asked at a real moment between the two writes (note the time after the first write, wait 1 s, send the second), since recorded time is the real clock.
36. As a reviewer, I want each probe scored in two cells: *accepts dates* (detected per probe from the dates that probe needs, not both `valid_from` and `invalid_at` for every probe) and *answers correctly given dates*. The probe is **absent** when a needed date is not accepted, confirmed by the schema probe; **fail** when the dates are accepted and any answer is wrong (labelled over-blocking when the control date fails); **pass** when every asked date is right and, on the patch, the history is intact (no value lost; where a stored end date changed or a value was retracted, the original is expired and its copy linked by `replaces_entry_id`, ADR 0005). T5 is absent only when `recorded_at` is not accepted; a buggy implementation that accepts it reads fail.
37. As a reviewer, I want one dated merge case on step 3 (topic A "April 20 since Jan 5"; duplicate B written later, "March 15 since Dec 1"; after the merge, today → April 20, both values in history, B's entry tagged `merged_from_topic_id`), so that merge by valid time is tested with dates.

**Storyline, triage and reinforcement precision**

38. As the presenter, I want one storyline of 20–30 events and 10–15 questions on the paper's Website Redesign example, each event a `/v1` placement with the expected state after it, each question labelled with a LongMemEval ability, a ground-truth answer and the topic that holds the answer, so that the checks, triage and chat runs share one scenario.
39. As a reviewer, I want every wrong storyline answer sorted with StateMemBench's first triage question: labelled topic not returned by `/v1/query` → search failure; returned but stored value wrong → memory failure, so that bad search is not mistaken for bad memory.
40. As a reviewer, I want reinforcement precision (salience increments to the labelled topic ÷ all increments over the storyline questions) and the number of questions whose labelled topic was bumped at all, with a note that it equals Precision@k because every returned topic is bumped.

**Latency**

41. As a reviewer, I want latency ramps at 100 / 250 / 500 / 1,000 / 2,000 topics on upstream and each step (not on the reference GEM), with identical undated writes and plain reads, logging per step the client latency of `/v1/query` and `/v1/ingest`, the settle time (poll floor about 0.1 s; it is not a Reasoner wait, F22) and the archived count, so that upstream → step 1 shows the engine, step 1 → 2 the time model and step 2 → 3 the merge change on ordinary writes.
42. As a reviewer, I want step 3 to also time 20 as-of reads at 2,000 topics.
43. As a reviewer, I want each ramp run once while building and, if time allows, three times on the final commits, reporting median and range and calling a difference inside the range "no measurable difference"; a ramp run only once is reported as one run, labelled provisional, with no such claim.

**Baseline**

44. As a reviewer, I want the baseline, a versioned row, put through the same checks, time probes and storyline, with MiniLM and top 8, so that the scorecard shows what MemState adds over a versioned database row (the kind of store MAFBench asks for).
45. As a reviewer, I want the scorecard to include the deviations table (MemState's intent router as shipped, Ollama model defaults, the think-off proxy, the baseline's settings, and the reference GEM's parameters and declared simplifications), so that every departure from a standard setup is declared.

**Patch** (report §9.5; ADRs 0005, 0006)

46. As the presenter, I want `scripts/run_memstate.sh --patched` to start the patched copy, default DB folders named per engine, and the engine and source folder printed at startup, so that a database is never opened by the wrong engine unnoticed.
47. As anyone reproducing the work, I want the three commits exported as `patches/0001-port-to-ladybugdb.patch`, `0002-bitemporal-field-histories.patch`, `0003-merge-by-valid-time.patch`, which rebuild `MemState-patched/` from the pinned submodule with the README's two commands.
48. As a reviewer of the patch, I want step 1 to change only the `kuzu_adapter.py` import and the `pyproject.toml` dependency, so that "the engine swap changes nothing" is checkable at a glance.
49. As a reviewer of the patch, I want step 2 to implement the entry model, writes, ordering, end-dated values, scoped overrides, keep-and-copy on a changed stored end or a retraction, C1′ queries (with `current` on every field) and the chat reference time as specified below, so that the time probes flip without breaking C1.
50. As a reviewer of the patch, I want step 3 to merge by valid time as specified below, so that the merge rows flip.
51. As a reviewer of the patch, I want MemState's 39 tests to pass unedited at every step, and developer tests for each rule added inside the patched copy, so that the patch breaks nothing the authors tested.

**Chat runs**

52. As the presenter, I want one recorded Ollama chat run on upstream after a bad merge, asking 2–3 storyline questions with no intent override, logging each turn's route, so that an answer can be shown looking right while state violates C2 or C4.
53. As the presenter, I want one recorded "two weeks ago" chat run on step 3: two separate requests, `reference_time` Oct 6 "I started my new job two weeks ago" and `reference_time` Oct 20 "how long have I been there?", graded on the stored start date (Sep 22 ± 1 day) and the answer (four weeks).
54. As the grader, I want each recorded turn to carry the ground truth, Sonnet's grade and a blind reviewer agent's grade (hand grading dropped by the user 2026-10-21), so that the n=1 cases are graded transparently.

**Maintenance**

55. As a maintainer, I want the suite's own tests to run in-process against the baseline and the reference GEM without any server, and every check written against one system adapter, so that tests are fast and adding a system means one adapter.
56. As a newcomer, I want the README to explain how to run the suite (recorded, live, replay) and `--patched`, and to drop "no demo code exists", so that the repo describes itself accurately.
57. As the presenter, I want every unexpected difficulty during the build or runs logged in `docs/journal.md`, so that the report can cite the build's lessons.

**Reference GEM and baseline** (report §9.3, §9.5; ADR 0007; "Reference GEM design")

58. As a reviewer, I want a reference GEM, our own in-process system built to the paper's definitions of C1–C6 behind the same adapter, so that "the time gap is in the conditions, not the prototype" is tested on a system built to meet them.
59. As a reviewer, I want phase 1 built once on the kindest reading of Definition 4 (t = when the value became true; "current" judged at the asked date among non-archived entries; no end date, no recorded time) and phase 2 to be phase 1 plus C1′ (report §9.5; ADR 0005 as narrowed), so that C1′'s effect is isolated on a system that meets the conditions.
60. As a reviewer, I want the reference GEM's design, parameters and every simplification written in this spec and declared in the report before it is built, and its result worded "passes the suite's checks, with declared simplifications", so that I am not asked to trust a system graded by its own authors.
61. As a reviewer, I want the baseline to be a versioned row (append-only history with recorded time, one transaction per write, in-process), so that "database guarantees are necessary but not sufficient" is tested against what MAFBench asks for.
62. As a reviewer, I want every in-process system to retrieve with MiniLM and top 8, so that C6 and the triage numbers are comparable with MemState's.
63. As the presenter, I want the C1–C6 checks, the time probes, the storyline with its triage and reinforcement precision, and the two windows run on the reference GEM, and no latency ramps and no chat runs on it, so that in-process milliseconds are never compared with an HTTP server and no LLM chat is invented.

**Stricter and new checks** (tickets "Reference GEM design" items 5 and 10; "Answer the challenge list")

64. As a reviewer, I want C3 to pass only when the dependent is flagged *because of* the extension edge (the read of B before B is re-checked carries a flag naming A's update, with the updated field and timestamp as evidence), a topic linked to A only by an association edge is **not** flagged (control), and the flag clears when B is next written, so that "passes C3" means more than "B changed".
65. As a reviewer, I want C2(c) to pass only when a policy added through the API at runtime ("Deadline not before Start") rejects a violating write with nothing saved, while an ordinary write still commits (control), so that "passes C2(c)" means more than "a policy surface exists".
66. As a reviewer, I want one C2 check on the lapsed-override story that reads "superseded" as "validity ended by a later statement": the value current today must not be one that a later statement ended; a lapsed override returning the base value is not a violation, and an ended override returned as current is a C1′ error counted in T4, not here.
67. As a reviewer, I want the C4′ probe: write a value with a source message, then check whether the entry's provenance resolves to the stored source. Expected [INFERENCE]: pass on the reference GEM (stores the source message with each write), absent on upstream, the patch and the versioned row.
68. As a reviewer, I want a transitive-walk measurement on one chain scenario with one anti-trap (a dependent that does not actually change), reporting flags raised against flags needed for the one-hop and the transitive propagation, with no verdict, for report §5.5 ("how many hops") and StateMem's over-propagation cost.
69. As a reviewer, I want each check run against one deliberately broken reference GEM per condition, which the check must catch, so that a check that passes the reference GEM is shown able to fail a wrong one.
70. As a reviewer, I want every system's expected verdict per row written in this spec before the build (Implementation Decisions, "Expected verdicts"), marked [INFERENCE] where not measured, so that the results are compared with a prediction made in advance.

**Verdicts and output**

71. As the presenter, I want a verdict to rest only on the cases that could run: a case that needs a capability belonging to another condition is n/a, the scorecard cell says how many were skipped (`pass (1 case n/a)`), and a row with no case that could run is not-scored (this differs from `absent`, which means the condition's whole capability is missing, ADR 0002).
72. As the presenter, I want the six time probes and the C4′ probe in their own scorecard section with two cells per probe, so that a system that cannot express a case reads "cannot express", not "wrong", and no probe is mixed into the claimed rows.
73. As the presenter, I want MemState's limits stated with their numbers (the 500-entry history cap: a correction uses two entries; C5's 500-topic soft limit against 2,000 active topics, F10) and the claim worded "no regressions on the rows the suite checks", so that the patch's result is not stretched beyond what is measured.
74. As the presenter, I want the scorecard to print the merge result as existence with the natural random-ID count (10/20, F9) beside it, and the merge violation count to appear in `scorecard.md`, not only in `results.json`.
75. As the presenter, I want the latency note never to claim "no measurable difference" from fewer than three repeats, so that a provisional single run is labelled provisional.
76. As the presenter, I want the run of record copied to a tracked `runs/record/<run-id>/` (scorecard, `results.json`, snapshots; databases stay in `.runtime/`, their paths cited), and MemState's 39 upstream tests run at upstream and at each patch step with the counts recorded, so that the report's snapshot links and its "39 tests at every commit" claim rest on files in the repository.

**Patch additions** (tickets "Close the suite audit's design gaps", items 1 and 3)

77. As a reviewer of the patch, I want an ordinary update to store no end date (an entry is valid until the next entry's `valid_from`, unless it carries its own end), keep-and-copy to run only when a stored end date changes or a value is retracted, and expired entries to be hidden unless history is requested, so that one undated update leaves exactly two entries, C1's history check holds, and upstream's `test_field_history_tools.py:27-49` (`history_count == 2`) passes unedited.
78. As a reviewer of the patch, I want `current` on every field (`null` when nothing is valid) on `/v1/query` and on the UI topic read, and the adapter to refuse the newest-entry fallback for any system that accepts dates, so that a missing `current` raises an error instead of producing a silent wrong verdict.

## Implementation Decisions

**Modules** (layout from "Demo folder layout"). A `demo` package:

- **client**: the system adapter interface and its MemState HTTP implementation (upstream and patched differ only in which server runs; the adapter detects the patch's extra fields and ignores none of them).
- **baseline**: the versioned-row adapter (in-process).
- **reference_gem**: the reference GEM, both phases, as an in-process adapter (design below). Its deliberately broken variants for the mutation tests live in the tests, not in the shipped module.
- **workload**: the storyline (events, questions, ground truth, ability and answer-topic labels), the time-probe stories, and the ramp topic generator.
- **checks**: one module per condition, plus `time_probes`, the C4′ probe, `merge_extras`, `triage` (search vs. memory and reinforcement precision), the over-flagging measurement and `latency`.
- **chat_run**: records and replays both Ollama runs.
- **run**: the runner, the scorecard and the change tables.

Outputs: `runs/recordings/` (chat runs), `runs/results/` (verdicts, snapshots, latency logs, one directory per run; git-ignored) and the tracked `runs/record/<run-id>/` (the run of record).

**System adapter: the single seam.**

- `ingest(request) -> response`: a scored transition, same shape as `/v1/ingest` (placements `new_topic` / `extend_topic` / `version_field`; fields with value, provenance, why-changed and optional `valid_from` / `invalid_at` where the system accepts them; edges with kind; salience; and, where the system stores one, the source message of the write).
- `query(request) -> response`: a scored transition, same shape as `/v1/query` (`q`, `stages`, `explain`, `top_k`, `topic_ids`, `field_names`; optional `valid_at` and `recorded_at` where accepted). The as-of probe still sends `valid_at` and `recorded_at` to a system that does not accept them, as evidence (F19).
- `read_state()` / `read_topic(id)`: every topic including archived ones (title, current value per field or none, field history with all timestamps, provenance and operation tags, the revision flag and its evidence, salience, archived flag, topic history, archived history overflow) and edges. MemState: `GET /api/ui/topics`, `GET /api/ui/topics/{id}`, `GET /api/ui/graph`. A missing topic reads as "deleted". For a system that accepts any date, a field without `current` raises an error: the adapter never falls back to the newest history entry (the first build fell back to `history[0]`, `memstate_system.py:54-64`).
- `resolve_source(entry)`: the stored source message an entry's provenance points to, or nothing (C4′ probe).
- `add_policy(rule)`: adds a ⟨event, condition, action⟩ policy at runtime where the system has a surface for it; otherwise an explicit nothing-value.
- `setup_write(...)`: forced topic ID, salience, archived flag through editor endpoints, recorded and labelled.
- `wait_until(predicate, timeout) -> elapsed`.
- `describe()`: system label, server URL, DB path, MemState commit, engine line, the declared bound for C5 (upstream: the 500-topic soft limit; reference GEM: β), and `accepts`: for each of `valid_from`, `invalid_at`, `valid_at`, `recorded_at`, whether the system accepts it (MemState: read from the server's OpenAPI schema over all schemas, one flag per date; in-process systems: declared). A probe tests only the dates it needs (Time-probe scoring), so a system that accepts a start date but no end date still receives start dates.

Missing capabilities (no salience, no edges, no as-of, no policy surface, no source store) are explicit nothing-values, never errors; `absent` is decided only from a probe's observed outcome.

**Reads used by checks.** A deterministic read of one topic is `/v1/query` with `stages=["temporal"]`, `topic_ids=[id]`; `explain=true` when the history is needed. With the semantic stage, `topic_ids` only filters the kNN result, and structural without temporal drops fields with no current value (`executor.py:239-240, 252-265, 297-299`, from code). Every read adds +0.1 salience to each returned topic (`executor.py:328-339`), so salience checks account for the suite's own reads. Storyline questions use the default stages and `top_k` 8 on every system.

**Baseline (versioned row).** An append-only history per (title, field) with the time each value was recorded; one transaction per write (all fields of a write apply, or none); in-process. It rejects empty and `null` values, like a NOT NULL / CHECK constraint (`Rejected`, nothing saved). A second `new_topic` with an existing title appends to that topic's history, so no merge ever occurs. No salience (reads return none), archived flag, edges or valid-time dates: each of these missing capabilities is scored `absent` and confirmed by a probe (ADR 0002). The read returns the latest recorded value and changes nothing; the query embeds with MiniLM and returns the top 8. It stands for the versioned fact store MAFBench calls for (versioned fact stores with multi-version concurrency control, write-ahead logging and conflict resolution; `2602.03128v2.md:568`): it gives C1, C2's atomic commit and current-value rule, and C4, and lacks declarative policies (C2(c)), dependency tracking (C3), forgetting (C5) and reinforcement (C6). Expected verdicts: see "Expected verdicts".

**Verdict model.** Fields: row ID, system, verdict (pass / partial / fail / absent / not-scored), cases (held, broke or n/a, with observation), observations that are not verdicts (over-reinforcement, salience not durable, topic deleted on merge, edge reported applied but not stored, route log, over-blocking, forgetting not shown to run), probe evidence for `absent`, snapshot reference, control flag, claim. Scale (ADR 0002): **a verdict rests only on the cases that could run**; a case that needs a capability belonging to another condition is n/a, and the scorecard cell says how many were skipped (`pass (1 case n/a)`, for example upstream's C4 and the baseline's C1, F13). pass = every case that could run held; partial = some held; fail = the capability is implemented and every case that could run broke; absent = the whole condition's capability is missing, confirmed by a probe run; **not-scored = no case could run** (for example C2(b)'s "neither outcome" rule, and C6 clause 2 when no forgetting pass ran). `absent` and `not-scored` differ: absent is a finding about the system, not-scored about the check's input. Time probes are scored in two cells (Time-probe scoring).

**Time-probe stories.** Story dates are shown in the report; the suite shifts each story so "today" is the run day (e.g. a run on Oct 20 stores the budget story's Nov 5 as Oct 20 and Sep 1 as Aug 16). A system receives the writes with the dates it accepts (`describe()["accepts"]`); a system that accepts none of the dates a probe needs gets the same writes in the same order, undated. The stories are ours, motivated by Zep and StateMemBench; results assume correct dates (a best case).

| Row | Dates it needs | Writes, in order | Asked → correct (answer of a system that returns its last write, with no dates) |
|---|---|---|---|
| T1 Retroactive fact | `valid_from` (the story gives the older value a start, Dec 1 of the previous year, so it can be placed; its end is implied by the next entry's start) | Jan 5 "deadline April 20"; Feb 15 "it was March 1 before it moved on Jan 5" | today Feb 15 → April 20 (March 1 ✗); Dec 20 → March 1 (March 1) |
| T2 Out-of-order arrival | `valid_from` | "pro since Oct 1" arrives first; "basic since Aug 1" arrives after | today Oct 20 → pro (basic ✗); Sep 1 → basic (basic) |
| T3 Future-dated change | `valid_from` | Jun 1 "basic"; Nov 20 "premium from December" | today Nov 20 → basic (premium ✗); Dec 5 → premium (premium) |
| T4 Lapsed scoped override, story 1 | `valid_from`, `invalid_at` (the override's end is stated and no later entry ends it) | Sep 1 "$50"; Oct 1 "$80 for October only" | Oct 15 → $80 ($80); today Nov 5 → $50 ($80 ✗) |
| T4 Lapsed scoped override, story 2 (plain statement during override) | `valid_from`, `invalid_at` | as story 1, plus Oct 10 "now $100" | today Nov 5 → $100 ($100); Oct 15 → $100 ($100; "a plain statement ends the override": the one date where "the shorter validity wins" alone would answer $80); Oct 5 → $80 ($100 ✗) |
| T6 Future value, nothing before | `valid_from` | Nov 20 "premium from December", only value | today Nov 20 → no current value (premium ✗); Dec 5 → premium (premium) |
| T5 As-of query | `valid_from`, `valid_at`, `recorded_at` | Jan 5 "deadline April 20"; Feb 15 "moved to May 1 on Feb 1" | true on Feb 10 (`valid_at`) → May 1; believed on Feb 10 (`recorded_at`, a real moment between the writes) → April 20 |

The control is the date every system should get right (the one where the last-write answer is correct). The lapsed-override probe passes only if both its stories pass.

**Time-probe scoring: two cells per probe.** *Accepts dates*: does the system accept the dates this probe needs (table column "Dates it needs"), detected per probe from `describe()["accepts"]`, so a system accepting `valid_from` only still gets T1, T2, T3 and T6 with dates. *Answers correctly given dates*: **pass** when every asked date is right and, on the patch, the history is intact (no value lost; where a stored end date changed or a value was retracted, the original carries `expired_at` and its copy is linked by `replaces_entry_id`); **fail** when the dates are accepted and any asked date is wrong, with the observation "over-blocking" when the control date is wrong; **absent** when a needed date is not accepted, confirmed by the schema probe and, for T5, by sending `valid_at` and `recorded_at` and observing the same answer (F19). So T5 is absent only when `recorded_at` is not accepted; a system that accepts it and answers wrong reads fail. A system that cannot express a probe is never called wrong. The probes are scored in their own scorecard section, "probes of the proposed C1′ and C4′, outside [P1]'s claims", beside the *claimed by [P1]?* column on every row.

**Reference GEM** (ADR 0007; wayfinder "Reference GEM design"; report §9.5). An in-process Python system behind the adapter, no server, no LLM. Every item below is a decision, fixed before the build and declared in the report.

- *State.* Topics with fields; each field a list of entries (value, provenance, the source message stored with the write, timestamps by phase); edges of kind extension or association; policies; per topic a salience, the interaction of its last touch and an archived flag. Retrieval: MiniLM brute-force top 8. Each ingest and each query is one **interaction**; the counter drives decay, the forgetting check and the windows.
- *C1 and C2(a), phases.* Phase 1: each entry has one timestamp, when the value became true (`valid_from`); the current value is the entry with the latest timestamp not after the asked date, among non-archived entries; no end date, no recorded time, so it accepts `valid_from` only. Phase 2 = phase 1 plus C1′ (report §9.5 rules, ADR 0005 as narrowed): end dates, recorded time, ordinary updates store no end date, keep-and-copy only on a changed stored end or a retraction, scoped overrides layering, `valid_at` and `recorded_at` reads. Revision (merge) runs **after every ingest, as MemState's Reasoner does** (`MemState/src/memstate/reasoner/engine.py:36-37`), as a separate step after the write commits: the survivor keeps both histories with their provenance; the current value is the later write in phase 1 and the later valid date in phase 2. Until revision has run, a read can see both copies; the merge revision window is reported in interactions.
- *C2(b), C2(c).* A transition is validated against the proposed next state and commits all or nothing. Policies are ⟨event, condition, action⟩ rules stored in the state as data and addable at runtime through `add_policy`. Conditions come from a small fixed vocabulary: field comparisons on the topic being written, and "a neighbour exists via an extension or association edge". Actions: *reject* (a postcondition checked before commit) and *flag for revision*. A default policy rejects empty and null values. Conditions that query the whole state are out (declared simplification).
- *C3.* Runs as the paper's Listing 1 policy, one hop, undirected as C3's own wording is ("for every pair connected by a typed edge, an update to one triggers evaluation of the other", `2605.26252v1.md:212`; "a change in one can entail a change in the other", `:275`): an update flags every topic connected to the updated one by an extension edge, whatever the edge's direction, with evidence (`{updated_field, timestamp}`, and the update named); association edges never flag; the flag clears when the dependent is next written, and that write flags its own neighbours. No repair (belongs to the revision operator). A transitive-walk mode with a visited set exists only for the over-flagging measurement.
- *C4.* History capped at 500 entries as in MemState, but overflow is archived, not deleted: it leaves the active history and stays readable by id. Each write stores its source message and provenance resolves to it. If the valid value is archived, a read returns no current value plus a note that an archived value exists.
- *C5.* MemState's behaviour is reused wherever its code has it: threshold 0.05, β = 500 (its `topic_count_soft_limit`), and halving a topic's salience when it is archived (`MemState/src/memstate/core/executor.py:360`; new). Added, because the paper requires it (`2605.26252v1.md:323`) and MemState's code lacks it (its docs, `docs/operations/forget.html`, describe decay; the code has none, F10, F24): decay on disuse per interaction, computed lazily (s · λ^Δinteractions on read), and a forgetting check after every interaction that archives topics below θ_archive (MemState's runs only at the soft limit). Any read or write of a topic resets its decay clock.
- *C6.* +0.1 per returned topic, as MemState's `query_salience_bump`; as-of reads count as reads. Reinforcement precision therefore stays 1/8 at top 8 with one labelled topic.

| Parameter | Value | Basis |
|---|---|---|
| θ_archive | 0.05 | MemState's `forget_salience_threshold` |
| λ per interaction | 0.05^(1/400) ≈ 0.9925: an untouched topic at 1.0 falls below θ after 400 interactions | added (decay on disuse, `2605.26252v1.md:323`; MemState has none) |
| Decay clock | any read or write of a topic resets it | declared |
| Forgetting check | after every interaction | added (MemState's runs only at the soft limit) |
| Salience on archive | halved | MemState `executor.py:360` |
| β, declared bound on active topics | 500 | MemState's `topic_count_soft_limit` |
| Salience bump | +0.1 per returned topic | MemState `query_salience_bump` |
| History cap | 500 entries; overflow archived, readable by id | MemState's cap, archive instead of delete |
| Retrieval | MiniLM, top 8 | MemState's default `top_k`; same for the versioned row |
| Propagation depth | one hop, over extension edges in either direction | the paper's Listing 1 and C3's pairwise, undirected wording (`:212`, `:275`) |
| Merge revision | after every ingest | MemState's Reasoner (`engine.py:36-37`) |
| C6 clause 2 seeds | target and control at 0.06 (upstream keeps 0.03 and 0.01) | declared per-system test setting: a seed below θ is archived by its own interaction |

Declared simplifications (report §9.5): one-hop flagging with no repair; the restricted policy vocabulary; a single archive threshold, no compress or hide rungs; revision after every ingest, as MemState's Reasoner does; no LLM, so no chat. Unreached by design: C2(c) conditions over the whole state (the paper's open "policy language").

**Stricter check pass criteria** (written before the reference GEM is built). A verdict follows the scale above; absent only with the probe run as evidence.

- *C3 cases.* Run on both pairs, B → A and A → B, each scored. (1) Extension edge: after A's field is updated, a read of the topic linked to A (B) before it is written carries a flag that names that update (the updated field and its timestamp as evidence); the flag is due to the extension edge, whatever its direction. (2) Control: a topic linked to A only by an association edge is not flagged after the same update. (3) The flag clears when the flagged topic is next written. A system with no flag and no propagation, confirmed by the F17 probe (B unchanged after a polled wait, no flag), is absent.
- *C2(c) cases.* (1) A policy "Deadline not before Start" added at runtime through `add_policy` rejects a write that sets Deadline before Start, and a read-back shows nothing saved (state identical to before). (2) Control: an ordinary write (Deadline after Start) commits. A system with no way to add a policy at runtime, confirmed by the schema probe (F17), is absent.
- *C2(d), the lapsed-override read.* On the T4 stories, the value current today must not be one a later statement ended. Story 1 (Nov 5): $50 and $80 both pass (the override ended by its own date is ended, not superseded; returning it is a T4 error, not a C2 violation). Story 2 (Nov 5): $100 passes; $80 or $50, both ended by the Oct 10 statement, is a violation.
- *C4 cases.* (1) Update survives (control). (2) Merge keeps history; n/a where the system has no merge. (3) Real forgetting keeps history: the field-bearing topic reaches forgetting through the system's own operations and its history and provenance are intact after; n/a where a topic with fields cannot be forgotten (upstream, F24; confirmed by the run). (4) Empty and `null` writes do not replace the current value. (5) Cap: 501 writes to one field, the first value still readable (in the history, or as archived overflow readable by id).
- *C5 verdict text* states the declared bound beside the active count (`describe()`).
- *C6 clause 2 on the reference GEM.* The reference GEM runs its forgetting check after every interaction, so a topic seeded at 0.03 (below θ) would be archived by its own interaction. The check therefore seeds the target and the control at 0.06 (a declared per-system test setting; upstream keeps 0.03 and 0.01) and reads the target on every interaction until the first forgetting pass; the control must be archived at that pass and the target not.
- *C4′ probe.* One write with a source message; the entry's provenance resolves (`resolve_source`) to that stored message. Absent where the system has no source store (probe: no field or endpoint); fail where it accepts a source and provenance does not resolve to it.
- *As-of read raises salience (C6 clause 1 case).* An as-of read (`valid_at` or `recorded_at`) returns a topic and its salience rises by the system's bump; n/a where no date is accepted.
- *Over-flagging measurement (no verdict).* One chain A ← B ← C ← D (extension edges), where D's value does not actually depend on the updated field of A (the anti-trap). The scenario labels which dependents need revision (B and C). The reference GEM runs it with one hop and with the transitive walk and reports flags raised against flags needed for each (one hop: B only, one needed flag missed; transitive: B, C and D, one flag not needed) [INFERENCE: hand-worked, to be measured].
- *Windows.* Merge revision window on the reference GEM: interactions from the duplicate-creating ingest until the merge is visible, median and range over 20 repetitions. Dependent-topic staleness window: interactions from A's update until B's flag is visible on a read [INFERENCE: 0, the flag is raised in the same transition].

**Expected verdicts** (pre-registered; written before the build). A cell with a finding number was measured (check as then written; the run of record re-measures it); every other cell is [INFERENCE]. "n/a" counts are cases that cannot run.

| Row | Upstream | Step 1 | Step 2 | Step 3 | Ref. phase 1 | Ref. phase 2 | Versioned row |
|---|---|---|---|---|---|---|---|
| C1 (control) | pass (F13) | pass (F16) | pass | pass | pass | pass | pass |
| C2(a) merge, existence | fail (F18) | fail | fail | pass | pass | pass | n/a, so not-scored: a second same-title `new_topic` appends to the same topic, so no merge occurs and the arrangement cannot be met [INFERENCE; the build confirms it from the check's behaviour] |
| C2(b) atomicity (`ref_topic_id` input) | fail (F23) | fail | fail | fail | pass | pass | pass |
| C2(c) policies | absent (F17) | absent | absent | absent | pass | pass | absent |
| C2(d) lapsed-override read | pass | pass | pass | pass | pass | pass | pass |
| C3 | absent (F17) | absent | absent | absent | pass | pass | absent |
| C4 | partial, 1 case n/a (F21, F24) | partial, 1 n/a | partial, 1 n/a | partial, 1 n/a (merge case fixed) | pass | pass | pass (merge and forgetting cases n/a; empty and `null` writes rejected) |
| C5 mechanism | pass (F22) | pass (F22) | pass | pass | pass | pass | absent (no archived flag, confirmed by the absence probe) |
| C5 natural trajectory | fail (F22) | fail (F22) | fail | fail | pass (about 400 active at 2,000 topics, bound β = 500) | pass | absent (no archived flag, confirmed by the absence probe) |
| C6 clause 1 | pass, 1 case n/a (F15) | pass, 1 n/a | pass | pass | pass | pass | absent (salience reads none, confirmed by the absence probe) |
| C6 clause 2 | pass (F15) | pass | pass | pass | pass | pass | absent (salience reads none, confirmed by the absence probe) |
| T1 retroactive | absent (F19) | absent | pass | pass | pass | pass | absent |
| T2 out-of-order | absent (F19) | absent | pass | pass | pass | pass | absent |
| T3 future-dated | absent (F19) | absent | pass | pass | pass | pass | absent |
| T4 lapsed override | absent (F19) | absent | pass | pass | absent (no end date) | pass | absent |
| T5 as-of | absent (F19) | absent | pass | pass | absent (no recorded time) | pass | absent (accepts `recorded_at`, not `valid_at`; the "believed on" half is recorded as an observation) |
| T6 future value | absent (F19) | absent | pass | pass | pass | pass | absent |
| C4′ probe | absent | absent | absent | absent | pass | pass | absent |

Beside the verdicts: storyline 15/15 on every system (upstream F20; the rest [INFERENCE]); reinforcement precision 0.125 on MemState (F20) and 1/8 on the reference GEM, not applicable on the versioned row; merge natural count 10/20 on upstream (F9); phase 1 → phase 2 changes exactly T4 and T5 (absent → pass) and no other row; step 1 → step 2 changes T1–T6 (absent → pass); step 2 → step 3 changes C2(a) (fail → pass) and the C4 case "merge keeps history" (broken → fixed) while the row stays partial.

**Mutation tests.** Each check is run against one deliberately broken reference GEM per condition and must give a non-pass verdict on the targeted row, with the other rows unaffected except where the break causes it. The mutants live in the tests.

| Condition | Broken reference GEM | The check must |
|---|---|---|
| C1 | returns the oldest entry as current | fail C1 |
| C2(a) | merge keeps the earlier write's value as current | not pass C2(a) |
| C2(b) | commits the first field before validating the second | fail C2(b) (partial commit) |
| C2(c) | ignores policies added at runtime | fail C2(c) (violating write accepted) |
| C3 | also flags association-linked topics | not pass C3 (control case breaks) |
| C4 | deletes overflow beyond 500 instead of archiving it | not pass C4 (cap case) |
| C5 | no decay | fail C5 natural trajectory |
| C6 | reads do not raise salience | fail C6 clause 1 |
| C4′ | accepts a source message but stores none | fail the C4′ probe |
| C1′ (phase 2) | ignores `invalid_at` | fail T4 |
| C1′ (phase 2) | answers "believed on" from the current history | fail T5 |

**Patch, step 1 (port).** `import kuzu` → `import ladybug as kuzu` in `src/memstate/store/kuzu_adapter.py`; `pyproject.toml` `kuzu>=0.11.0` → `ladybug==0.21.2`. No renames; MemState's README untouched.

**Patch, step 2 (bitemporal field histories).** From "Bitemporal history model and API":

- *Entry model:* each history entry in `Topic.fields_json` gains `invalid_at`, `created_at`, `expired_at` beside the existing `valid_from`, plus `operation`, `replaces_entry_id`, `corrected_by_entry_id` where they apply.
- *Writes:* `FieldWrite` takes optional `valid_from` and `invalid_at`. Without dates, `valid_from` = `created_at` = write time and no end, so undated writes behave as upstream. A `valid_from` that does not parse as a date keeps arrival order (upstream's `test_topic_fields.py` uses `"t0"`…`"t4"`).
- *Ordering and validity:* entries are ordered by `valid_from`; an entry is valid until the next entry's `valid_from`, unless it carries its own `invalid_at`. A late-arriving older value therefore ends where the later one begins, with no stored end; equal `valid_from` → later recorded wins. **An ordinary update stores no end date on the entry it replaces and does not expire or copy it**: one undated update leaves exactly two entries (C1's exact history check, and upstream's `test_field_history_tools.py:27-49`, `history_count == 2`, unedited).
- *Corrections keep and copy (ADR 0005, narrowed):* only when a later write changes an entry's **stored** end date or retracts a value, the entry gets `expired_at` = now and a corrected copy is appended with the original provenance, `operation: "interval_corrected"`, `replaces_entry_id`, `corrected_by_entry_id`. Copies count toward the 500-entry cap (a correction uses two entries).
- *End-dated values* stay current until their end.
- *Scoped overrides:* a write with `invalid_at` layers over the base value; when several values are valid at the asked time, the shorter validity wins; a plain statement ends every value whose validity contains its `valid_from`, overrides included (ending an override that has a stored end changes that stored end, so keep-and-copy applies).
- *No LLM conflict check:* values in the same field compete.
- *Queries:* default `/v1/query` returns the value valid now and not expired. Expired entries are hidden unless history is explicitly requested (`explain`, temporal stages, or a `valid_at` / `recorded_at` date); history reads show them with their `expired_at`. Optional `valid_at` (true on) and `recorded_at` (believed on) select the value at that time on either axis, count as history requests, and raise salience like any read. The patch returns `current` on every field, `null` when nothing is valid, on `/v1/query` and on `GET /api/ui/topics/{id}`. Hand-worked [INFERENCE]: in the as-of probe, "believed on Feb 10" returns April 20 with no expiry involved; the patch's developer tests must show it. The server's OpenAPI schema declares each date it accepts (`valid_from`, `invalid_at`; `valid_at`, `recorded_at`), which per-probe detection reads.
- *Chat:* optional `reference_time` on the chat request (default now), placed in the system prompt, used as default `valid_from` for `memory_append_field` (which also takes an optional model-filled `valid_from`), as the as-of time of that message's reads, and stored in provenance. Graphiti's future-tense rule is not adopted.

**Patch, step 3 (merge by valid time).** Interleave both histories by valid time; dropped-topic entries keep provenance and get `operation: "merged"`, `merged_from_topic_id`; entries whose validity changes are expired and copied; archived topics skipped; duplicate pairs recomputed after each merge; one "merged" event on the survivor. Dropped summary, topic events and salience stay lost (report limitation).

**Patch packaging** ("Patch packaging for the three-commit patch on LadybugDB"). Branch `bitemporal` in the git-ignored worktree `MemState-patched/` of the submodule, exactly three commits on `945d7c4`, exported with `git format-patch 945d7c4..bitemporal -o patches/` after every change. MemState's repo already uses this repo's `.githooks/`. Both engines live in the root venv. `run_memstate.sh --patched` sets `PYTHONPATH=$ROOT/MemState-patched/src`; default DB paths become `.runtime/memstate-kuzu-<ts>/memstate.kuzu` and `.runtime/memstate-ladybug-<ts>/memstate.lbug`; the script prints the loaded engine module and source folder. The runner resolves the steps with `git -C MemState-patched rev-list --reverse 945d7c4..bitemporal` (must be exactly three), checks each out detached, and returns to `bitemporal` when done. `MemState/` stays byte-for-byte unmodified; restore `src/memstate.egg-info` after any editable install.

**Database freshness.** Recorded mode: one fresh absolute DB per check per system; each time-probe story and each ramp gets its own DB; repetitions inside a check use distinct titles. `MemState/memstate.kuzu` is never opened.

**Runner.** Recorded mode: for upstream and each step, per check, start the server with the run script on a fresh DB, wait for `/health`, run, stop; run the in-process systems (reference GEM phase 1 and 2, baseline) with no server; write results; print the scorecard and the change tables. One server at a time. Live mode takes a URL, never starts or stops servers, uses one DB with distinct titles, labels output live. Replay mode renders recordings with no server. Ramp repeats are a flag (1 while building, 3 on the final commits if time allows; a ramp run once is labelled provisional). The reference GEM is not run on latency ramps or chat.

**Scorecard output.** Printed table plus a machine-readable results file: **one table in three groups** (MemState: upstream, step 1, step 2, step 3 | Reference: phase 1, phase 2 | Baseline: versioned row), each cell a verdict with its snapshot link (`pass (1 case n/a)` where cases were skipped), and the *claimed by [P1]?* column on every row; C5's cell text states the declared bound beside the active count; a separate section "probes of the proposed C1′ and C4′, outside [P1]'s claims" with the two cells per time probe (accepts dates; answers correctly given dates) and the C4′ probe; the change table in two chains (upstream → step 1 → step 2 → step 3; phase 1 → phase 2), changed cells marked and the case-level changes listed under each row; fail and absent counts; the merge result as existence with the natural random-ID count beside it, printed in `scorecard.md` as well as `results.json`; MemState's limits with their numbers (500-entry history cap, a correction uses two entries; C5's 500-topic soft limit against 2,000 active topics); the over-flagging measurement; the merge revision window and dependent-topic staleness window (seconds on MemState, interactions on the reference GEM); storyline triage (search failures, memory failures, correct) and reinforcement precision per system; latency tables for MemState's four systems (a table from fewer than three repeats is labelled provisional and never prints "no measurable difference"); deviations table; both chat cases. The summary says "no regressions on the rows the suite checks" only when the change table shows no row worse at step 3 than at step 1.

**Run of record.** The recorded command on the final commits writes `runs/results/<run-id>/` (git-ignored); a final step copies the scorecard, `results.json` and the snapshots to the tracked `runs/record/<run-id>/`; databases stay in `.runtime/` and `results.json` cites their absolute paths. The same command runs MemState's 39 upstream tests at upstream and, in `MemState-patched/`, at each step, and records the counts (passed, failed, total) per system in `results.json` and the scorecard. The report's snapshot links point into `runs/record/<run-id>/`.

**Chat runs.** MemState only; the reference GEM has no LLM chat. Ollama `qwen3.5:2b` (`MEMSTATE_OLLAMA_MODEL`, set by the run script) through the think-off proxy (ADR 0003), provider `ollama`, no `intent_override`, no Groq, no judge. Bad-merge run: upstream, state built through `/v1`, 2–3 storyline questions; each turn records question, ground truth, answer, route, latency, the state violation present, Sonnet's grade and a blind reviewer agent's grade (no hand grading; dropped by the user 2026-10-21). Two-weeks run: step 3, two separate requests with `reference_time` (shifted so Oct 20 is the run day), recording the stored start date and the answer, with two grade slots.

**Workload.** Storyline on the paper's Website Redesign example (deadline that changes, Alice, a vendor delay, dependent topics); checks take concrete values from it where they can, keeping §9.4's literal March 15 → April 20. Each question: ability label, ground-truth answer, answer topic. The user reviews the drafted content before the recorded run.

**Evaluation settings** ("Evaluation settings and deviations"). The versioned row and the reference GEM use MiniLM and top 8 (as MemState's default `top_k`), temperature 0.3 if generation is ever added. MemState internals stay as published and are listed as deviations, with the reference GEM's parameters and declared simplifications.

## Testing Decisions

- **One seam: the system adapter.** The suite's tests run each check in-process against the versioned row and the reference GEM and assert the verdicts "Expected verdicts" predicts for them, with the observations a reader relies on: the baseline's rejection of empty and `null` values, its salience reading none, the time probes' absent verdicts and the as-of probe's identical answers, the reference GEM's flag, rejection and archived overflow, a storyline search failure when the labelled topic is outside the top 8. The mutation tests run each check against its broken reference GEM. No server, GPU or network beyond the cached MiniLM model.
- **The story shift is tested** with a fixed run day: shifted dates keep the story's gaps, and "today" maps to the run day.
- **MemState verdicts are never pinned in tests.** Upstream and patch outcomes come only from recorded runs on fresh databases (evidence rule, ADR 0002). The versioned row and the reference GEM are our own code, so their verdicts are pinned.
- **No HTTP fixtures or mocks of MemState** ("How the conformance suite runs MemState"): the MemState adapter is proven by smoke runs against a real server.
- **Patch tests live in the patched copy**, beside upstream's 39, which pass unedited at every step: one developer test per step-2 rule (ordering, late older value, an ordinary update leaving exactly two entries, keep-and-copy only on a changed stored end or a retraction, expired entries hidden unless history is requested, end-dated value, override layering and lapse, plain statement ending an override, both as-of axes, "believed on" returning April 20 without expiry, `current: null` on `/v1/query` and the UI topic read, unparseable `valid_from`) and per step-3 rule (interleave, tags, archived skipped, three duplicates, `current` after the merge). They catch coding errors; the scorecard comes from the suite.
- **What makes a good test here:** it asserts a verdict or observation a scorecard reader would act on, through the adapter only; not snapshot layout, request forwarding, text formatting or defaults.
- **Prior art:** MemState's tests use pytest with an absolute temporary DB path (F6, F11); the suite's tests use pytest in the root venv in the same style.
- **Smoke proof before done:** a recorded run of all seven systems produces the scorecard, the change tables, triage, latency logs and snapshots; the run of record is copied to `runs/record/<run-id>/` with the 39-test counts; a live-mode run is watched in the Graph Explorer; replay renders both recordings with no server running.

## Out of Scope

- Any change to `MemState/` itself (ADR 0001); renaming `kuzu` identifiers or editing MemState's README in the patch.
- Patches beyond the three commits on real MemState: C3′ propagation and bounded flags, salience durability, decay, a policy language, extension-edge discovery, attributed salience (report §7.9). The reference GEM implements simplified flagging, policies and decay; MemState is not completed (ADR 0007).
- Mem0 or Zep columns, MAFBench runs, LongMemEval or a 500-turn workload, the cross-tenant leak check.
- Groq chat runs, Ollama repeats, a cloud-vs-local comparison, the three-rubric LLM judge.
- Pinned MemState verdicts in automated tests, recorded HTTP fixtures, a fake system clock.
- A public GitHub fork of the patch (may be added later; the patch files apply unchanged).
- The slides and rehearsal. (The report's §9 is revised with this spec; its §9.8 numbers are filled from the run of record.)
- Raising or lowering MemState thresholds such as the 500-topic gate (ADR 0001).

## Further Notes

- **Build plan:** two days with subagents, nothing cut ("Reinforcement precision and the engine latency ramps"). Critical path: step 2 (step 3 builds on it; per-step runs need all three). Parallel slices against the contracts above: (1) steps 1–2 and their developer tests; (2) step 3 after step 2's entry model lands; (3) adapter, verdict model, runner, scorecard; (4) condition checks and merge extras; (5) time probes and story shift; (6) storyline workload, triage and reinforcement precision; (7) latency ramps; (8) run-script changes, chat runs and replay; (9) the versioned-row baseline; (10) the stricter C3 and C2(c) checks and the C4′ probe, then the reference GEM (phase 1, phase 2), the over-flagging measurement and the mutation tests; (11) the run-of-record folder and the upstream-test runs. The stricter checks are written before the reference GEM. Runs are serial on the laptop; one server at a time, Ollama only for the chat runs, everything stopped when a run ends.
- Results that prove or disprove MemState behaviour go to `docs/findings.md` with command, DB path and key output; code-reading claims stay `[INFERENCE]` until a run backs them.
- `FieldWrite.value` is typed `Any`, so the `null` half of the C4 empty-write case may pass validation [INFERENCE]; the run decides.
- Upstream's chat request carries no date and its prompt contains none (`src/memstate/llm/chat_api.py:41-52`, from code), which is why the two-weeks case runs on step 3 only.
- "System adapter" is a term introduced by this spec; add it to `GLOSSARY.md` when the build settles it.
- Details left to the build: where step-3-only checks (the dated merge case, the as-of timing at 2,000 topics) sit in the scorecard (ticket 15). The reference GEM's parameters (decay clock reset on any read or write, revision after every ingest, the 0.06 C6 clause 2 seeds, one-hop flagging over extension edges in either direction) are decided in the parameter table and declared in the deviations table and the report.
- The reference GEM's "expected" column is a prediction made before the build. A result that departs from it is logged in `docs/journal.md` and reported; the expectation is not rewritten.
