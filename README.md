# Agent Memory Demo: Governed Evolving Memory on MemState

Review demo for *Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory* (Orogat & Mansour, arXiv:[2605.26252](https://arxiv.org/abs/2605.26252)). A GEM conformance suite checks the stored state of the authors' proof of concept, [MemState](https://github.com/CoDS-GCS/MemState), against the paper's correctness conditions C1–C6, beside a versioned-row baseline and an in-process reference GEM. The contribution is a bitemporal extension of MemState's field histories on LadybugDB (three patch steps), with time probes measured before and after.

MemState describes itself as a proof of concept, not a full implementation (its README). The scorecard therefore reads as a measurement of the published artifact against the paper's conditions: `fail` and `absent` mark gaps its authors state, not defects. The design (tests, verdict scale, baseline, extension, scorecard) lives in [report §9](docs/report/gem-limitations-and-directions.md#9-demo-time-correct-governed-memory).

## Status

The suite is built. Its run of record is [`runs/record/20261021-194912/`](runs/record/20261021-194912/scorecard.md): seven systems, 3 ramp repeats, both chat cases, on the final patch commits (finding F41). `runs/record/20261021-085949/`, on the superseded commits, stays as the evidence of findings F32–F35. Open decisions live on the wayfinder map (`.scratch/interview-package/map.md`).

## Quick start

```bash
git submodule update --init && git config core.hooksPath .githooks
git -C MemState fetch "$PWD/patches/bitemporal.bundle" 'refs/heads/bitemporal:refs/heads/bitemporal' 'refs/superseded/*:refs/superseded/*'
git -C MemState worktree add ../MemState-patched bitemporal   # the patched copy (patch steps 1-3)
uv venv -p 3.12 .venv
uv pip install -p .venv -e 'MemState[embedding]' 'kuzu==0.11.3' 'ladybug==0.21.2' httpx pytest pytest-asyncio ruff
git -C MemState checkout -- src/memstate.egg-info            # pip rewrites it; keep the submodule pristine

.venv/bin/python -m pytest                                    # offline tests: in-process systems, no server
.venv/bin/python -m demo.run --list                           # checks and systems
.venv/bin/python -m demo.run --systems baseline,reference-gem-p1,reference-gem-p2   # in-process run, no server
.venv/bin/python -m demo.chat.run replay                      # replay the recorded chat runs, no server or GPU
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C1   # starts MemState
```

[`docs/suite.md`](docs/suite.md) is the operating manual: MemState and its patched copy, Ollama, the runner's options, the run of record, live mode, the chat runs and their grading.

## Layout

```text
demo/                 the conformance suite (python -m demo.run)
  run.py              recorded runner and CLI; live.py drives an already-running server
  verdict.py          the verdict model; evidence.py writes a run's folder; failures.py turns errors into verdicts
  checks/             one module per condition (C1–C6, C4′, time probes, triage, over-flagging), discovered by the runner
  systems/            the adapter seam (adapter.py) and its adapters: MemState over HTTP, the versioned-row baseline,
                      the reference GEM; the registry, patch steps, server start/stop and the machine lock
  workloads/          what checks drive through the adapter: merges, ramps, windows, the storyline, time stories
  reporting/          scorecard, per-step change table, measurement tables, deviations, run of record
  chat/               chat runs on MemState's own chat: record, replay, Sonnet and blind-reviewer grades
tests/                pytest, mirroring demo/ (systems/, checks/, reporting/, chat/)
scripts/              MemState and Ollama start scripts, the think-off proxy, HTTP probes, chat-series runner
patches/              the three patch steps on MemState 945d7c4: .patch files and bitemporal.bundle (exact commits)
runs/                 run output: record/ (run of record), recordings/ (chat takes of record), chat-series/;
                      results/ and results-live/ are local and git-ignored
docs/                 report/, findings.md (facts proven by runs), journal.md (difficulties), adr/, papers/, suite.md
MemState/             upstream submodule, pinned at 945d7c4 and never modified
MemTX/                MemTX submodule at 4e1124c, reference only; its third_party/MemState equals 945d7c4 but README.md
.scratch/             wayfinder map, decision tickets, suite spec
.githooks/            commit-msg (Conventional Commits, no AI attribution) and pre-commit guardrails
```

## Read first

1. [`docs/papers/2605.26252v1.md`](docs/papers/2605.26252v1.md): §1 (the four failure modes), §3 (GEM operators and conditions C1–C6), §4 (MemState).
2. [`docs/report/gem-limitations-and-directions.md`](docs/report/gem-limitations-and-directions.md): the review, and in §9 the demo design.
3. [`docs/papers/2605.26252v1-alignment.md`](docs/papers/2605.26252v1-alignment.md): what MemState implements and what it leaves open.
4. [`docs/findings.md`](docs/findings.md): what runs have proven, each with its reproducing command.
5. [`GLOSSARY.md`](GLOSSARY.md): the project's terms.

## Papers

Each paper is converted to `docs/papers/<arxiv-id>.md` beside its PDF (git-ignored); an analysis is `docs/papers/<arxiv-id>-<topic>.md`.

| File | Paper | Use here |
|---|---|---|
| `2605.26252v1.md` | GEM: *Is Agent Memory a Database?* (Orogat & Mansour) | the paper under review |
| `2605.26252v1-alignment.md` | analysis | how MemState's code lines up with the paper, condition by condition |
| `2602.03128v2.md` | MAFBench: *Architectural Design, Not Only Model Intelligence, Governs Multi-Agent LLM Performance* (Orogat, Rostam, Mansour) | report §8 |
| `2602.19320.md` | *Anatomy of Agentic Memory* (Jiang et al.) | companion survey |
| `2602.05665.md` | *Graph-based Agent Memory: Taxonomy, Techniques, and Applications* (Yang et al.) | tests GEM's Table 1 coverage claim |
| `2501.13956.md` | *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* (Rasmussen et al.) | checks GEM's claims about Zep |
| `2512.12818.md` | *Hindsight is 20/20* (Latimer et al.) | compared against GEM's operators |
| `2607.23929v2.md` | *MemTX: Transactional Belief Commit for Stateful Agent Memory* (Li et al.) | a published conformance-suite precedent |
| `2608.19652v1.md` | *Can Agent Memory Systems Track Evolving State?* (Fan et al.) | StateMemBench vs GEM's planned workload |
| `2606.06240v1.md` | *TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory* (Wang) | report §5.11 and §6.2 |

## Source

- Paper: <https://arxiv.org/abs/2605.26252>
- Code: <https://github.com/CoDS-GCS/MemState> (CoDS Lab, Concordia University)
