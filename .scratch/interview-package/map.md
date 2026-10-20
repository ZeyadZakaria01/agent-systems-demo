# Interview package: GEM/MemState demo, report and slides

## Destination

The way to all three deliverables Prof. Mansour asked for is clear: a buildable demo spec handed off to `.scratch/gem-conformance-suite/spec.md` (from report §9: the conformance suite plus the bitemporal extension of MemState on LadybugDB), the report (`docs/report/gem-limitations-and-directions.md`) covering the limitations, gaps and research ideas of GEM (2605.26252) and MAFBench (2602.03128), and a slide outline. Nothing is left to decide before building.

## Notes

- Domain: governed agent memory (GEM, its MemState prototype) and multi-agent framework evaluation (MAFBench). Papers as Markdown in `docs/papers/`; evaluation practice from the survey `docs/papers/2602.19320.md`.
- Grilling tickets: call the Skill tool for "grilling" and "domain-modeling" (glossary and ADRs written as terms and decisions settle). Research tickets: "research". Agent-file edits: "writing-for-agents".
- Standing preferences: everything free; laptop hardware (6 GB GPU, little RAM); MemState measured unmodified; no gap reported without a reproducing run; demo, not full implementation, with the user's own contribution; agent recommends, user decides; no AI attribution in commits or PRs; difficulties logged in `docs/journal.md`.
- Environment is ready and live-verified (ticket "Environment setup"); start servers via the README.

## Decisions so far

- [Which system to demo](issues/01-which-system-to-demo.md): MemState only; MAFBench in report and slides (multi-hop selective forgetting < 5.0 everywhere, append-only memory); no Mem0/Zep.
- [Demo shape and framing](issues/02-demo-shape-and-framing.md): the GEM conformance suite driving live MemState plus one patch; scorecard upstream | patched | baseline; evidence rule.
- [What the conformance suite checks](issues/03-what-the-harness-checks.md): all six Cs (C1, C4 as controls), paper's three ground-truth levels, state-level primary, `/v1` path scored; one hand-graded Ollama chat run, n=1.
- [Verdict scale and unimplemented conditions](issues/04-verdict-scale.md): pass / partial / fail / absent; C3 and declarative policies probed and scored absent.
- [Baseline and setup rules](issues/05-baseline-and-setup-rules.md): last-write-wins baseline; editor endpoints for setup only; leak check out of the demo.
- [Repeats and forgetting test](issues/06-repeats-and-forgetting.md): deterministic once, merge ×20, one LLM run; topic ramp for C5 plus targeted tests.
- [Which gap to patch](issues/07-which-gap-to-patch.md): history-preserving merge that skips archived topics. *Superseded in part by Report v2 redraws the demo.*
- [Evaluation settings and deviations](issues/08-evaluation-settings.md): survey settings where we own the role; MemState internals as documented deviations; thinking off via proxy; no Groq in the demo.
- [Interview-day delivery](issues/09-interview-day-delivery.md): conformance suite and UI live, the Ollama run replayed, screen recording fallback.
- [Environment setup](issues/10-environment-setup.md): venv, MemState, Groq, Ollama on CUDA, scripts; live-verified.
- [Paper conversions verified](issues/11-paper-conversions.md): seven paper conversions and the README/alignment docs audited against sources and fixed.
- [Docs and planning process](issues/12-docs-and-process.md): wayfinder on local `.scratch/`, AGENTS.md + CLAUDE.md, papers in `docs/papers/`, journal and findings.
- [Merge history semantics for the patch](issues/17-merge-history-semantics.md): interleave histories by `valid_from`, tag `merged-from:<id>`, skip archived, recompute pairs. *Superseded in part: valid-time key, commit 3.*
- [Patch packaging](issues/18-patch-packaging.md): git worktree `MemState-patched/`, one commit, `run_memstate.sh --patched`. *Superseded in part: three commits on LadybugDB.*
- [How the conformance suite runs MemState](issues/19-how-the-harness-runs-memstate.md): real server only; poll for background effects and time them.
- [Demo folder layout](issues/20-demo-folder-layout.md): `demo/` with client, baseline, workload, checks, chat_run, run, recordings, results.
- [Review of the demo plan](issues/21-review-of-the-demo-plan.md): MAFBench framing fixed; C2(b) bad-edge test; C5 and C6 two verdicts each; latency row; LLM work cut to one Ollama run; one-week build.
- [Report draft, E4 mapping and staleness windows](issues/22-report-draft-and-e4.md): report lives at `docs/report/gem-limitations-and-directions.md`; E4 gets an empty/null `version_field` probe; C2(b) tests atomicity; two staleness-window lines. *Superseded in part: E4 folded into C4.*
- [Intent routing on the chat run](issues/14-intent-routing-on-chat-run.md): MemState classifies as shipped; the chat run logs each route; a misroute is a finding.
- [Report v2 redraws the demo](issues/23-report-v2-redraws-the-demo.md): contribution is bitemporal field histories (C1′) on LadybugDB in three commits (port, bitemporal, merge by valid time); verdicts read against [P1]'s §4 claims; five time probes; E3/E4 → C1′/C3′/C4′.
- [Reconcile report v2 with earlier decisions and the source audit](issues/25-reconcile-report-v2-with-earlier-decisions.md): audit fixes applied; C3 claimed by §4 but not §4.3, prototype absent; values ordered by valid time (our rule, not Zep's); practitioner note is field-level; C3′ argued from correctness. *Superseded in part: Zep's code also orders by valid time (Bitemporal history model and API).*
- [Reproduce the C3 staleness run and the LadybugDB port](issues/24-reproduce-c3-staleness-and-ladybugdb-port.md): both reproduce (F7–F12); LadybugDB in the root venv beside Kuzu, 39/39 tests, identical verdicts, 340 vs 382 ms at 2,000 topics; merge loses the dropped value 20/20.
- [Bitemporal history model and API](issues/26-bitemporal-history-model-and-api.md): Zep's four timestamps on MemState field histories with C1–C6 kept; departures from Zep only where a condition requires (keep-and-copy corrections, no LLM conflict check, server-picked current value); override layering the one addition beyond Zep; C1′ read as the precise C1; `current: null` when nothing is valid; chat `reference_time`; merge interleaves by valid time; new suite cases handed to Time probes and their controls.
- [Time probes and their controls](issues/27-time-probes-and-controls.md): each probe a dated story (report §9.6 dates) asked on several dates, one of them the control; stories shifted so "today" is the run day; own topics, apart from the storyline; "believed on" asked at a real moment between writes (`valid_at`, `recorded_at`); pass needs history intact, control failure = over-blocking, no date option = absent; "two weeks ago" chat on the patch only, graded on stored date and answer; one dated merge case on the patch.
- [Patch packaging for the three-commit patch on LadybugDB](issues/28-patch-packaging-for-three-commits.md): branch `bitemporal` in `MemState-patched/`, three `git format-patch` files under `patches/` (GitHub fork optional later); commit 1 = import + dependency line, no renames; root venv, `--patched` via `PYTHONPATH`, engine-named DB folders; suite runs on every commit, commit 3 is the scorecard column plus a per-commit change table (commit 1 → 2 isolates Zep's model); upstream tests unedited; ADR 0006.
- [Reinforcement precision and the engine latency ramps](issues/29-reinforcement-precision-and-latency-ramps.md): each storyline question labelled with its answer topic; wrong answers sorted search vs. memory failure (StateMemBench's first triage question); reinforcement precision = Precision@8, a number beside C6 with no verdict (wording vs. motivation gap); four ramps (upstream, commits 1–3), once while building, three times at the end; build in two days with subagents, nothing cut (replaces the one-week budget).
- [Revise the conformance-suite spec](issues/30-revise-the-conformance-suite-spec.md): spec rewritten to report §9 and tickets 25–29 and marked ready-for-agent: five systems, scorecard plus per-step change table, six time probes, triage and reinforcement precision, four ramps, patch steps 1–3, two chat runs; C4 gains a history-cap case; eight build slices.

## Not yet specified

- Report: v2 installed (`docs/report/gem-limitations-and-directions.md`); §9.7 now cites recorded runs (F7–F12); still open is filling §9.8's scorecard from the conformance suite, final length, and the PDF export to send before the interview.
- Research ideas: ranked in report §7.9 (C3′ first); still open is which to lead with in the slides.
- Slides: outline, how much of the demo appears as screenshots versus live.
- Demo storyline content: the concrete 20–30 events and 10–15 questions (shape is decided). The time probes stay out of it as scored tests (Time probes and their controls).
- Rehearsal and timing for the interview.

## Out of scope

- Mem0 / Zep comparison: needs paid keys (see "Which system to demo").
- Demoing MAFBench: it evaluates frameworks, not a memory system, and needs paid OpenAI embeddings.
- Cross-tenant salience leak test: empty by construction in MemState; report note only.
- Running LongMemEval or a 500-turn workload: free-tier limits and saturation; used as motivation only.
- Implementing GEM beyond the bitemporal patch: C3′ propagation and bounded flags, the decay ladder, the retention score, a policy language, extension-edge discovery (report §7.9 future directions).
- [Judge and reference answers](issues/13-judge-and-reference-answers.md): three-rubric LLM judge and agreement deferred to future work; the one answer-level case is hand-graded.
- [Measure Groq tokens per chat turn](issues/15-measure-groq-tokens-per-turn.md) and [Groq budget for chat runs](issues/16-groq-budget-for-chat-runs.md): no Groq runs in the demo.
- LLM repeats and the cloud-vs-local comparison: future work (see "Review of the demo plan").
