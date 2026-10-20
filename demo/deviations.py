"""The deviations table: every departure from a standard setup, declared. One place; the scorecard renders it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Deviation:
    item: str
    as_shipped: str
    used_here: str
    why: str


DEVIATIONS: tuple[Deviation, ...] = (
    Deviation("MemState's intent router",
              "[INFERENCE, from reading the chat code] each chat request first makes an extra Ollama call that routes to query, ingest or both",
              "as shipped: no `intent_override`; the route of every turn is recorded",
              "the chat runs show MemState as published, not a tuned path"),
    Deviation("Ollama model default",
              "`llama3.2:latest` (`MemState/src/memstate/config.py:21`), not installed on the demo machine",
              "`qwen3.5:2b` through `MEMSTATE_OLLAMA_MODEL`, set by `scripts/run_memstate.sh`",
              "the only local model pulled; chat runs are n=1 and hand-graded"),
    Deviation("Thinking-off proxy (ADR 0003)",
              "MemState sends no `think` field, so `qwen3.5:2b` thinks on every round",
              "`scripts/ollama_nothink_proxy.py` defaults `think` to false on `/api/chat` and `/api/generate`",
              "a thinking turn took 19 s instead of 2-4 s on the laptop (ADR 0003); MemState stays unmodified (ADR 0001)"),
    Deviation("Kuzu pin (ADR 0004)",
              "`kuzu>=0.11.0` (Kuzu is archived upstream)",
              "`kuzu==0.11.3`, the final release, for upstream; the patch runs on LadybugDB 0.21.2 (ADR 0006)",
              "a reproducible engine; the engine line of each server is in its snapshot"),
    Deviation("Baseline (versioned row) settings",
              "the baseline has no settings of its own; MemState retrieves with `top_k` 8 and the same MiniLM model",
              "an in-process versioned row: an append-only history per (title, field) with the recorded time, one transaction per write, empty and `null` values rejected, no valid-time dates; MiniLM embeddings (the model MemState uses), top 8 (the same as every in-process system)",
              "it stands for the versioned fact store MAFBench calls for (`2602.03128v2.md:568`), so the baseline differs from MemState in structure, not in embedder or top-k"),
    Deviation("Duplicate pairs for C2(a) and C4's merge case",
              "a duplicate arises from two same-title `/v1 new_topic` writes; which topic the merge drops is chance (random ids)",
              "two topics written through `/v1` under distinct titles, the older value on the lower id and the newer on the higher, then both given one title by a labelled setup `PATCH title` (an editor edit; values are written through `/v1` only); a system with no retitle path gets the plain same-title writes. The merge extras of C2(a) also retitle three topics, and force a low id and archive one topic, by labelled setup writes",
              "MemState keeps the lower id (F9), so this makes the dropped topic hold the newer value in every repetition; F9 recorded the stale value current in 10/20 on random ids"),
    Deviation("Bad-merge chat run (duplicate of the storyline's own topic)",
              "the user's re-explanation reaches memory as a second `/v1 new_topic` with the same title; which topic the merge keeps is chance (the lower random id, F9)",
              "two topics created through `/v1` under distinct placeholder titles, the lower id holding the re-explanation (`Deadline = April 20` only) and the higher the whole storyline (the original, with the deadline history March 15 -> April 20 and its `vendor delay` provenance); then both are given the title `Website Redesign` by a labelled setup `PATCH title`, and a field-less `/v1 extend_topic` triggers the merge scan. The chat model is loaded by one direct request to the proxy before the first turn, so turn 1's latency is not the model load",
              "the merge then keeps the re-explanation and drops the original in every run, which is the 'looks right' outcome (C4) the report's answer-level contrast needs; the scored storyline stays duplicate-free"),
)
