#!/usr/bin/env bash
# Start a user-local Ollama server for the demo (no sudo, no systemd), plus the think-off proxy
# on 127.0.0.1:11435 that MemState uses (scripts/ollama_nothink_proxy.py).
#   scripts/run_ollama.sh          # run in foreground, log to .logs/ollama.log (and stdout)
#   scripts/run_ollama.sh --bg     # run detached; PIDs written to .logs/ollama.pid, .logs/ollama-proxy.pid
# Stop:  kill "$(cat .logs/ollama.pid)" "$(cat .logs/ollama-proxy.pid)"   (or Ctrl-C in foreground mode)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_BIN="${OLLAMA_BIN:-$HOME/.local/ollama/bin/ollama}"
LOG_DIR="$REPO_ROOT/.logs"
LOG_FILE="$LOG_DIR/ollama.log"
mkdir -p "$LOG_DIR"

[ -x "$OLLAMA_BIN" ] || { echo "ollama binary not found at $OLLAMA_BIN" >&2; exit 1; }

# Loopback only; MemState's default base URL is http://127.0.0.1:11434.
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
# MemState sends no options.num_ctx, so the server-side default context must be 16k.
export OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-16384}"
# 6 GiB laptop GPU: keep a single model resident, one request at a time.
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"
export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"
# Halves KV-cache VRAM at 16k context (quantized KV cache requires flash attention).
export OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}"
export OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-q8_0}"
# Models stored in the default ~/.ollama/models unless overridden.
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"

nohup python3 "$REPO_ROOT/scripts/ollama_nothink_proxy.py" 11435 "http://$OLLAMA_HOST" >>"$LOG_DIR/ollama-proxy.log" 2>&1 &
echo $! >"$LOG_DIR/ollama-proxy.pid"
echo "think-off proxy started (pid $!): 127.0.0.1:11435 -> $OLLAMA_HOST, log: $LOG_DIR/ollama-proxy.log"

if [ "${1:-}" = "--bg" ]; then
  nohup "$OLLAMA_BIN" serve >>"$LOG_FILE" 2>&1 &
  echo $! >"$LOG_DIR/ollama.pid"
  echo "ollama serve started (pid $!), log: $LOG_FILE"
else
  trap 'kill "$(cat "$LOG_DIR/ollama-proxy.pid")" 2>/dev/null' EXIT
  "$OLLAMA_BIN" serve 2>&1 | tee -a "$LOG_FILE"
fi
