<!-- Audit of branch gem-suite @ 467de6a (worktree /home/zeyad/work/agent-systems-demo-wt/integration), 2026-10-20, read-only scout. Offline tests run afterwards by the main session: `pytest -q` → 151 passed in 20.8 s. Finding ids F1–F21 here are audit ids, not docs/findings.md entries. -->

# GEM conformance suite on `gem-suite`: audit against spec.md and build tickets 01–19

**Tests were not run.** This session had only read, grep, glob and web-search tools, so I could not execute `pytest`. There are 15 test files in `tests/`, and per `tests/conftest.py` they need only the shared fastembed cache, so the main agent can run `/home/zeyad/work/agent-systems-demo/.venv/bin/python -m pytest -q` from the integration worktree.

Everything below comes from reading the code. Claims about how the unbuilt patch (tickets 12–15) will behave are marked [INFERENCE].

## 1. Findings

| id | severity | what | evidence | owner |
|---|---|---|---|---|
| F1 | **blocker** [INFERENCE] | C1 may flip to fail on step 2 without anything being wrong. C1 requires the explain history to be exactly `["April 20","March 15"]`. But the spec's keep-and-copy rule says any entry whose validity changes is expired and copied. Report §9.5 says an ordinary update closes the previous entry by setting its `invalid_at`, which is such a change. So one undated update could leave 3 entries: April 20, the expired March 15, and its copy. Ticket 12 also requires both "C1 still passes" and "undated writes behave as upstream", and does not say whether closing an open interval triggers a copy, or whether expired entries appear in `explain` history. | `demo/checks/c1_query_soundness.py:40`; spec "Patch, step 2" (ordering, corrections); ticket 12 boxes 3–5 and 9 | Ticket 12: decide both points, or loosen C1 to ignore expired entries |
| F2 | **blocker** | Step 3 cannot show the C4 merge fix in the change table, because the table compares whole-row verdicts only. On upstream C4 is **partial** because of the merge case *and* the empty/null-write and cap cases. Step 3 fixes only the merge case, so C4 stays partial and only C2(a) changes. Ticket 15 expects "the change table shows the merge rows changed", and report §9.5 says commit 3 "fixes the merge's history loss (C2, C4)" and "the merge tests flip". | `demo/reporting/changes.py:32-49`; `demo/checks/c4_history.py:148-158`; F21 (upstream partial on 3 non-merge cases) | Ticket 15: show case-level changes in the table, or reword §9.5 / ticket 15 |
| F3 | **blocker** (report claim) | With 1 repeat the code still prints "no measurable difference". It never checks the repeat count; with 5 query reads per ramp the rule fires, and F22 shows it printed one such note. The amended report line 670 says a single run is provisional and makes no such claim. | `demo/reporting/latency.py:58-76`; `docs/findings.md:200` | `latency_tables.py` (suppress below 3 repeats or label provisional); ticket 19 |
| F4 | gap | **Bad-merge chat run (story 52) is unspecified for the storyline.** The storyline forbids duplicate titles, so no merge ever happens on storyline topics. Ticket 17 only says "state built through `/v1` up to a bad merge" and does not say which topic is duplicated, how the dropped topic is chosen (retitle setup write vs. random-ID chance), or whether the violation is C2 or C4. This choice decides the story: with the F18 arrangement (dropped topic holds the newer value) the chat answer is *wrong* (March 15). An answer that "looks right" while state is violated needs the opposite arrangement: survivor holds April 20 and the history loses March 15 (a C4 violation). The questions must also target the merged topic. | `demo/workloads/storyline.py:35-36, 131-132`; `demo/workloads/merge.py:136-152`; F18; ticket 17 box 1 | Ticket 17 |
| F5 | gap | The merge violation rate per system and the random-ID counts are not shown in `scorecard.md` or the change table. They exist only in `results.json` measurements and the findings paste block. The `random_id_counts` measurement was dropped on purpose, yet ticket 03's box "counts from random-ID tests are shown but not compared" is still ticked. The spec's "Scorecard output" lists the violation rate, and no build ticket renders it (ticket 19 only lists it as output). | `demo/run.py:72-91, 170-178`; `notes/rf-journal-g2.md:19`; ticket 03 box 3 | Reopen 03 or add to 19; update spec story 13 |
| F6 | gap (hidden coupling) | The adapter expects the patch to put `current` on each field in `GET /api/ui/topics/{id}`. Otherwise it falls back to `history[0]`. C2(a), C4 and storyline triage read the current value this way. If step 3's interleaved history is stored oldest-first or by recorded time, `history[0]` is wrong and so are those verdicts. Ticket 12 requires `current: null` only on `/v1/query`. The dated merge case (story 37) has the same risk if it reads through `read_topic`. | `demo/systems/memstate.py:54-64`; `demo/workloads/merge.py:170-178`; `demo/checks/c4_history.py:69-70`; `demo/workloads/triage.py:137` | Tickets 12/15: require `current` in the UI topic, or newest-first by valid time |
| F7 | gap | T5 (as-of) is scored **absent** whenever the two answers are identical, even on a system that advertises `recorded_at`. A buggy step 2 would then read "absent" (meaning not implemented, per ADR 0002) instead of fail. F19 acknowledges this. | `demo/checks/time_probes.py:138-164` | Ticket 13: give absent only when `accepts_recorded_at` is false |
| F8 | gap (coupling) | Date support is detected from the patch's OpenAPI schema. It needs one schema with both `valid_from` and `invalid_at`, plus a `valid_at` property somewhere. If the patch takes dates through an untyped body, the time probes silently take the plain path and fail. The flags are recorded in measurements, so this would at least be visible. | `demo/systems/memstate.py:90-102`; `demo/checks/time_probes.py:61-66` | Ticket 12 (name the requirement) |
| F9 | gap | Step-3-only work (20 as-of reads at 2,000 topics; the dated merge case) has no hook. `Ctx` carries no system id, so these must be separate checks restricted with `systems=("step3",)`. By default such a check becomes a scorecard row, and spec story 8 lists no row for it. Ticket 15 says neither where the as-of timing goes nor whether the dated merge case is a row. | `demo/checks/__init__.py:42-57, 88-96` | Ticket 15 |
| F10 | gap | No ticket wires the chat cases into `scorecard.md` / `results.json`. Ticket 17 only saves recordings; ticket 19 expects "both chat cases" in the output. Also, ticket 19's "both chat runs … with the approved storyline" does not fit the two-weeks run, which is not a storyline run. | spec "Scorecard output"; tickets 17, 19 | Ticket 17 or 19 |
| F11 | drift | The latency table's "Reasoner wait" was replaced by "settle time (poll floor 0.1 s), no Reasoner claim". Spec story 41 and ticket 08 (box ticked) still say "Reasoner wait", and report §9.2 says "the background Reasoner timed separately". The only real Reasoner timing left is the C2(a) merge window. | `demo/reporting/latency.py:3-4, 87`; `demo/checks/c5_topic_ramp.py:73-74`; `notes/rf-report-g4.md:3` | Spec 41 / report §9.2 |
| F12 | drift | Ramp ×3: ticket 19 requires 3 repeats; amended report line 670 says "time permitting". The integration worktree's copy of the report still has the old line 670. | ticket 19 box 1; `docs/report/...:670` in both checkouts | Ticket 19; sync the report |
| F13 | drift | C2(a) now forces the dropped topic to hold the newer value via a labelled setup `PATCH title` (it is in the deviations table), so the outcome is deterministic: 20/20 (F18). Report §9.2 still justifies ×20 by "which copy survives depends on ID order", and §9.5 says counts "may differ between runs". Spec story 13's 10/20 vs 8/20 framing is obsolete. | `demo/workloads/merge.py:136-152`; `demo/reporting/deviations.py:37-40`; report:670 | Report §9.2/§9.5; spec 13 |
| F14 | drift | C2(b) "success with the edge reported applied" scores **not-scored** with a soundness observation; upstream lands there (F17). The verdict model says not-scored is only for "neither outcome". Story 21 does not say what this outcome should score, so the scorecard shows not-scored for what is arguably a C2 soundness failure. | `demo/checks/c2b_atomicity.py:1-10`; F17 | Spec / report §9.4 decision |
| F15 | drift | Claim column (story 9) is incomplete. C2(a), C4, C5-1/2 and C6-1/2 do not state [P1]'s claim ("by construction" / "under transitions"); C1, C2(b), C2(c), C3 and T* do. | `demo/checks/c2a_merge.py:33`; `c4_history.py:21`; `c5_topic_ramp.py:24-29`; `c6_retrieval_adaptation.py:41-44` | No ticket; trivial fix |
| F16 | drift | Report §9.4 has no C2(c) row and does not mention C4's history-cap case, which contributes to upstream's partial. §9.8's row list does not mention the C2 split into (a)/(b)/(c). | report:681-688, 736 | Report §9.4/§9.8 |
| F17 | note | `from_cases` gives not-scored whenever every case is n/a (not only for C2(b)), and `error` is a verdict outside the scale. Both are journaled; the spec text is unchanged. | `demo/verdict.py:55-65`; `notes/rf-journal-g1.md:22` | Spec owner |
| F18 | note | Case-level controls (C4 update path, each time probe's control date) appear only in `results.json` and in the over-blocking observation, not in the printed scorecard or findings block. | `demo/reporting/scorecard.py:84-93`; `demo/run.py:155-164` | Story 12 / ticket 19 |
| F19 | note | The history-cap case is 1 `new_topic` + 500 `version_field` (501 writes, 500 updates); the spec and ticket say "501 updates". | `demo/checks/c4_history.py:23` | Spec wording |
| F20 | note | Module layout differs from the spec: `merge_extras` and `latency` live outside `checks/`, `client` is split into `adapter.py` + `memstate_system.py`, and `chat_run` / `runs/recordings/` do not exist yet (ticket 17). | `demo/` tree | — |
| F21 | note | `history_intact` needs an `expired_at` key on every entry (null allowed) and entry `id`s. Upstream entries already have `id` (`MemState/src/memstate/datamodel/fields.py:38`). | `demo/workloads/time_stories.py:163-190` | Ticket 12 |

### Spot-check of resolved tickets (code vs. ticked boxes)
- **01**: matches.
  - Adapter: `adapter.py:96-160`. MemState adapter: `memstate_system.py`. Baseline (upserts, accepts `""`/`null`, MiniLM top 10): `baseline.py:21-89`.
  - Verdict model; fresh absolute DB per check: `server.py:111-115`.
  - Evidence: `evidence.py`. Deviations table: `deviations.py`. README; glossary entry at `GLOSSARY.md:155`.
- **02**: README `--patched` documented (`README.md:73-76`). Only `patches/0001-port-to-ladybugdb.patch` exists, as expected at this stage. I could not check the commit contents without git.
- **03**: one box is unmet: "counts shown" (F5). Everything else matches (`steps.py`, `systems.py:93-140`, `changes.py`).
- **04, 05, 06, 07, 09, 10, 16**: boxes match the code. Small departures in 06 (F19) and 07: reinforcement precision is in its own table "beside C6 clause 1" (`storyline_tables.py:98-104`), which is acceptable.
- **08**: the "Reasoner wait" box is no longer true (F11).

### Do open tickets 12–15 and 17–19 cover everything unbuilt?
- **Covered:**
  - Dated merge case: ticket 15 (but F6, F9).
  - Step 3 as-of read timing: ticket 15 (F9).
  - Exactly-three-commits check: ticket 15.
  - Replay mode and README replay: ticket 17.
  - Patches 0002/0003: tickets 12/15.
  - Developer tests: tickets 12–15.
  - Two-weeks run: ticket 18.
  - Run of record: ticket 19.
- **Need no ticket:**
  - The change table for steps 2–3 fills itself; it is generic over the chain (`changes.py:20-21`).
  - The deviations table is already built.
- **Not covered:** F4, F5, F10, F15.

## 2. Per-story coverage (57 stories)

| status | count | stories |
|---|---|---|
| Implemented | 36 | 2–6, 8, 10, 11, 14–19, 22–24, 26–35, 38–40, 44–46, 48, 55, 57 |
| Implemented with deviation | 9 | 9 (F15), 12 (F18), 13 (F5/F13), 20 (setup-write arrangement, F13), 21 (F14), 25 (F19), 36 (F7), 41 (F11), 43 (F3/F12) |
| Pending in an open ticket | 12 | 1 (19), 7 (17), 37 (15), 42 (15), 47 (12/15; 0001 done), 49 (12–14), 50 (15), 51 (12–15; step 1 done), 52 (17, underspecified: F4), 53 (18), 54 (17/18), 56 (replay part: 17) |
| Missing with no ticket | 0 | (at story level; F5 and F10 are output gaps with no ticket) |

### Implementation Decisions

| Decision | Status |
|---|---|
| System adapter | Implemented, with extra `probe` and `list_topic_ids`; F6/F8 coupling |
| Verdict model | Implemented with deviations (F17, F14) |
| Runner | Recorded and live implemented; replay pending (17); ramp-repeat flag implemented |
| Scorecard output | Implemented except merge violation rate per system (F5) and chat cases (F10) |
| Workload | Implemented; user review pending (ticket 11) |
| Time-probe stories / scoring | Implemented (`time_stories.py`, `checks/time_probes.py`); F7 |
| Reads used by checks | Implemented (`reads.py:8-10`; storyline uses default stages, `top_k` 8) |
| Database freshness | Implemented |
| Patch packaging | Step 1 implemented; rest pending (12, 15) |
| Chat runs | Pending (17, 18); F4 |

## 3. What the POC proves now vs. what is still pending

**Proven by recorded smoke runs (not yet the run of record):**
- F13: C1 passes on upstream and the baseline.
- F17: C2(b) not-scored; C2(c) absent; C3 absent with an unbounded window.
- F18: C2(a) fails 20/20 when the dropped topic holds the newer value; the dropped topic is deleted.
- F21: C4 partial — merge loss, empty and null writes become current, the cap drops the oldest entry.
- F22: C5-1 passes; C5-2 fails (nothing archived through 2,000 topics).
- F15: C6 shows over-reinforcement and that salience is not durable.
- F19: upstream fails T1–T4 and T6 and is absent on T5.
- F20: storyline 15/15, reinforcement precision 0.125 = Precision@8.
- F16, F22: step 1 gives the same verdicts as upstream.
- Live mode works (F14).

**Still pending:**
- Everything about the patch: steps 2–3; the dated and `recorded_at` code paths have never run.
- Step 2/3 rows in the change table, with the F1 and F2 risks.
- The dated merge case and the step 3 as-of timing.
- Both chat runs and replay.
- Ramps ×3; the current latency gap is provisional.
- Approval of the storyline (ticket 11).
- The run of record (ticket 19).

**Checks for the main agent:** run `pytest -q` in the integration worktree, and decide F1, F2, F4 and F7 before tickets 12, 15 and 17 start.