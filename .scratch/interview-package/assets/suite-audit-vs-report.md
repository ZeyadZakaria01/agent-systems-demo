<!-- Audit of branch gem-suite @ 1ba8d31 against docs/report/gem-limitations-and-directions.md on main, 2026-10-20, read-only scout. Finding ids A1–A19 are audit ids. -->

# GEM conformance suite vs report §1, §5.3, §5.7 and §9: audit

I could not run pytest because this session has no shell tool. Every claim below comes from reading files. Claims about the code that no run reproduced are marked [INFERENCE].

## Summary

- **Check content (Q1):** the checks mostly match §9.4 and §9.6. Same scenarios, same values (March 15 → April 20; Oct 15 = $80, Nov 5 = $50; $100 stated Oct 10, current Nov 5; patch answers $80 for Oct 5; asked Nov 20; Feb 10 on both axes).
- **Mismatches that matter (Q1):**
  - C2(a) is no longer a random-ID measure. The dropped topic is arranged to hold the newer value, so the rate is 20/20 by construction.
  - The C4 row also scores a 500-entry history cap that the report never mentions.
  - Story 2 of the lapsed-override probe never asks a date between Oct 10 and Nov 1, so the rule "a plain statement ends overrides" is never tested.
  - The per-step change table compares verdicts only, so C4's merge fix on commit 3 will not show.
- **Baseline (Q2):** every recorded and tested baseline verdict matches §9.3. Two points need wording:
  - C1 passes on one case only: "pass (1 case n/a)".
  - C2(a) passes only because the row upserts, so no duplicate ever exists.
  - The suite also shows C2(c) absent on **upstream**, so "no policies `P_t`" does not separate MemState from the row.
- **Report text (Q3):** §9.7 (merge, latency, C5), the §9.4 C2/C5/C6 interpretations and §4.2 line 121 are superseded or made more precise by F15, F17, F18, F21 and F22.
- **POC coverage (Q4):** the time probes cover ordering, overrides, null-current, the default C1′ read and both as-of axes. Unmeasured by any suite check: equal-`valid_from` ties, `corrected_by_entry_id`, the `operation` tags, as-of reads raising salience, the survivor's single merge event, and the 39 tests at every commit as recorded evidence.
- **Hidden design conflict (Q4):** does closing an open entry trigger keep-and-copy? It decides whether T5, C1's exact history check and upstream's `history_count == 2` test can all pass. Neither the report nor ticket 12 says.

## Findings

| id | sev | what | evidence | owner |
|---|---|---|---|---|
| A1 | blocker | Per-step change table is verdict-level only. C4 on upstream is partial: merge, `""`, `null` and cap cases fail. Step 3 fixes only the merge case, so C4 stays partial and the table shows "no change". The §9.5 line 704 promise "(3) … the merge tests flip" and §9.8's "rows whose verdict changed" cannot show the C4 fix [INFERENCE from case lists] | `demo/changes.py:28-45`; `demo/verdict.py:52-63`; `demo/checks/c4_history.py:166-183`; F21 | ticket 15/19: case-level diff or split C4 rows; report §9.5 l.704 |
| A2 | blocker (risk) | §9.5 rules l.695-696: closing an entry sets its `invalid_at`, and "an entry whose validity changes" is kept and copied. If ordinary closes are copied, three things collide [INFERENCE]: <br>• C1's exact check `values == ["April 20","March 15"]` sees 3 entries; <br>• upstream `test_memory_get_field_returns_value_and_history` asserts `history_count == 2` on two dated writes; <br>• T5 "believed on Feb 10" needs the pre-close entry. <br>Copying everywhere breaks the first two; editing in place breaks T5. It is solvable only if default history views hide expired entries, which nobody specifies | `demo/checks/c1_query_soundness.py:37-40`; `MemState/tests/test_field_history_tools.py:31-49`; report l.695-696; ticket 12 | ticket 12; report §9.5 l.696 |
| A3 | gap | The adapter takes the stored current value from `history[0]` unless the server states `current`. The patch orders history by valid time, so C2(a), C4 and merge-extras rely on the patch adding `current` to `/api/ui/topics/{id}`. No ticket requires it | `demo/memstate_system.py:54-64`; tickets 12, 15 | ticket 12 |
| A4 | gap | The "plain statement ends overrides" rule is unmeasured. Story 2 asks only Nov 5 (the $80 override has lapsed on Nov 1 anyway) and Oct 5 (before $100). A patch that never ends the override still passes. Needs e.g. Oct 15 → $100 | `demo/time_stories.py:94-98`; report l.699, l.717 | ticket 12 + time_stories; report l.717 |
| A5 | drift | C2(a) arranges the dropped topic to hold the newer value: editor `PATCH title`, older value on the lower id. The rate is 20/20 by construction, not a random-ID estimate. Stale text: report l.670 "×20 with random topic IDs, since which copy survives depends on ID order"; l.684; l.704 "counts … may differ between runs"; spec story 13 | `demo/merge.py:179-195`; `demo/checks/c2a_merge.py:1-20`; `demo/deviations.py:37-40`; F18 | report §9.2/9.4/9.5; spec story 13 |
| A6 | drift | The C4 row scores a 501-write cap case (`v000` dropped → fail). §9.4 l.686 lists only update/merge/archive/empty/null. The patch's "copies count toward the cap" keeps this case failing on every step | `c4_history.py:148-163`; F21; ticket 12 | report §9.4 l.686 |
| A7 | drift | C4 "survives archiving" uses an editor `PATCH archived=true`, not the forgetting transition C4 names. Spec story 16 and ticket 19 say "no verdict rests on a setup write". Real forgetting is exercised only on field-less topics (C5-1, C6-2), so provenance under forgetting is never checked | `c4_history.py:110-122`; F21; ticket 19 checkbox 3 | ticket 19; report §9.4 l.686 |
| A8 | drift | `latency_tables` prints "no measurable difference" at 1 repeat, using the spread of the 5 reads within one run as its range. It labels nothing "provisional". Amended l.670 says a single run makes no such claim. Ticket 19 still says 3× | `demo/latency_tables.py:3-7,18-20,60-71`; F22 (note printed at n = 2,000) | ticket 19; latency_tables |
| A9 | drift | §9.2 l.673 says "the background Reasoner timed separately". The ramp's settle time is a poll floor, not the Reasoner. The only Reasoner timings are the merge window (0.083 s median) and the C3 wait | F22; `latency_tables.py:3-4`; F18 | report §9.2 l.673 |
| A10 | drift | §9.2 l.668 says "every trap probe has a paired control". C2(a) has none (survivor-holds-newer runs are now "not a case"), and neither do C3 and C2(b). Time-probe controls are dates where the recency answer is right by definition, so they only bite on the patch | `c2a_merge.py:_case`; `time_stories.py` `Ask.control` | report §9.2 l.668 |
| A11 | drift | §9.4 C2(b) says "invalid edge **or field reference**", but only the edge is built (spec story 21). The interpretation "A fail contradicts a stated claim" cannot apply: upstream is not-scored. The scale at l.667 omits `not-scored` | `demo/checks/c2b_atomicity.py:28,43`; F17 | report §9.2 l.667, §9.4 l.684 |
| A12 | drift | The scorecard has a C2(c) row (spec story 8) that §9.4 does not list. Upstream is C2(c) **absent** (F17), so §9.3's "has no policies `P_t`" does not distinguish MemState from the baseline | F17; spec.md:37 | report §9.3 l.677, §9.4 |
| A13 | gap | `demo/results/` is git-ignored (user decision, `notes/rf-report-g1.md:7`). §9.2 l.666 and §9.8 l.736 promise snapshot links, which will dangle in the committed report. Ticket 19 does not say where the run of record is stored | `.gitignore:8-9`; `scorecard.py:69`; `notes/review-reports-final.md:15-18` | ticket 19 |
| A14 | gap | "39 upstream tests pass unedited at every commit" (l.704; §1 item 6) has no run-of-record step. Step 1's 39/39 is in the journal (`journal.md:127`), not in findings. F11 used the scratch port, not commit `089b823` | ticket 19 checkboxes; findings F11/F16 | ticket 19 |
| A15 | note | Report l.719 says upstream and baseline answer every date with "the same plain read". T5 actually sends `valid_at` and `recorded_at` to every system to observe that they are ignored. A buggy `recorded_at` on the patch also scores absent | `time_stories.py:10-11`; `time_probes.py:138-164`; F19 | report l.719/721 |
| A16 | note | The T1 patch write invents a start for March 1 (Dec 1 of the previous year) and adds a "Dec 20" control. The report names neither | `time_stories.py:62-70` | report l.710 |
| A17 | note | Not re-recorded after review changes: <br>• C3 now waits 15 s from the update (F17 waited 5 s); <br>• C6-1 still comes from run 102353; <br>• F13 predates the refactor. <br>All need ticket 19 | F17 last para; F15 | ticket 19 |
| A18 | note | Ticket 11 (storyline review) is `ready-for-human` and blocks 19. The storyline gave 0 search and 0 memory failures on upstream, and the baseline also got 15/15. So triage (l.672) has no worked example, and the answer level cannot separate MemState from the database row | F20; ticket 11 | report §9.2 l.672, §9.3 |
| A19 | note | Report l.717 "asked on Nov 5 must return $50" sits in a sentence about controls that "every column" passes. Nov 5 is the trap that upstream fails ($80). The extra control (story 2, Nov 5 → $100) and the patch-only Oct 5 → $80 match the code | `time_stories.py:87-98`; F19 | report l.717 |

## Baseline vs §9.3 (Q2)

| Row | §9.3 / spec expected | Observed (finding) / asserted (test) |
|---|---|---|
| C1 | pass | **pass (1 case n/a)**: the history case is `held=None`, so pass rests on the default read alone (F13; test_c1.py:15) |
| C2(a) value | pass | pass, 0/20, no duplicate ever created, so the pass is vacuous (F18; test_c2a.py:108) |
| C2(b) | (not in §9.3) | not-scored (F17; test_c2b_c2c_c3.py:38) |
| C2(c) | absent ("no `P_t`") | absent, and **upstream is absent too** (F17) |
| C3 | absent | absent (F17; test l.54) |
| C4 | fail | **fail (1 case n/a)**: archiving n/a (F21; test_c4.py:40-43) |
| C5-1 / C5-2 | absent | absent / absent (F22; test_c5.py:45) |
| C6-1 / C6-2 | fail | fail / fail (F15; test_c6.py:26,35) |
| T1–T4, T6 / T5 | (not in §9.3; spec: fail / absent) | fail / absent (F19; test_time_probes.py:157-160) |

All match. §9.3 should add C2(b), C2(c) and the time-probe expectations, state the two n/a cells, and note that C2(a) passes by upsert.

## Report statements to update (Q3)

| Line | Current text (abridged) | Finding | Suggested wording |
|---|---|---|---|
| 731 (§9.7 Merge) | "stale value became current in 10 of 20 runs (8 of 20 on LadybugDB)" | F18 | "On random IDs the stale value was current in 10/20 (F9). When the dropped topic holds the newer value, it was current in 20/20; the dropped topic is deleted (404) and the window is 0.083 s median. An active topic merged into an archived duplicate disappears from `/v1` reads." |
| 684 (§9.4 C2) | "(b) atomic commit … invalid edge or field reference"; "A fail contradicts a stated claim" | F17 | "(b) not scorable on upstream: the ingest succeeds and reports `edge:<id>` applied, but no edge is stored (soundness issue)." Drop "field reference" or build it. |
| 677 (§9.3) | "has no policies `P_t`" | F17 | "Neither MemState's API nor the row exposes a policy surface (C2(c) absent on both). MemState's `P_t` is six internal numeric knobs." |
| 686 (§9.4 C4) | update/merge/archiving + empty/null | F21 | Add the 500-entry cap case (oldest dropped) and the fact that empty and `null` writes are accepted and become current. Archiving is by an editor write, not by forgetting. |
| 212 (§5.7), 32 (§1 item 5) | "C1 returns the most recent non-archived value as current" | F21 | "… the most recent value, even an empty string or `null` (recorded run)." |
| 121 (§4.2 table) | "superseded values are marked with provenance, not deleted" | F18, F21 | Add: "in the prototype, merge deletes the dropped topic and its values, and the history keeps only the newest 500 entries." |
| 552 (§7.5 non-destructive failure) | practitioner note only | F21 | Cite the recorded run: MemState accepts `""` and `null` writes as current. |
| 687 (§9.4 C5 interp.) | "If nothing ever decays, the transition never runs" | F22, F15 | "The forgetting pass runs at the 500-topic gate and archives a topic below 0.05 (C5-1 pass, salience 0.01 → 0.005). With no decay, nothing falls below 0.05 naturally: 0 archived through 2,000 topics (C5-2 fail)." |
| 729 (§9.7 C5) | nothing archived at 2,000 | F22 | Add the mechanism pass and that step 1 is identical. |
| 688 (§9.4 C6) | "A field write resetting salience …" | F15 | Make it precise: "one field write set a reinforced 0.13 to 1.0. Salience is overwritten, not accumulated (cause [INFERENCE])." Clause 2 also needs a forgetting pass that archives a 0.01 control. |
| 673 (§9.2), 531 (§7.4) | "at most 1/8"; "bumps every returned candidate" | F20 | "Measured 0.125 = 1/8 (the ceiling): the labelled topic was bumped on 15/15 questions, and 7/8 of the increments went to other topics." |
| 732 (§9.7 Engines) | "145 → 382 ms (Kuzu), 81 → 340 ms (LadybugDB)" | F22 | Replace with the run of record. Current provisional single run, 5 reads per ramp: 143 → 389 ms (Kuzu) and 79 → 329 ms (LadybugDB), labelled provisional with no "no measurable difference" claim. |
| 730 (§9.7 C6) | over-reinforcement | F15 | Add: 3 of 3 unrelated topics rose exactly as far as the target (1.0 → 1.3). |
| 164 (§5.3), 728 | B stays stale | F17 | Add: "reproduced by the suite; B unchanged after a 5 s polled wait in both edge directions; window unbounded within the wait." |
| 37 (§1 item 10), 677 | "necessary but not sufficient" | F20 | Add: at answer level on `/v1`, the row also answered 15/15; the difference is visible only in stored state (C4, C5, C6). |
| 717/721 (§9.6) | expected upstream column | F19 | Mark "confirmed (F19)": all six upstream verdicts as expected, `valid_at` and `recorded_at` ignored, every control date right. |
| 727 | "The conformance suite will rerun them with full snapshots" | F13–F22 | Snapshots exist but are git-ignored (A13). |
| 670 | "×20 with random topic IDs" | F18 | See A5. |

## POC coverage of §9.5 rules (Q4)

"Suite" means a scorecard check. "Ticket" means patch acceptance or developer tests (not scorecard evidence).

| Rule (§9.5 line) | Measured by | Status |
|---|---|---|
| Four timestamps per entry (692) | `history_intact` checks only that the `expired_at` key exists (`time_stories.py:162-188`); `invalid_at`/`created_at` only in ticket 12 | partial |
| Undated writes = upstream (692) | step 1 → 2 verdict equality on C1, C2–C6 and the storyline (tickets 12/19) | measured (pending) |
| Placement by `valid_from`; closes the containing entry (695) | T1, T3 | measured (pending) |
| Late older value ends where the later begins (695) | T2 | measured (pending) |
| Equal `valid_from` → later recorded wins (695) | none (not even listed in ticket 12's developer tests) | **unmeasured** |
| Keep and copy: `expired_at` + copy + `replaces_entry_id` (696) | `history_intact` on T1–T6; T5's recorded axis [INFERENCE] | measured (pending); see A2 |
| `operation:"interval_corrected"`, `corrected_by_entry_id`, original provenance on the copy (696) | not checked by `history_intact` | **unmeasured** |
| End-dated value current until it ends (697) | T4 story 1, Oct 15 via `valid_at` only; no default "today" read inside an end-dated interval | partial |
| No LLM judge (698) | by construction on `/v1`; no check | unmeasured (design property) |
| Override layers over the base; shorter validity wins (699) | T4 story 1 (Oct 15 → $80, Nov 5 → $50); story 2 Oct 5 → $80 | measured (pending) |
| Plain statement ends overrides (699) | not distinguished (A4) | **unmeasured** |
| C1′ default read: valid now, history on request (700) | C1 default case; "today" reads T1–T4, T6 | measured |
| As-of on both axes (700) | T5 (ticket 13) | measured (pending) |
| As-of raises salience (C6) (700) | ticket 12/13 text only; no suite check | **unmeasured** |
| Field returned with no current value (`current: null`) (700) | T6 | measured (pending) |
| `reference_time`: prompt, default `valid_from`, as-of time, provenance (701) | ticket 14 developer tests; ticket 18 chat, n = 1, hand-graded | ticket only, not on the scorecard |
| Future-tense rule not adopted (701) | T3/T6 on `/v1`; chat path untested | partial |
| Merge interleaves by valid time; dropped entries keep provenance (702) | C2(a), C4 merge case (`_holds_both` checks provenance), dated merge case (ticket 15, not built) | partial (pending) |
| `operation:"merged"`, `merged_from_topic_id` (702) | dated merge case checks `merged_from_topic_id` only (ticket 15) | partial |
| Merge-time expire-and-copy (702) | no `history_intact` on merges | **unmeasured** |
| Archived topics skipped (702) | `active_into_archived` extra: an observation, not a verdict | observation only |
| Pairs recomputed after each merge (702) | `three_same_title` extra: an observation | observation only |
| Survivor records one merge event (702) | nothing reads topic events | **unmeasured** |
| 39 upstream tests unedited at every commit (704) | ticket 12–15 checkboxes; not in the ticket 19 run of record (A14) | ticket only |

## Things §9 promises that the suite drops or cannot produce (Q5)

- **Snapshot links (l.666, l.736):** the files are saved but git-ignored (A13).
- **"Background Reasoner timed separately" (l.673):** the ramp only measures a settle time (A9).
- **"Every trap probe has a paired control" (l.668):** false for C2(a), C2(b) and C3 (A10).
- **C2(b) "field reference" (l.684):** not built (A11).
- **"Merge tests flip" for C4 in the per-commit table (l.704, l.736):** not visible at row level (A1).
- **Random-ID merge counts that "may differ" (l.704):** moot after the arrangement (A5).
- **×3 ramps:** report says "time permitting", ticket 19 says 3×, and the code applies the no-difference rule at 1 repeat (A8).
- **Provenance under the forgetting transition (C4's own wording):** only editor archiving is tested (A7).

## What the POC proves vs. what is pending

**Proven by recorded runs on fresh DBs, upstream `945d7c4` on Kuzu 0.11.3 (smoke runs, not the run of record):**
- C1 passes (F13).
- C2(a) fails: 20/20 when the dropped topic holds the newer value (F18).
- C2(b) not scorable, with a soundness issue: the edge is reported applied but not stored (F17).
- C2(c) absent (F17).
- C3 absent; window unbounded within a 5 s wait (F17).
- C4 partial: merge loss, `""`/`null` writes become current, and the history keeps only the newest 500 entries (F21).
- C5-1 passes and C5-2 fails (F22).
- C6-1 and C6-2 pass, with over-reinforcement and the 1.0 reset (F15).
- Reinforcement precision is 0.125 (F20).
- All six time probes match the "upstream expected" column (F19).
- The baseline matches §9.3 (F13–F22).
- Step 1 (LadybugDB) gives the same C1, C5-1 and C5-2 verdicts as upstream (F16, F22).
- LadybugDB vs Kuzu latency: one provisional run (F22).

**Pending:**
- Every patch column for steps 2 and 3, i.e. the whole C1′ contribution (tickets 12–15).
- The dated merge case and the 20 as-of reads at 2,000 topics (ticket 15).
- Both chat runs and replay (tickets 17, 18).
- Storyline approval (ticket 11).
- The run of record, snapshot storage, ×3 ramps and 39 tests per commit (ticket 19).
- Re-recording C3 (15 s wait) and C6-1.
- Fixes for A1–A4 before the patch can be scored as the report describes.