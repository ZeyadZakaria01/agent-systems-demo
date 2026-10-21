# Agent Memory Demo: Governed Evolving Memory on MemState

Review demo for *Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory* (Orogat & Mansour, arXiv:[2605.26252](https://arxiv.org/abs/2605.26252)). It runs a GEM conformance suite against the authors' proof-of-concept, [MemState](https://github.com/CoDS-GCS/MemState), checking its stored state against the paper's correctness conditions C1–C6.

## Status

Environment ready and live-verified (MemState, Groq, Ollama on CUDA; LadybugDB beside Kuzu). The demo design is decided: [report §9](docs/report/gem-limitations-and-directions.md#9-demo-time-correct-governed-memory), with the decisions behind it on the wayfinder map (`.scratch/interview-package/map.md`). The conformance suite (`.scratch/gem-conformance-suite/spec.md`) is built; its run of record is `demo/record/20261021-194912/` (seven systems, 3 ramp repeats, both chat cases, on the final patch commits; finding F41; `demo/record/20261021-085949/`, on the superseded commits, stays as findings F32–F35's evidence); see "Run the conformance suite". `scripts/probe_memstate.py` holds the probes behind findings F7–F12.

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
| `scripts/` | Start scripts for MemState and Ollama, the think-off proxy, and `probe_memstate.py` (HTTP probes for C3, salience, merge and a topic ramp; findings F7–F12) and `probe_chat_reference_time.py` (the chat `reference_time` against a running patched server; finding F28). |
| `demo/` | The GEM conformance suite: system adapters (`adapter.py` the interface, `memstate_system.py` MemState over HTTP, `baseline.py`), the verdict model, checks (`demo/checks/`, one module per condition, discovered by the runner), the runner and scorecard (`run.py`), the per-step patch runs (`steps.py`) and change table (`changes.py`), the chat runs (`chat_run.py` records and replays; `chat_recording.py` saves, loads and renders). `demo/results/` holds one directory per run (verdicts, snapshots, logs); git-ignored. `demo/record/<run id>/` holds the run of record (scorecard, `results.json`, snapshots), tracked. `demo/recordings/` holds the recorded chat runs; tracked. |
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

The patched copy used by the demo lives in a `MemState-patched/` worktree of the submodule (git-ignored here) on branch `bitemporal`: three commits on `945d7c4` (port to LadybugDB, bitemporal field histories, merge by valid time), committed in this repo as `patches/0001-port-to-ladybugdb.patch` (commit 1 changes only the `kuzu_adapter.py` import and the `pyproject.toml` dependency), `0002-bitemporal-field-histories.patch` (dated entries, valid-time and recorded-time reads, keep-and-copy, the chat reference time) and `0003-merge-by-valid-time.patch` (the Reasoner's merge interleaves both topics' histories by valid time, tags the dropped topic's entries `operation: "merged"` with `merged_from_topic_id`, skips archived duplicates, rescans after each merge and gives the survivor one "merged" event; the dropped topic's summary, events and salience are still lost). The runner refuses every patch step unless `945d7c4..bitemporal` holds exactly three commits. Rebuild it from the repo root, with `MemState/` initialised:

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

A GEM conformance suite checks MemState's stored state, not only its answers, against the guarantees the paper claims, beside a versioned-row baseline; the contribution is a bitemporal extension of MemState's field histories on LadybugDB, with time probes measured before and after. The design (tests, verdict scale, baseline, extension, scorecard) lives in one place: [report §9](docs/report/gem-limitations-and-directions.md#9-demo-time-correct-governed-memory). Terms are defined in [`GLOSSARY.md`](GLOSSARY.md).

MemState describes itself as a proof of concept, not a full implementation (its README). The scorecard therefore reads as a measurement of the published artifact against the paper's conditions: `fail` and `absent` mark gaps its authors state, not defects.

### Run the conformance suite

Recorded mode runs each check on a fresh database per system (a MemState server started by `scripts/run_memstate.sh` on a fresh absolute DB, stopped when the check ends; the baseline in-process) and writes `demo/results/<run id>/` with `results.json`, `scorecard.md`, one snapshot per (system, check) and the server logs. The runner starts a server on port 8765 and holds the machine-wide lock (`server.lock`, `demo/server_lock.py`) for the whole run whenever it starts a server, waiting if another run holds it; in-process-only runs take no lock. `scripts/run_memstate.sh` and `scripts/run_ollama.sh` started by hand hold it too, for as long as their servers live, and refuse to start if it is busy. The `flock` wrapper below is optional and harmless (the run uses the lock it inherits):

Run of record: `python -m demo.run ... --record` ends by copying `scorecard.md`, `results.json` and `snapshots/` from `demo/results/<run id>/` (git-ignored) into `demo/record/<run id>/`, which is tracked (`demo/record.py`; an existing record is never overwritten; `python -m demo.record <run dir>` copies a run already made). The scorecard's snapshot links are relative to the run folder, so they resolve inside the record. Databases stay in `.runtime/gem-suite/<run id>/`, and `results.json` (`servers`) cites their absolute paths; logs stay with the run. The same command runs MemState's 39 upstream tests (`demo/upstream_tests.py`) in `MemState/` for upstream (no bytecode, no pytest cache, so the folder is left unmodified) and, in `MemState-patched/` with the step checked out, the same 39 files by name at each step, and records passed, failed and total per system in `results.json` (`upstream_tests`) and in the scorecard's "MemState's 39 upstream tests" table; a step on which any fails is flagged.

The run of record, chats included, is one command: `flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --record --ramp-repeats 3 --chat`. After every system's checks it records both chat runs (`bad-merge` on upstream, `two-weeks` on step 3; "Chat runs and replay") in the same run folder: their snapshots are `snapshots/upstream/chat-bad-merge.json` and `snapshots/step3/chat-two-weeks.json` beside the suite's, so `--record` copies them with it, and each recording's `snapshot` field names the file inside `demo/record/<run id>/`. The recordings go to `demo/recordings/` (`--recordings DIR` changes it; tracked, commit them with the record) and the scorecard prints the two takes of this run. The scored case is the newest take run as the spec states it: a variant take (`--no-router-decides`, `--seed-profile`) is saved under `demo/recordings/attempts/` and never scored. The run owns every process it starts or finds: each MemState server stops when its check ends, and Ollama and the proxy are stopped when the chats end, also when they were already running (under the lock a running one is a leftover). A chat case that cannot be recorded is listed in `results.json` under `chat_errors`, printed on stderr, and makes the exit code 1; the suite's results are kept.

```bash
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C1
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(a)'            # merge existence (20 arranged repetitions), natural count
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(b),C2(c),C2(d),C3'   # atomicity, declarative policies, propagation
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C4               # history survival, empty writes, 501-write cap
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,step1,baseline --checks C5-1,C5-2 --ramp-repeats 1  # C5 mechanism, natural trajectory, latency ramps
.venv/bin/python -m demo.run --list    # checks and systems
.venv/bin/python -m pytest             # the suite's tests: baseline only, no server
```

Rows so far: `C1` (control), `C2(a)` (merge existence over 20 arranged repetitions, with the natural random-ID count beside it), `C2(b)` (a field referencing a missing topic) / `C2(c)` / `C2(d)` (the superseded read on the lapsed-override story) / `C3`, `C4` (history survival through update, merge and real forgetting, empty/`null` writes, 501-write cap; `demo/checks/c4_history.py`; the update path is the control), the two C5 rows `C5-1` / `C5-2` (`demo/checks/c5_topic_ramp.py`; mechanism and natural trajectory, one check each; `--checks C5-1,C5-2` prints the latency table at 100 / 250 / 500 / 1,000 / 2,000 as median (min–max) of ingest, query and settle time, with 5 plain reads per ramp, `--ramp-repeats` defaults to 1), the two C6 clauses `C6-1` / `C6-2` (`demo/checks/c6_retrieval_adaptation.py`; clause 2 ingests 500+ topics on its own fresh database to make the forgetting pass run, so it takes tens of seconds on a server), and time probes `T1`–`T6` (`--checks T1` runs all six; seven fresh DBs, about 20 s on upstream). `--systems` and `--checks` default to everything registered (`demo/systems.py`) and discovered (`demo/checks/`). The output is the scorecard (the claim column, each cell's verdict with its snapshot link, fails and absences counted separately), the staleness windows a check reported (each cites its run), the deviations table, and a block that pastes into `docs/findings.md` (command, DB path, key output). Smoke runs under `demo/results/` are not evidence of record. To add a check, drop a module in `demo/checks/` (see the docstring of `demo/checks/__init__.py`); to add a system, write a `System` subclass (`demo/client.py`) and register a `SystemSpec` in `demo/systems.py`; to add a scorecard column, add a `Column` in `demo/scorecard.py`.

Scorecard layout (`demo/scorecard.py`): one table in three groups, MemState (upstream, step 1, step 2, step 3) | Reference (the reference GEM, phase 1, phase 2) | Baseline (the versioned row), with a *claimed by [P1]?* column on every row (§4, §4.3). The probes of the proposed C1′ and C4′ (`Row(..., probe=True)`: T1–T6 with two cells each, C4′) are a separate section outside [P1]'s claims, followed by the case-level controls; the merge is printed as existence with the natural random-ID count beside it; MemState's limits are stated with their numbers; the change table has two chains (upstream → step 1 → step 2 → step 3; phase 1 → phase 2). The summary says "no regressions on the rows the suite checks" only when no row, and no case that held, is worse at step 3 than at step 1. A latency table from fewer than three repeats is labelled provisional and makes no "no measurable difference" claim. `results.json` carries `columns`, `rows` (with `claimed_by_p1`, `probe`), `counts` per system id and `change_tables` (`memstate`, `reference`).

Patch steps: `step1`, `step2`, `step3` are the commits of `bitemporal` above upstream (`git -C MemState-patched rev-list --reverse 945d7c4..bitemporal`, `demo/steps.py`). A step's `setup` checks its commit out detached in the shared `MemState-patched/` (refused if tracked files there are modified), its checks run on a `--patched` server on a fresh `.lbug`, and `teardown` returns to `bitemporal`, also after an error, as soon as that step's `setup` completed the checkout (also when HEAD was already at the step); a setup that refused (a dirty worktree, or one with a rebase, merge or cherry-pick in progress) leaves the worktree exactly as it was, and so does its teardown; the server's commit must equal the step's. Without `--systems` a run measures the steps that exist (a step that does not exist gives error verdicts naming the commit count). The scorecard has one column per step, and the per-step change table (`demo/changes.py`; also under `change_tables.memstate` in `results.json`) lists upstream, step 1, step 2 and step 3 per row, marking cells whose verdict differs from the nearest earlier real verdict of that row and naming the system compared with (step 1 against upstream, verdict for verdict). An `error` cell is shown unmarked and is never a baseline.


The reference GEM is registered twice, `reference-gem-p1` and `reference-gem-p2` (labels "reference GEM (phase 1)" / "(phase 2)"; `demo/systems.py`): in-process, a fresh instance per check, no server, so no lock is needed. It runs every check, the time probes and the storyline (`--systems reference-gem-p1,reference-gem-p2`). Its C5-2 ramps run once and time nothing (`describe()["latency_comparable"]` is False: in-process milliseconds are not comparable with an HTTP server): the verdict rests on the active and archived counts at n=2000, so it has no repeats, no latency rows and no ramp milliseconds in `results.json`, whatever `--ramp-repeats` says. That is this build's reading of ticket 19's "the reference GEM runs no ramps" (`docs/journal.md`). It has no chat run, and its over-flagging measurement (one hop and the transitive walk, `System.variant`) runs once, on phase 1. Its two windows, the merge revision window and the dependent-topic staleness window, are counted in interactions (an ingest or a query is one; reads of stored state are not) instead of seconds: both are 0 with revision after every ingest. `ReferenceGem(revise_after_ingest=False)` plus `revise()` exposes the pre-merge window.
### Live mode (watch it in the Graph Explorer)

Live mode drives a MemState server that is **already running**, so the Graph Explorer (`http://127.0.0.1:8765/ui/`) shows field histories growing and salience changing while the checks run. Start the server yourself on a fresh absolute DB (under the machine-wide lock when others share the machine), then:

```bash
flock ../agent-systems-demo-wt/server.lock bash scripts/run_memstate.sh /abs/fresh/path/memstate.kuzu   # terminal 1: you own this server
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
- A check reads `describe()["accepts"]`, one flag per date (`valid_from`, `invalid_at`, `valid_at`, `recorded_at`), never from a name. `MemStateSystem` reads each from the request models of `/openapi.json` (`request_date_fields`: a response model that merely returns `valid_from` does not count). A check reads a flag through `System.dates_accepted(*names)` or `source_accepted()`, which refuse when the schema could not be read. Each probe lists the dates it needs (`NEEDS` in `demo/checks/time_probes.py`) and has two cells: "accepts dates" (`measurements["accepts_dates"]`: yes, no or partly) and the verdict: `pass`, `fail` (the dates are accepted and an answer is wrong) or `absent` (a needed date is not accepted; the evidence is the schema reading and the answers given). A system that accepts a start date but no end date still gets dated writes for T1, T2, T3 and T6. A field read without `current` raises for a system that accepts any date; only undated systems fall back to the newest history entry. The stories and the story shift live in `demo/time_stories.py`.
- A check that raises, a server that dies or will not start, or a failing setup becomes `error` verdicts with whatever evidence could be captured; `results.json` is rewritten after every check (`"complete": false` until the end).
- The storyline (`demo/storyline.py`: events on the Website Redesign example, questions each labelled with a LongMemEval ability, a ground truth and the topic holding the answer) runs as the `Storyline` check (`--checks Storyline`). It is a measurement, not a scorecard row (`Row(..., on_scorecard=False)`): the output gains the triage counts (correct, search failures, memory failures), a per-question table and reinforcement precision beside C6 clause 1 (`demo/storyline_tables.py`). The human-reviewable draft is `.scratch/gem-conformance-suite/storyline-draft.md`, regenerated by `python -m demo.storyline_draft`.

### Chat runs and replay

A chat run asks storyline questions through MemState's own chat (`POST /api/llm/chat`, Ollama `qwen3.5:2b` through the think-off proxy, provider `ollama`; no `intent_override`, no Groq, no judge) and saves what happened as one JSON file in `demo/recordings/` (tracked: n = 1 evidence). Every turn holds the question, the ground truth, the answer, the route (intent, its source, the tools the model called), the latency, the state violation present, and an empty hand-grade slot a person fills in. The reference GEM has no LLM chat and gets none.

The **bad-merge** run (`demo/chat_run.py`): on upstream, the 29 storyline events go through `/v1`, then the user "re-explains" the project (the paper's Figure 1, "stored twice"): a second `Website Redesign` topic that holds only `Deadline = April 20`. The id order is arranged as in C2(a) (the merge keeps the lower id, F9; the deviations table lists the labelled setup `PATCH title`), so the merge keeps the re-explanation and drops the original, with its deadline history March 15 → April 20 and its "vendor delay" provenance. Q02 (deadline), Q06 (team) and Q11 (status) are then asked, one chat request each. The recording says per turn what the state lost on the question's own field.

The **two-weeks** run (`demo/chat_two_weeks.py`): on patch step 3 only (upstream's chat carries no date), two separate requests on a fresh database, each with `reference_time` (ticket 14): "I started my new job two weeks ago" at reference time Oct 6, then "How long have I been at my new job?" at Oct 20. The story is shifted so that its last day is the run day, as the time-probe stories are (a run on Oct 21 sends Oct 7 and Oct 21; the recording states the dates it used). The recording holds what the first turn wrote (each entry's value, `valid_from` and provenance) and the start date read from it (ground truth: two weeks before the first reference time, ± 1 day), and the second turn's answer (ground truth: four weeks), each with an empty hand-grade slot. Both routes are the router's, as the spec says; `--no-router-decides` forces W1 to the `ingest` route and `--seed-profile` writes one profile topic through `/v1` first, two variants whose takes sit in `demo/recordings/attempts/` (F31: the router sends W1 to `query`, and a 2B model rarely stores anything).

```bash
# record: starts MemState and Ollama with its proxy; stops them all at the end, also an Ollama that was already running (a leftover under the lock)
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.chat_run record bad-merge
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.chat_run record two-weeks   # checks step 3 out in MemState-patched/, then back on bitemporal
# replay: reads the JSON only; no server, no Ollama, no GPU (it imports neither httpx nor the server launcher)
.venv/bin/python -m demo.chat_run replay                                        # every recording in demo/recordings/
.venv/bin/python -m demo.chat_run replay demo/recordings/two-weeks-<run id>.json   # one file
```

Replay is the interview-day mode: it prints the recording as Markdown, each turn with its hand-grade slot (filled in by a person) and, once graded, Sonnet's grade beside it. `python -m demo.model_grade demo/recordings/<file>.json` runs that second grader (Claude Code CLI, `claude-sonnet-5-5`, in an empty folder with no tools); it sees the question, the ground truth and what the turn is graded on, never the match hints or the hand grade, and writes `model_grade` without touching `hand_grade` (`--force` grades again). The same recordings are printed as "Chat cases" in `scorecard.md` and carried in `results.json` under `chat_cases` (without the tool logs; the file keeps them) by every `python -m demo.run` (the newest recording of each case). Recording needs MemState's Python stack and the Ollama install of "Run MemState"; it refuses to run if `MEMSTATE_OLLAMA_BASE_URL` points past the proxy. `python -m demo.run --record --chat` records both cases inside the run of record (above); a variant take of the two-weeks case (`--no-router-decides`, `--seed-profile`) is saved under `attempts/` and is never the case the scorecard prints. A recording is one sample of a 2B model: a rerun can answer differently, which is why earlier takes, if kept, sit in `demo/recordings/attempts/` and `docs/journal.md` says how many were made.

Hand grading in a spreadsheet: `.venv/bin/python -m demo.grading_sheet export demo/chat-series/*/* --out demo/grading/hand-grading-sheet.csv` writes one row per turn (question, message, ground truth, stored entries, answer; no model grade or match hint, so Sonnet does not anchor you); fill `hand_grade` (`correct`, `partially correct`, `incorrect`) and `hand_note`, then `.venv/bin/python -m demo.grading_sheet import demo/grading/hand-grading-sheet.csv` checks every grade before writing `hand_grade` into the recordings and prints the agreement with Sonnet per case and turn and each disagreement. Blank rows are skipped.

Repeated takes live in `demo/chat-series/` (its README maps each folder to its model, reasoning setting, patch commit and finding). `scripts/chat_series.py` records them one take at a time and stops at the first error. Local models: `GEM_THINK=1` leaves the model's reasoning on (ADR 0003 turns it off for speed; with it on, `qwen3.5:4b` went from 1 to 10 of 10 correct start dates, F40). Hosted models (`--provider groq`): one MemState chat request is about 6.5k static tokens (system prompt and tool list) plus the turn, so a tier whose per-minute token limit is lower cannot run a single take; the script measures this and refuses before spending any quota (Groq's free tier caps chat models at 8,000 tokens per minute).

## Source

- Paper: <https://arxiv.org/abs/2605.26252>
- Code: <https://github.com/CoDS-GCS/MemState> (CoDS Lab, Concordia University)
