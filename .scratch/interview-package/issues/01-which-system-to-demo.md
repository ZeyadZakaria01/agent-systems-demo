# Which system to demo

Type: grilling
Status: resolved
Blocked by: —

## Question

The professor asked for a demo of one of the two systems. Which one, and where does the other paper appear?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- Demo **MemState** (GEM paper) only.
- **MAFBench** appears only in the report and slides. It evaluates multi-agent frameworks, not a memory system; its memory module needs a paid `OPENAI_API_KEY` for embeddings (`single_agent/memory/router_groq.py`); a full memory run costs about $300 (paper footnote 10). Its findings motivate the demo (revised after review, ticket 21): multi-hop selective forgetting stays below 5.0 in every framework (single-hop reaches 20.2 for retrieval-only LangGraph), every evaluated framework treats memory as append-only, scoring is answer-level only, and §6 asks for versioned fact stores (MVCC, WAL).
- No Mem0 / Zep comparison (paid keys); named as future work.
