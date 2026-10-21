# 14: Patch step 2c: chat `reference_time`

**What to build:** A chat request that knows what day it is. An optional `reference_time` (default now) is placed in the system prompt. It is the default `valid_from` for `memory_append_field`, the as-of time of that message's reads, and it is stored in provenance. This is what lets the "two weeks ago" chat run (ticket 18) store a dated start. Graphiti's future-tense rule is not adopted. Spec: user story 49; Implementation Decisions "Patch, step 2" (chat); Further Notes (upstream's chat carries no date).

**Blocked by:** 13 (recorded-time reads)

**Status:** resolved

- [x] The chat request accepts an optional `reference_time` that defaults to now and appears in the system prompt.
- [x] `memory_append_field` takes an optional model-filled `valid_from` and defaults it to the request's `reference_time`. The message's reads run as of `reference_time`, and the time is stored in provenance.
- [x] Developer tests exercise the tool path with a given `reference_time`, without an LLM: the default `valid_from`, the as-of read and the provenance. Upstream's 39 tests pass unedited.
- [x] The work is amended into commit 2 and `patches/` is re-exported.

## Comments

2026-10-21: Built by amending commit 2 on `bitemporal` (now `5f45848`, subject "…keep-and-copy on changed ends, chat reference time"); `patches/0002-bitemporal-field-histories.patch` re-exported, `0001` unchanged; rebuilding from `patches/` (README's two commands, scratch worktree) gave a tree identical to `bitemporal`. Developed in a private worktree (`MemState-step2c`, branch `bitemporal-step2c`) and landed in the shared worktree under `/tmp/gem-suite-live.lock` with a hard reset (it was clean); ticket 15 was messaged the new hash.
- Code: `ChatBody.reference_time` (ISO string, optional; a non-date is a 400 before any LLM call); `chat_api._resolve_reference_time` defaults to now; all three prompts (standard, study A, study B) get `tools_schema.reference_time_prompt_block`; `MemoryToolRunner(reference_time=...)`: `memory_append_field` takes an optional `valid_from` (a non-date is refused with an error the model can retry on), defaults it to the reference time, and appends `(reference_time <iso>)` to the provenance; `memory_get_field`, `memory_get_field_history`, `memory_get_topic_schema` and `memory_get_topic` pick the current value as of the reference time (history stays whole). Without a reference time (the MCP server) the runner is unchanged.
- Tests: `tests/test_chat_reference_time.py`, 11 tests (default `valid_from` and provenance, explicit `valid_from` wins, non-date refused and nothing stored, no reference time = old behaviour, as-of reads on all four read tools, an entry starting after the reference time is not current, tool schema, and through `_execute_chat_body` with a stand-in for the Ollama loop: prompt, write, as-of read, default now, 400). 73 passed with upstream's 39 unedited.
- Smoke (under the lock): `scripts/probe_chat_reference_time.py` against a live patched server with `qwen3.5:2b`; recorded as F28. The stored entry got `valid_from` = the reference time and the provenance; the 2B model did not pass `valid_from` and mis-computed the start date in the value (Oct 4), which is ticket 18's measurement.
- Decisions: "as-of time of the reads" is the valid-time axis only (`valid_at` = reference time); recorded time is not capped, because a shifted reference time is a story date, not a belief moment. The provenance carries the reference time as text in the existing `provenance` string, as the spec says; no new entry field.
- For tickets 18/19/32: the request field is `reference_time` on `POST /api/llm/chat` (ISO date or datetime; a date means midnight UTC). The stored `valid_from` is the reference time unless the model fills `valid_from`; `created_at` stays the wall clock. The patch hooks need `git -c core.hooksPath=<commit-msg-only dir>` for commits in `MemState-patched` (journal). `docs/findings.md` F28 is the next free number as of this branch.
