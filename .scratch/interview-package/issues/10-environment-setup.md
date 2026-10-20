# Environment setup

Type: task
Status: resolved
Blocked by: —

## Question

Get MemState, Groq and a local LLM running on this laptop, live-verified, before the harness is designed in detail.

## Answer

Done and live-verified (backfilled 2026-10-11). Facts later tickets depend on:

- Root `.venv` (Python 3.12): `-e MemState[embedding]`, `kuzu==0.11.3` (archived upstream; prebuilt wheel), fastembed 0.8.1 with MiniLM cached in `.cache/fastembed` (loads offline). Upstream tests: 39 passed.
- `scripts/run_memstate.sh [ABS_DB]`: 127.0.0.1:8765, `gpt-oss-120b` on Groq, refuses hash embeddings, points Ollama at the think-off proxy.
- `scripts/run_ollama.sh --bg`: Ollama 0.35.1 in `~/.local/ollama`, CUDA 13 backend (driver 580, CUDA 13.0, RTX 3060 Laptop compute 8.6), `qwen3.5:2b` 100% GPU at 16k context, think-off proxy on :11435. Unused `cuda_v12` deleted.
- Groq limits from headers: 8000 tokens/min, 1000 requests/day. One Groq chat turn: 72 s. One Ollama chat turn via proxy: 1.7–3.8 s (19.2 s with thinking on).
- Upstream bug: plain `GROQ_API_KEY` is dropped by `config.py`'s validator; the script passes `MEMSTATE_GROQ_API_KEY`.
- `.githooks/commit-msg` strips AI attribution; `core.hooksPath` set for this clone.
- Free disk ~8 GB.
