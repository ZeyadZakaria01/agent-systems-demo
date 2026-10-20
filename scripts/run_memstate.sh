#!/usr/bin/env bash
# Start the MemState API from the repo-root venv with real (fastembed) embeddings.
# Usage: scripts/run_memstate.sh [ABSOLUTE_KUZU_PATH]
#   default DB: .runtime/memstate-<timestamp>/memstate.kuzu (fresh, git-ignored)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

export MEMSTATE_KUZU_PATH="${1:-$ROOT/.runtime/memstate-$(date +%Y%m%d-%H%M%S)/memstate.kuzu}"
[[ "$MEMSTATE_KUZU_PATH" = /* ]] || { echo "Kuzu path must be absolute" >&2; exit 1; }
export FASTEMBED_CACHE_PATH="$ROOT/.cache/fastembed"
export MEMSTATE_GROQ_MODEL=openai/gpt-oss-120b
export MEMSTATE_API_HOST=127.0.0.1 MEMSTATE_API_PORT=8765
# Ollama via the think-off proxy started by scripts/run_ollama.sh (qwen3.5 thinks by default and
# MemState sends no `think`). Override with http://127.0.0.1:11434 to run with thinking on.
export MEMSTATE_OLLAMA_BASE_URL="${MEMSTATE_OLLAMA_BASE_URL:-http://127.0.0.1:11435}"
# Upstream's default model is llama3.2:latest (config.py:21), which is not pulled; qwen3.5:2b is.
export MEMSTATE_OLLAMA_MODEL="${MEMSTATE_OLLAMA_MODEL:-qwen3.5:2b}"
# Export the Groq key from MemState/.env without echoing it. Uses the MEMSTATE_ prefix because
# upstream's GROQ_API_KEY fallback (config.py model_validator returning a copy) is discarded by
# pydantic-settings >= 2.x, so plain GROQ_API_KEY never reaches Settings.
MEMSTATE_GROQ_API_KEY="$(sed -n 's/^[[:space:]]*GROQ_API_KEY[[:space:]]*=[[:space:]]*//p' "$ROOT/MemState/.env" | tail -n1 | tr -d '"'"'"'\r')"
export MEMSTATE_GROQ_API_KEY

"$PY" -c 'import sys
from memstate.embeddings import default_text_embedder, HashEmbeddingProvider
e = default_text_embedder()
sys.exit("ERROR: fastembed unavailable, would use HashEmbeddingProvider" if isinstance(e, HashEmbeddingProvider) else 0)'

mkdir -p "$(dirname "$MEMSTATE_KUZU_PATH")"
echo "MemState DB: $MEMSTATE_KUZU_PATH"
cd "$ROOT"   # not MemState/: keeps the upstream memstate.kuzu default out of reach
exec "$PY" -m memstate.api.cli
