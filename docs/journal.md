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
- Date: 2026-10-20
- Expected: `git format-patch` writes `patches/0001-port-to-ladybugdb.patch`.
- Observed: the name derives from the commit subject, so my first subject ("Port to LadybugDB: ...") gave a long, differently cased name.
- Evidence: `git rev-parse bitemporal^{tree}` equals the tree `ef3ed91…` of a throwaway worktree rebuilt with `git am patches/*.patch`; the README's "same tree as `bitemporal`" claim rests on this entry.
- Resolution: the commit subject is `port to ladybugdb` (body gives the detail), then re-exported; rebuilding in a throwaway worktree with `git am patches/*.patch` gave tree `ef3ed91…`, identical to `bitemporal`.
- Lesson: choose the commit subject for the file name it will produce.

### Ticket 01: C1 as written would fail the baseline, which §9.3 expects to pass `report:`
- Date: 2026-10-20
- Expected: the C1 check (default read returns only April 20, temporal read returns the full history) passes on both upstream and the baseline, as report §9.3 and the ticket predict.
- Observed: the baseline keeps no history, so its temporal read can never return `March 15`. Scored literally, the second case would fail the baseline, contradicting "C1 pass" for the baseline; the paper puts history preservation under C4, and C1's wording only restricts when prior values appear.
- Evidence: smoke run `20261020-095720` (command, DB path and key output quoted in `docs/findings.md` F13): baseline C1 `pass` with the case `temporal read returns the full history` at `held=None` ("the system keeps no history; its temporal read gives current='April 20' only (history is C4's concern)"), and upstream's `held=True` with history `['April 20', 'March 15']`.
- Resolution: the baseline's history reads as the nothing-value `None`; the C1 case "temporal read returns the full history" is recorded as not applicable (`held=None`, with the observation "the system keeps no history") and does not count toward the verdict. Upstream still has to return `['April 20', 'March 15']` for the case to hold. Verdict scale: `Verdict.from_cases` ignores `held=None` cases and gives `not-scored` only when none applies; the scorecard cell now says `(n case(s) n/a)` so a verdict resting on fewer cases is visible.
- Lesson: a check that needs a capability must treat a missing capability as "does not apply" (and say so in the evidence), leaving the capability's own row (C4) to score its absence.

### Edit tool resolved a relative path in the main checkout
- Date: 2026-10-20
- Expected: editing `README.md` with the cwd of the shell (the worktree) changes the worktree's file.
- Observed: the agent's working directory was the main checkout, so a relative `README.md` hashed to the main checkout's file; the edit was rejected (stale tag) before anything changed. `git status` in both checkouts stayed as expected.
- Evidence: the edit tool's stale-tag rejection on the relative `README.md`, then clean `git status` in both checkouts (terminal output, not kept as a file).
- Resolution: use absolute worktree paths for every edit and read of repo files (the `cwd` of `bash` is separate from the edit tool's).
- Lesson: in a worktree-based build, address files by absolute path; a hash mismatch on a file just read is the signal that the wrong checkout was addressed.

### Ticket 09: the dated paths and the patch detection cannot be run yet `report:`
- Date: 2026-10-20
- Expected: build the time probes so the patch rows can flip later.
- Observed: the patch does not exist at this commit, so only upstream and the baseline were run. The flags `accepts_valid_time` (dated writes + `valid_at`) and `accepts_recorded_at` are read from every schema in `/openapi.json`, not by model-name prefix; upstream gives both False (proved by the smoke run). Ticket 12 lands the first without the second; T1–T4/T6 then use the dated path. The patch's True is [INFERENCE] until tickets 12/13 run it. The dated request construction is unit-tested as pure functions; the dated read/write path and `history_intact` against real patch entries are not.
- Evidence: F19 (`docs/findings.md`); re-run `/tmp/t09-rerun/20261020-103817/results.json` (flags `accepts_valid_time=false`, `accepts_recorded_at=false` in every row's `measurements`; DBs under `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-103817/`).
- Resolution: an unreadable schema (`None` plus `accepts_error`) makes the time probes raise instead of guessing; a readable schema that simply lacks the keys is False, recorded in each row's `measurements`.
- Lesson: detect a capability from what the server declares, and say which parts were proven only on the side that exists.

### Ticket 09: the time-probe check is registered under its first row
- Date: 2026-10-20
- Expected: `--checks T5` selects the as-of probe.
- Observed: the runner selects a check by its id (the first row, T1) or any of its rows, but runs the whole check: all seven story servers start (measured 19 s on upstream, 2026-10-20 smoke `demo/results/20261020-101957`, seven fresh DBs) and every row's cell links all seven snapshots (`Verdict.snapshots` is per check). A smoke run for one row costs the whole check.
- Evidence: `demo/results/20261020-101957/results.json` (`--systems upstream,baseline --checks T1`; seven fresh upstream DBs under `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-101957/`, each row of the T1 check linking all seven snapshots).
- Resolution: none needed; stories are the unit of freshness the spec asks for.
- Lesson: a multi-row check costs the sum of its rows; keep single-row checks apart when a row needs to be rerun alone.

### Ticket 07: C6 on the baseline is "fail", not "absent", and the suite's own reads must not bump salience `report:`
- Date: 2026-10-20
- Expected: baseline C6 fails both clauses with salience unchanged (spec "Baseline"), and salience can be read without disturbing it.
- Observed: the baseline reads salience as `None` (a nothing-value); scoring that as `absent` would need probe evidence and contradict the spec's "C6 both fail". On MemState every `/v1/query` adds +0.1 to each returned topic, including the suite's own reads, so a read-by-query would corrupt the salience being measured.
- Evidence: `demo/results/20261020-102353/results.json` (F15; upstream C6-1 salience 1.0 -> 1.3 over three retrievals); the baseline reads salience `None` (`tests/test_c6.py`, baseline tests).
- Resolution: salience cases fail when salience is not tracked, with the observation "not tracked"; salience is read only through `read_topic` (`GET /api/ui/topics/{id}`, never bumps) and the only `/v1/query` calls are the counted retrievals, so the expected rise is the number of retrievals that returned the topic.
- Lesson: a measurement read must be a different endpoint from the operation being measured whenever the operation writes on read.

### Ticket 16: live output vanished when piped; one DB made same-title topics of later runs duplicates
- Date: 2026-10-20
- Expected: `python -m demo.run --mode live ... | tee log` shows each step as it happens, and a rerun against the same server starts clean.
- Observed: Python block-buffers stdout into a pipe/file, so the step lines and the `--step` prompt only appeared at exit (seen: a run log with only its first line while the run was mid-delay; that log was not kept); and the second run reused `Website Redesign [live C1]`, giving a second topic with the same title.
- Evidence: F14 (`docs/findings.md`): runs `...-101434` (`[live C1]` only) and `...-101605` (`[live C1 101605]` beside it) on DB `/home/zeyad/work/agent-systems-demo/.runtime/gs16-live-20261020-101318/memstate.kuzu`. That the Reasoner would merge such exact-title duplicates is [INFERENCE] here (F9 shows an exact-title merge on upstream, not on live runs).
- Resolution: live logging and the prompt `flush`; titles carry `<check> <HHMMSS of the run>` (`demo/live.py`).
- Lesson: anything a presenter watches must flush; "distinct titles per check" must also mean distinct across runs on one DB.

### Ticket 03: the step teardown moved a worktree its setup had refused `report:`
- Expected: a run that refuses a dirty `MemState-patched/` leaves it untouched ("refuses without damaging it").
- Observed (review, throwaway repo): HEAD detached at step 1 with a tracked file edited (a developer amending a step); `setup` refused, but `teardown` still ran `git checkout bitemporal` and carried the edit onto the branch (`53cfa9e` → `bitemporal 2e34735`, ` M g` still dirty). With an edit overlapping a file that differs between the commits the checkout would fail instead, only logged as a `teardown_error`. My test only covered a worktree already on `bitemporal`, where the checkout is a no-op.
- Evidence: the throwaway-repo reproduction above (HEAD `53cfa9e`, branch moved to `bitemporal 2e34735`); `tests/test_steps.py::test_a_refused_setup_leaves_a_detached_worktree_with_a_tracked_edit_exactly_where_it_was`.
- Resolution: `setup` compares HEAD and branch before and after; `teardown` returns to `bitemporal` only if it moved. The clean check also refuses a rebase, merge, cherry-pick, revert or bisect in progress. Tests cover a tracked edit on a detached HEAD. A later review found the "only if it moved" rule too narrow (a clean worktree left detached at the very commit the step selects moves nothing, so the teardown skipped the return): the teardown now returns whenever the setup completed the checkout, and still not after a refusal.
- Lesson: a teardown must undo what its setup did, not assert a fixed end state; test the refusal from a non-default starting state.

### Port 8765 was busy when the smoke run was started
- Expected: `ss -ltn | grep 8765` is empty before a run, as the conventions require.
- Observed: it showed a listener, another agent's server; the run, wrapped in `flock …/server.lock`, waited and the port was free when its server started.
- Resolution: none needed; the lock serialised the runs.
- Lesson: look at the port after taking the lock, not before; a listener seen before the lock is held is someone else's run.

### Ticket 05: C2(b) first scored a clean rejection as pass, against the spec `report:`
- Expected: the spec's classification (story 21: error with state persisted is fail; success with the edge reported applied is a soundness issue; neither outcome is not-scored) covers every system.
- Observed: while building I judged that a clean rejection (error, nothing persisted) demonstrates atomicity and scored it `pass`, "extending" the wording. Review found the spec and ticket say not-scored and had not been amended. Upstream is the soundness outcome, not the clean rejection: it succeeds and reports the edge applied (F17).
- Evidence: F17 (upstream: 200, `applied` lists `edge:<missing id>`, no edge stored); `tests/test_c2b_c2c_c3.py` (`test_a_clean_rejection_is_neither_outcome_so_not_scored` and the soundness tests, on fake systems that subclass the baseline; no MemState verdict is pinned).
- Resolution: clean rejection is `not-scored` with no observation; only error + persisted is `fail`; success + edge reported applied is `not-scored` and records "soundness issue" both as an observation and in the case text (also when the system's edges are unreadable).
- Lesson: do not widen a scale the spec fixed; if a case looks unscored-but-meaningful, log it and ask for a spec amendment.

### Ticket 05: a negative C3 result is a bounded wait, not a poll
- Expected: `wait_until` can detect when B is revised, so the dependent-topic window is measured.
- Observed: upstream never revises B, so the wait always times out; it can only say "not within the wait", and a positive window can only be measured on a system that propagates (the tests use a fake).
- Evidence: F17 (both pairs: `March 20` before, right after and after 5.0 s with the wait timed out; upstream DBs under `.runtime/gem-suite/20261020-102020/upstream-c3/`).
- Resolution: the window reads "unbounded (C3 absent)" and cites the C3 run, which records the wait length (`revision_wait_s`); F7's fixed 2 s became a poll every 0.1 s, first 5 s (the F17 run), then, after review, the 15 s of the C2(a) merge wait counted from the update's response (a slow revision must not be misread as absent). "B reflects" counts only B's fields, summary, kind, title or archived flag changing; events and salience do not.
- Lesson: report a window for an absent capability together with the wait that bounded the observation.

### Ticket 04: "dropped holds the newer value" is arrangeable without a forced id
- Expected: every C2(a) repetition has the topic that will be dropped hold the newer value (spec story 20).
- Observed: `/v1/ingest new_topic` assigns a uuid4 and the merge keeps the lower id (F9: lower id survives 20/20, the stale `March 15` is current in 10/20). Two same-title writes therefore make "dropped holds newer" a coin flip. An earlier remark that a first recorded run showed 7/20 has no run behind it and is dropped; F9's 10/20 is the cited figure. The journal previously said this was "only controllable with a forced id".
- Evidence: F9 (random ids, 10/20); F18 (the retitled arrangement: `dropped_held_newer` 20/20, stale value current 20/20).
- Resolution: write two `/v1 new_topic` under distinct titles, read the ids, write March 15 through `/v1` onto the lower id and April 20 onto the higher, then a labelled setup `PATCH title` (title only) and a `/v1 extend_topic` with `fields: []` to trigger the scan. All 20 repetitions then meet the precondition. The baseline cannot retitle and falls back to upsert (0/20, pass).
- Lesson: a random-id merge that keeps the lower id is still fully arrangeable from `/v1` plus a title-only setup write; do not treat chance as a measurement of the merge. The title edit is an editor-path arrangement, listed in the deviations table.

### Ticket 10: the storyline is a measurement, but a check must return a scorecard row
- Date: 2026-10-20
- Expected: the storyline (triage counts, reinforcement precision) is one more check in `demo/checks/`.
- Observed: `Check.execute` demands one `Verdict` per declared `Row`, and the runner builds the scorecard from every declared row, so a storyline "row" would appear in the scorecard and its counts, which the spec lists without it (story 8) and which reinforcement precision (no verdict, story 14, 40) must not join.
- Evidence: `Check.execute` raises `ValueError` when the returned rows differ from the declared ones (`demo/checks/__init__.py`); the Storyline run in F20 (`demo/results/20261020-104437/`) shows no Storyline row in the scorecard while its verdict is in `results.json`.
- Resolution: `Row` gained `on_scorecard: bool = True`; the storyline row sets it to `False`, so the runner leaves it off the scorecard but keeps its verdict, with the triage and reinforcement numbers in `measurements`, in `results.json` and the snapshot; `demo/storyline_tables.py` renders the tables from those measurements and the runner appends them to the printed scorecard.
- Lesson: a measurement that is not a verdict still needs a home in the check model; flag it on the row rather than special-casing its id in the scorecard.

### Ticket 10: the first storyline had nothing to triage
- Date: 2026-10-20
- Expected: some questions end as search or memory failures on a smoke run.
- Observed: the first draft stored 11 topics, so `top_k` 8 returned most of the store and all 15 questions were answered (old F14, superseded).
- Evidence: the first-draft run's output was not kept (only the superseded F14 text), so this is not reproducible from the repo; the recorded run after the change is F20 (`docs/findings.md`, run `20261020-104437`: 15/15 correct, ranks 1-3 of 14 topics).
- Resolution: dropped two low-value updates and spent them on look-alike distractors (Website Redesign Phase 2, Marketing Budget, Design Review Meeting) and paraphrased questions. 29 of 30 events used. The recorded run after that change is the storyline F-entry; failures are not tuned for.
- Lesson: a retrieval triage needs confusable neighbours, not just a topic count above `top_k`.

### Ticket 10: a Storyline-only run printed an empty per-step change table
- Date: 2026-10-20
- Expected: the per-step change table appears only when a scorecard row ran on upstream or a patch step (a baseline-only run has none).
- Observed: the smoke run (`--checks Storyline --systems upstream,baseline`) printed an empty table: `measured(verdicts)` treats the off-scorecard Storyline verdict as an upstream measurement.
- Evidence: the 10-storyline worktree's `demo/results/20261020-104437/` (git-ignored): `results.json` `change_table` = `{"chain": ["upstream","step1","step2","step3"], "measured": ["upstream"], "changes": {}}`, and `scorecard.md` holds a `### Per-step change table` with an empty body.
- Resolution: `save` counted chain systems from verdicts whose row is on the scorecard, but `changes_per_step` and `render_change_table` still got the raw verdicts, so a Storyline-only run with a patch step still wrote `measured: []` beside `changes: {"step1": []}`. `save` now filters to scorecard verdicts once and passes that list to all three; `tests/test_changes.py::test_a_storyline_only_run_has_no_measured_systems_and_no_changes_for_the_steps` covers it.
- Lesson: anything that decides "was this system measured" from the verdict list must skip rows with `on_scorecard=False`, not only the scorecard renderer; filter once and pass the filtered list to every consumer.

### Ticket 06: empty and null writes are accepted and become current `report:`
- Expected: `version_field` with `""` or `null` is rejected and April 20 stays current (or at least the empty value does not replace it).
- Observed: both writes returned 200; current became `""` and `None` (F21). [INFERENCE] from reading the code: `FieldWrite.value` is typed `Any`, so `null` passes validation, and `/v1` has no empty-value guard (the chat tool does). The run shows only that both writes are accepted.
- Evidence: F21; `demo/results/20261020-105907/snapshots/upstream/c4.json`.
- Resolution: both empty cases fail on upstream; the baseline fails them the same way. The C4 row is **partial** on upstream because the update and archive cases still hold.
- Lesson: an implied C2/C4 postcondition is not enforced on `/v1`; the run, not the type annotation, decides the empty-write case.

### Ticket 06: 501 writes leave 500 entries and drop the first `report:`
- Expected: the `[INFERENCE]` that `max_history=500` drops the oldest is decided by a run.
- Observed: after 501 writes to one field (1 `new_topic` + 500 `version_field`) the stored history length is 500, `v000` is gone, newest is `v500`.
- Evidence: F21, `measurements.history_cap`; `demo/results/20261020-105907/snapshots/upstream/c4.json`.
- Resolution: the cap case fails on upstream. The run proves that a 500-entry cap exists on the `/v1` path and that it drops the oldest; where the cap lives (`TopicFields.cap_history` unused, the slice in `graph_store.py`) is [INFERENCE] from code reading.
- Lesson: a documented cap that is not called can still be real on another path; the 501-write case measures the path `/v1` actually takes.

### Ticket 08: the forgetting pass runs, but the natural trajectory never archives anyone `report:`
- Date: 2026-10-20
- Expected: C5's natural trajectory might show some archived topics as the store grows to 2,000.
- Observed: C5-1 **pass** (a 0.01 canary is archived at 501 topics on upstream and step 1). C5-2 **fail**: archived = 0 at every ramp size (F22, same as F10). Default salience is 1.0 and only rises; nothing falls below 0.05 without a setup write.
- Evidence: F22; `demo/results/20261020-110721/results.json` (pre-split) and `/home/zeyad/work/agent-systems-demo-wt/rf-g4/demo/results/20261020-115404/results.json` (C5-1 pass, C5-2 fail, archived 0 at every n on upstream and step 1).
- Resolution: mechanism and natural trajectory are separate rows; the mechanism proves the pass exists, the natural trajectory proves it never fires on ordinary undated writes.
- Lesson: a working forgetting implementation can still leave C5's bound unmet if nothing ever decays.

### Ticket 08: one check for two C5 rows linked every ramp snapshot to the mechanism cell
- Date: 2026-10-20
- Expected: each scorecard row links only the databases it used (C6's pattern: one check per row).
- Observed: the smoke ran C5-1 and C5-2 as one function, so both cells listed the mechanism snapshot and all five ramp snapshots.
- Evidence: run `20261020-110721` (combined snapshot lists) vs `/home/zeyad/work/agent-systems-demo-wt/rf-g4/demo/results/20261020-115404/results.json` (C5-1 cells list only `c5-1--c5-mech.json`, C5-2 cells only the five `c5-2--ramp-<n>-r1.json`).
- Resolution: split into two `@check` functions so C5-1 opens only `c5-mech` and C5-2 opens the ramp DBs. Verdicts unchanged; run 115404 has the split snapshot lists.
- Lesson: two rows in one `execute` share the session's snapshot list; follow C6 when the databases differ.

### Ticket 02: the `--patched` smoke run (`/health` + one ingest/query round trip) has no recorded evidence
- Date: 2026-10-20
- Expected: the ticket's smoke-run checkbox is backed by a journal or findings line with command, DB path and output (AGENTS.md: a behaviour claim needs a reproducing run).
- Observed: the review found no recorded `/health` or `/v1` output for `scripts/run_memstate.sh --patched`. What exists: a LadybugDB directory `.runtime/memstate-ladybug-20261020-094609/` with a `.lbug` file and a 20 KB WAL, and two empty directories (`memstate-ladybug-20261020-094747/`, `memstate-kuzu-20261020-094751/`). [INFERENCE] the WAL fits a round trip and the empty directories fit startup-only checks; nothing records that the endpoints answered.
- Evidence: none recorded. The later step-1 recorded run (F16, `/home/zeyad/work/agent-systems-demo/.runtime/gem-suite/20261020-101946/step1-c1/memstate.lbug`, engine line `MemState engine module: ladybug`) shows the `--patched` server answering `/health` and C1's ingests and queries, but that run postdates ticket 02 and is not the ticket's own smoke run.
- Resolution: recorded on 2026-10-20 after the review. Command: `flock /home/zeyad/work/agent-systems-demo-wt/server.lock bash scripts/run_memstate.sh --patched /home/zeyad/work/agent-systems-demo/.runtime/smoke-02-patched-20261020b/memstate.lbug`, then `curl localhost:8765/health` -> `{"status":"ok"}`; `/health/graph` -> `"path":"/home/zeyad/work/agent-systems-demo/.runtime/smoke-02-patched-20261020b/memstate.lbug"` (the `backend` key still says `kuzu`: upstream's label); `POST /v1/ingest` (new_topic `Website Redesign`, field `Deadline = March 15`) -> `applied: [created_topic:..., field:Deadline]`; `POST /v1/query` with `{"q": "Website Redesign deadline"}` -> candidate `Website Redesign` with `Deadline` current `March 15`. Startup lines: `MemState engine module: ladybug`, `MemState source folder: /home/zeyad/work/agent-systems-demo/MemState-patched/src`. Ports free afterwards. Note: the first attempt sent `{"query": ...}` and got 422 (`q` is the field name). `MemState-patched` HEAD was `089b823` (the engine port, one commit above `945d7c4`).
- Lesson: record the one-line command, DB path and output of a smoke checkbox when it is run, not afterwards.

### Ticket 10 (review): the first change-table fix filtered only one of three consumers `report:`
- Date: 2026-10-20
- Expected: after the Storyline-only fix, a run of `--checks Storyline` with a patch step wrote no change-table data (spec `on_scorecard` rule in `demo/checks/__init__.py`).
- Observed: the review read `demo/run.py` and found `save` filtering the verdicts for `measured()` only; `changes_per_step(rows, verdicts)` and `render_change_table(rows, verdicts)` still got the raw list, so `--checks Storyline --systems upstream,step1` would write `measured: []` beside `changes: {"step1": []}`. Reproduced in-process with the baseline registered under the step ids: `tests/test_changes.py::test_a_storyline_only_run_has_no_measured_systems_and_no_changes_for_the_steps` failed (`changes == {'step1': []}`) before the fix.
- Evidence: that test, failing then passing (`pytest -q tests/test_changes.py`); fix commit on branch `gs-rf-g1` in `demo/run.py` (`scored` list passed to all three calls).
- Resolution: filter once (`scored`) and pass it to `measured`, `changes_per_step` and `render_change_table`.
- Lesson: when a rule says "iterate rows, not verdicts", filter at the one place verdicts enter the report and hand the filtered list on, rather than at each consumer.

### Ticket 01 (review): `from_cases` shows no sign that a case was skipped
- Date: 2026-10-20
- Expected: a `pass` on one applicable case reads differently from a `pass` on all cases.
- Observed: the baseline's C1 `pass` rests on one case (the history case is `held=None`, F13), and the scorecard cell showed only `pass`.
- Evidence: F13 (`docs/findings.md`): baseline `temporal read returns the full history` at `held=None`; `tests/test_verdict.py::test_a_verdict_resting_on_fewer_cases_than_were_run_says_so_in_its_scorecard_cell`.
- Resolution: the cell now reads `pass (1 case n/a)`; the not-scored rule stays "no case applied" and the `Verdict` docstring says so. The spec's wording ("not-scored only for C2(b)'s neither-outcome rule") is not changed; the spec owner may still ratify the broader rule.
- Lesson: a nothing-value that changes what a verdict rests on belongs in the cell, not only in the snapshot.

### 2026-10-20 Ticket 03 (review fix): a clean worktree left detached at the step was never returned to `bitemporal` `report:`
- Expected: a step run ends with `MemState-patched/` on `bitemporal` ("returns to `bitemporal` when done, including on error").
- Observed: the first fix of the "teardown moved a worktree its setup had refused" entry made the teardown return only if `setup` moved HEAD. A crashed earlier run leaves a clean worktree detached at the very commit the step selects; `setup` then moves nothing, so the teardown skipped the return and the worktree stayed detached.
- Evidence: `tests/test_steps.py::test_a_clean_worktree_already_detached_at_the_step_is_still_returned_to_the_branch` on a throwaway git repo: failed first (`assert '' == 'bitemporal'`), passes with the fix.
- Resolution: the teardown returns once `setup` completed the checkout (also when HEAD was already there) or when a failing `setup` left HEAD elsewhere than it found it; a refused `setup` (dirty tree, operation in progress) still leaves everything as it was.
- Lesson: "undo what setup did" is not "undo only when HEAD moved"; the end state the ticket names (back on the branch) holds whenever setup got as far as accepting the checkout.

### 2026-10-20 Ticket 05 (review fix): C2(b) missed a partial commit on a live server `report:`
- Expected: an ingest that errors after persisting the topic or its fields scores `fail` (spec story 21) on every system, live mode included.
- Observed: the check looked for stored topics with `title == "Website Redesign"`; `LiveSystem` stores titles as `Website Redesign [live C2(b) HHMMSS]`, so a partial commit in live mode was found as "nothing persisted" and scored not-scored.
- Evidence: `tests/test_c2b_c2c_c3.py::test_a_partial_commit_is_found_when_the_system_stores_titles_with_a_scope_suffix` (a baseline subclass that stores the suffixed title, then errors): failed first (`'not-scored' == 'fail'`), passes now. No MemState run involved.
- Resolution: the check reads `describe()["title_scope"]` (as the storyline does) and matches the stored title with the suffix, and matches by `topic_id` when the response names one.
- Lesson: a check that looks a topic up by title must go through the same title scoping the adapter applies; test it on a system whose stored titles differ from the written ones.

### 2026-10-20 Ticket 04 (review fix): the "dropped holds the newer value" precondition was recorded but not enforced
- Expected: every counted C2(a) repetition has the dropped topic hold the newer value (spec story 20).
- Observed: the check recorded `dropped_held_newer` but a repetition in which the newer topic survived still counted as a held case. The baseline's `results.json` also reported `merged: 20` next to `window_samples: 0`, because an upsert is returned as merged.
- Evidence: `tests/test_c2a.py::test_a_repetition_in_which_the_newer_topic_survived_is_not_a_case` and `::test_the_baseline_counts_its_upserts_apart_from_merges_and_has_no_window` (generic stand-ins, no MemState verdict pinned). The recorded upstream run (F18) is unaffected: `dropped_held_newer` 20/20.
- Resolution: such repetitions are `held=None` and counted as `arrangement_not_met` (a row with no counted case is not-scored); upserts are counted under `upserted` and real merges under `merges`. The duplicate pair made by a labelled setup `PATCH title` is now a row in the deviations table. The `random_id_counts` measurement (a 10/20 style count for the change table) is dropped: its only producer was this check, the arrangement made the outcome deterministic, and the key duplicated `violations`.
- Lesson: a precondition that is only recorded is not a precondition; and a measurement kept "for later" with one producer and no reader rots.

### 2026-10-20 Ticket 05 (review fix): C3's 5 s wait was shorter than the merge wait and started after the read
- Expected: background revision is awaited long enough that a slow Reasoner is not misread as absent (spec story 29); the window runs "from the update".
- Observed: `REVISION_WAIT_S` was 5 s against 15 s for the C2(a) merge wait, and the timer started after the `/v1/query` that follows the update.
- Evidence: F17 (the recorded run waited 5 s and shows `timed_out: true` after 5.034 s and 5.048 s); `tests/test_c2b_c2c_c3.py::test_the_wait_is_counted_from_the_update_not_from_the_end_of_the_read_after_it` and `::test_a_revision_that_arrives_late_is_still_seen_and_the_window_includes_the_delay`.
- Resolution: the wait is the merge timeout (15 s), counted from the update's response; the window is that elapsed time. The upstream C3 row has not been re-recorded with the 15 s wait (F17 says so).
- Lesson: one background-effect timeout for the suite, not one per check.

### 2026-10-20 Ticket 05 (review fix): C2(c) raised on any substring that looked like policy
- Expected: only a genuine policy-bearing route or schema stops the row from being scored absent.
- Observed: any path, schema or property name containing `polic|rule|constraint|invariant|trigger` as a substring (`triggered_at`, `ruleset_version`, a `trigger_count` on a stats model) turned the row into an `error` verdict.
- Evidence: `tests/test_c2b_c2c_c3.py::test_policy_words_only_inside_other_words_or_property_names_do_not_stop_the_row` and `::test_a_route_or_schema_named_for_policies_is_not_scored_absent`. F17's recorded upstream run had no hit under either rule.
- Resolution: whole words (camelCase and punctuation split) of route paths and schema names; property-name hits are recorded in the probe evidence only. The spec allows only the C2(b) not-scored rule, so a real policy surface still raises until a person extends the probe.
- Lesson: a guard that fails the run should be as narrow as the thing it guards.

### 2026-10-20 Ticket 06 (review fix): the cap mechanism claims in F21 and the journal had no `[INFERENCE]` tag
- Expected: claims from reading the code carry `[INFERENCE]` (AGENTS.md).
- Observed: F21 and two journal entries stated that `TopicFields.cap_history` is unused, that the cap is the slice in `graph_store.py`, and why `null` passes validation, as results; the run shows only that a 500-entry cap exists on the `/v1` path, drops the oldest, and that empty and null writes are accepted. The cap case was also described as "501 updates" while it makes one `new_topic` and 500 `version_field` writes.
- Evidence: F21 and `demo/results/20261020-105907/snapshots/upstream/c4.json` (history length 500, `v000` absent, newest `v500`).
- Resolution: the mechanism clauses are tagged `[INFERENCE]`; F21, the journal, the case name and the README say "501 writes (1 `new_topic` + 500 `version_field`)".
- Lesson: write the observation first and the mechanism as a labelled guess; count what the check actually sends.

### Ticket 07 review: C6-2 returned not-scored where the spec allows only pass/partial/fail `report:`
- Date: 2026-10-20
- Expected: C6 clause 2 follows the spec's Verdict model, where not-scored is reserved for the C2(b) "neither outcome" rule; a pass that could not be shown to have run is graded like the C5 mechanism's gate-only outcome.
- Observed: when the never-read control topic was not archived after the filler topics, `c6_clause_2` returned `not_scored`. That is the unconditional not-scored verdict the spec does not allow outside C2(b). The user's question on the right grade was cancelled before an answer; the recommended default was applied.
- Evidence: `tests/test_c6.py::test_clause_2_is_partial_when_the_control_shows_no_forgetting_pass_ran` (in-process, `BumpingStore(forgets=False)`: cases `[True, False]`, verdict partial; failed first with `not-scored`). Review reports `Rev07Spec` (HARD) in `notes/review-reports-final.md`.
- Resolution: the NOT_SCORED branch is gone. When the control is not archived the "left forgetting eligibility" case does not hold, so the row is `partial`: reinforcement held, forgetting not demonstrated; the observation says so. **Decision taken without the user's answer (question cancelled): `partial` is the recommended default; change it if the user prefers `fail`.**
- Lesson: a verdict outside the scale is a spec departure even when it feels more honest; use the scale and put the nuance in the observation.

### Ticket 09 review: `history_intact` read the query response and passed vacuously `report:`
- Date: 2026-10-20
- Expected: the patch's history-intact check ("no value lost; shortened entries carry `expired_at` with a copy linked by `replaces_entry_id`") inspects the stored entries.
- Observed: `_history_case` read `system.query(read_request(..., explain=True))`; upstream's query output type carries no `expired_at` or `replaces_entry_id` [INFERENCE: reviewer's code reading of `executor.py` `FieldVersionOut`; not run], so the "expired entry without a copy" check had nothing to inspect and would pass on a patch whose stored history is broken.
- Evidence: `tests/test_time_probes.py::test_the_history_case_fails_on_a_stored_defect_the_query_response_does_not_show[no_copy|unshaped]` failed first (the history case held) against a generic `HistoryStore` whose query response omits `expired_at` while `read_topic` has it; they pass after the change. In-process only; not run against the patch (tickets 12/13).
- Resolution: the case reads `read_topic(topic_id)["fields"][field]` and `history_intact` also fails when entries lack the `expired_at` key.
- Lesson: read a check's evidence from the endpoint that holds the full stored state; a check that cannot see the field it grades passes vacuously.

### Ticket 08 review fix: single-sample query latency was noise, so the ramp table had no median or range `report:`
- Date: 2026-10-20
- Expected: the latency table gives a median and range per (system, n) and calls a difference inside the range "no measurable difference" (spec story 43), for ingest and query.
- Observed: each ramp recorded one query read, so query had no range. The same cell varied between runs: upstream n=500 query was 218.924 ms in run 110721 and 321.351 ms in run 114251 (scorecards of the two runs; nothing about upstream changed). The table also printed one row per repeat, listed the baseline next to HTTP systems, and the "Reasoner wait" column was only the 0.1 s poll floor (the baseline, which has no Reasoner, also showed about 0.1 s).
- Evidence: `/home/zeyad/work/agent-systems-demo-wt/08-topic-ramp/demo/results/20261020-110721/scorecard.md` and `.../20261020-114251/scorecard.md` (row `upstream | 500`); new run `/home/zeyad/work/agent-systems-demo-wt/rf-g4/demo/results/20261020-115404/results.json` (5 reads per ramp; upstream n=500 query median 232.838 ms, range 219.635–256.71) and F22.
- Resolution: ramps take `QUERY_SAMPLES` (5) plain reads; `demo/latency_tables.py` aggregates per (system, n) to median and min-max for ingest, query and settle time, applies the no-difference rule to ingest and query between adjacent chain steps only, and skips systems whose C5-2 verdict is absent. The column is "settle time (poll floor 0.1 s)"; no Reasoner claim. C5 constants are read through `demo.ramp`. F22 re-recorded with 1 repeat; the LadybugDB vs Kuzu gap is marked provisional.
- Lesson: one latency read per cell cannot be compared across runs; take several reads and report the range before drawing an engine comparison.

### C2(b)'s input never exercised atomicity `report:`
- Date: 2026-10-20
- Expected: an edge to a missing topic would make upstream's ingest fail partway through, so C2(b) could tell an atomic commit from a partial one (spec story 21).
- Observed: the edge step is a `MATCH … MERGE` that silently does nothing, so the ingest succeeds and C2(b) came out not-scored (F17). While ratifying the verdict rule, I first recommended scoring that outcome `fail`, reasoning from the paper's "commits atomically or aborts". The user challenged that reasoning, and the code showed it was wrong: no step failed, so nothing was aborted or partly committed. A field `ref_topic_id` is validated mid-write, though, and a probe using it shows a real partial commit: HTTP 400 with the topic and first field stored (F23).
- Evidence: F17 and F23 in `docs/findings.md`; `tests/test_c2b_c2c_c3.py::test_accepting_the_missing_reference_means_atomicity_is_not_testable`.
- Resolution: proposed in "Ratify verdict rules set during the build": C2(b) switches its input to a field `ref_topic_id` pointing to a missing topic; the edge case stays as a soundness observation.
- Lesson: before scoring an outcome against a guarantee, check in the code that the test input actually reaches the guarantee's failure path.
### The "precise reading of C1" framing did not survive an adversarial review `report:`
- Date: 2026-10-20
- Expected (2026-10-20): C1′ could be presented as the precise reading of C1 (report §1 item 13, §7.5), and a reference GEM built to C1–C6 would show "the gap is in the conditions" (ticket 37).
- Observed: the two framings contradict each other. The challenge list (`.scratch/interview-package/assets/challenge-conditions-baseline-suite-probes.md`, C1 and C2) computed each reading of Definition 4 over `demo/time_stories.py`: reading `t` as valid time fixes T1 and T2. A cut-off at the question date fixes T3 and T6. T4 needs an end date and T5 a second timestamp, neither of which Definition 4 has. The same review found that plain Graphiti fails T3, T4 and T6 by code reading [INFERENCE], and that the dict baseline cannot back "database guarantees are necessary but not sufficient".
- Resolution: "Answer the challenge list": C1′ is an amendment (one clarification, two additions); reference GEM phase 1 uses the kindest reading; the model is described as "standard bitemporal, in the form Zep uses"; the baseline becomes a versioned row.
- Evidence: `.scratch/interview-package/assets/challenge-conditions-baseline-suite-probes.md` (C1 and C2 computed over `demo/time_stories.py`); plain Graphiti failing T3, T4, T6 is by code reading, not a run.
- Lesson: before claiming a definition is a reading of the paper's, compute what the paper's own wording returns on each test case; and run an adversarial review of the claims before building to them.

### A README grep missed the authors' own "NOT Full Implementation"
- Date: 2026-10-20
- Expected: a pattern search of `MemState/README.md` for "not implement|prototype|partial|…" would surface any completeness disclaimer.
- Observed: it matched only line 107 ("research prototype… proof-of-concept"). I told the user the README never says it is incomplete. The heading at line 5 reads "(It is Proof-of-Concept, NOT Full Implementation)", which a search for "full implementation" found.
- Resolution: ADR 0002 cites `MemState/README.md:5`.
- Evidence: `MemState/README.md:5` (heading) and `MemState/README.md:107`; cited in `docs/adr/0002-absent-verdict-for-unimplemented-conditions.md`.
- Lesson: before denying that a source says something, search for the user's exact words, not only my paraphrases of them.

## 2026-10-21

### "Any schema" date detection reads upstream as accepting `valid_from`
- Date: 2026-10-21
- Expected: searching every schema in `/openapi.json` for each date key (spec: "one flag per date, read over all schemas") gives all four flags False on upstream, as the combined flag did.
- Observed: the first smoke run of the four-flag adapter raised on every probe: `valid_from` is a property of upstream's history-entry response model (`MemState/src/memstate/datamodel/fields.py:39`), so `valid_from` read True and the adapter refused the `history[0]` fallback on an upstream topic. The old rule (`valid_from` and `invalid_at` in one schema) had hidden this.
- Evidence: `tests/test_time_probes.py` (line 323: `request_date_fields` on a schema whose response model returns `valid_from` gives an empty set; line 324: `valid_from`/`valid_at` read from request models); `MemState/src/memstate/datamodel/fields.py:39`; commit d3c631b.
- Resolution: `request_date_fields` (`demo/memstate_system.py`) reads a date from the models reachable from a request body (through `$ref`, `items`, `anyOf`), by use not by name; a response model that returns `valid_from` does not count. Departure from the spec's "all schemas" wording; unit-tested on a schema document with a response model carrying `valid_from`. Re-run: all four flags False, all six probes absent.
- Lesson: a field's presence in some schema says nothing about direction; check which models a request uses before reading a capability from the schema.

### Departures from the ticket wording
- Date: 2026-10-21
- Expected: the ticket wording of the time-probe verdicts; T5 needs `valid_from`, `valid_at` and `recorded_at` per the ticket's table, and the pre-registered versioned-row cell reads "absent (accepts `recorded_at`, not `valid_at`)".
- Observed: T5 is `absent` when any of its needed dates (`valid_from`, `valid_at`, `recorded_at`) is not accepted, not only `recorded_at`. It is `fail` when all three are accepted and the two answers are identical. A system that accepts `valid_at` but none of a probe's needed dates gets the plain read (same writes undated), as the spec says for "accepts none of the needed dates"; if any needed date is accepted, `valid_at` is sent whenever the system accepts it, also on T1, T2, T3, T4 and T6, whose needed lists do not name it.
- Evidence: commit d3c631b ("Score time probes per needed date: four accepts flags, absent when a needed date is not accepted, T5 fail rule…"); `tests/test_time_probes.py`.
- Resolution: as built, with the departures above. The absent verdicts carry no cases; the answers are in `probe_evidence.stories.<id>.asked`.
- Lesson: none recorded.


### Ticket 20: the versioned row's expected verdicts depend on checks that later tickets rewrite `report:`
- Date: 2026-10-21
- Expected: swapping the baseline for the versioned row (append-only history with recorded time, one transaction per write, empty and `null` rejected, top 8) gives the spec's "Expected verdicts" column on the checks as built.
- Observed: three rows differ from the column only because of the check, not the row. (1) C2(a) and C4's merge case scored a same-topic append as a held case (`pass`), because an upsert was treated as "nothing dropped"; the arrangement cannot be met when no duplicate exists, so both are now `n/a` (C2(a) reads `not-scored`). (2) C6 scored a system that tracks no salience `fail`; the spec now says `absent` confirmed by a probe, so both clauses return `absent` with the salience read as the evidence (this supersedes ticket 07's entry above). (3) C2(b) on the edge-to-a-missing-topic input reads `not-scored` (the row stores no edges and reports none applied), while "Expected verdicts" says `pass` after ticket 22 (the time probes read `absent` once ticket 21's per-probe date detection merged).
- Evidence: `tests/test_c2a.py`, `tests/test_c4.py`, `tests/test_c6.py`, `tests/test_c2b_c2c_c3.py`, `tests/test_time_probes.py` (baseline tests).
- Resolution: (1) and (2) fixed in the checks in this ticket; (3) C2(b) is pinned as built (`not-scored`), its flip to `pass` left to ticket 22.
- Lesson: pre-registering a verdict for a system is also pre-registering the check's arrangement; run the check on the stand-in before trusting the column.

### Ticket 22: revised checks, and where the build departed from the ticket wording
- Date: 2026-10-21
- Expected: apply the spec's revised checks to C2(a)/(b), C4, C5, C6 and add C2(d); smoke on upstream and step 1 reproduces the "Expected verdicts" (C2(b) fail, C2(d) pass, C4 partial with one n/a, C6 clause 2 pass).
- Observed: all five matched. Departures: (1) the versioned row needed a foreign-key check (`ref_topic_id` must name a stored topic) to read C2(b) `pass`; it is the same all-or-nothing rule ticket 20 gave it. (2) C2(a) is now one case (existence) instead of twenty; the per-repetition rows stay in `measurements.per_repetition`. (3) C4's real-forgetting case drives the forgetting pass with field-less fillers and a field-less control at 0.01 (the control shows the pass ran), so "n/a, confirmed by the run" needs no editor write; the cap case reads archived overflow from a field's `archived_history` key, which is a new adapter contract for the reference GEM. (4) `describe()` gained `declared_bound` (upstream: 500, `topic_count_soft_limit`; other systems must declare theirs for C5's text). (5) C6 clause 2 looks for a forgetting pass after each read and only forces one if none was seen; the filler ingests themselves are not observed one by one.
- Evidence: `docs/findings.md` "Revised checks on upstream and step 1"; tests in `tests/test_c2a.py`, `test_c2b_c2c_c3.py`, `test_c2d.py`, `test_c4.py`, `test_c5.py`, `test_c6.py`.
- Resolution: as built.
- Lesson: a check's n/a on one system needs the run to show the pass happened (the control), otherwise "cannot be forgotten" and "forgetting never ran" read the same.

### Ticket 17: the bad-merge chat run
- Date: 2026-10-21
- Expected: asking Q02 plus questions on fields only the original topic held would show a loss on those fields after the merge (ticket 17 comment, 2026-10-20).
- Observed: upstream's merge copies a field the keeper lacks, so `Team` and `Status` survived with their histories (F25); only the history of a field both topics hold (`Deadline`) is lost. The turns on Q06 and Q11 therefore record no state violation, and the C4 contrast rests on Q02's field.
- Observed: the chat answer is not stable across takes of the same state. Take 1 (recording deleted by mistake while re-recording after a matcher fix; its replay output: Q02 "April 20", Q06 correct, Q11 "I don't know" with a false-positive word match on "completed") ; take 2 answered Q02 "I don't have access to that information" (kept in `demo/recordings/attempts/`); take 3, the case on the scorecard, answered all three correctly. The kept take is the one that shows the "answer looks right" contrast the ticket asks for, chosen with the other two disclosed; no claim about how often a 2B model answers right follows from n = 1.
- Evidence: F25 in `docs/findings.md` (fields only the original held are copied; Deadline history lost); `tests/test_chat_run.py::test_the_word_match_needs_every_word_of_the_ground_truth_and_no_longer_word` (whole-word match); takes in `demo/recordings/attempts/`.
- Resolution: the answer-versus-ground-truth hint is a whole-word match (a substring match read "completed" as "Complete"); every turn keeps an empty hand-grade slot. Recording from a worktree: the venv, `MemState/` and the Ollama state live in the main checkout (`demo/paths.py`); the command in a recording uses the interpreter it was run with.
- Lesson: a recorder should refuse to delete its own evidence: re-recording to fix a rendering detail cost the first take. Fix the renderer, replay the old file; record again only for new evidence.
- Lock: this run held `/tmp/gem-suite-live.lock` (session rule); the README's command uses the repo's `server.lock` like the other runner commands.

### Committing in `MemState-patched/` trips the suite's pre-commit hook
- Date: 2026-10-21
- Expected: a commit on `bitemporal` goes through the shared hooks like any other.
- Observed: `.githooks/pre-commit` saw staged files under `tests/`, resolved the venv from the submodule's git dir (`.git/modules/.venv/bin/python`, not found) and reported the offline suite red. The hook is written for the suite's `demo/` and `tests/`, not for the submodule's own `tests/`.
- Evidence: `/tmp/pre-commit-pytest.*` from the failed commit.
- Resolution: committed step 2 with `git -c core.hooksPath=<dir holding only the commit-msg hook> commit`, so attribution stripping still ran; the patch's tests were run by hand first (57 passed). Not `--no-verify`.
- Lesson: patch-step commits need their own pre-commit story (the hook should skip when the repo is the submodule); later steps hit it again.

### Reference GEM phase 1: the written spec and the checks disagreed in four places (resolved without rewriting any expectation)
- Date: 2026-10-21
- Expected: the phase 1 column of "Expected verdicts" (C1-C6, T1, T2, T3, T6 pass; T4, T5 absent; C4′ pass) falls out of a build to the spec's parameter table, with `describe()["accepts"]` true for `valid_from` only.
- Observed: (1) with `valid_at` not accepted, the time-probe runner sends every non-"today" ask as a plain read, so T1, T2, T3 and T6 would fail their control dates; Definition 4's "latest timestamp not after the asked date" needs an asked date. Phase 1 therefore accepts `valid_from` (writes) and `valid_at` (reads); `invalid_at` and `recorded_at` stay unaccepted, so T4 and T5 read absent as pre-registered. (2) The time probes' history check refuses entries without an `expired_at` key as "not patch-shaped"; phase 1 entries carry `expired_at: None`. (3) C6 clause 2 seeded at 0.06 starts above θ, so the check's loop (read until the topic leaves eligibility) never ran and the forced pass archived the target too; the check now reads on every interaction until the first forgetting pass when the system declares seeds at or above θ (`describe()["c6_clause_2_seeds"]`, new; default `None` keeps 0.03/0.01 and the loop as it was). (4) Reinforcement precision measured by salience differences would count decay as negative increments; `triage._increment` counts rises only (a fall is decay, not an increment); no other system's number changes.
- Evidence: `tests/test_reference_gem.py`, `tests/test_c6.py::test_a_system_declaring_clause_2_seeds…`.
- Resolution: all four are in the code and the ticket comment; the pre-registered column is unchanged and met.
- Lesson: pre-register the request shape each probe sends (which date each ask needs), not only the verdicts. report: the phase 1 "accepts" cell is `valid_from` and `valid_at`.

### Reference GEM: with exponential decay, resetting the decay clock is not a restore
- Date: 2026-10-21
- Expected: "any read or write of a topic resets its decay clock" lets a touched topic live longer.
- Observed: if the touch materialises the decayed salience (s·λ^Δ) and restarts Δ, a write adds nothing and gives no extra life (the product of two decay factors equals one), apart from the touching interaction not decaying. If the touch instead keeps the stored salience and only restarts Δ, a read or write undoes the accrued decay: every returned topic rises by 0.1 plus a different recovered amount, so reinforcement precision would not be 1/8 and C6 clause 1's "rise by at least the bump per retrieval" would hold only by accident.
- Evidence: `tests/test_reference_gem.py::test_a_write_resets_the_decay_clock_without_changing_salience_and_a_retrieval_adds_0_1` (the built reading); commit 94f1843. The alternative reading was found by reasoning from the spec's wording; no run recorded.
- Resolution: the first reading is built (decay accrues over interactions of disuse; a touch at interaction n materialises interaction n-1's value, and a retrieval adds exactly 0.1). A retrieval keeps a topic alive through its bumps (+0.1 against a decay of 0.0075·s per interaction), a write does not. Declared in `demo/reference_gem.py`'s docstring.
- Lesson: report the decay rule as "decay accrues during disuse", not as "a read restores salience".

### Reference GEM phase 2: the pre-registered column held; four build decisions
- Date: 2026-10-21
- Expected: phase 1 → phase 2 changes exactly T4 and T5 (absent → pass) and no other row.
- Observed: it does (`tests/test_reference_gem_phase2.py::test_phase_1_to_phase_2_changes_exactly_t4_and_t5`: same verdict and the same held/broke list per case on every other row). No departure from the column. Decisions the spec left open: (1) the rules are ported from the patch (`patches/0002-bitemporal-field-histories.patch`: `resolve_valid`, `believed_at`, `write_entry`, `retract_entry`), so the reference and the patch cannot differ by accident; (2) a retraction has no adapter request (as on the patch, which has only a store method), so `ReferenceGem.retract(topic, field, entry_id)` is a public method and not an interaction; (3) a `valid_at` or `recorded_at` read returns the field's history (the "history request"), a plain read does not, and `recorded_at` shows an entry that expired since as live; (4) merge by valid time ends an end-dated entry that a plain entry of the other topic starts inside (keep and copy), tagged `merged` as on step 3.
- Evidence: `tests/test_reference_gem_phase2.py::test_phase_1_to_phase_2_changes_exactly_t4_and_t5`; commit 6a4f040 ("Reference GEM phase 2…").
- Resolution: phase 1's entry shape is unchanged (no `invalid_at`/`created_at` keys, `expired_at: None`); phase 2 adds them.
- Lesson: a phase is one mode flag on one class; the phase-1 suite stayed green untouched.

### Reference GEM workloads: both windows are 0 interactions, so the unit is what carries the information
- Date: 2026-10-21
- Expected: the merge revision window and the dependent-topic staleness window, in interactions, as ticket 30 predicts: 0 (revision runs after every ingest; the flag is raised in the same transition).
- Observed: both are 0 on both phases (`tests/test_reference_gem_workloads.py`). Polling reads of stored state are not interactions on the reference GEM, so a poll can never move the count: the window is the interactions between the trigger's response and the first read that shows the merge or the flag, and a probe's own query is subtracted (C3 reads B once right after the update). A system that does not count interactions (`read_state()["interactions"]` absent: MemState, the baseline) keeps seconds, unchanged. The pre-merge window is visible only with `revise_after_ingest=False`, where polling never revises, so `await_merge` times out; the test shows both copies and the merge after `revise()` directly.
- Evidence: `tests/test_reference_gem_workloads.py` (`test_merge_window_is_zero_interactions_with_revision_after_every_ingest`, `test_pre_merge_window_is_exposed_when_revision_is_held_back`, `test_dependent_topic_window_is_zero_interactions`, `test_windows_table_cites_the_interaction_unit`); commit b50347d; ticket `30-reference-gem-workloads-and-windows.md`.
- Resolution: `demo/windows.py::interactions` is the one place the unit is chosen; `await_merge` and C3 record `window_interactions`, the windows table prints "N interactions". The reference GEM runs C5-2's ramps (the archived counts and the 396 active at n=2000 against β need them) but is excluded from the latency table by `SystemSpec.latency=False`; chat runs are recordings of upstream only, so no chat cell exists for it.
- Lesson: report a window with its unit; "0 interactions" is a property of the design (revision in the same transition), not a measured latency.

### Ticket 15: step 3 developed in a private worktree; its commit hit the pre-commit hook again
- Date: 2026-10-21
- Expected: a commit in the private MemState worktree (`MemState-step3`) goes through `.githooks` like any other.
- Observed: the submodule's `core.hooksPath` points at the main checkout's `.githooks/`, which still has the version that runs the suite whenever `tests/` is staged, resolved the venv from `.git/modules/` and reported the suite red (same as step 2's commit).
- Evidence: `/tmp/pre-commit-pytest.*`; the tests had passed by hand (82 passed).
- Resolution: committed with `git -c core.hooksPath=<this branch's .githooks> commit`, whose pre-commit only runs the suite when both `demo/` and `tests/` exist (the submodule has no `demo/`) and whose commit-msg hook still strips attribution. Not `--no-verify`.
- Lesson: the main checkout's hook copy lags `gem-suite`; every patch-step commit needs the override until `gem-suite` merges to `main`.

### Ticket 15: step 3's duplicate scan returned stale pairs, and a three-way tie made the "one merged event" depend on pair order
- Date: 2026-10-21
- Expected: three same-title topics merge into one with every value; the survivor gets one `merged` event per merge.
- Observed: upstream computes the list of pairs once and merges them all; after (A,B) the list still holds (B,C) and (A,C), where B is gone. The first fix (rescan after each merge) passed, but the survivor's event count varied run to run: `find_duplicate_titles` had no order, so (B,C) could merge first and A would see one event, not two.
- Evidence: `tests/test_merge_by_valid_time.py::test_three_duplicates_merge_into_one_topic_with_every_value`, failing once in three runs before the `ORDER BY`.
- Resolution: rescan after each merge and order pairs by id, so the lowest id survives a tie and each merge adds its event to it.
- Lesson: an unordered query under a `LIMIT` makes a loop's outcome run-dependent; pin the order before asserting on counts.

### Ticket 32: the recorded folder had to link snapshots without rewriting the scorecard
- Date: 2026-10-21
- Expected: copying a run to `demo/record/<run id>/` needs its scorecard links rewritten to point there.
- Observed: the scorecard's snapshot links are already relative to the run folder (`snapshots/<system>/<check>.json`), so a verbatim copy of `scorecard.md` next to `snapshots/` resolves inside the record; a test follows a link in the copied file.
- Evidence: `tests/test_run_of_record.py::test_record_copies_scorecard_results_and_snapshots_but_not_logs`; commit 1b36a29 ("Run of record: copy a run to demo/record…"); ticket `32-run-of-record-folder-and-upstream-tests.md`.
- Resolution: copy verbatim; no rewriting.
- Lesson: keep links run-relative and a copy stays valid wherever the folder lands.

### Ticket 18: the two-weeks chat run
- Date: 2026-10-21
- Expected: two requests on step 3 ("I started my new job two weeks ago" at Oct 6, "how long have I been there?" at Oct 20, shifted to the run day) would store a start date for the first turn to be graded on and give the second something to read.
- Observed: MemState's router sent the first statement to `query` in every router-decided take (9/9 with the seeded takes), so the first turn runs on read tools; a 2B model on an empty database mostly asked what the job was and wrote nothing. 13 takes in four variants (F31): one spec-faithful take stored a start date (the right one, in the value; `valid_from` was the reference time), one seeded take stored a date one day off; no take answered "four weeks". A `query`-routed turn also executed `memory_create_topic` and `memory_append_field` (the tool log shows both succeeded).
- Evidence: `demo/recordings/two-weeks-20261021-033752.json` (the take of record) and 12 takes in `demo/recordings/attempts/`; F31 has the table.
- Resolution: the case follows the spec (empty database, no `intent_override`, nothing seeded). `--no-router-decides` (force W1 to `ingest`) and `--seed-profile` exist as variants because the router makes the spec's case rarely store anything; their takes are disclosed, not the case of record. I added both after the first takes, so four attempt files carry a command that now describes a different variant (the recording's `state` fields are authoritative). The take of record is the only spec-faithful take that stored a start date, picked among 7 router-decided takes; I did not rerun it to see whether it repeats.
- Lesson: choosing the take that shows the mechanism is a selection, so say how many takes there were and what the others did; and read the route the server reports before assuming a chat turn can write.
- Lock: every take held `/tmp/gem-suite-live.lock` and the repo's `server.lock` (13 times, one server at a time); Ollama and the proxy were started and stopped by the run each time; `MemState-patched` was on `bitemporal` and clean afterwards.

### Ticket 19: "the reference GEM runs no ramps" read as "runs C5-2's counts once"
- Date: 2026-10-21
- Expected: the run of record's box "the reference GEM runs no ramps and no chat" means no C5-2 ramp on the reference GEM.
- Observed: C5-2 has no system filter and its verdict rests on the active and archived counts at n=2000 (about 400 active against β = 500, `tests/test_reference_gem_workloads.py::test_c5_states_beta_beside_the_active_count_at_2000`); `SystemSpec.latency=False` only hid the latency table, so both phases still ran every size times `--ramp-repeats` and their milliseconds sat in `results.json`.
- Evidence: review of `92099d8...ec9e321` (spec axis, blocker 1); `demo/checks/c5_topic_ramp.py` before this change.
- Resolution: decided with the user: the reference GEM runs each C5-2 size once, with no repeats, no timing, no latency rows and no ramp milliseconds in `results.json` (`describe()["latency_comparable"]` is False; `SystemSpec.latency` is gone); it runs no chat. The reading is in the deviations table ("Reference GEM ramps"). Test: `test_c5_runs_each_size_once_and_records_no_milliseconds_on_the_reference_gem`.
- Lesson: a box that says "runs no X" needs the verdict that depends on X named beside it; here the verdict was the thing the ramp existed for.

### C4's expected verdict counts two n/a cases on upstream and step 1, not one
- Date: 2026-10-21
- Expected: ticket 22's "C4 partial, 1 case n/a" on upstream.
- Observed: the dated-merge case (added with step 3) is n/a on a system that accepts no `valid_from` (`demo/checks/c4_history.py`, `_dated_merge_case`), so upstream and step 1 read two n/a cases (the dated merge and real forgetting, F24) [INFERENCE: from the check's code, not re-run here]; step 3 reads one (F29: "C4 stays `partial` (the forgetting case is n/a, F24)"), and the versioned row reads n/a on the merge, dated-merge and forgetting cases (`tests/test_c4.py::test_c4_passes_on_the_baseline_with_the_merge_and_forgetting_cases_not_applicable`). No entry recorded the change.
- Evidence: `demo/checks/c4_history.py`, F29, `tests/test_c4.py`.
- Resolution: the verdict is unchanged (partial on upstream: the merge case breaks); the run of record states the n/a counts it measures.
- Lesson: when a later ticket adds a case, re-read the earlier ticket's expected count of n/a cases.

### Review fixes: the patch's graph snapshot and inner-field reads ignored the chat reference time, so `bitemporal` was rebuilt
- Date: 2026-10-21
- Expected: "the as-of time of that message's reads" (spec, chat) covers every read tool of a chat message.
- Observed: `memory_graph_snapshot` (`build_ui_graph_snapshot`) and `memory_get_field` by an inner field's name (`_find_nested_inner_field`) still read the current value as of now; the other reads took the reference time.
- Evidence: `MemState-patched/tests/test_chat_reference_time.py::test_the_graph_snapshot_is_as_of_the_reference_time` and `test_reads_of_a_nested_field_by_its_inner_name_are_as_of_the_reference_time` (both failed before the change; the patched copy's 84 tests pass with upstream's 39).
- Resolution: both take the reference time; commit 2 was amended and commit 3 rebased, so step 2 is now `2cfabee` and step 3 `cb5d48c`; `patches/` was re-exported as one series (`[PATCH n/3]`) and `git am` of it on `945d7c4` gives the tree of `bitemporal`. Earlier tickets' and findings' commit ids (`5f45848`, `5c5c9e6`) name the commits before this change.
- Lesson: when the spec lists what a time applies to, test each read path by name, not the one the first smoke run happened to use.

### The offline suite took 6.6 minutes on every commit that touched `demo/` or `tests/`
- Date: 2026-10-21
- Expected: a pre-commit suite of in-process tests runs in well under a minute.
- Observed: 439 tests took 6 m 37 s (`pytest --durations`): the mutation tests alone 214 s of setup. Almost all of it was waiting, not computing (user time 1 m 24 s): C2(a)'s "active topic merged into an archived duplicate" extra waits its full 15 s merge timeout on every in-process run (it times out by design there), and every one of about 15 reference-GEM runs of all the checks paid it; mutants that never forget also sat through several 20 s forgetting waits.
- Evidence: `pytest -q --durations=15` before the change (439 passed in 396.89 s, `tests/test_mutants.py::test_the_targeted_row_gives_a_non_pass_verdict[C1]` 214.31 s setup) and after (465 passed in 39.5 s).
- Resolution: `tests/reference_runs.py` shortens the merge timeout, the forgetting waits and the as-of gap (none changes a verdict), shrinks the C5 ramp for mutants only, and computes the unmutated runs once per session for the reference GEM and mutation tests; `c2a` reads `merge.DEFAULT_TIMEOUT_S` at call time so a test shortens it once. No marker and no test left out of the hook; the mutation tests now also cover C2(d), C5-1, C6-2 and T1-T3, T6 and check which case broke and that controls still hold.
- Lesson: when a suite is slow and the CPU is idle, look for timeouts that an in-process system always hits, before shrinking workloads.
