# 15: Patch step 3: merge by valid time

**What to build:** Commit 3, in which the Reasoner's merge interleaves both topics' histories by valid time instead of dropping the duplicate's values. The merge rows flip on step 3, and the dated merge case shows it with dates. The latency output gains as-of read timing at 2,000 topics, and the runner insists on exactly three commits. Spec: user stories 37, 42, 50, 51; Implementation Decisions "Patch, step 3", "Patch packaging".

**Blocked by:** 06 (C4, with its merge case), 08 (topic ramp), 13 (recorded-time reads)

**Status:** ready-for-agent

- [ ] Commit 3 ("merge by valid time") sits on `bitemporal` above commits 1–2. `patches/0003-merge-by-valid-time.patch` is exported, and the three files rebuild `MemState-patched/`.
- [ ] The merge interleaves both histories by valid time. The dropped topic's entries keep their provenance and get `operation: "merged"` and `merged_from_topic_id`. Entries whose validity changes are expired and copied. Archived topics are skipped. Duplicate pairs are recomputed after each merge, and the survivor gets one "merged" event. The dropped summary, topic events and salience stay lost (report limitation).
- [ ] Developer tests cover the interleave, the tags, archived topics being skipped, and three duplicates. Upstream's 39 tests pass unedited.
- [ ] The suite's dated merge case runs on step 3: topic A holds "April 20 since Jan 5"; duplicate B, written later, holds "March 15 since Dec 1". After the merge, today reads April 20, both values are in the history, and B's entry carries `merged_from_topic_id`.
- [ ] Step 3 also times 20 as-of reads at 2,000 topics, reported in the latency output.
- [ ] The runner fails unless `945d7c4..bitemporal` contains exactly three commits.
- [ ] Recorded run on step 3: the change table shows the merge rows changed from step 2, and the time probes still pass.
