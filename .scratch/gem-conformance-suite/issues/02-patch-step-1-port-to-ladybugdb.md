# 02: Patch step 1: port to LadybugDB and `--patched`

**What to build:** A patched copy of MemState that starts on LadybugDB 0.21.2 from `scripts/run_memstate.sh --patched`, with the engine and source folder printed at startup. It lives on branch `bitemporal` in the git-ignored worktree `MemState-patched/` of the submodule. Its first commit on `945d7c4` changes nothing but the engine import and dependency, so "the engine swap changes nothing" can be checked at a glance. The worktree left under `.runtime/` by the earlier LadybugDB probe (F12) is not this copy. Spec: user stories 46–48, 51; Implementation Decisions "Patch, step 1", "Patch packaging"; ADR 0006.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Commit 1 changes only the `kuzu_adapter.py` import (`import ladybug as kuzu`) and the `pyproject.toml` dependency (`ladybug==0.21.2`). Nothing is renamed and MemState's README is untouched.
- [ ] `MemState/` stays byte-for-byte unmodified, and `src/memstate.egg-info` is restored after any editable install.
- [ ] `--patched` points `PYTHONPATH` at the patched source. Default DB paths become `.runtime/memstate-kuzu-<ts>/memstate.kuzu` and `.runtime/memstate-ladybug-<ts>/memstate.lbug`. The script prints the loaded engine module and the source folder. Without `--patched` it behaves as before, apart from the folder name.
- [ ] `patches/0001-port-to-ladybugdb.patch` is exported with `git format-patch 945d7c4..bitemporal -o patches/`. The README's two commands rebuild `MemState-patched/` from the pinned submodule, which is shown by recreating the worktree from the patch files.
- [ ] Upstream's 39 tests pass unedited in the patched copy.
- [ ] Smoke run: a `--patched` server answers `/health` and completes one `/v1/ingest` + `/v1/query` round trip. The startup lines name ladybug and `MemState-patched/`.
- [ ] The README documents `--patched` and the rebuild.
