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
    Deviation("Reference GEM parameters (phase 1)",
              "the paper names a policy-defined bound β(n), thresholds θ and decay on disuse (`2605.26252v1.md:323`) and sets no values; MemState has a 0.05 archive threshold and a 500-topic soft limit, but no decay in its code (F10, F24)",
              "θ_archive 0.05 (MemState's); λ = 0.05^(1/400) ≈ 0.9925 per interaction, so an untouched topic at 1.0 falls below θ after 400 interactions (computed lazily; an ingest and a query are one interaction each); the forgetting check runs after every interaction; the decay clock restarts on any read or write; salience is halved when a topic is archived (MemState `executor.py:360`); declared β = 500 active topics (MemState's `topic_count_soft_limit`); +0.1 per returned topic (MemState's `query_salience_bump`), as-of reads included; history capped at 500 entries per field, overflow archived and readable by id; MiniLM, top 8; revision (merge) after every ingest, as MemState's Reasoner does",
              "values fixed in the spec before the build; the paper leaves them open, so the reference GEM's C5 verdict is stated beside its declared β"),
    Deviation("Reference GEM C6 clause 2 seeds",
              "upstream seeds the read topic at 0.03 and the never-read control at 0.01 (below the 0.05 threshold, which upstream's forgetting pass reaches only at the 500-topic gate)",
              "target and control both at 0.06 on the reference GEM, a per-system test setting (`describe()[\"c6_clause_2_seeds\"]`); the topic is read on every interaction until the first forgetting pass, where the control must be archived and the target not",
              "the reference GEM's forgetting check runs after every interaction, so a topic seeded below θ is archived by its own interaction"),
    Deviation("Reference GEM declared simplifications",
              "the paper's C3 revision repairs dependents, its policies may reference the whole state (`:353`, an open policy language), and forgetting is a graded ladder (compress, hide, archive, `:323`)",
              "one-hop flagging over extension edges in either direction (Listing 1: flag with evidence `{updated_field, timestamp}`, no repair, association edges never flag, the flag clears when the topic is next written); policy conditions limited to field comparisons on the topic being written and \"a neighbour exists via an extension or association edge\", actions reject and flag; a single archive threshold, no compress or hide rungs; no LLM, so no chat. Phase 1 reads Definition 4 with one timestamp per value (when it became true): no end date and no recorded time",
              "each one is a build decision of ADR 0007; the result is worded \"passes the suite's checks, with declared simplifications\""),
)
