# 15: Patch step 3: merge by valid time

**What to build:** Commit 3, in which the Reasoner's merge interleaves both topics' histories by valid time instead of dropping the duplicate's values. The merge case flips on step 3, and the dated merge case shows it with dates. The change table shows it at case level: C4 stays `partial` on step 3, but its case "merge keeps history" goes from broken to fixed (ticket 23). The latency output gains as-of read timing at 2,000 topics, and the runner insists on exactly three commits. Spec: user stories 13, 37, 42, 50, 51, 78; Implementation Decisions "Patch, step 3", "Patch packaging", "Expected verdicts".

**Blocked by:** 06 (C4, with its merge case), 08 (topic ramp), 13 (recorded-time reads), 22 (revised C4 cases), 23 (case-level change table)

**Status:** ready-for-agent

- [ ] Commit 3 ("merge by valid time") sits on `bitemporal` above commits 1–2. `patches/0003-merge-by-valid-time.patch` is exported, and the three files rebuild `MemState-patched/`.
- [ ] The merge interleaves both histories by valid time. The dropped topic's entries keep their provenance and get `operation: "merged"` and `merged_from_topic_id`. Entries whose stored end changes are expired and copied (ordinary entries are not). Archived topics are skipped. Duplicate pairs are recomputed after each merge, and the survivor gets one "merged" event. The dropped summary, topic events and salience stay lost (report limitation).
- [ ] After a merge, `current` is recomputed on every field of the survivor (on `/v1/query` and the UI topic read), so the adapter never needs a newest-entry fallback.
- [ ] Developer tests cover the interleave, the tags, archived topics being skipped, three duplicates and `current` after the merge. Upstream's 39 tests pass unedited.
- [ ] The suite's dated merge case runs on step 3: topic A holds "April 20 since Jan 5"; duplicate B, written later, holds "March 15 since Dec 1". After the merge, today reads April 20, both values are in the history, and B's entry carries `merged_from_topic_id`.
- [ ] Step 3 also times 20 as-of reads at 2,000 topics, reported in the latency output. Where this check and the dated merge case sit in the scorecard (a step-3-only row or a note) is decided and declared here.
- [ ] The runner fails unless `945d7c4..bitemporal` contains exactly three commits.
- [ ] Recorded run on step 3: the change table shows C2(a) changed from step 2 (fail → pass) and C4's case "merge keeps history" changed (broken → fixed) while the C4 row stays `partial`; the time probes still pass.
