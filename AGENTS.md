# Agent systems demo

Interview package for Prof. Essam Mansour: a demo of MemState (the GEM paper's system) plus a report and slides on the limitations of GEM (arXiv 2605.26252) and MAFBench (arXiv 2602.03128). Planning lives in the wayfinder map `.scratch/interview-package/map.md`; read it before choosing work.

## Rules

- `MemState/` is upstream at `945d7c4` and stays byte-for-byte unmodified. Measure it as published, over its HTTP API. Changes to MemState live in a separate patched worktree.
- A claim about MemState behaviour enters `docs/findings.md`, the report, or the slides only with a reproducing run (command, DB path, key output); the command runs a script committed in the repo (probes go in `scripts/`: `probe_memstate.py` for the HTTP probes, `probe_chat_reference_time.py` for the chat `reference_time`). Claims from reading code carry `[INFERENCE]`.
- Commit messages and PR bodies contain the change description and human co-authors only. `.githooks/` enforces it: `commit-msg` strips AI attribution and refuses a subject that is not a Conventional Commit of at most 72 characters (merge commits included); `pre-commit` keeps the report on `main`, map lines ≤ 400 chars, the offline suite green, staged Python `ruff`-clean, and refuses a test identity or an API key in a staged line. Each clone enables it with `git config core.hooksPath .githooks`. Keys live in git-ignored files (`.secrets/`, `MemState/.env`), never in a command or a committed file.
- History: one logical change per commit, typed per the `git-commit` skill. A branch or ticket lands on `main` as one squashed (or rebased) commit that includes its docs, findings and ticket status; never a merge commit, a "Resolve ticket" commit or a "Merge main into ..." commit. Where a skill says merge (`implement-spec`: implementers merge the integration tip, a merger subagent merges each ticket), rebase onto the tip and land with `git merge --squash` instead.
- Layout: suite code lives in the `demo/` package that owns it (`systems/` adapters and servers, `checks/` one module per condition, `workloads/` what checks drive, `reporting/` rendering, `chat/` chat runs); `demo/` itself holds only the runner and the verdict/evidence model. Tests mirror the package under `tests/`. Run output goes under `runs/`, never inside `demo/`. Add a module only when no existing one owns the behaviour.
- Subagents receive these rules in their task. They edit; they do not commit. The parent reviews the diff, runs `.venv/bin/ruff check .` and `.venv/bin/python -m pytest`, and makes the commit.
- Record each difficulty when it happens in `docs/journal.md`: date, expected, observed, evidence, resolution, lesson. Tag `report:` when the report should cite it.
- A chat result (model, router, resolver) enters findings or the report only from a fresh series of at least 10 takes, never from the pilot or the takes a rule was tuned on. Before a series: replay a rule change offline on recorded model output (`scripts/replay_two_weeks_writes.py`), then a 3-take pilot; series run one take at a time with `scripts/chat_series.py`, which stops at the first error.

## Running

Before starting MemState or Ollama, read the README section "Run MemState"; the scripts in `scripts/` encode the workarounds. Every MemState DB path is absolute and fresh; `MemState/memstate.kuzu` is upstream data and stays closed. This is a laptop with a 6 GB GPU and little free RAM: stop servers when a run ends. The one machine-wide lock is `../agent-systems-demo-wt/server.lock`; the runner and the server scripts hold it themselves.

## Docs

- `docs/papers/`: the papers as Markdown (GEM, MAFBench, the two surveys, Zep, Hindsight, MemTX, StateMemBench), their PDFs, and `2605.26252v1-alignment.md` (code vs paper). Cite the paper text, not a paraphrase.
- `docs/report/gem-limitations-and-directions.md`: the report, single source of truth; its §9 is the demo design. Edit it only on `main`.
- `MemState/docs/` (HTML): upstream's own design docs (`data-model/`, `operations/`). Read them, and the code they describe, before stating what MemState intends or recommending a design that departs from it.
- `docs/findings.md`: MemState facts proven by runs. Append when a run proves or disproves something.
- `docs/journal.md`: difficulties and lessons.

## Agent skills

### Issue tracker

Local markdown under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the root, created lazily. See `docs/agents/domain.md`.
