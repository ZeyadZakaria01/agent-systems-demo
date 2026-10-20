# Agent Memory Demo: Governed Evolving Memory on MemState

Review demo for *Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory* (Orogat & Mansour, arXiv:[2605.26252](https://arxiv.org/abs/2605.26252)). It runs a GEM conformance suite against the authors' proof-of-concept, [MemState](https://github.com/CoDS-GCS/MemState), checking its stored state against the paper's correctness conditions C1–C6.

## Status

Environment ready and live-verified (MemState, Groq, Ollama on CUDA; LadybugDB beside Kuzu). The demo design is decided: [report §9](docs/report/gem-limitations-and-directions.md#9-demo-time-correct-governed-memory), with the decisions behind it on the wayfinder map (`.scratch/interview-package/map.md`). **No demo code exists yet**; `scripts/probe_memstate.py` holds the probes behind findings F7–F12, and the build spec is `.scratch/gem-conformance-suite/spec.md` (ready to build).

## Layout

| Path | Contents |
|---|---|
| `MemState/` | Upstream repo <https://github.com/CoDS-GCS/MemState> as a git submodule pinned at `945d7c4`. Unmodified. |
| `MemTX/` | MemTX's code and data <https://github.com/lxy1134/MEMTX_> as a git submodule pinned at `4e1124c`. Reference only, not run. Its `third_party/MemState` matches `945d7c4` file for file; only `README.md` differs. |
| `docs/papers/2605.26252v1.md` | The paper converted to Markdown (abstract, GEM definitions, C1–C6, MemState design, research agenda, references). |
| `docs/papers/2605.26252v1-alignment.md` | Why MemState is a proof of concept, and how its code lines up with the paper, condition by condition. |
| `docs/papers/2602.19320.md` | Companion survey, *Anatomy of Agentic Memory* (Jiang et al., arXiv:[2602.19320](https://arxiv.org/abs/2602.19320)), converted to Markdown: MAG taxonomy, benchmark/metric/backbone/latency analysis, prompts, references. Not analyzed against MemState. |
| `docs/papers/2602.03128v2.md` | MAFBench paper, *Architectural Design, Not Only Model Intelligence, Governs Multi-Agent LLM Performance* (Orogat, Rostam, Mansour, arXiv:[2602.03128](https://arxiv.org/abs/2602.03128)), converted to Markdown: five-dimension taxonomy, MAFBench suite, memory/planning/specialization/topology/overhead results, six design principles, references. Not analyzed against MemState. |
| `docs/papers/2501.13956.md` | *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* (Rasmussen et al., arXiv:[2501.13956](https://arxiv.org/abs/2501.13956)), converted to Markdown. GEM's main reference point for graph-structured memory; used to check GEM's claims about Zep. |
| `docs/papers/2512.12818.md` | *Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects* (Latimer et al., arXiv:[2512.12818](https://arxiv.org/abs/2512.12818)), converted to Markdown. Not cited by GEM; compared against GEM's operators. |
| `docs/papers/2602.05665.md` | Survey, *Graph-based Agent Memory: Taxonomy, Techniques, and Applications* (Yang et al., arXiv:[2602.05665](https://arxiv.org/abs/2602.05665)), converted to Markdown. Not cited by GEM; used to test GEM's Table 1 coverage claim. |
| `docs/papers/2607.23929v2.md` | *MemTX: Transactional Belief Commit for Stateful Agent Memory* (Li et al., arXiv:[2607.23929](https://arxiv.org/abs/2607.23929)), converted to Markdown. Cites GEM and runs MemState as a baseline; a published conformance-suite precedent for the demo. |
| `docs/papers/2608.19652v1.md` | *Can Agent Memory Systems Track Evolving State?* (Fan et al., arXiv:[2608.19652](https://arxiv.org/abs/2608.19652)), converted to Markdown. Introduces StateMemBench and StateMem; compared against GEM's planned 500-turn workload. |
| `docs/report/gem-limitations-and-directions.md` | The report for Prof. Mansour: limitations, gaps and research directions of the GEM paper, the MAFBench link (§8), and the demo design (§9). Single source of truth for the report. |
| `docs/findings.md` | MemState behaviour proven by runs, each with its reproducing run. |
| `docs/journal.md` | Dated difficulties and lessons, tagged `report:` where the report should cite them. |
| `GLOSSARY.md` | Domain terms (GEM memory model and conformance-suite vocabulary). Definitions only. |
| `docs/adr/` | Decisions that are hard to reverse, surprising and a real trade-off (measure MemState unmodified, `absent` verdict, think-off proxy, Kuzu pin, corrections keep and copy, patch on LadybugDB). |
| `docs/agents/` | Configuration for the agent skills (issue tracker, domain docs, triage labels). |
| `.scratch/interview-package/` | Wayfinder map and decision tickets. |
| `AGENTS.md`, `CLAUDE.md` | Instructions for coding agents; `CLAUDE.md` imports `AGENTS.md`. |
| `scripts/` | Start scripts for MemState and Ollama, the think-off proxy, and `probe_memstate.py` (HTTP probes for C3, salience, merge and a topic ramp; findings F7–F12). |
| `.githooks/` | `commit-msg` hook that strips AI attribution from commit messages. |
| `docs/papers/*.pdf` | Local copies of the papers, next to their Markdown conversions. Git-ignored. |

Naming convention: each converted paper is `docs/papers/<arxiv-id>.md`, matching its PDF filename, and its analysis is `docs/papers/<arxiv-id>-<topic>.md`.

## Read first

1. [`docs/papers/2605.26252v1.md`](docs/papers/2605.26252v1.md): §1 (the four failure modes), §3 (GEM operators and conditions C1–C6), §4 (MemState).
2. [`docs/report/gem-limitations-and-directions.md`](docs/report/gem-limitations-and-directions.md): the review, and in §9 the demo design.
3. [`docs/papers/2605.26252v1-alignment.md`](docs/papers/2605.26252v1-alignment.md): what the repo implements and what it leaves open.
4. [`docs/findings.md`](docs/findings.md): what runs have proven so far.
5. [`GLOSSARY.md`](GLOSSARY.md): the project's terms.

## Run MemState

From the upstream quickstart (`MemState/docs/guides/quickstart.md`); requires Python 3.11+.

```bash
cd MemState
pip install -e .
cp .env.example .env            # edit as needed
python -m memstate.api.cli      # or: memstate-api
```

| Resource | URL |
|---|---|
| Graph Explorer | <http://127.0.0.1:8765/ui/> |
| Interactive API docs | <http://127.0.0.1:8765/docs> |

This repo's demo path uses a root venv with real embeddings (fastembed) instead:

```bash
git submodule update --init           # MemState/ pinned at upstream 945d7c4; MemTX/ (reference) at 4e1124c
git config core.hooksPath .githooks   # once per clone: strips AI co-author trailers from commits
cp MemState/.env.example MemState/.env   # then set GROQ_API_KEY (optional; MemState's own .gitignore keeps it out of git)
uv venv -p 3.12 .venv
uv pip install -p .venv -e 'MemState[embedding]' 'kuzu==0.11.3' 'ladybug==0.21.2' httpx pytest pytest-asyncio
scripts/run_memstate.sh [/abs/path/memstate.kuzu]   # default: fresh DB under .runtime/
```

The script serves on 127.0.0.1:8765 with `MEMSTATE_GROQ_MODEL=openai/gpt-oss-120b`, caches the embedding model in `.cache/fastembed`, passes the Groq key from `MemState/.env` as `MEMSTATE_GROQ_API_KEY` (with this pydantic-settings version, upstream's plain `GROQ_API_KEY` fallback is silently dropped), and refuses to start if MemState would fall back to hash embeddings. Kuzu is archived upstream (final release 0.11.3); this setup pins that version. `pip install -e` rewrites the tracked `MemState/src/memstate.egg-info/`; run `git -C MemState checkout -- src/memstate.egg-info` afterwards to keep the clone pristine.

`MemState/` is a git submodule pinned at `945d7c4`; `git submodule status` shows the pin and a `+` prefix if it ever drifts. The patched copy used by the demo lives in a `MemState-patched/` worktree of the submodule (git-ignored here) on branch `bitemporal`: three commits on `945d7c4` (port to LadybugDB, bitemporal field histories, merge by valid time), committed in this repo as `patches/0001-port-to-ladybugdb.patch`, `0002-bitemporal-field-histories.patch` and `0003-merge-by-valid-time.patch` (not yet built). Rebuild it with `git -C MemState worktree add -b bitemporal ../MemState-patched 945d7c4 && git -C MemState-patched am "$PWD"/patches/*.patch`. The patch runs on LadybugDB and upstream on Kuzu ([ADR 0006](docs/adr/0006-patch-on-ladybugdb-upstream-on-kuzu.md)); a database written by one engine cannot be opened by the other.

Local LLM (optional): Ollama 0.35.1 installed user-locally in `~/.local/ollama` (official Linux tarball, CUDA 13 backend; driver 580 / CUDA 13.0, RTX 3060 Laptop compute 8.6) serving `qwen3.5:2b` with a 16k context:

```bash
~/.local/ollama/bin/ollama pull qwen3.5:2b          # once
scripts/run_ollama.sh --bg                          # Ollama on :11434 + think-off proxy on :11435
kill "$(cat .logs/ollama.pid)" "$(cat .logs/ollama-proxy.pid)"   # stop
```

`qwen3.5:2b` thinks by default and MemState sends no `think` field; Ollama's Modelfile has no `think` parameter and the model ignores `/no_think`. `run_memstate.sh` therefore points `MEMSTATE_OLLAMA_BASE_URL` at `scripts/ollama_nothink_proxy.py`, which defaults `think` to false on `/api/chat` and `/api/generate` without modifying MemState. Set `MEMSTATE_OLLAMA_BASE_URL=http://127.0.0.1:11434` before `run_memstate.sh` to run with thinking on.

Kuzu holds an exclusive file lock on the database. If the project lives in a synced folder (OneDrive etc.), set `MEMSTATE_KUZU_PATH` to a path outside it. LLM chat is optional (Ollama locally, or Groq via `MEMSTATE_GROQ_API_KEY`; the upstream quickstart's plain `GROQ_API_KEY` is not picked up, see above). The conformance suite scores transitions through `/v1/ingest` and `/v1/query`; `GET`/`PATCH /api/ui/topics/{id}` serve only setup writes and state reads. Upstream commits a pre-populated `memstate.kuzu`, and the default `MEMSTATE_KUZU_PATH` is relative to the working directory. For a clean demo, point `MEMSTATE_KUZU_PATH` at a fresh absolute path.

## Demo

A GEM conformance suite checks MemState's stored state, not only its answers, against the guarantees the paper claims, beside a last-write-wins baseline; the contribution is a bitemporal extension of MemState's field histories on LadybugDB, with time probes measured before and after. The design (tests, verdict scale, baseline, extension, scorecard) lives in one place: [report §9](docs/report/gem-limitations-and-directions.md#9-demo-time-correct-governed-memory). Terms are defined in [`GLOSSARY.md`](GLOSSARY.md).

## Source

- Paper: <https://arxiv.org/abs/2605.26252>
- Code: <https://github.com/CoDS-GCS/MemState> (CoDS Lab, Concordia University)
