# Spec: GEM conformance suite and the bitemporal patch

Status: ready-for-agent

Source of the design: report §9 (`docs/report/gem-limitations-and-directions.md`) and the resolved tickets on the wayfinder map (`.scratch/interview-package/map.md`), in particular "Bitemporal history model and API", "Time probes and their controls", "Patch packaging for the three-commit patch on LadybugDB" and "Reinforcement precision and the engine latency ramps". Terms follow `GLOSSARY.md`. ADRs: 0001 (MemState measured unmodified over HTTP), 0002 (`absent` for unimplemented capabilities), 0003 (thinking off via proxy), 0004 (Kuzu pinned at 0.11.3 for upstream), 0005 (corrections keep and copy), 0006 (patch on LadybugDB, upstream on Kuzu).

## Problem Statement

The GEM paper defines memory correctness as a property of the trajectory (C1–C6) but reports no measurements, and MemState's 39 tests cover only C1 and the append path of C4. In front of the paper's author, the user must show which conditions MemState meets as published, which it gets wrong, and which it does not implement, each backed by a recorded run on a fresh database; what MemState adds over a plain database row; and a contribution of their own, measured before and after: Zep's bitemporal time model added to MemState's field histories (C1′), on LadybugDB. Recorded probes exist (findings F7–F12, `scripts/probe_memstate.py`); no suite or patch code exists. The interview demo and report §9.7–§9.8 depend on it.

## Solution

A **GEM conformance suite**: state-level checks that drive a memory system only through GEM operators (`/v1/ingest`, `/v1/query`), read back what it stores (current values, field histories with timestamps and provenance, salience, archived flags, edges) and give each scorecard row a verdict: pass, partial, fail or absent. It runs on five systems:

- **upstream**: MemState at `945d7c4` on Kuzu 0.11.3, unmodified, over HTTP;
- **step 1, step 2, step 3**: the three commits of the patched copy on LadybugDB 0.21.2: (1) port, (2) bitemporal field histories and C1′ queries, (3) merge by valid time;
- **baseline**: a last-write-wins row keyed by (title, field).

The scorecard's columns are **[P1]'s claim | upstream (Kuzu) | bitemporal patch (step 3, LadybugDB) | baseline**. A second table lists, per step, the rows whose verdict changed (step 1: none, compared verdict for verdict; step 2: the time probes; step 3: the merge rows). Step 1 → step 2 holds the engine constant and isolates the effect of Zep's model.

Beside the verdicts the suite records: the merge violation rate (×20), the merge revision window and dependent-topic staleness window, search-vs-memory triage of the storyline questions, reinforcement precision for C6, and latency ramps on upstream and each step. Two recorded Ollama chat runs (n=1 each, hand-graded, replayable): the bad-merge contrast on upstream, and the "two weeks ago" case on step 3. A live mode drives a running server so the Graph Explorer shows histories and salience changing during the interview.

## User Stories

**Running**

1. As the presenter, I want one command that runs the suite on all five systems and prints the scorecard and the per-step change table, so that the evidence of record needs no manual steps.
2. As the presenter, I want each check run against a server started on a fresh absolute database, so that every verdict meets the evidence rule.
3. As the presenter, I want the runner to stop each server when its check finishes, so that the laptop never holds two servers or a stale database lock.
4. As the presenter, I want the runner to select step 1, 2 or 3 by checking out that commit in `MemState-patched/` before starting the server, so that every step is measured from the same branch without copies.
5. As the presenter, I want a live mode that drives an already running server, so that Prof. Mansour can watch field histories and salience change in the Graph Explorer.
6. As the presenter, I want live-mode verdicts labelled live and kept apart from recorded results, so that the scorecard of record comes only from fresh-database runs.
7. As the presenter, I want a replay mode that renders both chat recordings with no server or GPU, so that interview day does not depend on the laptop's GPU.

**Scorecard**

8. As the presenter, I want rows for C1, C2(a) superseded value, C2(b) atomicity, C2(c) declarative policies, C3, C4, C5 mechanism, C5 natural trajectory, C6 clause 1, C6 clause 2, and the six time probes, so that each clause is scored against its exact wording.
9. As the presenter, I want the claim column to state [P1]'s claim per row (§4 and §4.3: C1, C2, C4 by construction; C3 claimed by §4's opening but not listed in §4.3; C5, C6 under transitions; time probes under C1, read as C1′), so that each verdict is read against the paper's own claim.
10. As the presenter, I want each cell to show a verdict and link to its raw-state snapshot, so that any verdict can be audited live.
11. As the presenter, I want fails and absences counted separately, so that missing capabilities read as open research rather than defects (ADR 0002).
12. As the presenter, I want the controls (C1, the update path of C4, and each time probe's control date) marked as controls, so that the suite shows it can detect a pass and catches over-blocking.
13. As the presenter, I want the per-step change table to compare step 1 with upstream verdict for verdict, with counts from random-ID tests shown but not compared, so that chance variation (stale value current 10/20 vs 8/20, F9/F11) is not read as an engine effect.
14. As the presenter, I want the C6 rows to quote the clause wording and show reinforcement precision beside clause 1 without a verdict, so that the gap between C6's wording and its motivation is visible without grading the author on a rule he did not write.

**Evidence**

15. As a reviewer, I want every verdict to save its requests and responses, the full state it read (every topic including archived ones, plus edges), timestamps, the DB path, the system label, the MemState commit and the engine line printed by the run script, so that it can be reproduced and cited in `docs/findings.md`.
16. As a reviewer, I want every setup write labelled and kept apart from scored transitions, so that no verdict rests on an editor-endpoint edit.
17. As a reviewer, I want every `absent` verdict to carry the probe run that confirmed the absence, so that no absence is asserted from reading code.
18. As the author of `docs/findings.md`, I want each recorded run to print the command, DB path and key output in pasteable form, so that new findings meet the evidence rule.

**Condition checks** (report §9.4)

19. As a reviewer, I want C1 to store `Deadline: March 15`, update it to `April 20` through `/v1/ingest version_field`, and confirm a default query returns only April 20 and a temporal query the full history.
20. As a reviewer, I want C2(a) to create two same-title topics where the one to be dropped holds the newer value, trigger the Reasoner's merge, and check which value is current, repeated 20 times with random topic IDs and distinct titles, reporting the violation rate.
21. As a reviewer, I want C2(b) to send one `/v1/ingest new_topic` with valid fields and an edge to a non-existent topic, and classify the outcome: an error with the topic or fields persisted is a partial commit (fail); success with the edge reported applied is a soundness issue and is reported; neither means atomicity is not testable with this input (not scored).
22. As a reviewer, I want C2(c) declarative policies probed and scored absent when the system exposes only numeric knobs.
23. As a reviewer, I want C3 to link B → A with an extension edge (and a second pair A → B), update A, and read B before and after revision, so that propagation is probed as in F7.
24. As a reviewer, I want C4 to verify that a field history survives a value update, a merge and archiving with provenance intact, and that `version_field` with `""` and separately with `null` does not replace April 20 (rejection with April 20 current holds; an empty current value breaks the case).
25. As a reviewer, I want C4 to include a history-cap case: 501 updates to one field, then check whether the first value is still in the history, so that the 500-entry cap (`TopicFields.cap_history`, `graph_store.py` `max_history=500`; drops the oldest [INFERENCE]) is decided by a run.
26. As a reviewer, I want the C5 mechanism verdict to ramp past the 500-topic trigger with a field-less topic ingested at `salience=0.01` and check whether it is archived (`partial` if only the count gate fires), and the natural-trajectory verdict to count archived topics at each ramp step with no setup.
27. As a reviewer, I want C6 clause 1 to confirm each retrieval raises the salience of the topics it returns and record whether unrelated candidates rise too, and clause 2 to query a field-less topic at 0.03 until it passes 0.05 and score whether it left forgetting eligibility; a field write resetting salience is recorded as a durability observation.
28. As a reviewer, I want the merge extras (three topics sharing one title; an active topic merged into an archived duplicate; whether upstream deletes the dropped topic) run and recorded, so that MemState's "not what is permanently erased" promise is cited only after a run.
29. As a reviewer, I want background effects awaited by polling state with a timeout, each wait logged apart from client latency, so that asynchronous revision is not misread as absent.
30. As a reviewer, I want the merge revision window (duplicate-creating ingest → merge visible, median and range over the 20 repetitions) and the dependent-topic window ("unbounded (C3 absent)", citing the C3 run) reported.

**Time probes** (report §9.6; "Time probes and their controls")

31. As a reviewer, I want each time probe told as a dated story and asked on its story "today" plus at least one other date, one of which is the control, using the stories in Implementation Decisions, so that a wrong answer and a rejected legitimate update are both caught.
32. As a reviewer, I want each story shifted so its "today" falls on the run day, the "today" question asked as a plain read with no date, and the other dates asked as as-of reads, so that the default path is exercised against the real server clock.
33. As a reviewer, I want upstream and the baseline to receive the same writes in the same order with no dates and to answer every asked date with the same plain read, so that the comparison isolates the time model.
34. As a reviewer, I want each story on its own topic and fresh database per system, apart from the storyline, so that a failure is attributable to the time logic.
35. As a reviewer, I want the as-of probe's "believed on Feb 10" asked at a real moment between the two writes (note the time after the first write, wait 1 s, send the second), since recorded time is the real clock.
36. As a reviewer, I want a probe to pass only when every asked date is right and, on the patch, the history is intact (no value lost; shortened entries expired with copies linked by `replaces_entry_id`, ADR 0005); any wrong date fails, labelled over-blocking when the control date fails; a system with no as-of read is scored absent on the as-of probe after sending `valid_at` and observing the same answer to both questions.
37. As a reviewer, I want one dated merge case on step 3 (topic A "April 20 since Jan 5"; duplicate B written later, "March 15 since Dec 1"; after the merge, today → April 20, both values in history, B's entry tagged `merged_from_topic_id`), so that merge by valid time is tested with dates.

**Storyline, triage and reinforcement precision**

38. As the presenter, I want one storyline of 20–30 events and 10–15 questions on the paper's Website Redesign example, each event a `/v1` placement with the expected state after it, each question labelled with a LongMemEval ability, a ground-truth answer and the topic that holds the answer, so that the checks, triage and chat runs share one scenario.
39. As a reviewer, I want every wrong storyline answer sorted with StateMemBench's first triage question: labelled topic not returned by `/v1/query` → search failure; returned but stored value wrong → memory failure, so that bad search is not mistaken for bad memory.
40. As a reviewer, I want reinforcement precision (salience increments to the labelled topic ÷ all increments over the storyline questions) and the number of questions whose labelled topic was bumped at all, with a note that it equals Precision@k because every returned topic is bumped.

**Latency**

41. As a reviewer, I want latency ramps at 100 / 250 / 500 / 1,000 / 2,000 topics on upstream and each step, with identical undated writes and plain reads, logging per step the client latency of `/v1/query` and `/v1/ingest`, the Reasoner wait and the archived count, so that upstream → step 1 shows the engine, step 1 → 2 Zep's model and step 2 → 3 the merge change on ordinary writes.
42. As a reviewer, I want step 3 to also time 20 as-of reads at 2,000 topics.
43. As a reviewer, I want each ramp run once while building and three times on the final commits, reporting median and range and calling a difference inside the range "no measurable difference".

**Baseline**

44. As a reviewer, I want the baseline put through the same checks, time probes and storyline, with its query using MiniLM and top-k 10 (survey settings), so that the scorecard shows what MemState adds over a database row.
45. As a reviewer, I want the scorecard to include the deviations table (MemState's intent router as shipped, Ollama model defaults, the think-off proxy, the baseline's survey settings), so that every departure from a standard setup is declared.

**Patch** (report §9.5; ADRs 0005, 0006)

46. As the presenter, I want `scripts/run_memstate.sh --patched` to start the patched copy, default DB folders named per engine, and the engine and source folder printed at startup, so that a database is never opened by the wrong engine unnoticed.
47. As anyone reproducing the work, I want the three commits exported as `patches/0001-port-to-ladybugdb.patch`, `0002-bitemporal-field-histories.patch`, `0003-merge-by-valid-time.patch`, which rebuild `MemState-patched/` from the pinned submodule with the README's two commands.
48. As a reviewer of the patch, I want step 1 to change only the `kuzu_adapter.py` import and the `pyproject.toml` dependency, so that "the engine swap changes nothing" is checkable at a glance.
49. As a reviewer of the patch, I want step 2 to implement the entry model, writes, ordering, keep-and-copy corrections, end-dated values, scoped overrides, C1′ queries and the chat reference time as specified below, so that the time probes flip without breaking C1.
50. As a reviewer of the patch, I want step 3 to merge by valid time as specified below, so that the merge rows flip.
51. As a reviewer of the patch, I want MemState's 39 tests to pass unedited at every step, and developer tests for each rule added inside the patched copy, so that the patch breaks nothing the authors tested.

**Chat runs**

52. As the presenter, I want one recorded Ollama chat run on upstream after a bad merge, asking 2–3 storyline questions with no intent override, logging each turn's route, so that an answer can be shown looking right while state violates C2 or C4.
53. As the presenter, I want one recorded "two weeks ago" chat run on step 3: two separate requests, `reference_time` Oct 6 "I started my new job two weeks ago" and `reference_time` Oct 20 "how long have I been there?", graded on the stored start date (Sep 22 ± 1 day) and the answer (four weeks).
54. As the grader, I want each recorded turn to carry the ground truth and an empty hand-grade slot, so that the n=1 cases are graded transparently.

**Maintenance**

55. As a maintainer, I want the suite's own tests to run in-process against the baseline without any server, and every check written against one system adapter, so that tests are fast and adding a system means one adapter.
56. As a newcomer, I want the README to explain how to run the suite (recorded, live, replay) and `--patched`, and to drop "no demo code exists", so that the repo describes itself accurately.
57. As the presenter, I want every unexpected difficulty during the build or runs logged in `docs/journal.md`, so that the report can cite the build's lessons.

## Implementation Decisions

**Modules** (layout from "Demo folder layout"). A `demo` package:

- **client**: the system adapter interface and its MemState HTTP implementation (upstream and patched differ only in which server runs; the adapter detects the patch's extra fields and ignores none of them).
- **baseline**: the last-write-wins adapter.
- **workload**: the storyline (events, questions, ground truth, ability and answer-topic labels), the time-probe stories, and the ramp topic generator.
- **checks**: one module per condition, plus `time_probes`, `merge_extras`, `triage` (search vs. memory and reinforcement precision) and `latency`.
- **chat_run**: records and replays both Ollama runs.
- **run**: the runner, the scorecard and the per-step change table.

Outputs: `demo/recordings/` (chat runs) and `demo/results/` (verdicts, snapshots, latency logs, one directory per run).

**System adapter: the single seam.**

- `ingest(request) -> response`: a scored transition, same shape as `/v1/ingest` (placements `new_topic` / `extend_topic` / `version_field`; fields with value, provenance, why-changed and, on the patch, optional `valid_from` / `invalid_at`; edges with kind; salience).
- `query(request) -> response`: a scored transition, same shape as `/v1/query` (`q`, `stages`, `explain`, `top_k`, `topic_ids`, `field_names`; on the patch, optional `valid_at` and `recorded_at`). Systems without as-of reads receive the dates and ignore them; checks detect this from the answers.
- `read_state()` / `read_topic(id)`: every topic including archived ones (title, current value per field or none, field history with all timestamps, provenance and operation tags, salience, archived flag, topic history) and edges. MemState: `GET /api/ui/topics`, `GET /api/ui/topics/{id}`, `GET /api/ui/graph`. A missing topic reads as "deleted".
- `setup_write(...)`: forced topic ID, salience, archived flag through editor endpoints, recorded and labelled.
- `wait_until(predicate, timeout) -> elapsed`.
- `describe()`: system label, server URL, DB path, MemState commit, engine line.

Missing capabilities (no salience, no edges, no as-of) are explicit nothing-values, never errors; `absent` is decided only from a probe's observed outcome.

**Reads used by checks.** A deterministic read of one topic is `/v1/query` with `stages=["temporal"]`, `topic_ids=[id]`; `explain=true` when the history is needed. With the semantic stage, `topic_ids` only filters the kNN result, and structural without temporal drops fields with no current value (`executor.py:239-240, 252-265, 297-299`, from code). Every read adds +0.1 salience to each returned topic (`executor.py:328-339`), so salience checks account for the suite's own reads. Storyline questions use the default stages and `top_k` 8 (upstream and patch).

**Baseline.** Row keyed by (title, field), last write wins; accepts the ingest shape and writes whatever arrives, `""` and `null` included; a second `new_topic` with an existing title upserts; no history, salience, archived flag, edges or dates; query embeds with MiniLM and returns the top 10 (a read changes nothing). Expected verdicts (report §9.3): C1 pass; C2(a) value pass, violation 0/20; C2(b) not scored; C2(c) absent; C3 absent; C4 fail; C5 both absent; C6 both fail, reinforcement precision not applicable; time probes fail, as-of probe absent.

**Verdict model.** Fields: row ID, system, verdict (pass / partial / fail / absent / not-scored), cases (held or not, observation), observations that are not verdicts (over-reinforcement, salience not durable, topic deleted on merge, route log, over-blocking), probe evidence for `absent`, snapshot reference, control flag. Scale (ticket "Verdict scale and unimplemented conditions", ADR 0002): pass = every case held; partial = some held; fail = implemented and every case broke; absent = probe confirmed missing; not-scored only for the C2(b) "neither outcome" rule. Time probes use pass / fail / absent only (Scoring below).

**Time-probe stories.** Story dates are shown in the report; the suite shifts each story so "today" is the run day (e.g. a run on Oct 20 stores the budget story's Nov 5 as Oct 20 and Sep 1 as Aug 16). Patch writes carry the shifted `valid_from` / `invalid_at`; upstream and baseline writes carry none.

| Row | Writes, in order | Asked → correct (upstream expected) |
|---|---|---|
| Retroactive fact | Jan 5 "deadline April 20"; Feb 15 "it was March 1 before it moved on Jan 5" | today Feb 15 → April 20 (March 1 ✗); Dec 20 → March 1 (March 1) |
| Out-of-order arrival | "pro since Oct 1" arrives first; "basic since Aug 1" arrives after | today Oct 20 → pro (basic ✗); Sep 1 → basic (basic) |
| Future-dated change | Jun 1 "basic"; Nov 20 "premium from December" | today Nov 20 → basic (premium ✗); Dec 5 → premium (premium) |
| Lapsed scoped override, story 1 | Sep 1 "$50"; Oct 1 "$80 for October only" | Oct 15 → $80 ($80); today Nov 5 → $50 ($80 ✗) |
| Lapsed scoped override, story 2 (plain statement during override) | as story 1, plus Oct 10 "now $100" | today Nov 5 → $100 ($100); Oct 5 → $80 ($100 ✗) |
| Future value, nothing before | Nov 20 "premium from December", only value | today Nov 20 → no current value (premium ✗); Dec 5 → premium (premium) |
| As-of query | Jan 5 "deadline April 20"; Feb 15 "moved to May 1 on Feb 1" | true on Feb 10 (`valid_at`) → May 1; believed on Feb 10 (`recorded_at`, a real moment between the writes) → April 20 (upstream: absent) |

The control is the date every system should get right (the one where upstream's expected answer is correct). The lapsed-override row passes only if both its stories pass.

**Time-probe scoring.** Pass: every asked date right, and on the patch the history intact (no value lost; shortened entries carry `expired_at` with a copy linked by `replaces_entry_id`). Fail: any date wrong; the observation "over-blocking" when the control date is wrong. Absent: the as-of probe on a system that returns the same answer to both questions after receiving `valid_at` / `recorded_at`.

**Patch, step 1 (port).** `import kuzu` → `import ladybug as kuzu` in `src/memstate/store/kuzu_adapter.py`; `pyproject.toml` `kuzu>=0.11.0` → `ladybug==0.21.2`. No renames; MemState's README untouched.

**Patch, step 2 (bitemporal field histories).** From "Bitemporal history model and API":

- *Entry model:* each history entry in `Topic.fields_json` gains `invalid_at`, `created_at`, `expired_at` beside the existing `valid_from`, plus `operation`, `replaces_entry_id`, `corrected_by_entry_id` where they apply.
- *Writes:* `FieldWrite` takes optional `valid_from` and `invalid_at`. Without dates, `valid_from` = `created_at` = write time and no end, so undated writes behave as upstream. A `valid_from` that does not parse as a date keeps arrival order (upstream's `test_topic_fields.py` uses `"t0"`…`"t4"`).
- *Ordering:* a new entry is placed by `valid_from`; it closes the entry whose validity contains its `valid_from`; a late-arriving older value ends where the later one begins; equal `valid_from` → later recorded wins.
- *Corrections keep and copy (ADR 0005):* an entry whose validity changes gets `expired_at` = now and a corrected copy is appended with the original provenance, `operation: "interval_corrected"`, `replaces_entry_id`, `corrected_by_entry_id`. Copies count toward the 500-entry cap.
- *End-dated values* stay current until their end.
- *Scoped overrides:* a write with `invalid_at` layers over the base value; when several values are valid at the asked time, the shorter validity wins; a plain statement ends every value whose validity contains its `valid_from`, overrides included.
- *No LLM conflict check:* values in the same field compete.
- *Queries:* default `/v1/query` returns the value valid now and not expired; history only on request. Optional `valid_at` (true on) and `recorded_at` (believed on) select the value at that time on either axis, count as history requests, and raise salience like any read. No value valid → the field is listed with `current: null`.
- *Chat:* optional `reference_time` on the chat request (default now), placed in the system prompt, used as default `valid_from` for `memory_append_field` (which also takes an optional model-filled `valid_from`), as the as-of time of that message's reads, and stored in provenance. Graphiti's future-tense rule is not adopted.

**Patch, step 3 (merge by valid time).** Interleave both histories by valid time; dropped-topic entries keep provenance and get `operation: "merged"`, `merged_from_topic_id`; entries whose validity changes are expired and copied; archived topics skipped; duplicate pairs recomputed after each merge; one "merged" event on the survivor. Dropped summary, topic events and salience stay lost (report limitation).

**Patch packaging** ("Patch packaging for the three-commit patch on LadybugDB"). Branch `bitemporal` in the git-ignored worktree `MemState-patched/` of the submodule, exactly three commits on `945d7c4`, exported with `git format-patch 945d7c4..bitemporal -o patches/` after every change. MemState's repo already uses this repo's `.githooks/`. Both engines live in the root venv. `run_memstate.sh --patched` sets `PYTHONPATH=$ROOT/MemState-patched/src`; default DB paths become `.runtime/memstate-kuzu-<ts>/memstate.kuzu` and `.runtime/memstate-ladybug-<ts>/memstate.lbug`; the script prints the loaded engine module and source folder. The runner resolves the steps with `git -C MemState-patched rev-list --reverse 945d7c4..bitemporal` (must be exactly three), checks each out detached, and returns to `bitemporal` when done. `MemState/` stays byte-for-byte unmodified; restore `src/memstate.egg-info` after any editable install.

**Database freshness.** Recorded mode: one fresh absolute DB per check per system; each time-probe story and each ramp gets its own DB; repetitions inside a check use distinct titles. `MemState/memstate.kuzu` is never opened.

**Runner.** Recorded mode: for upstream and each step, per check, start the server with the run script on a fresh DB, wait for `/health`, run, stop; run the baseline in-process; write results; print the scorecard and per-step table. One server at a time. Live mode takes a URL, never starts or stops servers, uses one DB with distinct titles, labels output live. Replay mode renders recordings with no server. Ramp repeats are a flag (1 while building, 3 for the final run).

**Scorecard output.** Printed table plus a machine-readable results file: rows × the four columns (verdict + snapshot link); the per-step change table (upstream, step 1, step 2, step 3 verdicts per row, changed cells marked); fail and absent counts; merge violation rate per system; staleness windows; storyline triage (search failures, memory failures, correct) and reinforcement precision per system; latency tables; deviations table; both chat cases.

**Chat runs.** Ollama `qwen3.5:2b` (`MEMSTATE_OLLAMA_MODEL`, set by the run script) through the think-off proxy (ADR 0003), provider `ollama`, no `intent_override`, no Groq, no judge. Bad-merge run: upstream, state built through `/v1`, 2–3 storyline questions; each turn records question, ground truth, answer, route, latency, the state violation present, and a hand-grade slot. Two-weeks run: step 3, two separate requests with `reference_time` (shifted so Oct 20 is the run day), recording the stored start date and the answer, with two grade slots.

**Workload.** Storyline on the paper's Website Redesign example (deadline that changes, Alice, a vendor delay, dependent topics); checks take concrete values from it where they can, keeping §9.4's literal March 15 → April 20. Each question: ability label, ground-truth answer, answer topic. The user reviews the drafted content before the recorded run.

**Evaluation settings** ("Evaluation settings and deviations"). The baseline uses MiniLM, top-k 10, temperature 0.3 if generation is ever added. MemState internals stay as published and are listed as deviations.

## Testing Decisions

- **One seam: the system adapter.** The suite's tests run each check in-process against the baseline and assert the verdicts §9.3 predicts (listed under Baseline), with the observations a reader relies on: C4's lost earlier value and the empty value becoming current, C6's unchanged salience, the time probes' wrong date, the as-of probe's identical answers, a storyline search failure when the labelled topic is outside the top 10. No server, GPU or network beyond the cached MiniLM model.
- **The story shift is tested** with a fixed run day: shifted dates keep the story's gaps, and "today" maps to the run day.
- **MemState verdicts are never pinned in tests.** Upstream and patch outcomes come only from recorded runs on fresh databases (evidence rule, ADR 0002).
- **No HTTP fixtures or mocks of MemState** ("How the conformance suite runs MemState"): the MemState adapter is proven by smoke runs against a real server.
- **Patch tests live in the patched copy**, beside upstream's 39, which pass unedited at every step: one developer test per step-2 rule (ordering, late older value, keep-and-copy, end-dated value, override layering and lapse, plain statement ending an override, both as-of axes, `current: null`, unparseable `valid_from`) and per step-3 rule (interleave, tags, archived skipped, three duplicates). They catch coding errors; the scorecard comes from the suite.
- **What makes a good test here:** it asserts a verdict or observation a scorecard reader would act on, through the adapter only; not snapshot layout, request forwarding, text formatting or defaults.
- **Prior art:** MemState's tests use pytest with an absolute temporary DB path (F6, F11); the suite's tests use pytest in the root venv in the same style.
- **Smoke proof before done:** a recorded run of all five systems produces the scorecard, per-step table, triage, latency logs and snapshots; a live-mode run is watched in the Graph Explorer; replay renders both recordings with no server running.

## Out of Scope

- Any change to `MemState/` itself (ADR 0001); renaming `kuzu` identifiers or editing MemState's README in the patch.
- Patches beyond the three commits: C3′ propagation and bounded flags, salience durability, decay, a policy language, extension-edge discovery, attributed salience (report §7.9).
- Mem0 or Zep columns, MAFBench runs, LongMemEval or a 500-turn workload, the cross-tenant leak check.
- Groq chat runs, Ollama repeats, a cloud-vs-local comparison, the three-rubric LLM judge.
- Pinned MemState verdicts in automated tests, recorded HTTP fixtures, a fake system clock.
- A public GitHub fork of the patch (may be added later; the patch files apply unchanged).
- Filling report §9.7–§9.8, the slides and rehearsal; they consume the scorecard.
- Raising or lowering MemState thresholds such as the 500-topic gate (ADR 0001).

## Further Notes

- **Build plan:** two days with subagents, nothing cut ("Reinforcement precision and the engine latency ramps"). Critical path: step 2 (step 3 builds on it; per-step runs need all three). Parallel slices against the contracts above: (1) steps 1–2 and their developer tests; (2) step 3 after step 2's entry model lands; (3) client, baseline, verdict model, runner, scorecard; (4) condition checks and merge extras; (5) time probes and story shift; (6) storyline workload, triage and reinforcement precision; (7) latency ramps; (8) run-script changes, chat runs and replay. Runs are serial on the laptop; one server at a time, Ollama only for the chat runs, everything stopped when a run ends.
- Results that prove or disprove MemState behaviour go to `docs/findings.md` with command, DB path and key output; code-reading claims stay `[INFERENCE]` until a run backs them.
- `FieldWrite.value` is typed `Any`, so the `null` half of the C4 empty-write case may pass validation [INFERENCE]; the run decides.
- Upstream's chat request carries no date and its prompt contains none (`src/memstate/llm/chat_api.py:41-52`, from code), which is why the two-weeks case runs on step 3 only.
- "System adapter" is a term introduced by this spec; add it to `GLOSSARY.md` when the build settles it.
