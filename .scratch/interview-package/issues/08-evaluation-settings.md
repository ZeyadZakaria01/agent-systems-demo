# Evaluation settings and deviations

Type: grilling
Status: resolved
Blocked by: 03

## Question

Which fixed settings apply, and how are MemState's own hard-coded settings handled?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- Survey settings (2602.19320 App. E: MiniLM embeddings, temperature 0.3, top-k 10) for every role we own: the baseline, and any answer generation outside MemState.
- MemState internals stay as published and go in a deviations table: intent router temperature 0, Ollama model defaults, the think-off proxy. Groq is not used in the demo (ticket 21); its loop temperature 0.2 and silent parse retries are noted for the report only.
- Local model `qwen3.5:2b` thinks by default and MemState sends no `think`; thinking is turned off by `scripts/ollama_nothink_proxy.py`. The thinking-on cost is already measured (`docs/findings.md` F4: 19.2 s vs 1.7–3.8 s) and serves the cost row.
