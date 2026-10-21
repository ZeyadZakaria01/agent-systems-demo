# Review of the demo plan

Type: grilling
Status: resolved
Blocked by: 03, 04, 06

## Question

An external review of the demo plan proposed corrections, a reduced scope, an extra measurement and a framing. Which parts apply?

## Answer

Resolved 2026-10-11: applied with three amendments (C5 setup through `/v1`, C6 clause 2 scored by an eligibility test, the "E4" label dropped). The demo must be buildable within about one week. **Superseded in part by ticket 22:** E4 is defined in the report (§7.5) and gets its own probe; the merge patch is mapped to C4/C2 and MAFBench §6, not to E4. **Superseded in part 2026-10-20 by [Reinforcement precision and the engine latency ramps](29-reinforcement-precision-and-latency-ramps.md):** built in two days with subagents, nothing cut.

**Corrections**
- MAFBench framing: *"multi-hop selective forgetting stays below 5.0 in every framework; every evaluated framework-native architecture treats memory as append-only"* (`docs/papers/2602.03128v2.md:397`, §6 l.568). Single-hop reaches 20.2 (retrieval-only LangGraph). The earlier "≈ 0 everywhere" was wrong.
- "Database guarantees are necessary but not sufficient" is the user's claim, tested by the baseline; GEM's own answer is *"No … not a database problem"* (`docs/papers/2605.26252v1.md:146`).
- F3 (Groq key ignored) is a reproducibility note, not a research gap.

**Test design changes**
- Harness name: **GEM conformance suite**. Scorecard columns: MemState upstream | MemState patched | last-write-wins baseline.
- **C2(b) atomicity**, merged with the bad-edge test: one `/v1/ingest new_topic` with valid fields plus an edge to a non-existent topic id. Error with topic/fields persisted → partial commit, `fail`. Success with the edge reported applied → soundness issue, reported. Neither → atomicity not testable over HTTP with this input; not scored.
- **Baseline C2**: "value part passes; no policies (P_t) exist", not a full pass.
- **C5, two verdicts**: (1) mechanism: ≥500 topics plus a field-less `/v1/ingest` topic at `salience=0.01` → `partial` (count-triggered at ≥500, a gate not a bound); (2) natural `/v1` trajectory, no setup: salience starts at 1.0 and never decays → `absent`; ramp 100 / 250 / 500 / 1000 topics, 2000 if timings allow (each ingest after 500 runs the forget scan and a pairwise duplicate-title query, `graph_store.py:1236-1246`); record the archived count.
- **C6, two clauses, quoted on the scorecard**: clause 1 *"every retrieval that accesses u_i induces a transition in which the salience of u_i is updated"* → `pass` with over-reinforcement (every returned candidate is bumped, F2). Clause 2 *"repeated retrieval strictly reduces u_i's eligibility for attenuation"* → tested with a field-less topic at 0.03 queried until above 0.05; a field write resetting reinforced salience to the field average is recorded as "reinforcement is not durable" (`partial` at most), since the reset does not make a topic eligible.
- **Latency row**: during the C5 ramp, log client latency of `/v1/query` and `/v1/ingest` and, separately, the time until the background Reasoner finishes, at each step; save under `runs/results/`. Expect roughly linear query growth (brute-force vector scan) and a step at 500 topics.

**Scope**
- Kept: everything on the `/v1` path, all merge tests, C3 probe, C2(b), C5 both verdicts, C6 both clauses, scorecard with snapshots, patch worktree and re-run.
- One recorded **Ollama** chat run after the bad merge, 2–3 questions, hand-graded, labelled n=1.
- Cut to future work: three-rubric LLM judge and agreement, Ollama repeats, any Groq runs, cloud-vs-local comparison.

**Framing**
- The merge patch is the demonstrated instance of MAFBench §6's call for versioned fact stores, and of MemState's own documented promise that consolidation adjusts what is easy to find, *"not what is permanently erased"* (`MemState/docs/product/architecture/reasoning.html:27`); quote the promise only after a run shows `merge_topics` deleting the dropped topic.
