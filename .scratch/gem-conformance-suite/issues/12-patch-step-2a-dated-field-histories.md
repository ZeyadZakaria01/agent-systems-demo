# 12: Patch step 2a: dated field histories and valid-time reads

**What to build:** The first part of commit 2 ("bitemporal field histories"). Field-history entries carry Zep's timestamps. Writes take optional `valid_from` / `invalid_at` and are ordered by valid time. Corrections keep and copy (ADR 0005). End-dated values and scoped overrides behave as the spec states. The default read returns the value valid now, and `valid_at` asks what was true on another date. With this, five of the six time probes flip on step 2 while C1 keeps passing. Recorded-time reads are ticket 13; chat is ticket 14. Spec: user stories 49, 51; Implementation Decisions "Patch, step 2" (entry model, writes, ordering, corrections, end-dated values, scoped overrides, no LLM conflict check, queries).

**Blocked by:** 03 (per-step runs), 09 (time probes)

**Status:** ready-for-agent

- [ ] The work lands as commit 2 on `bitemporal` with commit 1 untouched, and `patches/` is re-exported.
- [ ] Each history entry gains `invalid_at`, `created_at` and `expired_at` beside `valid_from`, plus `operation`, `replaces_entry_id` and `corrected_by_entry_id` where they apply.
- [ ] Undated writes behave as upstream: `valid_from` = `created_at` = write time, with no end. A `valid_from` that does not parse as a date keeps arrival order.
- [ ] A new entry is placed by `valid_from` and closes the entry whose validity contains it. A late-arriving older value ends where the later one begins. With equal `valid_from`, the later recorded entry wins.
- [ ] Keep and copy: an entry whose validity changes gets `expired_at` = now, and a corrected copy is appended with the original provenance, `operation: "interval_corrected"`, `replaces_entry_id` and `corrected_by_entry_id`. Copies count toward the 500-entry cap.
- [ ] End-dated values stay current until their end. A write with `invalid_at` layers over the base value, and when several values are valid the shorter validity wins. A plain statement ends every value whose validity contains its `valid_from`, overrides included. Values in the same field compete with no LLM conflict check.
- [ ] The default `/v1/query` returns the value valid now and not expired, with the history only on request. `valid_at` selects the value true at that time, counts as a history request and raises salience like any read. When no value is valid, the field is listed with `current: null`.
- [ ] Developer tests inside the patched copy cover ordering, the late older value, keep and copy, the end-dated value, override layering and lapse, a plain statement ending an override, `valid_at`, `current: null` and the unparseable `valid_from`. Upstream's 39 tests pass unedited.
- [ ] Recorded run on step 2: the retroactive, out-of-order, future-dated, lapsed-override (both stories) and future-value probes pass with history intact, and C1 still passes. The change table shows those flips against step 1.
