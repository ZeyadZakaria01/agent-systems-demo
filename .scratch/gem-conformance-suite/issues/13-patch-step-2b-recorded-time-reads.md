# 13: Patch step 2b: recorded-time reads

**What to build:** The second axis of the as-of query. With `recorded_at`, `/v1/query` answers what memory believed at a past moment, using the expired entries that keep-and-copy preserved. The as-of probe flips from absent to pass on step 2. Spec: user stories 35, 36, 49; Implementation Decisions "Patch, step 2" (queries), "Time-probe scoring".

**Blocked by:** 12 (dated field histories)

**Status:** ready-for-agent

- [ ] `recorded_at` selects the value memory held at that time, counting entries that have since expired. It combines with `valid_at`, counts as a history request and raises salience like any read.
- [ ] Developer tests cover `recorded_at` on its own and combined with `valid_at`. Upstream's 39 tests pass unedited.
- [ ] The work is amended into commit 2 and `patches/` is re-exported. The branch still has its commits in order.
- [ ] Recorded run on step 2: the as-of probe passes ("true on Feb 10" → May 1, "believed on Feb 10" → April 20), and the probes from ticket 12 still pass.
