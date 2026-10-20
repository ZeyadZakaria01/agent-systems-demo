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
              "each chat request first makes an extra Ollama call that routes to query, ingest or both",
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
    Deviation("Baseline retrieval settings",
              "the baseline has no settings of its own",
              "survey settings: MiniLM embeddings (the model MemState uses), top-k 10, temperature 0.3 if generation is added",
              "the baseline differs from MemState in structure, not in embedder"),
)
