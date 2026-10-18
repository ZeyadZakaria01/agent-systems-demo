# Agent systems demo

Interview package for Prof. Essam Mansour: a demo of MemState (the GEM paper's system) plus a report and slides on the limitations of GEM (arXiv 2605.26252) and MAFBench (arXiv 2602.03128). Planning lives in the wayfinder map `.scratch/interview-package/map.md`; read it before choosing work.

## Rules

- `MemState/` is upstream at `945d7c4` and stays byte-for-byte unmodified. Measure it as published, over its HTTP API. Changes to MemState live in a separate patched worktree.
- A claim about MemState behaviour enters `docs/findings.md`, the report, or the slides only with a reproducing run (command, DB path, key output). Claims from reading code carry `[INFERENCE]`.
- Commit messages and PR bodies contain the change description and human co-authors only. `.githooks/commit-msg` strips AI attribution; each clone enables it with `git config core.hooksPath .githooks`.
- Record each difficulty when it happens in `docs/journal.md`: date, expected, observed, evidence, resolution, lesson. Tag `report:` when the report should cite it.

## Running

Before starting MemState or Ollama, read the README section "Run MemState"; the scripts in `scripts/` encode the workarounds. Every MemState DB path is absolute and fresh; `MemState/memstate.kuzu` is upstream data and stays closed. This is a laptop with a 6 GB GPU and little free RAM: stop servers when a run ends.

## Docs

- `docs/papers/`: the papers as Markdown (GEM, MAFBench, the two surveys, Zep, Hindsight, MemTX, StateMemBench), their PDFs, and `2605.26252v1-alignment.md` (code vs paper). Cite the paper text, not a paraphrase.
- `docs/report/gem-limitations-and-directions.md`: the report, single source of truth; its §9 is the demo design. Edit here, never a copy elsewhere.
- `docs/findings.md`: MemState facts proven by runs. Append when a run proves or disproves something.
- `docs/journal.md`: difficulties and lessons.

## Agent skills

### Issue tracker

Local markdown under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the root, created lazily. See `docs/agents/domain.md`.
