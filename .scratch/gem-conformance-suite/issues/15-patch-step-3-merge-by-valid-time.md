# 15: Patch step 3: merge by valid time

**What to build:** Commit 3, in which the Reasoner's merge interleaves both topics' histories by valid time instead of dropping the duplicate's values. The merge case flips on step 3, and the dated merge case shows it with dates. The change table shows it at case level: C4 stays `partial` on step 3, but its case "merge keeps history" goes from broken to fixed (ticket 23). The latency output gains as-of read timing at 2,000 topics, and the runner insists on exactly three commits. Spec: user stories 13, 37, 42, 50, 51, 78; Implementation Decisions "Patch, step 3", "Patch packaging", "Expected verdicts".

**Blocked by:** 06 (C4, with its merge case), 08 (topic ramp), 13 (recorded-time reads), 22 (revised C4 cases), 23 (case-level change table)

**Status:** resolved

- [x] Commit 3 ("merge by valid time") sits on `bitemporal` above commits 1–2. `patches/0003-merge-by-valid-time.patch` is exported, and the three files rebuild `MemState-patched/`.
- [x] The merge interleaves both histories by valid time. The dropped topic's entries keep their provenance and get `operation: "merged"` and `merged_from_topic_id`. Entries whose stored end changes are expired and copied (ordinary entries are not). Archived topics are skipped. Duplicate pairs are recomputed after each merge, and the survivor gets one "merged" event. The dropped summary, topic events and salience stay lost (report limitation).
- [x] After a merge, `current` is recomputed on every field of the survivor (on `/v1/query` and the UI topic read), so the adapter never needs a newest-entry fallback.
- [x] Developer tests cover the interleave, the tags, archived topics being skipped, three duplicates and `current` after the merge. Upstream's 39 tests pass unedited.
- [x] The suite's dated merge case runs on step 3: topic A holds "April 20 since Jan 5"; duplicate B, written later, holds "March 15 since Dec 1". After the merge, today reads April 20, both values are in the history, and B's entry carries `merged_from_topic_id`.
- [x] Step 3 also times 20 as-of reads at 2,000 topics, reported in the latency output. Where this check and the dated merge case sit in the scorecard (a step-3-only row or a note) is decided and declared here.
- [x] The runner fails unless `945d7c4..bitemporal` contains exactly three commits.
- [x] Recorded run on step 3: the change table shows C2(a) changed from step 2 (fail → pass) and C4's case "merge keeps history" changed (broken → fixed) while the C4 row stays `partial`; the time probes still pass.


## Comments

2026-10-21: Built. Patch commit 3 is `5c5c9e6` on `bitemporal` (on top of ticket 14's amended commit 2, `5f45848`); `patches/0003-merge-by-valid-time.patch` exported; rebuilding the three patches on `945d7c4` gave a tree identical to `bitemporal`. The private worktree `MemState-step3` is removed.
- Patch: `datamodel/fields.py` (`merge_histories`), `store/graph_store.py` (`merge_topics` interleaves, tags a moved field's entries; `find_duplicate_titles` skips archived topics and orders by id), `core/executor.py` (`run_revise_duplicates` rescans after each merge and appends one `merged` event to the survivor). 9 developer tests in `tests/test_merge_by_valid_time.py`; 82 passed with upstream's 39 unedited.
- Suite: C4 gains the dated merge case (id `merge-dated`: A "April 20 since Jan 5", B written later "March 15 since Dec 1"; n/a where no `valid_from` is accepted; the `merged_from_topic_id` tag is reported in the observation and `measurements.dated_merge`, not scored, since it is the patch's own key); the C5-2 ramp at the largest n times 20 as-of reads for systems accepting `valid_at` (`as_of_samples_ms`, own table in the latency output); `PatchRepo.step_commit` refuses every step unless `945d7c4..bitemporal` holds exactly three commits (`demo.systems.registry.default_systems` removed: a run without `--systems` measures every registered system).
- Smoke and change table: F29. Step 3 vs step 2: C2(a) fail → pass; C4 merge and dated merge broken → fixed; T1-T6 pass.
- Departures: the as-of timing runs on every system accepting `valid_at` (steps 2 and 3), not step 3 only, so the two can be compared. The spec's "archived topics skipped" also changes the merge extra "active topic merged into an archived duplicate": the merge no longer happens on step 3 (F29).
- Later tickets: 18/19/32 read the step 3 rows from a recorded run on the final commits (ramps were run once here: provisional). Patch commit hashes: step 1 `089b823`, step 2 `5f45848`, step 3 `5c5c9e6`; F26/F27 still cite older step 2 hashes. A step-3 commit needs `git -c core.hooksPath=<gem-suite .githooks>` until the main checkout's hook is updated (journal).
