# Turn local-model thinking off with a proxy, not a MemState patch

The local model (`qwen3.5:2b`) thinks by default and MemState's Ollama client sends no `think` field, which made one chat turn take 19 s instead of 2–4 s on the laptop. A small proxy (`scripts/ollama_nothink_proxy.py`) sits between MemState and Ollama and defaults `think` to false, so MemState stays unmodified (ADR 0001); the proxy is listed as a deviation, and one thinking-on run is kept for the cost comparison.

## Considered Options

- An Ollama Modelfile variant: fails (`unknown parameter 'think'`).
- A `/no_think` instruction in the system or user message: the model ignores it.
- Patching MemState's Ollama client: rejected by ADR 0001.
