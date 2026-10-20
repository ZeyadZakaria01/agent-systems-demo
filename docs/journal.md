# Journal: difficulties and lessons

One entry per difficulty, newest last. Fields: expected, observed, evidence, resolution, lesson. Tag `report:` when the report should cite it.

## 2026-10-06 – 2026-10-11 (backfilled from the planning session)

### Paper conversion paraphrased the paper `report:`
- Expected: `docs/papers/2605.26252v1.md` faithful to the PDF.
- Observed: independent audit failed it: redrawn figures factually wrong (Figure 1 week rows, Figure 3 timestamp, Figure 2 labels), paraphrased prose in §1–§3, invented §5.1–5.4 numbering, condensed references; math inside italics did not render on GitHub.
- Resolution: rewrite against page images; second audit; GitHub Markdown API render check (88/88 math spans).
- Lesson: verify every machine conversion against page images before citing it; a render check catches what text checks miss.

### The repo's own analysis doc was wrong in places
- Observed: audit of `2605.26252v1-alignment.md` found the forgetting recipe could not work (forget scan only at ≥500 topics; field writes reset topic salience), a wrong salience cap, wrong recovery paths, stale line numbers.
- Resolution: 23 corrections from code.
- Lesson: code-reading claims need a run before they are reported (became the evidence rule).

### Kuzu is archived upstream
- Observed: kuzudb/kuzu archived 2025-10-10; 0.11.3 is the final release.
- Resolution: pinned `kuzu==0.11.3`; prebuilt cp312 manylinux wheel installs without compiling; no extension needed (MemState's vector search is numpy).
- Lesson: the GEM prototype sits on a substrate with no future fixes; a report point on substrate risk. `report:`

### Groq key silently ignored
- Observed: chat returned 503 with `GROQ_API_KEY` set, as the upstream quickstart instructs.
- Resolution: pass `MEMSTATE_GROQ_API_KEY` (see `docs/findings.md` F3).
- Lesson: follow the error into the settings object, not the docs.

### `pip install -e` dirtied the upstream clone
- Observed: editable install rewrote tracked `MemState/src/memstate.egg-info/`.
- Resolution: `git -C MemState checkout -- src/memstate.egg-info` after installs.

### Local model thinks on every request
- Observed: `qwen3.5:2b` thinks by default; MemState sends no `think`; "Say hello" took 52 s.
- Tried: an Ollama model variant (`PARAMETER think false` → "unknown parameter 'think'"); `/no_think` in system or user message (model still produced 2–3K characters of reasoning).
- Resolution: `scripts/ollama_nothink_proxy.py` defaults `think:false`; MemState chat turn 19.2 s → 1.7–3.8 s.
- Lesson: when a client cannot be changed, a thin proxy at the protocol boundary keeps the system under test unmodified.

### Groq free tier is slow and tight
- Observed: one MemState chat turn took 72 s; headers show 8000 tokens/min, 1000 requests/day; MemState's tool schemas and system prompt alone are ~7K tokens per round.
- Resolution: LLM runs recorded and replayed; budget ticket opened.
- Lesson: measure tokens per turn before planning repeats.

### Laptop limits
- Observed: ~2.9 GB free RAM with browsers open (5.5–9.9 GB swapped); GPU at 82 °C, 87% load during inference; disk down to 6.8 GB after Ollama.
- Resolution: one backend loaded at a time; servers stopped after runs; unused `cuda_v12` deleted (8.0 GB free).

### AI attribution trailers cannot be turned off by settings alone
- Observed: Claude Code `attribution.commit: ""` and Cursor rules are reported not to stop trailers (claude-code issues #45137, #77830; Cursor forum).
- Resolution: `.githooks/commit-msg` strips them; tested in a throwaway repo (AI lines removed, human co-author kept).

## 2026-10-11

### MAFBench selective-forgetting result mis-cited `report:`
- Expected: the plan quotes MAFBench accurately.
- Observed: an external review caught "selective forgetting ≈ 0 for every framework" in the plan. The paper says single-hop reaches 20.2 (retrieval-only LangGraph) and multi-hop stays below 5.0 everywhere (`docs/papers/2602.03128v2.md:397`). The error came from an agent's summary of a `pdftotext` dump in which Table 10's columns were scrambled; it was repeated without checking the verified conversion.
- Resolution: tickets 01 and 21 and the map corrected; the reviewed framing is the one to cite.
- Lesson: quote numbers from the verified paper text, never from a summary of it.

### Review also corrected two verdict designs
- C5 needs two verdicts (mechanism vs natural trajectory), and C6 needs its two clauses scored separately; a field write resetting salience does not make a topic eligible for forgetting, so it cannot by itself fail clause 2 (ticket 21).
- Lesson: score each clause of a definition separately, against the clause's exact wording.

## 2026-10-12

### Converter's own render check missed leaking bold
- Observed: the Zep converter reported a clean GitHub render, but the independent verifier found 9 table cells where `**77.7%**↑` renders as literal asterisks (GitHub does not close `**` after `%` when a symbol follows), and a dataset name whose subscript `s` had flattened into a plural (`LongMemEvals`).
- Resolution: `<strong>…</strong>` in those cells; subscript restored; all three new conversions passed independent audits after fixes.
- Lesson: a self-check by the author is not verification; keep the independent audit for every conversion.

## 2026-10-18

### Large GitHub clones drop mid-transfer
- Expected: `git clone https://github.com/vectorize-io/hindsight` and `npx skills add vectorize-io/hindsight --skill hindsight-docs` complete.
- Observed: both failed repeatedly after minutes: `curl 92 HTTP/2 stream 5 was not closed cleanly: CANCEL`, then with `http.version=HTTP/1.1` `curl 18 transfer closed with outstanding read data remaining`. `multinex` and `supermemory` cloned fine.
- Resolution: the skill installed once its git was forced to HTTP/1.1 through `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.version GIT_CONFIG_VALUE_0=HTTP/1.1` (the CLI shallow-clones). The repo cloned with `git -c http.version=HTTP/1.1 clone --depth 1` (110 s), then `git fetch --unshallow` brought the full history (3,700 commits, 270 s).
- Lesson: on this connection, force HTTP/1.1 and clone large repos shallow first, then unshallow; the smaller transfers finish where one big pack does not.

## 2026-10-19

### Report revised from a stale export lost two repo edits
- Expected: the revised report (`~/Downloads/README (2).md`) builds on the committed `docs/report/gem-limitations-and-directions.md`.
- Observed: it builds on the earlier export `~/Downloads/README (1).md`, which differs from the repo copy in three lines. The repo-only edits were lost: the MemTX qualifier "only on four of the five backbones (0.959 and 0.963 on the weakest, Qwen2.5-14B)" (§5.11) and the practitioner-note wording decided in ticket 22 (§7.5). Evidence: `git diff --no-index "~/Downloads/README (1).md" docs/report/gem-limitations-and-directions.md` (3 lines) vs. the v2 diff (183+/84−).
- Resolution: v2 installed as the repo copy; the two lost edits go to the map ticket "Reconcile report v2 with earlier decisions and the source audit".
- Lesson: export from the repo copy right before editing elsewhere, and diff the returned draft against that export, not against memory.

### MAFBench's prose mislabels its own Table 10 `report:`
- Expected: the 2026-10-11 correction ("single-hop reaches 20.2") matches the paper.
- Observed: it matches the prose (`docs/papers/2602.03128v2.md:397`), but Table 10 (:372) gives retrieval-only LangGraph FC-SH 36.0, FC-MH 4.5 and Selective Forgetting average 20.2; the prose calls the average "single-hop". Found by the source audit of report v2 (`.scratch/interview-package/assets/report-v2-audit.md`, B8). "Multi-hop below 5.0 everywhere" holds.
- Resolution: report fix goes to the map ticket "Reconcile report v2 with earlier decisions and the source audit".
- Lesson: when a paper's prose quotes its own table, check the number against the table cell.

## 2026-10-20

### `ladybug` 0.21.2 imports, then crashes on its own version getter
- Expected: `import ladybug; ladybug.__version__` works after `uv pip install ladybug==0.21.2`.
- Observed: `RuntimeError: Could not find lbug C API shared library`, then exit code 139. The wheel ships only the pybind extension `_lbug.cpython-312-x86_64-linux-gnu.so`; `__version__` goes through the separate C-API backend, which needs `liblbug.so`. `Database` and `Connection` use the pybind backend and work (findings F12).
- Resolution: none needed for MemState, which never reads the version; check the backend with a real query, not with `__version__`.
- Lesson: smoke-test a new native dependency with the calls the program makes, not with the first attribute that comes to mind.

### Sandbox numbers held up in direction, not in value `report:`
- Expected: the report's sandbox figures (hash embeddings) reproduce with MiniLM on this laptop.
- Observed: every verdict reproduced (F7–F11), but the numbers moved: 2,000-topic query median 382 vs 340 ms here against the sandbox's 392 vs 321 ms; salience reached 2.1, not 1.5; and the merge result is stronger than the sandbox's "in one run": the stale value became current in 10/20 runs and the dropped value was lost in 20/20.
- Resolution: report §1, §5.3, §5.10, §5.11 and §9.7 now cite the recorded runs.
- Lesson: verdicts transfer between environments; numbers have to be re-measured where they will be cited.

### Zep's paper and Graphiti's code disagree on ordering `report:`
- Expected: report §9.5's claim that Zep resolves contradictions along the transaction timeline, so a late-arriving older value wins (from the paper: "Graphiti consistently prioritizes new information", `2501.13956.md:91`).
- Observed: Graphiti `main` at `6e3e3cb` ends a late-arriving older fact where the later fact begins (`graphiti_core/utils/maintenance/edge_operations.py:730-743`), i.e. it orders by valid time. The code also edits invalidated facts in place (`:779-780`) and expires a fact that arrives with an end date at once (`:726-728`); neither is in the paper. Recommendations made from the paper alone (the first draft of the bitemporal model) had to be redone.
- Resolution: report §9.5 rewritten in "Bitemporal history model and API": Zep's behaviour is the default and each departure names the GEM condition that requires it (C4 for keep-and-copy, C1 for end-dated values, C1/C2 for no LLM judge).
- Lesson: check a system's code, not only its paper, before contrasting with it or recommending a design based on it; papers describe intent, code is the behaviour.

### Chat defaults to a model that is not installed
- Expected: MemState's chat uses the Ollama model the README serves (`qwen3.5:2b`).
- Observed: `scripts/run_memstate.sh` never set `MEMSTATE_OLLAMA_MODEL`, so the server falls back to upstream's `llama3.2:latest` (`MemState/src/memstate/config.py:21`). Run from the repo root: `.venv/bin/python -c 'from memstate.config import Settings; print(Settings().ollama_model)'` printed `llama3.2:latest`; `~/.ollama/models/manifests/registry.ollama.ai/library/` holds only `qwen3.5`. A chat request without `"model"` would ask Ollama for a model it lacks [INFERENCE: no chat call made].
- Resolution: the script exports `MEMSTATE_OLLAMA_MODEL="${MEMSTATE_OLLAMA_MODEL:-qwen3.5:2b}"`; with it set, the same command prints `qwen3.5:2b`. Found while designing the "two weeks ago" chat case (Time probes and their controls).
- Lesson: when a wrapper script pins one setting of a service (base URL), check the settings that pair with it (model name).

### Run script fails in a fresh git worktree
- Expected: `scripts/run_memstate.sh` starts MemState from any checkout of this repo, so parallel build agents can each work in their own worktree.
- Observed: in a new worktree `MemState/` is empty (submodule not initialised) and `.venv/`, `.cache/` and `.runtime/` are git-ignored, so absent. `scripts/run_memstate.sh` exited 2 with `sed: can't read .../MemState/.env: No such file or directory`.
- Resolution: the script resolves a `SHARED` root from `git rev-parse --git-common-dir` (the main checkout) and takes the venv, embedding cache, `MemState/.env` and default `.runtime/` DB folder from it. Run from the worktree, it served `{"status":"ok"}` on `/health` with `MEMSTATE_KUZU_PATH=/tmp/hz/memstate.kuzu`; the server was stopped afterwards and the main checkout stayed clean. `ROOT` (the worktree) is still where the script `cd`s.
- Lesson: a script that reads git-ignored state by relative-to-script paths works only in the checkout that holds that state; resolve shared state from the git common dir.

### Editable install would shadow the patched source
- Expected: the patched copy's 39 tests and the `--patched` server import `MemState-patched/src`.
- Observed: the venv's `__editable__.memstate-0.1.0.pth` contains `/home/zeyad/work/agent-systems-demo/MemState/src`, so a plain `import memstate` loads upstream. Reinstalling would rewrite the tracked `MemState/src/memstate.egg-info`.
- Resolution: `PYTHONPATH=<MemState-patched>/src` precedes `.pth` entries; no install is done. Check: `memstate.__file__` was `.../MemState-patched/src/memstate/__init__.py`, `store.kuzu_adapter.kuzu.__name__` was `ladybug`, `'kuzu' in sys.modules` was `False`, and `pytest` reported `39 passed`. `git -C MemState status` stayed clean.
- Lesson: after pointing a path at a modified copy, print where the module loaded from instead of assuming.

### Patch file name
- Expected: `git format-patch` writes `patches/0001-port-to-ladybugdb.patch`.
- Observed: the name derives from the commit subject, so my first subject ("Port to LadybugDB: ...") gave a long, differently cased name.
- Resolution: the commit subject is `port to ladybugdb` (body gives the detail), then re-exported; rebuilding in a throwaway worktree with `git am patches/*.patch` gave tree `ef3ed91…`, identical to `bitemporal`.
- Lesson: choose the commit subject for the file name it will produce.
