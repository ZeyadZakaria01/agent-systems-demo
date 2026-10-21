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
    Deviation(
        "MemState's intent router",
        "[INFERENCE, from reading the chat code] each chat request first makes an extra Ollama call that routes to query, ingest or both",
        "as shipped: no `intent_override`; the route of every turn is recorded",
        "the chat runs show MemState as published, not a tuned path",
    ),
    Deviation(
        "Ollama model default",
        "`llama3.2:latest` (`MemState/src/memstate/config.py:21`), not installed on the demo machine",
        "`qwen3.5:2b` through `MEMSTATE_OLLAMA_MODEL`, set by `scripts/run_memstate.sh`, for the run of record; the chat series (`demo/chat-series/qwen3.5-4b/`, 10 takes per case) uses `qwen3.5:4b`, run by the demo's own Ollama on port 11436 (a system Ollama may hold 11434)",
        "2b routed the two-weeks statement to `query` in 7 of 7 takes, so the case measured the router, not the reference time; 4b routed it to ingest in 3 of 3 pilot takes (`scripts/pilot_two_weeks.py`); 4b is the largest qwen3.5 that loads on the 6 GB GPU at 16k context (3.1 of 3.9 GB on the GPU)",
    ),
    Deviation(
        "Thinking-off proxy (ADR 0003)",
        "MemState sends no `think` field, so `qwen3.5:2b` thinks on every round",
        "`scripts/ollama_nothink_proxy.py` defaults `think` to false on `/api/chat` and `/api/generate`",
        "a thinking turn took 19 s instead of 2-4 s on the laptop (ADR 0003); MemState stays unmodified (ADR 0001)",
    ),
    Deviation(
        "Kuzu pin (ADR 0004)",
        "`kuzu>=0.11.0` (Kuzu is archived upstream)",
        "`kuzu==0.11.3`, the final release, for upstream; the patch runs on LadybugDB 0.21.2 (ADR 0006)",
        "a reproducible engine; the engine line of each server is in its snapshot",
    ),
    Deviation(
        "Baseline (versioned row) settings",
        "the baseline has no settings of its own; MemState retrieves with `top_k` 8 and the same MiniLM model",
        "an in-process versioned row: an append-only history per (title, field) with the recorded time, one transaction per write, empty and `null` values rejected, no valid-time dates; MiniLM embeddings (the model MemState uses), top 8 (the same as every in-process system)",
        "it stands for the versioned fact store MAFBench calls for (`2602.03128v2.md:568`), so the baseline differs from MemState in structure, not in embedder or top-k",
    ),
    Deviation(
        "Duplicate pairs for C2(a) and C4's merge case",
        "a duplicate arises from two same-title `/v1 new_topic` writes; which topic the merge drops is chance (random ids)",
        "two topics written through `/v1` under distinct titles, the older value on the lower id and the newer on the higher, then both given one title by a labelled setup `PATCH title` (an editor edit; values are written through `/v1` only); a system with no retitle path gets the plain same-title writes. The merge extras of C2(a) also retitle three topics, and force a low id and archive one topic, by labelled setup writes",
        "MemState keeps the lower id (F9), so this makes the dropped topic hold the newer value in every repetition; F9 recorded the stale value current in 10/20 on random ids",
    ),
    Deviation(
        "Bad-merge chat run (duplicate of the storyline's own topic)",
        "the user's re-explanation reaches memory as a second `/v1 new_topic` with the same title; which topic the merge keeps is chance (the lower random id, F9)",
        "two topics created through `/v1` under distinct placeholder titles, the lower id holding the re-explanation (`Deadline = April 20` only) and the higher the whole storyline (the original, with the deadline history March 15 -> April 20 and its `vendor delay` provenance); then both are given the title `Website Redesign` by a labelled setup `PATCH title`, and a field-less `/v1 extend_topic` triggers the merge scan. The chat model is loaded by one direct request to the proxy before the first turn, so turn 1's latency is not the model load",
        "the merge then keeps the re-explanation and drops the original in every run, which is the 'looks right' outcome (C4) the report's answer-level contrast needs; the scored storyline stays duplicate-free",
    ),
    Deviation(
        "Two-weeks chat run (dates shifted to the run day)",
        'the spec tells the case on Oct 6 and Oct 20 (ticket 18: "I started my new job two weeks ago" at reference time Oct 6, "how long have I been there?" at Oct 20) and says the dates are shifted so that Oct 20 is the run day; the second message is now "How long have I been at my new job?"',
        "both `reference_time` values and the ground-truth start date move by the run day's offset from Oct 20 (a run on Oct 21 sends Oct 7 and Oct 21 and grades the start date against Sep 23, ± 1 day); the two messages are sent verbatim, one request each with no conversation history, on a fresh step-3 database with nothing seeded, no `intent_override` and no `model`; the recording states the dates it used. The model is loaded by one direct request to the proxy before the first turn. The variants that force W1's route or seed a profile topic are not the case of record (`demo/recordings/attempts/`)",
        'relative time is resolved against the request\'s date, as the spec asks; the second request carries nothing from the first, so the answer can only come from what the first one stored; "there" had nothing to refer to in a request with no history, and with 4b the second turn called no memory tool in 6 of 6 pilot takes, so the question was reworded to name the job (3 of 3 takes then read memory)',
    ),
    Deviation(
        "Reference GEM parameters (phase 1)",
        "the paper names a policy-defined bound β(n), thresholds θ and decay on disuse (`2605.26252v1.md:323`) and sets no values; MemState has a 0.05 archive threshold and a 500-topic soft limit, but no decay in its code (F10, F24)",
        "θ_archive 0.05 (MemState's); λ = 0.05^(1/400) ≈ 0.9925 per interaction, so an untouched topic at 1.0 falls below θ after 400 interactions (computed lazily; an ingest and a query are one interaction each); the forgetting check runs after every interaction; the decay clock restarts on any read or write; salience is halved when a topic is archived (MemState `executor.py:360`); declared β = 500 active topics (MemState's `topic_count_soft_limit`); +0.1 per returned topic (MemState's `query_salience_bump`), as-of reads included; history capped at 500 entries per field, overflow archived and readable by id; MiniLM, top 8; revision (merge) after every ingest, as MemState's Reasoner does",
        "values fixed in the spec before the build; the paper leaves them open, so the reference GEM's C5 verdict is stated beside its declared β",
    ),
    Deviation(
        "Reference GEM C6 clause 2 seeds",
        "upstream seeds the read topic at 0.03 and the never-read control at 0.01 (below the 0.05 threshold, which upstream's forgetting pass reaches only at the 500-topic gate)",
        'target and control both at 0.06 on the reference GEM, a per-system test setting (`describe()["c6_clause_2_seeds"]`); the topic is read on every interaction until the first forgetting pass, where the control must be archived and the target not',
        "the reference GEM's forgetting check runs after every interaction, so a topic seeded below θ is archived by its own interaction",
    ),
    Deviation(
        "Reference GEM declared simplifications",
        "the paper's C3 revision repairs dependents, its policies may reference the whole state (`:353`, an open policy language), and forgetting is a graded ladder (compress, hide, archive, `:323`)",
        'one-hop flagging over extension edges in either direction (Listing 1: flag with evidence `{updated_field, timestamp}`, no repair, association edges never flag, the flag clears when the topic is next written); policy conditions limited to field comparisons on the topic being written and "a neighbour exists via an extension or association edge", actions reject and flag; a single archive threshold, no compress or hide rungs; no LLM, so no chat. Phase 1 reads Definition 4 with one timestamp per value (when it became true): no end date and no recorded time',
        'each one is a build decision of ADR 0007; the result is worded "passes the suite\'s checks, with declared simplifications"',
    ),
    Deviation(
        "Reference GEM ramps (C5-2 counts, once)",
        "every other system's C5-2 runs each ramp size 1 or 3 times and its milliseconds fill the latency table",
        'the reference GEM runs each ramp size once, times nothing and records only the counts (no repeats, no latency rows, no ramp milliseconds in `results.json`); `describe()["latency_comparable"]` is False',
        'ticket 19 says the reference GEM "runs no ramps", but its C5-2 verdict rests on the active and archived counts at n=2000 (about 400 active against β = 500); in-process milliseconds are not comparable with an HTTP server',
    ),
)
