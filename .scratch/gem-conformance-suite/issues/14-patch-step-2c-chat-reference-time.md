# 14: Patch step 2c: chat `reference_time`

**What to build:** A chat request that knows what day it is. An optional `reference_time` (default now) is placed in the system prompt. It is the default `valid_from` for `memory_append_field`, the as-of time of that message's reads, and it is stored in provenance. This is what lets the "two weeks ago" chat run (ticket 18) store a dated start. Graphiti's future-tense rule is not adopted. Spec: user story 49; Implementation Decisions "Patch, step 2" (chat); Further Notes (upstream's chat carries no date).

**Blocked by:** 13 (recorded-time reads)

**Status:** ready-for-agent

- [ ] The chat request accepts an optional `reference_time` that defaults to now and appears in the system prompt.
- [ ] `memory_append_field` takes an optional model-filled `valid_from` and defaults it to the request's `reference_time`. The message's reads run as of `reference_time`, and the time is stored in provenance.
- [ ] Developer tests exercise the tool path with a given `reference_time`, without an LLM: the default `valid_from`, the as-of read and the provenance. Upstream's 39 tests pass unedited.
- [ ] The work is amended into commit 2 and `patches/` is re-exported.
