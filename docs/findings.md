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
