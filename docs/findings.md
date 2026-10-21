# Findings: MemState behaviour proven by runs

Each entry is a fact about upstream MemState (`945d7c4`, unmodified) backed by a run on a fresh database. Claims from reading code alone stay in [`papers/2605.26252v1-alignment.md`](papers/2605.26252v1-alignment.md) until a run reproduces them.

Environment for all runs: root `.venv`, `kuzu==0.11.3`, fastembed MiniLM, `scripts/run_memstate.sh <fresh absolute DB>`; see the README "Run MemState".

## F1. Default read returns the newest value; temporal read returns the full history (C1 holds on `/v1`)

Run: `/v1/ingest` `new_topic` "Website Redesign" with `Deadline="March 15"` (provenance `kickoff-notes`), then `version_field` `Deadline="April 20"` (provenance `pm-email`, why `vendor delay`); `/v1/query` with `stages=[semantic, temporal]`, `explain=true`. DBs `/tmp/ms_live/`, `/tmp/main-smoke/`.

Observed: current `April 20`; history `[(April 20, pm-email, vendor delay), (March 15, kickoff-notes)]` with `valid_from` timestamps. Default query (no temporal stage) returns only the current value.

## F2. Every `/v1/query` raises the salience of every returned topic by 0.1

Run: three `/v1/query` calls on "Marathon Training", then `GET /api/ui/topics/{id}`. DB `/tmp/ms_live/`.

Observed: salience 1.30 → 1.60; `topic_history` holds one `{"kind": "salience", "reason": "query_bump"}` event per step (1.0→1.1 … 1.5→1.6). The topic was already at 1.30 because earlier semantic queries returned it as a lower-ranked candidate: the bump applies to every returned candidate, not only the best match.

## F3. The upstream quickstart's `GROQ_API_KEY` is ignored; Groq chat returns 503

Run: server started with `GROQ_API_KEY` set; `POST /api/llm/chat` with `provider: "groq"`.

Observed: `503 Groq is not configured. Set GROQ_API_KEY in .env`. `Settings().groq_api_key` is empty with `GROQ_API_KEY` and set with `MEMSTATE_GROQ_API_KEY`; pydantic-settings warns *"A custom validator is returning a value other than `self`"*. Versions: pydantic 2.13.5, pydantic-settings 2.15.0. Cause in code: `config.py`'s `model_validator` returns `model_copy(...)`, which pydantic-settings discards.

## F4. MemState's Ollama client lets thinking models think on every round

Run: `POST /api/llm/chat` with `provider: "ollama"`, `model: "qwen3.5:2b"`, question "What is the deadline of the Website Redesign project?", direct to Ollama vs through `scripts/ollama_nothink_proxy.py`.

Observed: 19.2 s with thinking (MemState sends no `think` field; `qwen3.5:2b` defaults to thinking on) vs 3.8 s and 1.7 s with thinking off. All three answers correct ("April 20").

## F5. Semantic retrieval separates paraphrases with real embeddings

Run: three topics (Sourdough, Kubernetes upgrade, Marathon Training) queried with paraphrases sharing almost no words. DB `/tmp/ms_live/`.

Observed: each paraphrase ranks its own topic first: 0.433 vs next 0.051; 0.524 vs 0.203; 0.533 vs 0.064.

## F6. Upstream test suite passes on the pinned stack

Run: `cd MemState && MEMSTATE_KUZU_PATH=/tmp/ms_pytest/t.kuzu ../.venv/bin/python -m pytest -q -p no:cacheprovider`.

Observed: `39 passed`. The suite covers field history, topic fields, Study ingest, chunking, visualization hints and system context; none targets revise, forget, the Reasoner, salience or edges.

## F7. An update does not reach a topic linked by an `extension` edge, before or after revision (C3 absent)

Run (2026-10-20): `scripts/run_memstate.sh .runtime/probes-20261020/kuzu-c3/memstate.kuzu`, then `.venv/bin/python scripts/probe_memstate.py c3`. Two pairs: B → A, and A → B (edge added by `extend_topic`), each with A `Deadline="March 15"`, B `Date="March 20"`, kind `extension`. A updated by `version_field` to `April 20`; B read through `/v1/query` (`topic_ids=[B]`, structural + temporal) right after the update and again after a 2 s wait for the background Reasoner.

Observed, both directions: A current `April 20`; B `Date` `March 20` right after the update and after the wait, history `["March 20"]`; B's `topic_history` holds only `created` and `salience` events (no revision entry); B's record has no flag field (keys: archived, created_at, failed_salience, fields, id, salience, summary, title, topic_history, topic_kind, updated_at). The `/v1/query` neighbour list gives `{id, title}` only, without the edge kind; `/api/ui/graph` does show `kind: "extension"`. The Reasoner's revise step only merges same-title topics (`executor.py:345-350`) [INFERENCE, code reading].

## F8. Every returned candidate gets the query bump, including unrelated topics

Run (2026-10-20): `.venv/bin/python scripts/probe_memstate.py salience` on a fresh DB (`.runtime/probes-20261020/kuzu-salience/`). Five topics (Marathon Training, Sourdough, Garden, Kubernetes upgrade, Tax return), one `/v1/query` "how far is my weekend running session" (semantic, `top_k=8`).

Observed: all five returned, similarities 0.336, 0.116, 0.106, 0.052, 0.041; every one went from salience 1.0 to 1.1. Retrieval returns the top `k` regardless of similarity, so with real (MiniLM) embeddings unrelated topics are reinforced. Extends F2.

## F9. Merging duplicate titles keeps the lower topic ID and drops the other topic's value

Run (2026-10-20): `.venv/bin/python scripts/probe_memstate.py merge` (20 repeats, distinct titles, server-assigned UUIDs) on `.runtime/probes-20261020/kuzu-merge/`. Per repeat: `new_topic` "Vendor Contract <x>" `Deadline="March 15"`, then a second `new_topic` with the same title and `Deadline="April 20"`; state read after the Reasoner's merge.

Observed: always merged (0/20 unmerged); the surviving topic is the one with the lexicographically lower ID in 20/20; the stale `March 15` is current in 10/20; the survivor's `Deadline` history holds only its own value in 20/20 (the dropped topic's value is gone); the dropped topic is deleted (`GET /api/ui/topics/{id}` → 404).

## F10. Nothing is archived at 2,000 topics; query latency grows with topic count

Run (2026-10-20): `.venv/bin/python scripts/probe_memstate.py ramp` on `.runtime/probes-20261020/kuzu-ramp/`: 2,000 `new_topic` ingests (two fields each, distinct titles), 20 semantic queries per step, single run.

Observed:

| Topics | Archived | `/v1/query` median (p95) | `/v1/ingest` median, last 50 |
|---|---|---|---|
| 100 | 0 | 145.0 ms (150.4) | 45.9 ms |
| 250 | 0 | 159.5 ms (164.8) | 46.3 ms |
| 500 | 0 | 203.1 ms (208.1) | 47.6 ms |
| 1,000 | 0 | 258.7 ms (269.4) | 68.3 ms |
| 2,000 | 0 | 381.5 ms (409.1) | 94.2 ms |

Salience of the first 200 topics ranged 1.0–2.1 (query bumps only); nothing fell below the 0.05 forget threshold, so the forget scan, running at every ingest from 500 topics on, never archived anything.

## F11. MemState runs on LadybugDB with a one-line change; verdicts match Kuzu

Not upstream: a scratch worktree of the submodule at `945d7c4` (`.runtime/ms-ladybug/`) with `import kuzu` → `import ladybug as kuzu` in `src/memstate/store/kuzu_adapter.py`; `ladybug==0.21.2` installed in the root venv beside `kuzu==0.11.3` (no dependency changes). Server: `PYTHONPATH=$PWD/.runtime/ms-ladybug/src scripts/run_memstate.sh <fresh DB>`; the process maps `ladybug/_lbug.cpython-312-x86_64-linux-gnu.so` and no Kuzu library.

Tests (2026-10-20): `cd .runtime/ms-ladybug && MEMSTATE_KUZU_PATH=/tmp/ms_pytest_lb/t.kuzu PYTHONPATH=$PWD/src ../../.venv/bin/python -m pytest -q -p no:cacheprovider` → `39 passed in 11.51s`; same day on Kuzu (F6 command) → `39 passed in 2.84s`.

Probes on fresh DBs `.runtime/probes-20261020/lbug-{c3,salience,merge,ramp}/`: C3 identical to F7; salience identical to F8 (same similarities, every candidate 1.0 → 1.1); merge: lower ID survives 20/20, stale current 8/20, dropped value lost 20/20; ramp: 0 archived at every step, salience 1.0–2.1.

| Topics | `/v1/query` median, Kuzu | `/v1/query` median, LadybugDB | `/v1/ingest` median, Kuzu | `/v1/ingest` median, LadybugDB |
|---|---|---|---|---|
| 100 | 145.0 ms | 80.8 ms | 45.9 ms | 28.0 ms |
| 250 | 159.5 ms | 105.1 ms | 46.3 ms | 28.1 ms |
| 500 | 203.1 ms | 166.0 ms | 47.6 ms | 29.5 ms |
| 1,000 | 258.7 ms | 211.4 ms | 68.3 ms | 57.1 ms |
| 2,000 | 381.5 ms | 340.1 ms | 94.2 ms | 82.1 ms |

Single run per engine, run back to back on the same laptop.

## F12. LadybugDB and Kuzu database files are not interchangeable; `ladybug.__version__` fails without the C-API library

Run (2026-10-20): copy of the F7 Kuzu DB opened with `ladybug.Database(...)` → `RuntimeError: Unable to open database. The file is not a valid Lbug database file!`. Separately, `import ladybug; ladybug.__version__` raises `RuntimeError: Could not find lbug C API shared library` (the wheel ships only the pybind extension `_lbug`; the version getter goes through the C API), and the interpreter exits with code 139. `Database`/`Connection` use the pybind extension and work; MemState never reads the version.

## F13. The conformance suite's C1 control passes on upstream and on the baseline

Run (2026-10-20): `flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems upstream,baseline --checks C1` (recorded mode; the run's `results.json` records `command: "python -m demo.run --systems upstream,baseline --checks C1"` because the run predates the refactor that added the `complete` key and the lock/path prefix to the recorded command; upstream `945d7c4`, Kuzu 0.11.3 per ADR 0004, engine line `MemState engine module: kuzu`). DB: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-095720/upstream-c1/memstate.kuzu`. `demo/results/20261020-095720/` is git-ignored and not in the repo, so its key output is quoted here: verdicts `upstream C1 pass`, `baseline C1 pass`; upstream case `default read returns only April 20` held (`current='April 20', values returned=['April 20']`) and `temporal read returns the full history` held (`history newest first=['April 20', 'March 15']`); the baseline's history case is `held=None` (not applicable). The server was stopped by the runner and port 8765 was free afterwards (`port_free_after_stop: true`). Run of record: ticket 19.

Observed (reads are `/v1/query` with `stages=["temporal"]`, `topic_ids=[id]`; [INFERENCE] that no similarity is involved, from reading the stage handling, not from a run): after `new_topic` "Website Redesign" `Deadline="March 15"` and `version_field` `Deadline="April 20"`, the default read returned `current='April 20'` and values `['April 20']`; the read with `explain=true` returned history newest first `['April 20', 'March 15']`. Verdict: C1 **pass** on upstream. The baseline (last-write-wins row) also passes C1, on one case only: default read `April 20`; its temporal read has no history (nothing-value), so that case is `held=None` (the cell shows `(1 case n/a)`) and the baseline's lost `March 15` is left to C4.

## F14. Live mode against a running upstream server: the Graph Explorer shows a field history growing and salience changing

Run (2026-10-20): server started by hand under the lock, `flock /home/zeyad/work/agent-systems-demo-wt/server.lock` over `scripts/run_memstate.sh /home/zeyad/work/agent-systems-demo/.runtime/gs16-live-20261020-101318/memstate.kuzu` (upstream `945d7c4`, engine `kuzu`); then `.venv/bin/python -m demo.run --mode live --url http://127.0.0.1:8765 --step --checks C1` with Enter sent after each screenshot (earlier runs with `--delay 12`/`15` on the same DB). Browser: `http://127.0.0.1:8765/ui/`, refresh then click the topic after each step (`docs/live-mode/*.png`). Server stopped afterwards; 8765/11434/11435 free.

Observed (topic `Website Redesign [live C1 101826]`, id `312dfa4d-16be-45b2-89da-e45c50dfe2eb`): after the `new_topic` step the timeline holds `March 15` and salience reads 1; after `version_field` it holds `April 20` (current) above `March 15`, salience still 1 (`step2-detail-after-version-field.png`); after the two C1 reads (`/v1/query`, temporal stage) salience reads 1.2000000000000002 (`step4-detail-after-second-query.png`); the node badge in the overview is the salience (`step1-new-topic.png`: 1 on the new topic; `final-overview.png`: the new topic is 1.2 as well). Verdict `C1` pass, `results.json` `"mode": "live"`, written to `demo/results-live/20261020-101826/`. Also observed: a second live run against the same DB made a topic with the same title, so titles now carry the run time. The earlier runs on that DB: `...-101434` (`--delay 15`) was titled `Website Redesign [live C1]` only (it ran before that change); `...-101605` (`--delay 12`) already had the suffix (`Website Redesign [live C1 101605]`, beside the unsuffixed topic of 101434); `...-101713` was aborted (no `results.json`, which is why 101826 reports `topics_before: 3`) and its topic `Website Redesign [live C1 101713]` shows badge 1 in the overview screenshot, not 1.2.

## F15. C6 on upstream: every returned topic is reinforced (unrelated ones too), 0.03 passes 0.05 in one read and survives the forgetting pass at 501 topics, and a field write then resets salience to 1.0

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/07-c6-reinforcement && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks C6-1,C6-2` (recorded mode, upstream `945d7c4` on Kuzu 0.11.3; results `demo/results/20261020-102353/`, git-ignored; each row on its own fresh DB). DBs: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-102353/upstream-c6-1/memstate.kuzu` and `.../upstream-c6-2/memstate.kuzu`. Salience and `archived` are read with `GET /api/ui/topics/{id}`, which never bumps; the suite's own retrievals are the only `/v1/query` calls.

Observed on upstream. C6-1 pass: four field-less topics (one target, three unrelated), three semantic retrievals (`top_k=8`, "how far is my weekend long running session"); each returned all four, and every topic rose 1.0 -> 1.3, exactly 0.1 per retrieval that returned it (over-reinforcement: the three unrelated topics rose as far as the target, 3 of 3; matches F8). C6-2 pass: a field-less topic ingested at `salience=0.03` read 0.03, then 0.13 after one read by id (`stages=["temporal"]`, `topic_ids=[id]`). A never-read control ingested at 0.01 and 499 field-less filler topics later (501 topics), the control read `archived=true` (salience 0.005) within 0.023 s of the last ingest, so the forgetting pass ran; the 0.13 topic read `archived=false`, salience 0.13. A later `extend_topic` with one field set its salience to 1.0 (durability observation: a field write overwrites the reinforced salience; the cause, `sync_topic_salience_from_fields`, is [INFERENCE] from code reading). Baseline: both rows fail, salience reads `None` before and after (not tracked), the forgetting pass is not run and the field write has nothing to reset.

Re-run for C6-2 only (2026-10-20, after the review fixes: durability now compares with the salience re-read after the forgetting pass, and a control that is not archived gives `partial`): `cd /home/zeyad/work/agent-systems-demo-wt/rf-g3 && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks C6-2` (results `/home/zeyad/work/agent-systems-demo-wt/rf-g3/demo/results/20261020-120114/results.json`, git-ignored; upstream `945d7c4`, Kuzu). DB: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-120114/upstream-c6-2/memstate.kuzu`. Upstream C6-2 **pass**: salience 0.03 -> 0.13 after one read by id; after the filler topics and one more ingest (501 topics) the never-read control (0.01) read `archived=true`, salience 0.005, found within 0.008 s; the target read `archived=false`, salience 0.13; durability before the field write 0.13 (read after the pass), after 1.0, `reset=true`. Baseline **fail**. The C6-1 numbers above are from run `20261020-102353`, not re-run.

Row wording: C6-1 and C6-2 quote the two sentences of C6 from `docs/papers/2605.26252v1.md:218`.

## F16. The runner measures patch step 1 from the `bitemporal` branch; C1 gives the same verdict as upstream

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/03-per-step-runs && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,step1,baseline --checks C1` (recorded mode, results `demo/results/20261020-101946/`, smoke run, git-ignored; run of record: ticket 19). Step 1 is the only commit of `git -C MemState-patched rev-list --reverse 945d7c4..bitemporal`: `089b823d2a44c65e539db51173770ee499ce80b2` ("port to ladybugdb"). The runner checked it out detached, ran C1 on a `--patched` server, and returned to `bitemporal`; afterwards `git -C MemState-patched branch --show-current` printed `bitemporal`, `git status --short` was empty and port 8765 was free.

Engine lines in the evidence (`results.json` `servers`): upstream `MemState engine module: kuzu`, commit `945d7c45a054dfc20cdcf53e37ec2b1b31384a50`, DB `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-101946/upstream-c1/memstate.kuzu`; step 1 `MemState engine module: ladybug`, commit `089b823d2a44c65e539db51173770ee499ce80b2`, DB `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-101946/step1-c1/memstate.lbug`.

Observed: C1 **pass** on upstream, step 1 and the baseline (the baseline's temporal case is not applicable, as in F13). Step 1's temporal read returned history newest first `['April 20', 'March 15']`, like upstream. The change table printed `C1 (control) | pass | pass | — | —` and `step 1 vs upstream: no change.` Step 1 is the engine port alone (commit message "port to ladybugdb"; F11 compared verdicts on both engines), so a verdict identical to upstream's is the expected result [INFERENCE: from the commit message, the diff itself was not re-read here]; it is one control row, not evidence for the other rows.

## F17. Upstream: the invalid-edge ingest succeeds and reports the edge applied (C2(b) not scored); no policy surface (C2(c) absent); no propagation to dependents (C3 absent, window unbounded)

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/05-c2b-c2c-c3 && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(b),C2(c),C3'` (recorded mode, upstream `945d7c4` on Kuzu 0.11.3, engine line `MemState engine module: kuzu`). One fresh DB per check: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-102847/upstream-{c2-b,c2-c,c3}/memstate.kuzu`; snapshots `demo/results/20261020-102847/snapshots/{upstream,baseline}/{c2-b,c2-c,c3}.json` and `results.json` (smoke run, git-ignored; run of record: ticket 19). Each server was stopped by the runner; port 8765 was free afterwards. Everything quoted below is from this run. A first run of the same command (`20261020-102020`) was made before a review changed the check (its snapshots used other field names and another case text) and is superseded; it gave the same three verdicts.

**C2(b), not-scored with a soundness observation.** One `/v1/ingest new_topic` "Website Redesign" (`Deadline="March 15"`, `Owner="Alice"`) with an edge `{to_topic_id: <fresh uuid4 that is no topic>, kind: "extension"}` returned HTTP 200: `applied = [created_topic:<id>, field:Deadline, field:Owner, edge:<missing id>]`. The stored state afterwards: 1 topic, both fields present, no edge (`/api/ui/graph` edges `[]`), no topic with the missing id. So the edge is reported applied but does not exist, and nothing failed, so atomicity is not testable with this input (this confirms the code reading in `notes/memstate-api.md` §1.1, which was `[INFERENCE]` until now). The baseline also succeeds, reports no edge and stores no edges: not-scored.

**C2(c), absent.** The probe (`GET` only, through the adapter) read `/openapi.json` (200, 23 paths). In the snapshot's probe evidence `policy_term_hits`, `triple_schemas` and `policy_knob_names_in_schema` are all empty: at the time of this run the check searched every path, schema and property name for the substrings `polic|rule|constraint|invariant|trigger` (it now matches whole words of route and schema names, so a stray word in a property name no longer stops the row), no schema has `event`, `condition` and `action` together, and none of the six numeric `Policies` knobs of `core/models.py` (`max_field_history`, `forget_salience_threshold`, `topic_count_soft_limit`, `query_salience_bump`, ...) appears in the schema. The 15 guessed routes (`/policies`, `/rules`, `/config`, `/settings`, `/v1/policies`, `/api/ui/policies`, ...) all answered 404. The config-like routes that do exist: `GET /api/ui/system-context` (`{"configured": false, "system_context": null}`) and `GET /api/ui/datamodel` (a Mermaid diagram). The schema has 11 numeric parameters, all request fields (`IngestRequest.salience`, `QueryRequest.top_k`, `AppendFieldBody.max_history`, `ChatBody.intent_turns`, `ChatBody.max_tool_rounds`, ...). `/docs` and `/redoc` answer 200 (the standard FastAPI docs). The baseline has no API: every probe returned nothing.

**C3, absent; dependent-topic staleness window "unbounded (C3 absent)".** F7 reproduced through the suite: both pairs (B → A with the edge written with B; A → B with the edge added to A by `extend_topic`), edge `extension` stored in the graph (`edge_linked: true` in both pairs), A `March 15` → `April 20` by `version_field` (`a_deadline_now: "April 20"`). B's `Date` read `March 20` before (`b_date_before`), `March 20` through `/v1/query` right after the update (`b_date_read_right_after_update`), and `March 20` after `wait_until` polled B's stored record (fields, history, events, keys; salience excluded) without a change: `reflected: false` in both pairs, the logged waits `{"timeout_s": 5.0}` ended `timed_out: true` after 5.034 s (B → A) and 5.048 s (A → B), `measurements.revision_wait_s` 5.0. B's `b_history_after` `["March 20"]`, `b_topic_events_after` `["created", "salience"]`, no flag key (`b_topic_keys_after`: archived, created_at, failed_salience, fields, id, salience, summary, title, topic_history, topic_kind, updated_at). The window is bounded only by the wait, which is why it is reported as unbounded within it, citing this run. The baseline has no edges and shows the same unchanged B. This run waited 5 s counted from after the read that follows the update; the check now waits the 15 s of the C2(a) merge wait counted from the update's response, and has not been re-recorded with that wait.

C2(b) in this run: not-scored with the observation "soundness issue: the response lists edge:<id> as applied, but the target topic does not exist and no edge is stored", also in the case text (`snapshots/upstream/c2-b.json`).

## F18. C2(a) on upstream: when the dropped topic holds the newer value, the merge makes the superseded value current in 20/20; the dropped topic is deleted

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/04-c2a-merge && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks 'C2(a)' --results-root /tmp/c2a-rerun` (recorded mode, upstream `945d7c4` on Kuzu 0.11.3, engine line `MemState engine module: kuzu`). DB: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-103536/upstream-c2-a/memstate.kuzu`; results `/tmp/c2a-rerun/20261020-103536/` (`snapshots/upstream/c2-a.json`, `results.json`). The runner stopped the server; port 8765 was free afterwards.

Each of 20 repetitions in one database: two `/v1 new_topic` under distinct titles, March 15 written through `/v1` onto the lower id and April 20 onto the higher (the merge keeps the lower id, F9), both given one title by a labelled setup `PATCH title` (values untouched by the editor; the title edit is part of the arranged state and is listed in the deviations table), then a `/v1 extend_topic` with `fields: []` to trigger the scan; merge awaited by polling every 50 ms, timeout 15 s. Precondition `dropped_held_newer` held in **20/20**. Merged 20/20, no timeouts. The superseded value "March 15" was current after the merge in **20/20**; verdict **fail**. Merge window (trigger ingest's response → merge seen): median 0.083 s, range 0.077–0.126 s. The dropped topic read as missing (`GET /api/ui/topics/{id}` 404) in 20/20: observation "topic deleted on merge".

Extras: three-way tie arranged by retitling, 1 survivor (lowest id) after 0.17 s, current `April 20`, history `['April 20']` (the other two values were dropped); an active topic merged into an archived duplicate (forced low id, labelled setup) deleted the active topic, the archived survivor kept `March 15` only, and a `/v1` read did not return it. Baseline: **pass**, 0/20, no window (upsert), archived extra skipped (no editor path); that recorded run's `results.json` counts the baseline's 20 upserts as `merged: 20` (the check now reports upserts under `upserted`, merges under `merges`).

## F19. Upstream answers the six time probes with its last-written value and ignores `valid_at` / `recorded_at`

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/09-time-probes && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks T1` (the `command` field of `demo/results/20261020-101957/results.json`) (the time-probe check is registered under its first row, T1, and yields rows T1-T6; recorded mode, upstream `945d7c4` on Kuzu 0.11.3). One fresh DB per story, e.g. `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-101957/upstream-t1-as-of/memstate.kuzu`, `.../upstream-t1-retroactive/...`, and five more; snapshots `demo/results/20261020-101957/snapshots/upstream/t1--<story>.json` (smoke run, git-ignored; run of record: ticket 19). The runner stopped each server; port 8765 was free afterwards. This first run did not record the capability flags (`measurements` is `{}` in every row of its `results.json`); the flags come from the re-run below.

Observed, upstream: T1 retroactive fact **fail** (today: `March 1`, correct `April 20`; Dec 20: `March 1`, held). T2 out-of-order **fail** (today: `basic`, correct `pro`; Sep 1 `basic`, held). T3 future-dated **fail** (today: `premium`, correct `basic`; Dec 5 `premium`, held). T4 lapsed override **fail** (story 1: Oct 15 `$80` held, today `$80`, correct `$50`; story 2: today `$100` held, Oct 5 `$100`, correct `$80`). T6 future value **fail** (today: `premium`, correct no current value; Dec 5 held). T5 as-of **absent**: the `valid_at` question and the `recorded_at` question (noted 1 s before the second write, `2026-10-20T07:20:11.792598+00:00`) both returned `May 1` although the second question's correct answer is `April 20`. Every control date was answered correctly, so no row carries the "over-blocking" observation. All six verdicts equal the spec table's "upstream expected" column. The baseline gave identical answers and the same six verdicts (it is in-process, so this is not MemState evidence).

Re-run after splitting the capability flags (same six verdicts; every row's `measurements` is `{"accepts_valid_time": false, "accepts_recorded_at": false}`, i.e. the adapter's `describe()` found none of `valid_from`, `invalid_at`, `valid_at`, `recorded_at` in any of upstream's OpenAPI schemas; all schemas are searched, not only `FieldWrite` / `QueryRequest`): `cd /home/zeyad/work/agent-systems-demo-wt/09-time-probes && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream --checks T1 --results-root /tmp/t09-rerun` (results `/tmp/t09-rerun/20261020-103817`, 17 s for seven fresh DBs; DBs `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-103817/upstream-t1-<story>/memstate.kuzu`, one per story, e.g. `.../upstream-t1-as-of/memstate.kuzu`).

Not yet proven: the dated path (the patch declaring `valid_from` / `invalid_at` / `valid_at`, ticket 12, then `recorded_at`, ticket 13; the `accepts_valid_time` / `accepts_recorded_at` flags turning True; and `history_intact` against real patch entries). Ticket 12 can exercise T1–T4 and T6 without `recorded_at`. A buggy `recorded_at` on a dates-capable system still scores T5 **absent** when the two answers are identical, which is the spec's literal definition.

Re-scored under the verdict rules of ticket 21 (per-probe date detection, four `accepts` flags): the same upstream behaviour now reads **absent** on all six probes, never fail. Upstream accepts none of `valid_from`, `invalid_at`, `valid_at`, `recorded_at` on any request model, so the writes go undated and every asked date gets the same plain read. The wrong answers above stay in each verdict's `probe_evidence` (`stories.<id>.asked[].answer`), e.g. T1 `['March 1', 'March 1']` (today and Dec 20), T4 story 2 `['$100', '$100', '$100']` (today, Oct 15, Oct 5; the new Oct 15 ask's $100 is right by recency). T5 is absent because `valid_from`, `valid_at` and `recorded_at` are all missing. Run: `cd /home/zeyad/work/agent-systems-demo-wt/21-verdict-rules && flock /tmp/gem-suite-live.lock flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream --checks T1 --results-root /tmp/t21-run` (results `/tmp/t21-run/20261021-014003`, 17 s for seven fresh DBs under `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-014003/`). Every row printed `accepts_dates=no` and `absent`; no verdict reads fail.

## F20. Storyline on upstream: all 15 questions answered, reinforcement precision 0.125 (= Precision@k); look-alike distractors did not produce a search failure

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/10-storyline && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks Storyline` (recorded mode, upstream `945d7c4` on Kuzu 0.11.3, engine line `MemState engine module: kuzu`). DB: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-104437/upstream-storyline/memstate.kuzu`; results `demo/results/20261020-104437/` (smoke run, git-ignored; run of record: ticket 19). The runner stopped the server; port 8765 was free afterwards.

The storyline is 29 `/v1` placements (14 topics, including look-alikes Website Redesign Phase 2, Marketing Budget and Design Review Meeting) then 15 questions (`top_k` 8, default stages). After every event the run compared title, current field values and, on the five events that write edges, the topic's related edges with the folded expected state.

Observed on upstream: **15/15 correct**, 0 search failures, 0 memory failures; 0 of 29 events left unexpected stored state (edges compared on 5 of 5). Every labelled topic was returned (ranks 1–3; paraphrases Q12 "site revamp" / Q13 "weekly team gatherings" still rank 1). Reinforcement: labelled-topic increments 1.5, all increments 12.0, precision **0.125**, labelled topic bumped on 15 of 15 questions, Precision@k from the returned lists 0.125 (equal). 15 questions × 8 returned × 0.1 bump = 12.0; one labelled topic per question × 0.1 = 1.5, so 1.5/12 = 1/8, the ceiling for one labelled topic at `top_k` 8. Baseline (in-process, top 10): 15/15 correct, 0 of 29 unexpected state, edges n/a, reinforcement n/a. The Storyline row is off the scorecard (`on_scorecard=False`); the numbers are in the storyline tables and `results.json`.

## F21. C4 on upstream: history survives an update and archiving; merge drops the dropped topic's value; empty and null writes become current; the 500-entry cap drops the oldest

Run (2026-10-20): `cd /home/zeyad/work/agent-systems-demo-wt/06-c4-history && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,baseline --checks C4` (recorded mode, upstream `945d7c4` on Kuzu 0.11.3, engine line `MemState engine module: kuzu`). DB: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-105907/upstream-c4/memstate.kuzu`; results `demo/results/20261020-105907/` (`snapshots/upstream/c4.json`, `snapshots/baseline/c4.json`). The runner stopped the server; port 8765 was free afterwards. Wall time 21 s.

Observed on upstream: **partial**. The update path (control) held: after `Deadline: March 15` (`kickoff-notes`) then `April 20` (`pm-email`), the stored history is `[('April 20', 'pm-email'), ('March 15', 'kickoff-notes')]`. Archiving by a labelled setup `PATCH archived=true` left the same two values, `archived=True`. Merge (dropped holds newer, F18 arrangement) left only `('March 15', 'kickoff-notes')` on the survivor; the dropped topic was deleted (F9). `version_field` with `""` was accepted and became current; with `null` was accepted and became current (`None`). 501 writes to one field (1 `new_topic` + 500 `version_field`): history length **500**, first value `v000` **absent**, newest `v500`, so the cap drops the oldest entry. The run observed behaviour only. The mechanism is code reading and stays `[INFERENCE]`: `FieldWrite.value: Any` is why `null` passes validation, and the slice `max_history=500` in `graph_store.py` drops the oldest entry, with `TopicFields.cap_history` unused.

Baseline: **fail**. No history (update, merge, cap); cannot archive (setup write returned nothing); empty and null writes became current. Observations: lost earlier value; empty value becoming current.

## F22. C5 mechanism archives a 0.01 topic at the 500-topic gate; the natural trajectory archives nothing through 2,000 topics; step 1 matches upstream; step 1 (LadybugDB) read lower latencies than upstream (Kuzu) in a 1-repeat run (provisional)

Run (2026-10-20, after the split into C5-1 and C5-2 and the median/range table): `cd /home/zeyad/work/agent-systems-demo-wt/rf-g4 && flock /home/zeyad/work/agent-systems-demo-wt/server.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,step1,baseline --checks C5-1,C5-2 --ramp-repeats 1` (recorded mode, **1 repeat**, 5 plain query reads per ramp; results `/home/zeyad/work/agent-systems-demo-wt/rf-g4/demo/results/20261020-115404/`, started 08:54:04Z, finished 09:01:14Z UTC, 430 s; `demo/results/` is git-ignored). Upstream `945d7c4` on Kuzu 0.11.3; step 1 `089b823` on LadybugDB 0.21.2 (engine lines as in the earlier run below). The runner stopped each server. Port 8765 was free afterwards.

DBs (all under `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-115404/`): C5-1 `upstream-c5-1-c5-mech/memstate.kuzu`, `step1-c5-1-c5-mech/memstate.lbug`; C5-2 `{upstream,step1}-c5-2-ramp-{100,250,500,1000,2000}-r1/` (`memstate.kuzu` / `memstate.lbug`). The snapshots are split as intended: the C5-1 cells list only `snapshots/<system>/c5-1--c5-mech.json`; the C5-2 cells list only the five `snapshots/<system>/c5-2--ramp-<n>-r1.json`.

**C5-1 mechanism:** **pass** on upstream and step 1 (`results.json`). Field-less topic ingested at salience 0.01, fillers to 501 topics. Upstream: `topics=501, archived_total=1, target_archived=True, salience=0.005, waited 0.007 s`. Step 1: same counts, waited 0.008 s. Baseline: **absent** (no archived flag). C5-1 has no `fail` outcome (the count gate holds by construction after the check's own 501 ingests): it is pass, partial or absent.

**C5-2 natural trajectory:** **fail** on upstream and step 1. Identical undated writes, no salience setup: archived **0** at n = 100, 250, 500, 1,000 and 2,000, on both (total = n at every step; confirms F10). Baseline: **absent**. Per-step change table: step 1 vs upstream **no change**.

**Latency** (scorecard `### Latency ramps`; median (min–max) over the 1 repeat; query = 5 plain reads per ramp; settle time = poll until the archived count repeats on two polls, floor about 0.1 s, **not a Reasoner wait**; baseline left out because its C5-2 verdict is absent):

| system | n | ingest ms | query ms | settle s |
|---|---:|---|---|---|
| upstream | 100 | 30.311 | 143.465 (142.823–203.331) | 0.125 |
| upstream | 250 | 30.161 | 162.32 (155.991–184.219) | 0.112 |
| upstream | 500 | 31.148 | 232.838 (219.635–256.71) | 0.133 |
| upstream | 1,000 | 41.499 | 259.79 (234.574–271.188) | 0.161 |
| upstream | 2,000 | 55.469 | 389.067 (342.128–464.653) | 0.196 |
| step1 | 100 | 18.566 | 78.881 (78.598–83.451) | 0.115 |
| step1 | 250 | 18.891 | 101.186 (97.047–109.534) | 0.116 |
| step1 | 500 | 19.337 | 136.413 (131.54–137.373) | 0.142 |
| step1 | 1,000 | 27.79 | 186.208 (180.799–197.369) | 0.183 |
| step1 | 2,000 | 45.181 | 328.793 (310.395–350.514) | 0.24 |

With one repeat the ingest range is 0 (one per-repeat median), so the rule "no measurable difference" can only fire for ingest when the medians are equal; the run printed one note: upstream vs step1 at n = 2,000, query: no measurable difference (389.067 / 328.793 ms, the query ranges overlap). Every other adjacent comparison is outside the range. **The step 1 (LadybugDB) vs upstream (Kuzu) latency gap is provisional**: one repeat and 5 reads per ramp, no 3x run yet. The run showed a client-side single read is noisy: an earlier single-sample query at upstream n = 500 read 219 ms in run 110721 and 321 ms in run 114251, which is why the table now takes several reads per ramp. The settle time says nothing about the Reasoner; the archived count never changed.

**Earlier pre-split run (110721, 1 repeat, single query sample per ramp, `--checks C5-1` ran both rows as one check; DBs `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-110721/`, relative paths in its original text were these):** upstream ingest 30.8 / 32.7 / 31.0 / 41.7 / 54.5 ms and query 170.6 / 222.7 / 218.9 / 268.0 / 359.3 ms at 100 / 250 / 500 / 1,000 / 2,000; step 1 ingest 18.8 / 18.7 / 18.9 / 29.0 / 43.9 ms and query 83.2 / 143.6 / 130.0 / 204.8 / 272.9 ms. Baseline ingest about 0.001 ms; its query is MiniLM over the whole store (0.5 s at n = 100, 4.2 s at n = 2,000) and is an in-process baseline, not an engine comparison.

## F23. Upstream commits part of a rejected ingest: an error on the second field leaves the topic and the first field stored (C2(b) atomicity broken)

Run (2026-10-20, first seen with a throwaway script; reproduced 2026-10-21 with the committed probe): from the main checkout, `flock /home/zeyad/work/agent-systems-demo-wt/server.lock scripts/run_memstate.sh /home/zeyad/work/agent-systems-demo/.runtime/retro-probes-20261021/memstate.kuzu`, then `.venv/bin/python scripts/probe_memstate.py partial-commit` (upstream `945d7c4`, Kuzu). Key output of the reproduction: `"status": 400`, `"topics_stored": 1`, `"fields_stored": {"Deadline": "March 15"}`. First run's DB: `/home/zeyad/work/agent-systems-demo/.runtime/c2b-ref-probe-20261020-233656/memstate.kuzu`.

The probe sent one `/v1/ingest new_topic` "Website Redesign" with two fields: `Deadline="March 15"`, and `Owner="Alice"` with `ref_topic_id` set to a fresh uuid4 that is no topic. Observed: HTTP **400** `{"detail":"ref_topic_id not found: b4aff4e3-…"}`. In the stored state afterwards, 1 topic "Website Redesign" exists with fields `{'Deadline': 'March 15'}`, and the missing id is not a topic. The server was stopped (`port_free_after_stop: true`).

So the request was rejected, yet the topic and its first field were committed. That breaks the paper's "the transition either commits atomically or aborts" (`docs/papers/2605.26252v1.md:291`). This is the spec's partial-commit outcome (error with the topic persisted → fail).

Cause [INFERENCE from code]: `Executor` creates the topic, then appends each field in turn (`MemState/src/memstate/core/executor.py:105-140`). `append_field_history` raises on a missing `ref_topic_id` (`store/graph_store.py:450-452`). No store call is wrapped in a transaction: a grep finds no transaction, BEGIN, COMMIT or rollback in `store/` or `core/executor.py`.

F17's input differs: an edge, not a field, points to the missing topic. `add_related_edge` (`graph_store.py:1081-1088`) is a `MATCH … MERGE` that silently creates nothing, so no step fails and atomicity is never exercised. Its finding stands as a separate response-soundness issue: an edge is reported as applied but is not stored.

## F24. On upstream, a topic with fields cannot be forgotten through `/v1`: its salience is reset to the field average (1.0)

Run (2026-10-20, first seen with a throwaway script; reproduced 2026-10-21 with the committed probe): same server and DB as F23's reproduction, then `.venv/bin/python scripts/probe_memstate.py field-salience` (upstream `945d7c4`, Kuzu). Key output of the reproduction: `"requested_salience": 0.01`, `"stored_salience": 1.0`, `"archived": false`. First run's DB: `/home/zeyad/work/agent-systems-demo/.runtime/c4-forget-probe-20261020-234103/memstate.kuzu`.

The probe sent one `/v1/ingest new_topic` "Old Vendor" with `salience: 0.01` and one field (`Contact="Bob"`). The ingest returned HTTP 200 with `applied = [created_topic:…, field:Contact]`. The stored topic then read **salience 1.0**, `archived: false`. The server was stopped (`port_free_after_stop: true`).

Cause [INFERENCE from code]:
- Every field write calls `sync_topic_salience_from_fields`, which sets the topic's salience to the average field salience (`MemState/src/memstate/store/graph_store.py:214-218`, `185-189`).
- `FieldWrite` has no salience (`core/models.py:22-30`).
- Reads only bump salience upward, and the forgetting pass archives only below 0.05 (`core/executor.py:353-362`); nothing decays.

So a topic with fields stays at or above 1.0 and is never archived by forgetting. Only field-less topics can be (F15, F22).

Consequence for the suite: C4's "history survives forgetting" case cannot reach forgetting on upstream through `/v1`. Today it archives with a labelled editor write (audit A7). This is the same mechanism as F15's durability observation, where a field write reset a reinforced 0.13 to 1.0.

## Revised checks on upstream and step 1 (ticket 22 smoke run, 2026-10-21): C2(b) fail, C2(a) existence with the natural count, C2(d) pass, C4 partial with the forgetting case n/a, C6 clause 2 pass

Runs (recorded mode, under `flock /tmp/gem-suite-live.lock`; `/home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.run --systems upstream,step1 --checks 'C2(b),C2(d),C4,C6-1,C6-2,C5-1'` and `... --checks 'C2(a)'`; results `demo/results/20261021-015154` and `demo/results/20261021-015428` in the 22-revised-checks worktree; DBs under `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-015154/` and `.../20261021-015428/`, one `memstate.kuzu` (upstream) or `memstate.lbug` (step 1) per check). Upstream `945d7c4`, step 1 `089b823`.

- **C2(b)** fail on both (F23 reproduced through the check): HTTP 400 `ref_topic_id not found`, one topic "Website Redesign" stored with `Deadline: March 15`. The separate edge ingest also reports the edge applied and stores none (F17), now an observation only.
- **C2(a)** fail on both as existence: 20 of 20 arranged repetitions made March 15 current. Natural count (random ids, no setup write): **7/20 on upstream, 9/20 on step 1** (F9 recorded 10/20 and 8/20; the natural count is chance and is not compared). Step 1 changes no C2(a) result, as the spec expects (step 3 changes it).
- **C2(d)** pass on both: with no valid-time dates accepted, story 1 reads $80 (ended, not superseded) and story 2 reads $100.
- **C4** partial on both: update held; merge broken (survivor keeps March 15 only); **real forgetting n/a**: the pass ran (the never-read 0.01 control was archived) but a topic with a field ingested at 0.01 read salience 1.0 and was not archived (F24, confirmed by the run); `""` and `null` writes accepted and current (broken); the cap case result is in the snapshot (F21).
- **C5-1** pass on both, with the F24 observation: a topic with a field at 0.01 reads salience 1.0, archived false. The gate case text states the declared bound (500 topics, `topic_count_soft_limit`) beside 501 topics.
- **C6-1** pass with the as-of case n/a (neither `valid_at` nor `recorded_at` accepted); **C6-2** pass on both (the control is archived at the forced pass, the read topic is not).

## F25. Bad merge on upstream, answered through chat: the merge keeps the re-explanation and drops the original's deadline history and "vendor delay" provenance; fields only the original held are copied over; the deadline answer still reads April 20

Run (2026-10-21): `cd /home/zeyad/work/agent-systems-demo-wt/17-bad-merge-chat && flock /tmp/gem-suite-live.lock /home/zeyad/work/agent-systems-demo/.venv/bin/python -m demo.chat_run record bad-merge` (upstream `945d7c4`, Kuzu 0.11.3; Ollama `qwen3.5:2b` through the think-off proxy, ADR 0003; the model warmed up through the proxy first, 8.06 s). DB: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-014605/upstream-chat-bad-merge/memstate.kuzu`; recording `demo/recordings/bad-merge-20261021-014605.json` (replay: `.venv/bin/python -m demo.chat_run replay`); snapshot `demo/results/20261021-014605/snapshots/upstream/chat-bad-merge.json` (git-ignored). The run stopped MemState and Ollama; port 8765 and the Ollama ports were free afterwards.

Observed: the 29 storyline events went through `/v1` onto the original `Website Redesign` topic (id `6ded8358-…`, higher); the re-explanation (`539174ed-…`, lower) got `Deadline = April 20` only; both were retitled by a labelled setup `PATCH title` and a field-less `extend_topic` triggered the scan. The merge ran 0.086 s after the trigger: the lower id survived and the original read as deleted (F9). The survivor's `Deadline` history is `[April 20 (chat-reexplanation)]`; the original's entries `April 20 (pm-email, why: vendor delay)` and `March 15 (kickoff-notes)` are gone, so the value March 15 exists nowhere (C4 history survival violated on `Deadline`). `Team` and `Status`, which only the original held, were **copied to the survivor** with their histories intact (`graph_store.py:1270-1273` copies a field the keeper lacks, [INFERENCE] from code, now seen in the run); so the loss is confined to fields both topics hold. Chat (`POST /api/llm/chat`, provider `ollama`, no `intent_override`, one request per question, route `query` by the classifier every time): Q02 (deadline) answered "April 20" in 4.6 s, Q06 (team) with all three members in 4.9 s, Q11 (status) "Complete" in 5.1 s. The state violation is present on Q02's field and absent on Q06's and Q11's; no turn changed the surviving topic.

Limits: n = 1 sample of a 2B model per take. This was the third take: take 1 (recording not kept; replay output transcribed in the journal) answered Q02 and Q06 correctly and Q11 with "I don't know"; take 2 (`demo/recordings/attempts/bad-merge-20261021-014459.json`) answered Q02 "I don't have access to that information" and Q06 and Q11 correctly. The grade slots are empty; the answers are graded by hand.

## F26. Step 2a: five of the six time probes flip on the patch's dated field histories; C1 still passes

Run (2026-10-21): `flock /tmp/gem-suite-live.lock .venv/bin/python -m demo.run --systems step1,step2 --checks C1,T1,T2,T3,T4,T5,T6 --results-root /tmp/t12-results` (recorded mode; results `/tmp/t12-results/20261021-014748/`). Step 2 is commit `7924760` on `bitemporal` (`patches/0002-bitemporal-field-histories.patch`); step 1 is `089b823`. DBs: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-014748/step{1,2}-<check>/memstate.lbug`.

Key output (change table, step 2 vs step 1): T1, T2, T3, T4 and T6 go `absent → pass`; T5 stays `absent` (accepts `valid_from` and `valid_at`, not `recorded_at`; ticket 13); C1 `pass` on both. On step 2:
- T4 story 1: Oct 15 → `$80`, Nov 5 → `$50`. Story 2 (plain "now $100" on Oct 10, override stored to Nov 1): Oct 15 → `$100`, Nov 5 → `$100`, Oct 5 → `$80` (7 cases held, 0 broke).
- T6: today → no current value, Dec 5 → `premium`.
- C1's history check holds: `history newest first=['April 20', 'March 15']`, two entries after one update.
- Developer tests in the patched copy (`tests/test_bitemporal_histories.py`, 18 tests) plus upstream's 39 pass unedited: `cd MemState-patched && PYTHONPATH=$PWD/src ../.venv/bin/python -m pytest -q` → 57 passed.

## F27. Step 2b: with `recorded_at` accepted, T5 flips to pass ("true on Feb 10" → May 1, "believed on Feb 10" → April 20) and the as-of read raises salience

Run (2026-10-21): `flock /tmp/gem-suite-live.lock .venv/bin/python -m demo.run --systems step1,step2 --checks C1,T1,T2,T3,T4,T5,T6,C6-1 --results-root /tmp/t13-results` (recorded mode; results `/tmp/t13-results/20261021-025801/`). Step 2 is now commit `1847882` on `bitemporal` (ticket 13 amended commit 2; it replaces `7924760` of F26; `patches/0002-bitemporal-field-histories.patch` re-exported, a rebuild from `patches/` gives a tree identical to `bitemporal`). DBs: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-025801/step{1,2}-<check>/memstate.lbug`.

Key output (step 2): T5 `pass`: true on Feb 10 (`valid_at`) → `May 1`, believed on Feb 10 (`recorded_at`, a real moment between the writes) → `April 20`, history intact (2 entries, 0 expired: the answer comes from `created_at` alone). T1, T2, T3, T4, T6 and C1 still pass. C6-1 `pass` on step 2: the as-of read raises salience (`valid_at` read: 0.500 → 0.600); on step 1 that case is n/a. `recorded_at` is declared on `QueryRequest` in the OpenAPI schema, so the suite's detection reads T5's three dates. Rule: the entries memory held at a moment are those with `created_at` ≤ it and not expired then (entries that expired since still count); `valid_at` defaults to now.
- Developer tests (`tests/test_bitemporal_histories.py`, 23 tests) plus upstream's 39 unedited: `cd MemState-patched && PYTHONPATH=$PWD/src ../.venv/bin/python -m pytest -q` → 62 passed.

## F28. Step 2c: the chat request's `reference_time` reaches the system prompt, the default `valid_from` and the provenance of what a chat message writes

Run (2026-10-21): `flock /tmp/gem-suite-live.lock` around `scripts/run_ollama.sh --bg`, `scripts/run_memstate.sh --patched /home/zeyad/work/agent-systems-demo/.runtime/gs14-smoke-20261021-030409/memstate.lbug` and `.venv/bin/python scripts/probe_chat_reference_time.py` (second take; Ollama `qwen3.5:2b` through the think-off proxy; both servers stopped afterwards). Step 2 is now commit `5f45848` on `bitemporal` (ticket 14 amended commit 2; it replaces `1847882` of F27; `patches/0002-bitemporal-field-histories.patch` re-exported, rebuilding from `patches/` gives the same tree).

Key output: the OpenAPI `ChatBody` declares `reference_time`; `reference_time: "last tuesday"` is a 400 (`reference_time is not an ISO date or datetime`). One ingest chat with `reference_time` `2026-10-06` ("I started my new job two weeks ago: I am a manager at Initech", the model told to call `memory_append_field`) made the model call `memory_append_field` without a `valid_from`; the stored entry has `valid_from` `2026-10-06T00:00:00+00:00` (the default) and provenance `llm (reference_time 2026-10-06T00:00:00+00:00)`, while `created_at` is the wall clock (`2026-10-21`); the earlier `job` entry (`valid_from` `2025-01-01`) is intact. The first take (a looser prompt) made two read calls and no write; the model's reply quoted `2026-10-06` as the system time, so the prompt block reaches it.

Limits: n = 1 write by a 2B model. The model stored the value "Started: 2026-10-04 (two weeks ago)", i.e. it mis-computed two weeks before Oct 6 as Oct 4 and put it in the value, not in `valid_from`; that is a model-quality limit that ticket 18's graded run measures, not a defect of the plumbing. The tool path itself (default `valid_from`, an explicit `valid_from` winning, a non-date `valid_from` refused, reads as of the reference time, provenance) is covered without an LLM by `tests/test_chat_reference_time.py` (11 tests) in the patched copy: with upstream's 39 and ticket 12-13's 23, 73 passed (`cd MemState-patched && PYTHONPATH=$PWD/src ../.venv/bin/python -m pytest -q`).

## F29. Step 3: the merge interleaves both histories by valid time; C2(a) flips fail → pass (20/20 → 0/20), C4's merge cases flip, the time probes still pass

Run (2026-10-21): `flock /tmp/gem-suite-live.lock flock /home/zeyad/work/agent-systems-demo-wt/server.lock .venv/bin/python -m demo.run --systems step2,step3 --checks "C2(a),C4,T1,T2,T3,T4,T5,T6,C5-2" --results-root /tmp/t15-results` (recorded mode; results `/tmp/t15-results/20261021-030847/`; ramps ran once, so the latency figures are provisional). Step 3 is commit `5c5c9e6` on `bitemporal` (step 2 is `5f45848`); `patches/0003-merge-by-valid-time.patch` is exported and rebuilding all three patches on `945d7c4` gave a tree identical to `bitemporal`. DBs: `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261021-030847/step{2,3}-<check>/memstate.lbug` (C2(a): `step3-c2-a`, C4: `step3-c4`, the 2,000-topic ramp: `step3-c5-2-ramp-2000-r1`).

Key output (step 3 against step 2):
- C2(a) `fail → pass`: March 15 current after the merge in 20/20 arranged repetitions on step 2, 0/20 on step 3; the natural count (random ids, no arrangement) goes 10/20 → 0/20 (shown, not compared). Merge window median 0.064 s → 0.07 s.
- C4 stays `partial` (the forgetting case is n/a, F24); "history survives a merge" `broken → fixed` (survivor history April 20 (pm-email) and March 15 (kickoff-notes), where step 2 keeps only the survivor's value).
- The dated merge case (topic A "April 20 since Jan 5" with the lower id, duplicate B written later "March 15 since Dec 1"): step 2 reads April 20 today but B's value is gone (`history=[('April 20', 'pm-email')]`, `broken`); step 3 reads April 20, holds both values with their provenance, and the March 15 entry carries `merged_from_topic_id` = B's id (`84fb6d36-…`). `broken → fixed`.
- T1–T6 pass on step 3 as on step 2 (T5 included).
- Merge extras on step 3: three same-title topics → one survivor (lowest id) with all three values in the history, current `May 31`, where step 2 keeps `['April 20']`. An active topic and an archived duplicate no longer merge: the archived duplicate is skipped, so the active topic stays active (step 2 deleted it, the archived survivor kept only `March 15`); the wait for the merge timed out, as intended.
- Latency, 2,000 topics (one repeat, provisional): plain read median 314.7 ms (step 2) vs 313.1 ms (step 3); 20 as-of reads (`valid_at`) median 347.7 ms (step 2, range 270.7–415.8) vs 318.7 ms (step 3, 266.0–349.3); ingest 45.4 vs 46.4 ms. Step 2 and step 3 show no measurable difference at any n.

Rule: the duplicate scan skips archived topics, merges the first pair (by id), scans again, and repeats; the survivor (lower id) gets one `merged` topic event per merge. Each of the dropped topic's history entries is copied to the survivor with its value, dates, provenance and `created_at` unchanged, tagged `operation: "merged"` and `merged_from_topic_id`; a live entry goes in like a write, so a survivor entry whose stored end it cuts short is expired and copied (keep-and-copy, ADR 0005). A field only the dropped topic had moves over with its entries tagged. The dropped topic's summary, topic events and salience are still lost (limitation). Developer tests: `tests/test_merge_by_valid_time.py` (9 tests) with upstream's 39 unedited: `cd MemState-patched && PYTHONPATH=$PWD/src ../.venv/bin/python -m pytest -q` → 82 passed.
