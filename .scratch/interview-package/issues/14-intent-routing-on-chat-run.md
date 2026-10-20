# Intent routing on the chat run

Type: grilling
Status: resolved
Blocked by: 03

## Question

MemState classifies each chat message as `query` / `ingest` / `both` before choosing tools; `intent_override` can fix the route (`chat_api.py:127-130,208-209`). On the separate chat run, let the classifier decide (as shipped, log each route, count misroutes) or fix the route per turn?

Recommendation so far: let it classify and log routes. Risk to watch: the classifier uses `max_tokens=16` and gpt-oss is a reasoning model, so it may return empty and silently fall back to `both` [INFERENCE].

## Answer

Resolved 2026-10-12 (was carried as "deferred", a status wayfinder does not have; the local tracker can only block on tickets, not on a condition, and the question already had a default answer): MemState classifies each message as shipped, and the single Ollama chat run records the route chosen for every turn. No `intent_override`. A misroute seen in the run is a finding about MemState, logged in `docs/findings.md`, not a new decision. The `max_tokens=16` risk above applies to gpt-oss; the chat run uses `qwen3.5:2b` through the think-off proxy.
