#!/usr/bin/env bash
# Start the MemState API from the repo-root venv with real (fastembed) embeddings.
# Usage: scripts/run_memstate.sh [--patched] [ABSOLUTE_DB_PATH]
#   default DB (fresh, git-ignored):
#     upstream on Kuzu:        .runtime/memstate-kuzu-<timestamp>/memstate.kuzu
#     --patched on LadybugDB:  .runtime/memstate-ladybug-<timestamp>/memstate.lbug
#   --patched runs the MemState-patched/ worktree (branch bitemporal) of the shared checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Git-ignored state (venv, embedding cache, MemState/ submodule with .env, .runtime/) lives only in the
# main checkout; a linked worktree has none of it. SHARED is that main checkout (== ROOT outside a worktree).
SHARED="$(cd "$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)"
PY="$SHARED/.venv/bin/python"

PATCHED=0 DB_ARG=""
for arg in "$@"; do
  if [[ "$arg" == "--patched" ]]; then
    PATCHED=1
  elif [[ -z "$DB_ARG" && "$arg" != -* ]]; then
    DB_ARG="$arg"
  else
    echo "usage: $0 [--patched] [ABSOLUTE_DB_PATH]" >&2; exit 2
  fi
done

source "$ROOT/scripts/server_lock.sh"
hold_server_lock

# The venv's editable install points at MemState/src; PYTHONPATH wins over that .pth entry.
if [[ "$PATCHED" == 1 ]]; then
  SRC="$SHARED/MemState-patched/src"
  [[ -d "$SRC/memstate" ]] || { echo "ERROR: $SRC missing; rebuild MemState-patched/ (README, Run MemState)" >&2; exit 1; }
  export PYTHONPATH="$SRC${PYTHONPATH:+:$PYTHONPATH}"
  DEFAULT_DB="$SHARED/.runtime/memstate-ladybug-$(date +%Y%m%d-%H%M%S)/memstate.lbug"
  ABSOLUTE_MSG="DB path must be absolute"
else
  DEFAULT_DB="$SHARED/.runtime/memstate-kuzu-$(date +%Y%m%d-%H%M%S)/memstate.kuzu"
  ABSOLUTE_MSG="Kuzu path must be absolute"
fi
# Upstream's setting name is MEMSTATE_KUZU_PATH even when the patched copy opens a LadybugDB file.
export MEMSTATE_KUZU_PATH="${DB_ARG:-$DEFAULT_DB}"
[[ "$MEMSTATE_KUZU_PATH" = /* ]] || { echo "$ABSOLUTE_MSG" >&2; exit 1; }
export FASTEMBED_CACHE_PATH="$SHARED/.cache/fastembed"
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
MEMSTATE_GROQ_API_KEY="$(sed -n 's/^[[:space:]]*GROQ_API_KEY[[:space:]]*=[[:space:]]*//p' "$SHARED/MemState/.env" | tail -n1 | tr -d '"'"'"'\r')"
export MEMSTATE_GROQ_API_KEY

"$PY" -c 'import sys
from memstate.embeddings import default_text_embedder, HashEmbeddingProvider
e = default_text_embedder()
sys.exit("ERROR: fastembed unavailable, would use HashEmbeddingProvider" if isinstance(e, HashEmbeddingProvider) else 0)'

"$PY" -c 'import memstate, memstate.store.kuzu_adapter as a, os
print("MemState engine module: " + a.kuzu.__name__)
print("MemState source folder: " + os.path.dirname(os.path.dirname(os.path.abspath(memstate.__file__))))'

mkdir -p "$(dirname "$MEMSTATE_KUZU_PATH")"
echo "MemState DB: $MEMSTATE_KUZU_PATH"
cd "$ROOT"   # not MemState/: keeps the upstream memstate.kuzu default out of reach
exec "$PY" -m memstate.api.cli
