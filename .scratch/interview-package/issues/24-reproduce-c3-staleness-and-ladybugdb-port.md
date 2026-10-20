# Reproduce the C3 staleness run and the LadybugDB port

Type: task
Status: resolved

## Question

The report states two MemState results as verified that have no run in this repo (they come from a sandbox with fallback hash embeddings). Do they reproduce on this laptop with MiniLM, on fresh absolute DBs, recorded per the evidence rule?

1. **C3 staleness** (report §5.3, §9.7): B → A via an `extension` edge; update A's deadline through `/v1/ingest`; read B before and after the Reasoner's revision. Claimed: the read does not block, B returns its old value, B's row has no flag, revision returns no actions, B stays stale; the query result lists A as a neighbour without the edge kind.
2. **LadybugDB port** (report §1 item 6, §5.10, §9.7): in a scratch worktree (never `MemState/`), replace `import kuzu` with `import ladybug as kuzu` in `kuzu_adapter.py`, `ladybug==0.21.2` (not `real_ladybug`). Claimed: all 39 upstream tests pass; probe verdicts identical to Kuzu; query median 321 ms (LadybugDB) vs 392 ms (Kuzu) at 2,000 topics.

Each result enters `docs/findings.md` (command, DB path, key output) or the report is corrected. Where ladybug is installed (root venv beside kuzu, or a separate venv) is recorded, since packaging depends on it. Stop every server when done.

## Answer

Resolved 2026-10-20. Both reproduce; findings F7–F12 in `docs/findings.md`, probes in `scripts/probe_memstate.py`, raw outputs in `.runtime/probes-20261020/` (git-ignored).

- **C3 staleness reproduces** (F7), in both edge directions: B keeps its old value right after A's update and after the Reasoner runs; no flag field; no revision event in B's history; the `/v1/query` neighbour list omits the edge kind (the UI graph shows `extension`). "Revision returned no actions" is not observable over HTTP; the report now says "revision made no change to B".
- **LadybugDB port reproduces** (F11): one-line import change in a scratch worktree `.runtime/ms-ladybug/` at `945d7c4`; 39/39 upstream tests pass (11.5 s vs 2.8 s on Kuzu); C3, salience, merge and ramp verdicts identical. Latency at 2,000 topics: query median 340 ms (LadybugDB) vs 382 ms (Kuzu), not the sandbox's 321 vs 392; LadybugDB is faster at every step from 100 topics.
- **Installed in the root venv beside `kuzu`** (`ladybug==0.21.2`, no other dependencies); the worktree runs via `PYTHONPATH=<worktree>/src scripts/run_memstate.sh <db>` and the process loads only `_lbug`. `ladybug.__version__` crashes (missing C-API library), harmless to MemState (F12). DB files are not interchangeable (F12).
- **Also measured** (§9.7 bullets): nothing archived at 2,000 topics on either engine, salience 1.0–2.1 (F10); every returned candidate bumped, including unrelated ones at similarity 0.04 (F8); merge keeps the lower ID in 20/20, stale value current 10/20 (Kuzu) and 8/20 (LadybugDB), dropped value lost 20/20 (F9).
- **Report updated**: §1 items 3 and 6, §5.3, §5.10, §5.11, §7.5 (C3′ motivation) and §9.7 cite the recorded runs; README install line and layout updated.
