# Baseline and setup rules

Type: grilling
Status: resolved
Blocked by: 03

## Question

What is MemState compared against, may the harness use editor endpoints, and does the cross-tenant leak check belong in the demo?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- **Baseline**: a last-write-wins upsert keyed by (title, field), the "plain database row". Expected to pass C1/C2 and fail C4/C6, isolating what GEM adds over CRUD. The paper's Figure 1 append-and-evict store is an illustration slide only.
- **Editor endpoints** (`/api/ui/...`: forced `topic_id`, salience, archived): allowed for **setup only**, labelled; every scored transition goes through `/v1/ingest`, `/v1/query` or the chat.
- **Leak check** (GEM §5.3): out of the demo. MemState ranks by similarity only and has no tenants, so the result is empty by construction; report carries a research note.
