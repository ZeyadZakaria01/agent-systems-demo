# Measure Groq tokens per chat turn

Type: task
Status: closed
Blocked by: —

## Question

How many tokens does one MemState chat turn consume on Groq (`gpt-oss-120b`), for an ingest turn and for a query turn, and does prompt caching reduce it? Needed before deciding the Groq budget.

Method: run one ingest turn and one query turn through `/api/llm/chat` on a fresh DB; read Groq's `x-ratelimit-remaining-tokens` before and after (or the usage field if exposed); record wall time and tool rounds. Known so far: limits are 8000 tokens/min and 1000 requests/day; one query turn took 72 s.

## Closed

Out of scope, 2026-10-11 (ticket 21): the demo uses no Groq runs.
