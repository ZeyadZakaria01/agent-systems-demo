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

### Ticket 01: C1 as written would fail the baseline, which §9.3 expects to pass `report:`
- Expected: the C1 check (default read returns only April 20, temporal read returns the full history) passes on both upstream and the baseline, as report §9.3 and the ticket predict.
- Observed: the baseline keeps no history, so its temporal read can never return `March 15`. Scored literally, the second case would fail the baseline, contradicting "C1 pass" for the baseline; the paper puts history preservation under C4, and C1's wording only restricts when prior values may appear.
- Resolution: the baseline's history reads as the nothing-value `None`; the C1 case "temporal read returns the full history" is recorded as not applicable (`held=None`, with the observation "the system keeps no history") and does not count toward the verdict. Upstream still has to return `['April 20', 'March 15']` for the case to hold. Verdict scale: `Verdict.from_cases` ignores `held=None` cases and gives `not-scored` only when none applies.
- Lesson: a check that needs a capability must treat a missing capability as "does not apply" (and say so in the evidence), leaving the capability's own row (C4) to score its absence.

### Edit tool resolved a relative path in the main checkout
- Expected: editing `README.md` with the cwd of the shell (the worktree) changes the worktree's file.
- Observed: the agent's working directory was the main checkout, so a relative `README.md` hashed to the main checkout's file; the edit was rejected (stale tag) before anything changed. `git status` in both checkouts stayed as expected.
- Resolution: use absolute worktree paths for every edit and read of repo files (the `cwd` of `bash` is separate from the edit tool's).
- Lesson: in a worktree-based build, address files by absolute path; a hash mismatch on a file just read is the signal that the wrong checkout was addressed.

### Ticket 09: the dated paths and the patch detection cannot be run yet `report:`
- Expected: build the time probes so the patch rows can flip later.
- Observed: the patch does not exist at this commit, so only upstream and the baseline were run. The flags `accepts_valid_time` (dated writes + `valid_at`) and `accepts_recorded_at` are read from every schema in `/openapi.json`, not by model-name prefix; upstream gives both False (proved by the smoke run). Ticket 12 lands the first without the second; T1–T4/T6 then use the dated path. The patch's True is [INFERENCE] until tickets 12/13 run it. The dated request construction is unit-tested as pure functions; the dated read/write path and `history_intact` against real patch entries are not.
- Resolution: an unreadable schema (`None` plus `accepts_error`) makes the time probes raise instead of guessing; a readable schema that simply lacks the keys is False, recorded in each row's `measurements`.
- Lesson: detect a capability from what the server declares, and say which parts were proven only on the side that exists.

### Ticket 09: the time-probe check is registered under its first row
- Expected: `--checks T5` selects the as-of probe.
- Observed: the runner selects a check by its id (the first row, T1) or any of its rows, but runs the whole check: all seven story servers start (measured 19 s on upstream, 2026-10-20 smoke `demo/results/20261020-101957`, seven fresh DBs) and every row's cell links all seven snapshots (`Verdict.snapshots` is per check). A smoke run for one row costs the whole check.
- Resolution: none needed; stories are the unit of freshness the spec asks for.
- Lesson: a multi-row check costs the sum of its rows; keep single-row checks apart when a row needs to be rerun alone.

### Ticket 07: C6 on the baseline is "fail", not "absent", and the suite's own reads must not bump salience `report:`
- Expected: baseline C6 fails both clauses with salience unchanged (spec "Baseline"), and salience can be read without disturbing it.
- Observed: the baseline reads salience as `None` (a nothing-value); scoring that as `absent` would need probe evidence and contradict the spec's "C6 both fail". On MemState every `/v1/query` adds +0.1 to each returned topic, including the suite's own reads, so a read-by-query would corrupt the salience being measured.
- Resolution: salience cases fail when salience is not tracked, with the observation "not tracked"; salience is read only through `read_topic` (`GET /api/ui/topics/{id}`, never bumps) and the only `/v1/query` calls are the counted retrievals, so the expected rise is the number of retrievals that returned the topic.
- Lesson: a measurement read must be a different endpoint from the operation being measured whenever the operation writes on read.

### Ticket 16: live output vanished when piped; one DB made same-title topics of later runs duplicates
- Expected: `python -m demo.run --mode live ... | tee log` shows each step as it happens, and a rerun against the same server starts clean.
- Observed: Python block-buffers stdout into a pipe/file, so the step lines and the `--step` prompt only appeared at exit (seen: a run log with only its first line while the run was mid-delay); and the second run reused `Website Redesign [live C1]`, an exact-title duplicate the Reasoner would merge.
- Resolution: live logging and the prompt `flush`; titles carry `<check> <HHMMSS of the run>` (`demo/live.py`).
- Lesson: anything a presenter watches must flush; "distinct titles per check" must also mean distinct across runs on one DB.

### Ticket 03: the step teardown moved a worktree its setup had refused `report:`
- Expected: a run that refuses a dirty `MemState-patched/` leaves it untouched ("refuses without damaging it").
- Observed (review, throwaway repo): HEAD detached at step 1 with a tracked file edited (a developer amending a step); `setup` refused, but `teardown` still ran `git checkout bitemporal` and carried the edit onto the branch (`53cfa9e` → `bitemporal 2e34735`, ` M g` still dirty). With an edit overlapping a file that differs between the commits the checkout would fail instead, only logged as a `teardown_error`. My test only covered a worktree already on `bitemporal`, where the checkout is a no-op.
- Resolution: `setup` compares HEAD and branch before and after; `teardown` returns to `bitemporal` only if it moved. The clean check also refuses a rebase, merge, cherry-pick, revert or bisect in progress. Tests cover a tracked edit on a detached HEAD.
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
- Observed: upstream never revises B, so the wait always times out; it can only say "not within 5 s", and a positive window can only be measured on a system that propagates (the tests use a fake).
- Evidence: F17 (both pairs: `March 20` before, right after and after 5.0 s with the wait timed out; upstream DBs under `.runtime/gem-suite/20261020-102020/upstream-c3/`).
- Resolution: the window reads "unbounded (C3 absent)" and cites the C3 run, which records the wait length (`revision_wait_s`); F7's fixed 2 s became a 5 s poll every 0.1 s. "B reflects" counts only B's fields, summary, kind, title or archived flag changing; events and salience do not.
- Lesson: report a window for an absent capability together with the wait that bounded the observation.

### Ticket 04: "dropped holds the newer value" is arrangeable without a forced id
- Expected: every C2(a) repetition has the topic that will be dropped hold the newer value (spec story 20).
- Observed: `/v1/ingest new_topic` assigns a uuid4 and the merge keeps the lower id (F9). Two same-title writes therefore make "dropped holds newer" a coin flip; the first recorded run's 7/20 stale-current rate measured that chance, not a merge defect. The journal previously said this was "only controllable with a forced id".
- Resolution: write two `/v1 new_topic` under distinct titles, read the ids, write March 15 through `/v1` onto the lower id and April 20 onto the higher, then a labelled setup `PATCH title` (title only) and a `/v1 extend_topic` with `fields: []` to trigger the scan. All 20 repetitions then meet the precondition. The baseline cannot retitle and falls back to upsert (0/20, pass).
- Lesson: a random-id merge that keeps the lower id is still fully arrangeable from `/v1` plus a title-only setup write; do not treat chance as a measurement of the merge.

### Ticket 10: the storyline is a measurement, but a check must return a scorecard row
- Expected: the storyline (triage counts, reinforcement precision) is one more check in `demo/checks/`.
- Observed: `Check.execute` demands one `Verdict` per declared `Row`, and the runner builds the scorecard from every declared row, so a storyline "row" would appear in the scorecard and its counts, which the spec lists without it (story 8) and which reinforcement precision (no verdict, story 14, 40) must not join.
- Resolution: `Row` gained `on_scorecard: bool = True`; the storyline row sets it to `False`, so the runner leaves it off the scorecard but keeps its verdict, with the triage and reinforcement numbers in `measurements`, in `results.json` and the snapshot; `demo/storyline_tables.py` renders the tables from those measurements and the runner appends them to the printed scorecard.
- Lesson: a measurement that is not a verdict still needs a home in the check model; flag it on the row rather than special-casing its id in the scorecard.

### Ticket 10: the first storyline had nothing to triage
- Expected: some questions end as search or memory failures on a smoke run.
- Observed: the first draft stored 11 topics, so `top_k` 8 returned most of the store and all 15 questions were answered (old F14, superseded).
- Resolution: dropped two low-value updates and spent them on look-alike distractors (Website Redesign Phase 2, Marketing Budget, Design Review Meeting) and paraphrased questions. 29 of 30 events used. The recorded run after that change is the storyline F-entry; failures are not tuned for.
- Lesson: a retrieval triage needs confusable neighbours, not just a topic count above `top_k`.

### Ticket 10: a Storyline-only run printed an empty per-step change table
- Expected: the per-step change table appears only when a scorecard row ran on upstream or a patch step (a baseline-only run has none).
- Observed: the smoke run (`--checks Storyline --systems upstream,baseline`) printed an empty table: `measured(verdicts)` treats the off-scorecard Storyline verdict as an upstream measurement.
- Evidence: `demo/results/20261020-104437/scorecard.md`; `results.json` `change_table.measured = ["upstream"]` with `changes: {}`.
- Resolution: `save` counts chain systems from verdicts whose row is on the scorecard; a Storyline-only run now has `measured: []` and no table.
- Lesson: anything that decides "was this system measured" from the verdict list must skip rows with `on_scorecard=False`, not only the scorecard renderer.

### Ticket 06: empty and null writes are accepted and become current `report:`
- Expected: `version_field` with `""` or `null` is rejected and April 20 stays current (or at least the empty value does not replace it).
- Observed: both writes returned 200; current became `""` and `None` (F21). `FieldWrite.value` is typed `Any`, so `null` passes validation; `/v1` has no empty-value guard (the chat tool does).
- Evidence: F21; `demo/results/20261020-105907/snapshots/upstream/c4.json`.
- Resolution: both empty cases fail on upstream; the baseline fails them the same way. The C4 row is **partial** on upstream because the update and archive cases still hold.
- Lesson: an implied C2/C4 postcondition is not enforced on `/v1`; the run, not the type annotation, decides the empty-write case.

### Ticket 06: 501 updates leave 500 entries and drop the first `report:`
- Expected: the `[INFERENCE]` that `max_history=500` drops the oldest is decided by a run.
- Observed: after 501 `version_field` writes the stored history length is 500, `v000` is gone, newest is `v500`.
- Evidence: F21, `measurements.history_cap`.
- Resolution: the cap case fails on upstream; `TopicFields.cap_history` is still unused, the real cap is the slice in `graph_store.py`.
- Lesson: a documented cap that is not called can still be real on another path; the 501-update case measures the path `/v1` actually takes.

### Ticket 08: the forgetting pass runs, but the natural trajectory never archives anyone `report:`
- Expected: C5's natural trajectory might show some archived topics as the store grows to 2,000.
- Observed: C5-1 **pass** (a 0.01 canary is archived at 501 topics on upstream and step 1). C5-2 **fail**: archived = 0 at every ramp size (F22, same as F10). Default salience is 1.0 and only rises; nothing falls below 0.05 without a setup write.
- Evidence: F22, `demo/results/20261020-110721/`.
- Resolution: mechanism and natural trajectory are separate rows; the mechanism proves the pass exists, the natural trajectory proves it never fires on ordinary undated writes.
- Lesson: a working forgetting implementation can still leave C5's bound unmet if nothing ever decays.

### Ticket 08: one check for two C5 rows linked every ramp snapshot to the mechanism cell
- Expected: each scorecard row links only the databases it used (C6's pattern: one check per row).
- Observed: the smoke ran C5-1 and C5-2 as one function, so both cells listed the mechanism snapshot and all five ramp snapshots.
- Evidence: F22 scorecard cells.
- Resolution: split into two `@check` functions so C5-1 opens only `c5-mech` and C5-2 opens the ramp DBs. Verdicts unchanged; the next recorded run will have the split snapshot lists.
- Lesson: two rows in one `execute` share the session's snapshot list; follow C6 when the databases differ.
