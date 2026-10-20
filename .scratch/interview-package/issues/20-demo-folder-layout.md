# Demo folder layout

Type: grilling
Status: resolved
Blocked by: 18, 19

## Question

What is the code layout of the demo, and how does the README's "Planned demo scenarios" section change?

Proposal so far: `demo/client.py`, `demo/baseline.py`, `demo/workload.py` (storyline + ground truth), `demo/checks/` (one module per C), `demo/llm_runs.py` (chat and judge runs), `demo/run.py` (scorecard), `demo/recordings/` (replay), `demo/results/` (verdicts with raw state snapshots); README scenarios section rewritten to match the C1–C6 harness.

## Answer

Resolved 2026-10-11 (recommendation accepted with the review, ticket 21), adjusted for the reduced LLM scope: `demo/client.py`, `demo/baseline.py`, `demo/workload.py` (storyline + ground truth), `demo/checks/` (one module per C), `demo/chat_run.py` (the single recorded Ollama run), `demo/run.py` (GEM conformance suite scorecard: upstream | patched | baseline), `demo/recordings/`, `demo/results/` (verdicts with raw state snapshots, latency log). README scenarios section rewritten to match the suite.
