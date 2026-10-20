# Docs and planning process

Type: grilling
Status: resolved
Blocked by: —

## Question

Where do decisions, terms, difficulties and findings live so the work survives across sessions and tools?

## Answer

Resolved 2026-10-11.

- Wayfinder map for the whole interview package, local markdown tracker in `.scratch/` (committed; was git-ignored until 2026-10-12, when the user chose to track it).
- `AGENTS.md` is the agent-instruction source; `CLAUDE.md` imports it. Setup-skill config in `docs/agents/`.
- Decisions live in tickets; `GLOSSARY.md` and `docs/adr/` are created by domain-modeling as grilling tickets settle terms and hard-to-reverse decisions.
- `docs/findings.md`: MemState facts proven by runs. `docs/journal.md`: dated difficulties and lessons. Both committed.
- Papers moved to `docs/papers/`.
- No AI attribution in commits or PRs: `.githooks/commit-msg`, `.claude/settings.json` attribution off, Cursor CLI already off; Cursor IDE toggle is the user's.
