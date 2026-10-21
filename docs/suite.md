# Running MemState and the conformance suite

The operating manual: the environment, MemState and its patched copy, the suite's runner, live mode and the chat runs. The [README](../README.md) has the short version; terms are in [`GLOSSARY.md`](../GLOSSARY.md).

## Set up

The demo uses a root venv with real embeddings (fastembed):

```bash
git submodule update --init           # MemState/ pinned at upstream 945d7c4; MemTX/ (reference) at 4e1124c
git config core.hooksPath .githooks   # once per clone: commit-message and pre-commit guardrails
cp MemState/.env.example MemState/.env   # then set GROQ_API_KEY (optional; MemState's own .gitignore keeps it out of git)
uv venv -p 3.12 .venv
uv pip install -p .venv -e 'MemState[embedding]' 'kuzu==0.11.3' 'ladybug==0.21.2' httpx pytest pytest-asyncio ruff
```

`MemState/` is a git submodule pinned at `945d7c4`; `git submodule status` shows the pin and a `+` prefix if it ever drifts. `pip install -e` rewrites the tracked `MemState/src/memstate.egg-info/`; run `git -C MemState checkout -- src/memstate.egg-info` afterwards to keep the clone pristine.

## Run MemState

```bash
scripts/run_memstate.sh [/abs/path/memstate.kuzu]             # upstream on Kuzu; default: .runtime/memstate-kuzu-<ts>/memstate.kuzu
scripts/run_memstate.sh --patched [/abs/path/memstate.lbug]   # patched copy on LadybugDB; default: .runtime/memstate-ladybug-<ts>/memstate.lbug
```

| Resource | URL |
|---|---|
| Graph Explorer | <http://127.0.0.1:8765/ui/> |
| Interactive API docs | <http://127.0.0.1:8765/docs> |

The script serves on 127.0.0.1:8765 with `MEMSTATE_GROQ_MODEL=openai/gpt-oss-120b`, caches the embedding model in `.cache/fastembed`, passes the Groq key from `MemState/.env` as `MEMSTATE_GROQ_API_KEY` (with this pydantic-settings version, upstream's plain `GROQ_API_KEY` fallback is silently dropped), and refuses to start if MemState would fall back to hash embeddings. Kuzu is archived upstream (final release 0.11.3); this setup pins that version.

`--patched` puts `MemState-patched/src` (from the main checkout, also when run from a worktree) first on `PYTHONPATH`, ahead of the venv's editable install of `MemState/`. Both modes print the engine module (`kuzu` or `ladybug`) and the source folder before the server starts. A database written by one engine cannot be opened by the other.

Kuzu holds an exclusive file lock on the database. If the project lives in a synced folder (OneDrive etc.), set `MEMSTATE_KUZU_PATH` to a path outside it. Upstream commits a pre-populated `memstate.kuzu`, and the default `MEMSTATE_KUZU_PATH` is relative to the working directory: for a clean demo, point it at a fresh absolute path. The conformance suite scores transitions through `/v1/ingest` and `/v1/query`; `GET`/`PATCH /api/ui/topics/{id}` serve only setup writes and state reads.

Upstream's own quickstart (`MemState/docs/guides/quickstart.md`, Python 3.11+) is `cd MemState && pip install -e . && cp .env.example .env && python -m memstate.api.cli`.

### The patched copy

The patched copy lives in a `MemState-patched/` worktree of the submodule (git-ignored here) on branch `bitemporal`: three commits on `945d7c4`, committed in this repo as `patches/`:

| Patch | Step | Change |
|---|---|---|
| `0001-port-to-ladybugdb.patch` | 1 | only the `kuzu_adapter.py` import and the `pyproject.toml` dependency |
| `0002-bitemporal-field-histories.patch` | 2 | dated entries, valid-time and recorded-time reads, keep-and-copy, the chat reference time |
| `0003-merge-by-valid-time.patch` | 3 | the Reasoner's merge interleaves both topics' histories by valid time, tags the dropped topic's entries `operation: "merged"` with `merged_from_topic_id`, skips archived duplicates, rescans after each merge and gives the survivor one "merged" event; the dropped topic's summary, events and salience are still lost |

The runner refuses every patch step unless `945d7c4..bitemporal` holds exactly three commits. Rebuild it from the repo root, with `MemState/` initialised:

```bash
git -C MemState worktree add -b bitemporal ../MemState-patched 945d7c4
git -C MemState-patched am "$PWD"/patches/*.patch
```

Recreating the worktree this way from `patches/` gave the same tree as `bitemporal`, and upstream's 39 tests pass unedited against the patched source (`docs/journal.md`): `cd MemState-patched && PYTHONPATH=$PWD/src ../.venv/bin/python -m pytest` (`PYTHONPATH` must precede the editable install, which points at `MemState/src`). The patch runs on LadybugDB and upstream on Kuzu ([ADR 0006](adr/0006-patch-on-ladybugdb-upstream-on-kuzu.md)).

### Local LLM (optional)

Ollama 0.35.1 installed user-locally in `~/.local/ollama` (official Linux tarball, CUDA 13 backend; driver 580 / CUDA 13.0, RTX 3060 Laptop compute 8.6) serving `qwen3.5:2b` with a 16k context. LLM chat can also use Groq via `MEMSTATE_GROQ_API_KEY`.

```bash
~/.local/ollama/bin/ollama pull qwen3.5:2b          # once
scripts/run_ollama.sh --bg                          # Ollama on :11436 (a system Ollama may hold 11434) + think-off proxy on :11435
kill "$(cat .logs/ollama.pid)" "$(cat .logs/ollama-proxy.pid)"   # stop
```

`qwen3.5:2b` thinks by default and MemState sends no `think` field; Ollama's Modelfile has no `think` parameter and the model ignores `/no_think`. `run_memstate.sh` therefore points `MEMSTATE_OLLAMA_BASE_URL` at `scripts/ollama_nothink_proxy.py`, which defaults `think` to false on `/api/chat` and `/api/generate` without modifying MemState ([ADR 0003](adr/0003-thinking-off-via-proxy.md)). Set `MEMSTATE_OLLAMA_BASE_URL` to Ollama itself before `run_memstate.sh` to run with thinking on.

## Run the conformance suite

```bash
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C1
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(a)'            # merge existence (20 arranged repetitions), natural count
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(b),C2(c),C2(d),C3'   # atomicity, declarative policies, propagation
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C4               # history survival, empty writes, 501-write cap
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,step1,baseline --checks C5-1,C5-2 --ramp-repeats 1  # C5 mechanism, natural trajectory, latency ramps
.venv/bin/python -m demo.run --list    # checks and systems
.venv/bin/python -m pytest             # the suite's tests: in-process systems only, no server
```

Recorded mode runs each check on a fresh database per system (a MemState server started by `scripts/run_memstate.sh` on a fresh absolute DB, stopped when the check ends; the in-process systems need none) and writes `runs/results/<run id>/` with `results.json`, `scorecard.md`, one snapshot per (system, check) and the server logs. The runner starts a server on port 8765 and holds the machine-wide lock (`server.lock`, `demo/systems/server_lock.py`) for the whole run whenever it starts a server, waiting if another run holds it; in-process-only runs take no lock. `scripts/run_memstate.sh` and `scripts/run_ollama.sh` started by hand hold it too, for as long as their servers live, and refuse to start if it is busy. The `flock` wrapper above is optional and harmless (the run uses the lock it inherits).

### Rows and output

Rows: `C1` (control), `C2(a)` (merge existence over 20 arranged repetitions, with the natural random-ID count beside it), `C2(b)` (a field referencing a missing topic) / `C2(c)` / `C2(d)` (the superseded read on the lapsed-override story) / `C3`, `C4` (history survival through update, merge and real forgetting, empty/`null` writes, 501-write cap; `demo/checks/c4_history.py`; the update path is the control), the two C5 rows `C5-1` / `C5-2` (`demo/checks/c5_topic_ramp.py`; mechanism and natural trajectory, one check each; `--checks C5-1,C5-2` prints the latency table at 100 / 250 / 500 / 1,000 / 2,000 as median (min–max) of ingest, query and settle time, with 5 plain reads per ramp, `--ramp-repeats` defaults to 1), the two C6 clauses `C6-1` / `C6-2` (`demo/checks/c6_retrieval_adaptation.py`; clause 2 ingests 500+ topics on its own fresh database to make the forgetting pass run, so it takes tens of seconds on a server), and time probes `T1`–`T6` (`--checks T1` runs all six; seven fresh DBs, about 20 s on upstream).

`--systems` and `--checks` default to everything registered (`demo/systems/registry.py`) and discovered (`demo/checks/`). The output is the scorecard (the claim column, each cell's verdict with its snapshot link, fails and absences counted separately), the staleness windows a check reported (each cites its run), the deviations table, and a block that pastes into `docs/findings.md` (command, DB path, key output). Smoke runs under `runs/results/` are not evidence of record.

Scorecard layout (`demo/reporting/scorecard.py`): one table in three groups, MemState (upstream, step 1, step 2, step 3) | Reference (the reference GEM, phase 1, phase 2) | Baseline (the versioned row), with a *claimed by [P1]?* column on every row (§4, §4.3). The probes of the proposed C1′ and C4′ (`Row(..., probe=True)`: T1–T6 with two cells each, C4′) are a separate section outside [P1]'s claims, followed by the case-level controls; the merge is printed as existence with the natural random-ID count beside it; MemState's limits are stated with their numbers; the change table has two chains (upstream → step 1 → step 2 → step 3; phase 1 → phase 2). The summary says "no regressions on the rows the suite checks" only when no row, and no case that held, is worse at step 3 than at step 1. A latency table from fewer than three repeats is labelled provisional and makes no "no measurable difference" claim. `results.json` carries `columns`, `rows` (with `claimed_by_p1`, `probe`), `counts` per system id and `change_tables` (`memstate`, `reference`).

### Run of record

The run of record, chats included, is one command:

```bash
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --record --ramp-repeats 3 --chat
```

`--record` ends the run by copying `scorecard.md`, `results.json` and `snapshots/` from `runs/results/<run id>/` (git-ignored) into `runs/record/<run id>/`, which is tracked (`demo/reporting/record.py`; an existing record is never overwritten; `python -m demo.reporting.record <run dir>` copies a run already made). The scorecard's snapshot links are relative to the run folder, so they resolve inside the record. Databases stay in `.runtime/gem-suite/<run id>/`, and `results.json` (`servers`) cites their absolute paths; logs stay with the run.

The same command runs MemState's 39 upstream tests (`demo/systems/upstream_tests.py`) in `MemState/` for upstream (no bytecode, no pytest cache, so the folder is left unmodified) and, in `MemState-patched/` with the step checked out, the same 39 files by name at each step, and records passed, failed and total per system in `results.json` (`upstream_tests`) and in the scorecard's "MemState's 39 upstream tests" table; a step on which any fails is flagged.

`--chat` records both chat runs after every system's checks (`bad-merge` on upstream, `two-weeks` on step 3; see [Chat runs and replay](#chat-runs-and-replay)) in the same run folder: their snapshots are `snapshots/upstream/chat-bad-merge.json` and `snapshots/step3/chat-two-weeks.json` beside the suite's, so `--record` copies them with it, and each recording's `snapshot` field names the file inside `runs/record/<run id>/`. The recordings go to `runs/recordings/` (`--recordings DIR` changes it; tracked, commit them with the record) and the scorecard prints the two takes of this run. The scored case is the newest take run as the spec states it: a variant take (`--no-router-decides`, `--seed-profile`) is saved under `runs/recordings/attempts/` and never scored. The run owns every process it starts or finds: each MemState server stops when its check ends, and Ollama and the proxy are stopped when the chats end, also when they were already running (under the lock a running one is a leftover). A chat case that cannot be recorded is listed in `results.json` under `chat_errors`, printed on stderr, and makes the exit code 1; the suite's results are kept.

### Patch steps

`step1`, `step2`, `step3` are the commits of `bitemporal` above upstream (`git -C MemState-patched rev-list --reverse 945d7c4..bitemporal`, `demo/systems/steps.py`). A step's `setup` checks its commit out detached in the shared `MemState-patched/` (refused if tracked files there are modified), its checks run on a `--patched` server on a fresh `.lbug`, and `teardown` returns to `bitemporal`, also after an error, as soon as that step's `setup` completed the checkout (also when HEAD was already at the step); a setup that refused (a dirty worktree, or one with a rebase, merge or cherry-pick in progress) leaves the worktree exactly as it was, and so does its teardown; the server's commit must equal the step's. Without `--systems` a run measures the steps that exist (a step that does not exist gives error verdicts naming the commit count).

The scorecard has one column per step, and the per-step change table (`demo/reporting/changes.py`; also under `change_tables.memstate` in `results.json`) lists upstream, step 1, step 2 and step 3 per row, marking cells whose verdict differs from the nearest earlier real verdict of that row and naming the system compared with (step 1 against upstream, verdict for verdict). An `error` cell is shown unmarked and is never a baseline.

### The reference GEM

Registered twice, `reference-gem-p1` and `reference-gem-p2` (labels "reference GEM (phase 1)" / "(phase 2)"; `demo/systems/registry.py`): in-process, a fresh instance per check, no server, so no lock is needed. It runs every check, the time probes and the storyline (`--systems reference-gem-p1,reference-gem-p2`). Its C5-2 ramps run once and time nothing (`describe()["latency_comparable"]` is False: in-process milliseconds are not comparable with an HTTP server): the verdict rests on the active and archived counts at n=2000, so it has no repeats, no latency rows and no ramp milliseconds in `results.json`, whatever `--ramp-repeats` says. That is this build's reading of ticket 19's "the reference GEM runs no ramps" (`docs/journal.md`). It has no chat run, and its over-flagging measurement (one hop and the transitive walk, `System.variant`) runs once, on phase 1. Its two windows, the merge revision window and the dependent-topic staleness window, are counted in interactions (an ingest or a query is one; reads of stored state are not) instead of seconds: both are 0 with revision after every ingest. `ReferenceGem(revise_after_ingest=False)` plus `revise()` exposes the pre-merge window.

### Extension points

- To add a check, drop a module in `demo/checks/` (see the docstring of `demo/checks/__init__.py`); to add a system, write a `System` subclass (`demo/systems/adapter.py`) and register a `SystemSpec` in `demo/systems/registry.py`; to add a scorecard column, add a `Column` in `demo/reporting/scorecard.py`.
- A check needing several fresh databases (a story each, a ramp per repeat) uses `with ctx.fresh_system("tag") as s:`; each gets its own server (MemState) and snapshot, one at a time (opening a second while one is open raises `SystemBusy`, and `ctx.system` stays open until the check ends, so use one style per check). A row may be assembled from several of them (`Verdict.snapshots` lists every snapshot).
- A `SystemSpec` may carry `setup(run)` / `teardown(run)` hooks around all of that system's checks in a run (a patch step checks its commit out and returns to `bitemporal`); `teardown` runs after errors too, and a failing `setup` gives that system's checks error verdicts.
- Every adapter field has an explicit `current` (entry, or `None` for "no value"; `{"value": None}` is a written `null`). Read it with `demo.systems.reads.current_value` (`NO_VALUE` vs `None`). A patch server must state `current` in its stored-topic fields, because its history is ordered by valid time and `history[0]` is only upstream's definition of current.
- A check reads capabilities from `system.describe()` (`keeps_history`), never from a missing key. `wait_until` returns `Waited(elapsed, timed_out)`.
- A check reads `describe()["accepts"]`, one flag per date (`valid_from`, `invalid_at`, `valid_at`, `recorded_at`), never from a name. `MemStateSystem` reads each from the request models of `/openapi.json` (`request_date_fields`: a response model that merely returns `valid_from` does not count). A check reads a flag through `System.dates_accepted(*names)` or `source_accepted()`, which refuse when the schema could not be read. Each probe lists the dates it needs (`NEEDS` in `demo/checks/time_probes.py`) and has two cells: "accepts dates" (`measurements["accepts_dates"]`: yes, no or partly) and the verdict: `pass`, `fail` (the dates are accepted and an answer is wrong) or `absent` (a needed date is not accepted; the evidence is the schema reading and the answers given). A system that accepts a start date but no end date still gets dated writes for T1, T2, T3 and T6. A field read without `current` raises for a system that accepts any date; only undated systems fall back to the newest history entry. The stories and the story shift live in `demo/workloads/time_stories.py`.
- A check that raises, a server that dies or will not start, or a failing setup becomes `error` verdicts with whatever evidence could be captured; `results.json` is rewritten after every check (`"complete": false` until the end).
- The storyline (`demo/workloads/storyline.py`: events on the Website Redesign example, questions each labelled with a LongMemEval ability, a ground truth and the topic holding the answer) runs as the `Storyline` check (`--checks Storyline`). It is a measurement, not a scorecard row (`Row(..., on_scorecard=False)`): the output gains the triage counts (correct, search failures, memory failures), a per-question table and reinforcement precision beside C6 clause 1 (`demo/reporting/storyline.py`). The human-reviewable draft is `.scratch/gem-conformance-suite/storyline-draft.md`, regenerated by `python -m demo.reporting.storyline_draft`.

## Live mode

Live mode drives a MemState server that is **already running**, so the Graph Explorer (`http://127.0.0.1:8765/ui/`) shows field histories growing and salience changing while the checks run. Start the server yourself on a fresh absolute DB (under the machine-wide lock when others share the machine), then:

```bash
flock ../agent-systems-demo-wt/server.lock bash scripts/run_memstate.sh /abs/fresh/path/memstate.kuzu   # terminal 1: you own this server
.venv/bin/python -m demo.run --mode live --url http://127.0.0.1:8765 --delay 5                         # terminal 2
.venv/bin/python -m demo.run --mode live --url http://127.0.0.1:8765 --step --checks C1                 # Enter after every step
```

- The runner never starts or stops a server and takes no lock. It refuses to run if nothing answers at `--url`.
- One database for the whole run. To keep the checks apart, every title a check writes gets ` [live <check> <HHMMSS>]` appended. The time keeps a second run against the same server from reusing the first run's titles (F14: a second run against the same DB made a topic with the same title; F9: upstream merges exact-title duplicates, so without the suffix [INFERENCE] checks would merge). Limits, both [INFERENCE] (not run): a check that forces a fixed topic id collides with another that forces the same id (the server would answer 500 and the verdict would be `error`), and an empty title is not rewritten.
- Pace: `--delay N` sleeps N seconds after every write or query (the topic badge in the Explorer is its salience; the topic detail shows the value timeline); `--step` waits for Enter instead (Ctrl-D runs on). State reads are not paced. The Explorer does not auto-refresh: press its refresh button after each step.
- `--checks` selects rows as in recorded mode; without it, every check discovered at that time runs. `--as upstream` (default) says which system the server is, for checks restricted by `systems=`; `--systems` is not accepted.
- Everything is labelled live: verdict system `live`, `results.json` has `"mode": "live"`, the scorecard file is `scorecard-live.md` headed "LIVE RUN - not a result of record", every printed line starts with `[LIVE]`. Output goes to `runs/results-live/<run id>/` (git-ignored), never to `runs/results/`; a results root inside the recorded one is refused. A live run never enters the scorecard of record.
- A live check sees a shared database, so checks that assume an empty one (counts of all topics, the 500-topic forgetting threshold) are not meaningful live; use recorded mode for evidence.

Smoke evidence (2026-10-20, upstream on a fresh DB, `--step` and `--delay`): screenshots of the Explorer are in [`docs/live-mode/`](live-mode/): `step2-detail-after-version-field.png` (the `Deadline` timeline holds `April 20` current over `March 15`), `step1-detail-new-topic.png` against `step4-detail-after-second-query.png` (salience 1 → 1.2000000000000002 after two reads), `step1-new-topic.png` (overview right after the first write: badge 1 on the new topic) and `final-overview.png` (the new topic's badge is now 1.2 too). See `docs/findings.md` F14.

## Chat runs and replay

A chat run asks storyline questions through MemState's own chat (`POST /api/llm/chat`, Ollama `qwen3.5:2b` through the think-off proxy, provider `ollama`; no `intent_override`, no Groq, no judge) and saves what happened as one JSON file in `runs/recordings/` (tracked: n = 1 evidence). Every turn holds the question, the ground truth, the answer, the route (intent, its source, the tools the model called), the latency, the state violation present, and Sonnet's grade and a blind reviewer's grade (`demo/chat/model_grade.py`, `demo/chat/review_grade.py`) once they are applied. The reference GEM has no LLM chat and gets none.

The **bad-merge** run (`demo/chat/run.py`): on upstream, the 29 storyline events go through `/v1`, then the user "re-explains" the project (the paper's Figure 1, "stored twice"): a second `Website Redesign` topic that holds only `Deadline = April 20`. The id order is arranged as in C2(a) (the merge keeps the lower id, F9; the deviations table lists the labelled setup `PATCH title`), so the merge keeps the re-explanation and drops the original, with its deadline history March 15 → April 20 and its "vendor delay" provenance. Q02 (deadline), Q06 (team) and Q11 (status) are then asked, one chat request each. The recording says per turn what the state lost on the question's own field.

The **two-weeks** run (`demo/chat/two_weeks.py`): on patch step 3 only (upstream's chat carries no date), two separate requests on a fresh database, each with `reference_time` (ticket 14): "I started my new job two weeks ago" at reference time Oct 6, then "How long have I been at my new job?" at Oct 20. The story is shifted so that its last day is the run day, as the time-probe stories are (a run on Oct 21 sends Oct 7 and Oct 21; the recording states the dates it used). The recording holds what the first turn wrote (each entry's value, `valid_from` and provenance) and the start date read from it (ground truth: two weeks before the first reference time, ± 1 day), and the second turn's answer (ground truth: four weeks), each graded by Sonnet and a blind reviewer. Both routes are the router's, as the spec says; `--no-router-decides` forces W1 to the `ingest` route and `--seed-profile` writes one profile topic through `/v1` first, two variants whose takes sit in `runs/recordings/attempts/` (F31: the router sends W1 to `query`, and a 2B model rarely stores anything).

```bash
# record: starts MemState and Ollama with its proxy; stops them all at the end, also an Ollama that was already running (a leftover under the lock)
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.chat.run record bad-merge
flock ../agent-systems-demo-wt/server.lock .venv/bin/python -m demo.chat.run record two-weeks   # checks step 3 out in MemState-patched/, then back on bitemporal
# replay: reads the JSON only; no server, no Ollama, no GPU (it imports neither httpx nor the server launcher)
.venv/bin/python -m demo.chat.run replay                                           # every recording in runs/recordings/
.venv/bin/python -m demo.chat.run replay runs/recordings/two-weeks-<run id>.json   # one file
```

Replay is the interview-day mode: it prints the recording as Markdown, each turn with, once graded, Sonnet's grade and the blind reviewer's grade. The same recordings are printed as "Chat cases" in `scorecard.md` and carried in `results.json` under `chat_cases` (without the tool logs; the file keeps them) by every `python -m demo.run` (the newest recording of each case). Recording needs MemState's Python stack and the Ollama install above; it refuses to run if `MEMSTATE_OLLAMA_BASE_URL` points past the proxy. `python -m demo.run --record --chat` records both cases inside the run of record; a variant take of the two-weeks case (`--no-router-decides`, `--seed-profile`) is saved under `attempts/` and is never the case the scorecard prints. A recording is one sample of a 2B model: a rerun can answer differently, which is why earlier takes, if kept, sit in `runs/recordings/attempts/` and `docs/journal.md` says how many were made.

### Grading

- **Sonnet**: `python -m demo.chat.model_grade runs/recordings/<file>.json` (Claude Code CLI, `claude-sonnet-5-5`, in an empty folder with no tools); it sees the question, the ground truth and what the turn is graded on, never the match hints or the reviewer's grade, and writes `model_grade` without touching `reviewer_grade` (`--force` grades again).
- **Blind review**: a second grader, an AI agent that sees only what Sonnet's prompt shows, never a model grade or match hint. `.venv/bin/python -m demo.chat.review_grade export runs/chat-series/*/* --out /tmp/review-items.json` writes one item per turn (`id`, `case`, `question`, `prompt`); the reviewer returns `[{"id", "grade", "note"}]` (`correct`, `partially correct`, `incorrect`); `.venv/bin/python -m demo.chat.review_grade apply graded.json --grader NAME` checks every grade and id before writing `reviewer_grade` into the recordings (`--force` overwrites an existing one); `.venv/bin/python -m demo.chat.review_grade agreement runs/chat-series/*/*` prints both graders' counts, the agreement with Sonnet per case and turn, and each disagreement. No one grades by hand (dropped by the user, 2026-10-21).

### Chat series

Repeated takes live in `runs/chat-series/` (its README maps each folder to its model, reasoning setting, patch commit and finding). `scripts/chat_series.py` records them one take at a time and stops at the first error. Local models: `GEM_THINK=1` leaves the model's reasoning on (ADR 0003 turns it off for speed; with it on, `qwen3.5:4b` went from 1 to 10 of 10 correct start dates, F40). Hosted models (`--provider groq`): one MemState chat request is about 6.5k static tokens (system prompt and tool list) plus the turn, so a tier whose per-minute token limit is lower cannot run a single take; the script measures this and refuses before spending any quota (Groq's free tier caps chat models at 8,000 tokens per minute).
