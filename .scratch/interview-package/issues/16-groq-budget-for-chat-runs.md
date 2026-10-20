# Groq budget for chat runs

Type: grilling
Status: closed
Blocked by: 14, 15

## Question

Given the measured tokens per turn and the free-tier limits, how many turns per chat run and how many Groq runs?

Options on the table: 4 turns per run (2 ingest, 2 query) × 3 runs, spread over two days if needed; 8 turns × 3 runs over about three days; Groq ×1 plus Ollama ×3.

Recommendation so far: 4 turns × 3 runs; fall back to Groq ×1 (labelled n=1) plus Ollama ×3 if the measurement shows it does not fit.

## Closed

Out of scope, 2026-10-11 (ticket 21): the demo uses no Groq runs; LLM work is one recorded Ollama run.
