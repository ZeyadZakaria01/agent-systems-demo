# Agent Memory Demo: Governed Evolving Memory on MemState

Review demo for *Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory* (Orogat & Mansour, arXiv:[2605.26252](https://arxiv.org/abs/2605.26252)). It runs a GEM conformance suite against the authors' proof-of-concept, [MemState](https://github.com/CoDS-GCS/MemState), checking its stored state against the paper's correctness conditions C1–C6.

## Status

Environment ready and live-verified (MemState, Groq, Ollama on CUDA; LadybugDB beside Kuzu). The demo design is decided: [report §9](docs/report/gem-limitations-and-directions.md#9-demo-time-correct-governed-memory), with the decisions behind it on the wayfinder map (`.scratch/interview-package/map.md`). The conformance suite is being built from `.scratch/gem-conformance-suite/spec.md`: the `demo/` package runs check C1 in recorded mode on upstream MemState and on the baseline (see "Run the conformance suite"); `scripts/probe_memstate.py` holds the probes behind findings F7–F12.

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
| `demo/` | The GEM conformance suite: system adapters (`adapter.py` the interface, `memstate_system.py` MemState over HTTP, `baseline.py`), the verdict model, checks (`demo/checks/`, one module per condition, discovered by the runner), the runner and scorecard (`run.py`), the per-step patch runs (`steps.py`) and change table (`changes.py`). `demo/results/` holds one directory per run (verdicts, snapshots, logs); git-ignored. |
| `tests/` | The suite's own pytest: checks run in-process against the baseline, no server. |
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
scripts/run_memstate.sh [/abs/path/memstate.kuzu]   # upstream on Kuzu; default: .runtime/memstate-kuzu-<ts>/memstate.kuzu
scripts/run_memstate.sh --patched [/abs/path/memstate.lbug]   # patched copy on LadybugDB; default: .runtime/memstate-ladybug-<ts>/memstate.lbug
```

`--patched` puts `MemState-patched/src` (from the main checkout, also when run from a worktree) first on `PYTHONPATH`, ahead of the venv's editable install of `MemState/`. Both modes print the engine module (`kuzu` or `ladybug`) and the source folder before the server starts. A database written by one engine cannot be opened by the other.

The script serves on 127.0.0.1:8765 with `MEMSTATE_GROQ_MODEL=openai/gpt-oss-120b`, caches the embedding model in `.cache/fastembed`, passes the Groq key from `MemState/.env` as `MEMSTATE_GROQ_API_KEY` (with this pydantic-settings version, upstream's plain `GROQ_API_KEY` fallback is silently dropped), and refuses to start if MemState would fall back to hash embeddings. Kuzu is archived upstream (final release 0.11.3); this setup pins that version. `pip install -e` rewrites the tracked `MemState/src/memstate.egg-info/`; run `git -C MemState checkout -- src/memstate.egg-info` afterwards to keep the clone pristine.

`MemState/` is a git submodule pinned at `945d7c4`; `git submodule status` shows the pin and a `+` prefix if it ever drifts.

#### Patched copy

The patched copy used by the demo lives in a `MemState-patched/` worktree of the submodule (git-ignored here) on branch `bitemporal`: three commits on `945d7c4` (port to LadybugDB, bitemporal field histories, merge by valid time), committed in this repo as `patches/0001-port-to-ladybugdb.patch` (built; commit 1 changes only the `kuzu_adapter.py` import and the `pyproject.toml` dependency), `0002-bitemporal-field-histories.patch` and `0003-merge-by-valid-time.patch` (not yet built). Rebuild it from the repo root, with `MemState/` initialised:

```bash
git -C MemState worktree add -b bitemporal ../MemState-patched 945d7c4
git -C MemState-patched am "$PWD"/patches/*.patch
```

Recreating the worktree this way from `patches/` gave the same tree as `bitemporal`, and upstream's 39 tests pass unedited against the patched source (`docs/journal.md`): `cd MemState-patched && PYTHONPATH=$PWD/src ../.venv/bin/python -m pytest` (`PYTHONPATH` must precede the editable install, which points at `MemState/src`). The patch runs on LadybugDB and upstream on Kuzu ([ADR 0006](docs/adr/0006-patch-on-ladybugdb-upstream-on-kuzu.md)).

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

MemState describes itself as a proof of concept, not a full implementation (its README). The scorecard therefore reads as a measurement of the published artifact against the paper's conditions: `fail` and `absent` mark gaps its authors state, not defects.

### Run the conformance suite

Recorded mode runs each check on a fresh database per system (a MemState server started by `scripts/run_memstate.sh` on a fresh absolute DB, stopped when the check ends; the baseline in-process) and writes `demo/results/<run id>/` with `results.json`, `scorecard.md`, one snapshot per (system, check) and the server logs. The runner starts a server on port 8765 and does not take the machine-wide lock itself, so wrap it when other agents or servers share the machine:

```bash
flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C1
flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(a)'            # merge violation rate (20 repetitions)
flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(b),C2(c),C3'   # atomicity, declarative policies, propagation
flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C4               # history survival, empty writes, 501-write cap
flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,step1,baseline --checks C5-1,C5-2 --ramp-repeats 1  # C5 mechanism, natural trajectory, latency ramps
.venv/bin/python -m demo.run --list    # checks and systems
.venv/bin/python -m pytest             # the suite's tests: baseline only, no server
```

Rows so far: `C1` (control), `C2(a)` (merge violation rate, 20 repetitions), `C2(b)` / `C2(c)` / `C3`, `C4` (history survival, empty/`null` writes, 501-write cap; `demo/checks/c4_history.py`; the update path is the control), the two C5 rows `C5-1` / `C5-2` (`demo/checks/c5_topic_ramp.py`; mechanism and natural trajectory, one check each; `--checks C5-1,C5-2` prints the latency table at 100 / 250 / 500 / 1,000 / 2,000 as median (min–max) of ingest, query and settle time, with 5 plain reads per ramp, `--ramp-repeats` defaults to 1), the two C6 clauses `C6-1` / `C6-2` (`demo/checks/c6_retrieval_adaptation.py`; clause 2 ingests 500+ topics on its own fresh database to make the forgetting pass run, so it takes tens of seconds on a server), and time probes `T1`–`T6` (`--checks T1` runs all six; seven fresh DBs, about 20 s on upstream). `--systems` and `--checks` default to everything registered (`demo/systems.py`) and discovered (`demo/checks/`). The output is the scorecard (the claim column, each cell's verdict with its snapshot link, fails and absences counted separately), the staleness windows a check reported (each cites its run), the deviations table, and a block that pastes into `docs/findings.md` (command, DB path, key output). Smoke runs under `demo/results/` are not evidence of record. To add a check, drop a module in `demo/checks/` (see the docstring of `demo/checks/__init__.py`); to add a system, write a `System` subclass (`demo/client.py`) and register a `SystemSpec` in `demo/systems.py`; to add a scorecard column, add a `Column` in `demo/scorecard.py`.

Patch steps: `step1`, `step2`, `step3` are the commits of `bitemporal` above upstream (`git -C MemState-patched rev-list --reverse 945d7c4..bitemporal`, `demo/steps.py`). A step's `setup` checks its commit out detached in the shared `MemState-patched/` (refused if tracked files there are modified), its checks run on a `--patched` server on a fresh `.lbug`, and `teardown` returns to `bitemporal`, also after an error, as soon as that step's `setup` completed the checkout (also when HEAD was already at the step); a setup that refused (a dirty worktree, or one with a rebase, merge or cherry-pick in progress) leaves the worktree exactly as it was, and so does its teardown; the server's commit must equal the step's. Without `--systems` a run measures the steps that exist (a step that does not exist gives error verdicts naming the commit count). The scorecard's patch column shows the last step measured (a cell whose verdict comes from an earlier step is labelled `(from stepN)`), and the per-step change table (`demo/changes.py`; also under `change_table` in `results.json`) lists upstream, step 1, step 2 and step 3 per row, marking cells whose verdict differs from the nearest earlier real verdict of that row and naming the system compared with (step 1 against upstream, verdict for verdict). An `error` cell is shown unmarked and is never a baseline.

### Live mode (watch it in the Graph Explorer)

Live mode drives a MemState server that is **already running**, so the Graph Explorer (`http://127.0.0.1:8765/ui/`) shows field histories growing and salience changing while the checks run. Start the server yourself on a fresh absolute DB (under the machine-wide lock when others share the machine), then:

```bash
flock /home/zeyad/work/agent-systems-demo-wt/server.lock bash scripts/run_memstate.sh /abs/fresh/path/memstate.kuzu   # terminal 1: you own this server
.venv/bin/python -m demo.run --mode live --url http://127.0.0.1:8765 --delay 5                                       # terminal 2
.venv/bin/python -m demo.run --mode live --url http://127.0.0.1:8765 --step --checks C1                               # Enter after every step
```

- The runner never starts or stops a server and takes no lock. It refuses to run if nothing answers at `--url`.
- One database for the whole run. To keep the checks apart, every title a check writes gets ` [live <check> <HHMMSS>]` appended. The time keeps a second run against the same server from reusing the first run's titles (F14: a second run against the same DB made a topic with the same title; F9: upstream merges exact-title duplicates, so without the suffix [INFERENCE] checks would merge). Limits, both [INFERENCE] (not run): a check that forces a fixed topic id collides with another that forces the same id (the server would answer 500 and the verdict would be `error`), and an empty title is not rewritten.
- Pace: `--delay N` sleeps N seconds after every write or query (the topic badge in the Explorer is its salience; the topic detail shows the value timeline); `--step` waits for Enter instead (Ctrl-D runs on). State reads are not paced. The Explorer does not auto-refresh: press its refresh button after each step.
- `--checks` selects rows as in recorded mode; without it, every check discovered at that time runs. `--as upstream` (default) says which system the server is, for checks restricted by `systems=`; `--systems` is not accepted.
- Everything is labelled live: verdict system `live`, `results.json` has `"mode": "live"`, the scorecard file is `scorecard-live.md` headed "LIVE RUN - not a result of record", every printed line starts with `[LIVE]`. Output goes to `demo/results-live/<run id>/` (git-ignored), never to `demo/results/`; a results root inside the recorded one is refused. A live run never enters the scorecard of record.
- A live check sees a shared database, so checks that assume an empty one (counts of all topics, the 500-topic forgetting threshold) are not meaningful live; use recorded mode for evidence.

Smoke evidence (2026-10-20, upstream on a fresh DB, `--step` and `--delay`): screenshots of the Explorer are in [`docs/live-mode/`](docs/live-mode/): `step2-detail-after-version-field.png` (the `Deadline` timeline holds `April 20` current over `March 15`), `step1-detail-new-topic.png` against `step4-detail-after-second-query.png` (salience 1 → 1.2000000000000002 after two reads), `step1-new-topic.png` (overview right after the first write: badge 1 on the new topic) and `final-overview.png` (the new topic's badge is now 1.2 too). See `docs/findings.md` F14.

Extension points:

- A check needing several fresh databases (a story each, a ramp per repeat) uses `with ctx.fresh_system("tag") as s:`; each gets its own server (MemState) and snapshot, one at a time (opening a second while one is open raises `SystemBusy`, and `ctx.system` stays open until the check ends, so use one style per check). A row may be assembled from several of them (`Verdict.snapshots` lists every snapshot).
- A `SystemSpec` may carry `setup(run)` / `teardown(run)` hooks around all of that system's checks in a run (a patch step checks its commit out and returns to `bitemporal`); `teardown` runs after errors too, and a failing `setup` gives that system's checks error verdicts.
- Every adapter field has an explicit `current` (entry, or `None` for "no value"; `{"value": None}` is a written `null`). Read it with `demo.reads.current_value` (`NO_VALUE` vs `None`). A patch server must state `current` in its stored-topic fields, because its history is ordered by valid time and `history[0]` is only upstream's definition of current.
- A check reads capabilities from `system.describe()` (`keeps_history`), never from a missing key. `wait_until` returns `Waited(elapsed, timed_out)`.
- A check reads `describe()["accepts_valid_time"]` (dated writes and `valid_at` reads) and `describe()["accepts_recorded_at"]` (`recorded_at` reads), never from a name. `MemStateSystem` searches every schema in `/openapi.json` for those keys, so ticket 12 can flip T1–T4 and T6 before ticket 13 lands `recorded_at`. The flags are recorded in each time-probe row's `measurements`. The stories and the story shift live in `demo/time_stories.py`.
- A check that raises, a server that dies or will not start, or a failing setup becomes `error` verdicts with whatever evidence could be captured; `results.json` is rewritten after every check (`"complete": false` until the end).
- The storyline (`demo/storyline.py`: events on the Website Redesign example, questions each labelled with a LongMemEval ability, a ground truth and the topic holding the answer) runs as the `Storyline` check (`--checks Storyline`). It is a measurement, not a scorecard row (`Row(..., on_scorecard=False)`): the output gains the triage counts (correct, search failures, memory failures), a per-question table and reinforcement precision beside C6 clause 1 (`demo/storyline_tables.py`). The human-reviewable draft is `.scratch/gem-conformance-suite/storyline-draft.md`, regenerated by `python -m demo.storyline_draft`.

## Source

- Paper: <https://arxiv.org/abs/2605.26252>
- Code: <https://github.com/CoDS-GCS/MemState> (CoDS Lab, Concordia University)
