# Cross-paper grounding: the user's questions on MAFBench, Anatomy, the graph survey and StateMem

2026-10-22. Feeds ticket 32 (which research direction leads) and every later report edit. Answers are the agent's; each rests on the quoted lines. Quotes are verbatim; `[INFERENCE]` marks code reading or reasoning that no run or paper text backs. No report text is changed here.

**Sources** (line numbers are the Markdown conversions in `docs/papers/`):

| Short | File | Paper |
|---|---|---|
| GEM | `2605.26252v1.md` | Orogat & Mansour, *Is Agent Memory a Database?* [P1] |
| MB | `2602.03128v2.md` | Orogat, Rostam & Mansour, MAFBench [P6] |
| AN | `2602.19320.md` | *Anatomy of Agentic Memory* [P2] |
| GS | `2602.05665.md` | *Graph-based Agent Memory* survey [P3] |
| HS | `2512.12818.md` | Hindsight [P5] |
| SM | `2608.19652v1.md` | *Can Agent Memory Systems Track Evolving State?* (StateMem, StateMemBench) |
| TX | `2607.23929v2.md` | MemTX |
| R | `docs/report/gem-limitations-and-directions.md` | our report |

## Corrections to carry before anything else

1. "Paraphrase Penalty" and "Negation Trap" are prose terms (AN:206). Table 9's rows are labelled Surface Variation, Semantic Equivalence Gap, Polarity Flip and Entity Drift (AN:672-679). Lining up the two vocabularies is our own mapping.
2. "Rigid structure struggles to represent overlapped or non-hierarchical relationships" sits in GS's Hypergraph row (GS:324), but the converter notes that the Temporal, Hypergraph and Hierarchical rows are shifted (GS:318). By content it is the **tree/hierarchical** limitation. The hypergraph's own limitations are algorithm cost and the problem-to-hyperedge mapping (GS:323).
3. "FactConsolidation" is not a MAFBench word. MAFBench uses only the labels FC-SH and FC-MH (MB:366). The name comes from MemoryAgentBench, via SM:542.
4. MAFBench fixes the model per dimension, not globally: gpt-oss-20b for memory, gpt-4o-mini for orchestration and specialization, ten LLMs for planning (MB:99).
5. MB:397 calls 20.2 "single-hop forgetting", but 20.2 is the SF average; FC-SH is 36.0 (MB:372). R:650 already has the right split.
6. MB:399's TTL sentence ("accumulation with a weaker LLM still outperforms retrieval-only with a stronger one") holds only for hybrid LangGraph (28.9 and 27.0 against Haiku's 26.2). Pure accumulation peaks at 20.7.
7. AN gives LongMemEval-S as 103k tokens (AN:157). R:360-367 gives "~115k", which is LongMemEval's or Zep's figure. Attribute it to that source, not to [P2].
8. AN never measures Δ. Full Context appears only as a latency row (AN:240).
9. No ticket records a decision about "combining Hindsight with MemState" (searched `.scratch/`, `docs/adr/`, `docs/journal.md`). What exists is in the report: hybrid conflict resolution (R:465-478), the visibility principle behind C3′ (R:176), and "no new condition" from epistemic separation (R:500).
10. "Search failure" and "memory failure" are our labels (R:680), built on StateMemBench's Q1. StateMemBench's own terms are retrieval failure, drift, and maintain vs. acquire (SM:130, SM:455).

---

## A. MAFBench [P6]

**A1. Memory as one of five dimensions; "fixing the underlying LLM".**
- Memory is "Storage Architecture" over {LTM, STM, EM, WM, EK}, with four properties: lifetime, structure, access mode ("retrieval, context accumulation, or state update") and ownership ("agent-local vs. environment-level") (MB:183).
- The control is MB:99: "We fix the underlying LLM and vary only architectural design choices, so observed differences follow from architecture and not from model capability."
- It is enforced by "fixed-size text chunking with controlled overlap, consistent ordering, and identical session initialization" (MB:225) and configuration parity at or near temperature 0, with "no seed is set" (MB:217). Each configuration runs once (MB:308).
- **Our analogue is stronger on `/v1`.** There, no LLM is in the loop at all: "On `/v1` the harness decides placement" (R:677), and `Executor.ingest` only embeds (`2605.26252v1-alignment.md:45`). Every conformance verdict is therefore a memory-semantics verdict by construction.

**A2. Practitioner note: tools defined but not called, depending on the LLM.** MAFBench shows the same effect qualitatively and declines to measure it:
- MB:185: "A permissive one offering the tool as optional never calls it and yields no valid plan. A directive one naming it as the way to obtain prices invokes it and completes. … *Opus 5* invokes under both."
- MB:276: "We do not report quantitative tool-use results, because current frameworks delegate tool invocation entirely to the LLM without architectural control over selection."

Our runs add a twist. MemState's chat layer *does* have architectural control: an intent router decides which tools are offered. That router is where our failures sit:
- `qwen3.5:2b` routed "two weeks ago" to `query` in 7 of 7 takes (F31).
- `qwen3.5:4b` routed it to `ingest` in 10/10, but wrote in only 6/10 (F37).
- The runner executed tools the route had not offered (F31, `findings.md:293`, [INFERENCE] from the runner code).

So the note is backed by MB:185 and by our runs. The gap MB:276 names (no architectural control over selection) is partly closed by a router, which then becomes the failure point.
- **Report:** tool invocation is not covered (R:445 covers planning-format failures only). → **P6**.

**A3. LLM-based semantic scoring: can we use an LLM judge?**
- MB:217: "*LLM-based semantic scoring* replaces brittle string matching and handles diverse answer formats."
- MAFBench names no judge model, no prompt and no agreement check (searched judge, grader, evaluator, agreement). MemoryAgentBench, which it adopts, "does not separate an outdated answer from any other wrong answer, so the stale value is not a scored outcome" (SM:542).
- **Yes, but as the third tool, not the first.** Use (1) state-level reads with exact match where the truth is a stored value: our verdicts need no judge. Use (2) a closed pool plus a deterministic matcher where answers are graded: StateMemBench's matcher decides 28% of answers verbatim and "agrees with the judge on 94.1% of those" (SM:548). Use (3) an LLM judge only for free text, validated twice: across prompts (AN:187-189: rankings stable, absolute scores shift) and across judges (ours: blind reviewer agrees with Sonnet on 151 of 155 turns, F42; SM:136: κ 0.67 same-family, 0.37 cross-family).
- **Caveat:** AN uses gpt-4o-mini both as judge and as a backbone (AN:137, :177). Our judge (Sonnet) and our chat model (qwen) are different families.
- **Report:** R:303 and R:400 cover judge practice; MAFBench's unvalidated judge is not noted. → **P4**.

**A4. Why MemoryAgentBench, and how this relates to our proposal.**
- MB:221: "Prior memory benchmarks … evaluate isolated capabilities … None captures how agents retain, integrate, generalize, and revise information across multi-turn interactions. We therefore adopt *MemoryAgentBench* [25], which unifies these dimensions into four core competencies."
- **The bridge is in GEM itself.** GEM:351: "Current benchmarks measure answer-level recall and exercise C1 only partially [16, 21, 37, 42]". Here [16] *is* MemoryAgentBench (GEM:404, Hu, Wang & McAuley). The lab's two papers therefore already disagree about one benchmark: MAFBench adopts it because it captures revision, and GEM says it covers C1 only partially. Our suite stands in that gap.
- **Report:** not stated anywhere. → **P1** (strongest new link).

**A5. AR, TTL, LRU and SF mapped onto C1–C6.** The definitions are at MB:223 and the subtasks at MB:366. Mapping (our reading; all four competencies are graded on answers only, "Accuracy, F1, Recall@5", MB:314):

| Competency (MB:223) | Nearest GEM element | What it can observe | What it cannot |
|---|---|---|---|
| AR: "factual recall and multi-hop reasoning over long contexts" | Retrieval operator; C1 on facts that never change | Whether the right content reaches the answer (acquisition) | C6 (salience is never read), C1 under updates |
| TTL: "in-session learning of concepts and preferences" | Ingestion integrating into a unit; C1 for a newly learned value | Whether a new preference is used | Where it was stored and whether its history is kept (C4) |
| LRU: "long-range abstraction and cross-document reasoning" | Revision as consolidation or promotion; C5's compression rung; C4′'s "compressed" provenance | Whether the summary answers | Whether the summary replaced sources recoverably (C5, C4) |
| SF: "controlled memory revision through counterfactual updates" | FC-SH → C1/C2 (superseded value not returned); FC-MH → C3 (dependents) | Whether the post-update answer is given | Whether the stale value is still current in storage (C2), whether dependents were flagged (C3) |

- Missing entirely: C4 (provenance), C5 (bounded footprint), C6 (retrieval-induced adaptation), C2(c) (policy compliance), atomicity, and time (C1′'s six probes).
- MAFBench's own term search finds 0 hits for provenance, salience, footprint, atomic, decay and evict. Dependency tracking and transactions appear only as future work (MB:568).

**A6. How many Cs does MAFBench cover?** **None at state level.** At answer level: C1 partially (SF and AR), C2 and C3 only indirectly (FC-MH below 5.0 is *consistent with* a C3 failure, R:656), and C4–C6 not at all. This is GEM:351's own verdict on [16], so the claim is the interviewer's, not ours.

**A7. Four dimensions as the base of a future suite? Not enough on their own.** They are *competencies*: what an agent can do, graded on answers. GEM's conditions are *invariants on the state trajectory*: GEM:349 says "Correctness in GEM is a property of the state trajectory … not of individual records". GEM:351 asks for "ground truth at three levels: the current value of each unit over time (C2), the dependent units that change after each update (C3), and the active footprint at each interaction count (C5)."

Proposed shape: a **competency × condition grid**. Rows are AR, TTL, LRU, SF (plus time); columns are C1–C6 (plus C1′, C3′, C4′). Each cell is graded at the three levels of R §6.9 (answer, labelled, state). MemoryAgentBench gives the rows; the conformance suite gives the state-level columns. → **P2**.

**A8. "A unified evaluation suite … within a standardized execution pipeline" applied to MemState.**
- MB:40 is the quote.
- MB:217 lists the infrastructure: unified execution pipeline, LLM semantic scoring, configuration parity, cost control and backend routing.
- MB:227: "MAFBench's adapter interface holds the framework fixed while varying the memory backend, so it enables their in-depth evaluation." MAFBench left this unexercised; no plugin-memory results appear.
- Our suite already has the same seam: one **system adapter** per memory system (GLOSSARY "System adapter"), with seven systems behind it.

**The proposal** is a unified GEM evaluation suite with two adapters per system: MAFBench's answer-level pipeline (MemoryAgentBench, LongMemEval, StateMemBench as rows) and our state-level adapter (reads of current values, histories, edges, salience, archived flags). MemState then becomes a memory backend behind MB:227's adapter interface, which is the plugin evaluation MAFBench enabled but did not run.
- Cost: "roughly \$300 at gpt-oss-20b pricing" (MB:665). Our own measurement rules out free Groq: one MemState chat request is 8,515 tokens (`journal.md:587-588`).
- → **P2**, and **P3** as the concrete §7.9 direction.

**A9. "Observed differences reflect memory execution semantics rather than model capability", and the Haiku sensitivity row.**
- The full quote is MB:360; the result is MB:399: "Model capability affects absolute scores but does not alter architectural rankings".
- What the row actually shows, per subtask (MB:372 vs MB:389):
  - AR "stable" 33.2→33.7 hides SH 14.0→9.0, MH 24.0→8.0 and EventQA 63.3→82.5.
  - TTL MCC collapses 22.8→0.8 while Recom rises 0.0→51.6.
  - SF falls 20.2→16.5.
  - It is one row, one framework, one run.
- **How it applies to us:**
  1. The claim holds when the memory does not use the LLM to write. MAFBench's native stores mostly chunk and append (MB:225). MemState's chat path does use the LLM to write: it routes, picks a host topic and places a field (GEM:319). There, the backbone is part of the memory's execution semantics, which is AN's "Silent Failure" (AN:227) and our F31/F37.
  2. So split the evaluation in two. **Memory semantics** with the LLM removed: `/v1`, already done, model-free verdicts. **Acquisition reliability** per backbone: write rate, route accuracy and format-error rate, reported like AN's Table 4 (AN:220-223).
  3. A sensitivity row is cheap and honest if it is reported **per subtask**, because category averages hid opposite moves in MB:389. Our chat series already holds the memory system fixed and varies the model (2b → 4b, thinking off → on; F31, F37-F40). That is MAFBench's design inverted, and it should be labelled so.
- → **P5**.

---

## B. Anatomy of Agentic Memory [P2]

**B1. A basis for evaluating MemState.** AN:48 says the survey "clarifies why current agentic memory systems often fall short of their theoretical promise". Its four dimensions (AN:128-131) are answer-level and system-cost lenses, and AN never mentions MemState, GEM or state correctness (searched; AN predates GEM). Use them as the evaluation *hygiene* checklist; R:298-305 already maps them onto GEM's 500-turn workload. They cannot be the *correctness* basis, because "correctness" in AN always means a semantically right answer (AN:46, :177).

**B2. Agency Tax vs MAFBench; Silent Failure vs our qwen failures.**
- Agency Tax (AN:240-255) measures per-turn latency and construction cost **across memory systems**. MAFBench measures runtime against context window **across framework architectures** (MB:401). They are complementary: AN's is a system's cost, MAFBench's is a design's scaling.
- Silent Failure (AN:227: "while the agent can converse fluently in the short term, its long-term memory becomes corrupted due to failed write operations") is about malformed structured output (AN:225). Our qwen failures are a *different* silent failure: the write was **never attempted** (routed to `query`, or 4/10 takes wrote nothing; F31, F37), not attempted and malformed. The one malformed call we recorded is F31's `memory_append_field` with no `field_name`. AN's table counts "recoverable" deviations (AN:216) yet speaks of corruption (AN:227); keep that tension in mind when citing it.

**B3. Context saturation, and the 500-turn workload in GEM.**
- AN:139 defines the risk. AN:145: "Only datasets that substantially exceed the active window (e.g., *LongMemEval-M* at >1M tokens) structurally require external memory." AN:147 adds that cross-session data "may still be solvable through direct in-context aggregation" unless dependencies "exceed the active window or require persistent state tracking beyond prompt capacity".
- GEM's target (GEM:357) is "a 500-turn adversarial workload". At 100–200 tokens a turn that is 50–100k tokens, inside a 128k window (R:302).

Three consequences:
1. Report Δ (AN:167-169) for the workload's answer level. AN:171 says Δ is "a diagnostic rather than a strict pass/fail criterion".
2. Scale volume with LongMemEval-M-style haystacks, so the workload sits in AN's "Low (Requires External Memory)" row.
3. State-level verdicts are immune to saturation. A full-context baseline has no stored state to inspect, and on state tracking full context is not even an upper bound (StateMemBench, R:343).

The three axes (Volume, Interaction Depth, Entity Diversity; AN:145-149) become the workload's design parameters. Interaction Depth is the one GEM's time probes and C3 chains need.
- **Report:** saturation, Δ and LongMemEval-M are covered (R:302, 343, 363-371). The axis-as-parameter framing and the "state level is immune" point are not. → **P7**.

**B4. Lexical vs semantic metrics; F1 favours surface memorisation; replicating Table 9.**
- AN:183: "optimizing solely for F1 may favor surface-level memorization over genuine reasoning and memory integration".
- AN:668: lexical metrics are "systematically misaligned".
- Table 9 rows: AN:672-679 (reproduced in `agent://AnatomyGrounding`).
- **Extend Table 9 with a state column instead of replicating it.** Our bad-merge chat case is a failure mode Table 9 cannot show. The answer is right by the judge in 30 of 30 (reviewer 29), while every take's stored state has lost the deadline history (F37, F39). Call it **State masking**: both lexical and semantic answer metrics pass while the state is wrong. It is the argument of GEM:351 ("A system that overwrites history or never forgets can still score well if its recent answers are correct"), shown in one row.
- It is cheap. Compute F1 offline on the 155 recorded turns (F42) beside the Sonnet, reviewer and state verdicts. No new LLM call is needed, but it needs a committed script and a finding before it enters the report (AGENTS.md evidence rule). → **P8**.

**B5. Prompt overfitting and three protocols.** AN:187-189; Table 3 at AN:195-200. Rankings are stable except where Nemori and MAGMA swap under Nemori's own prompt; absolute scores move (Nemori 0.602→0.781). Ticket 13 deferred a three-rubric judge to future work. Our F42 is a cross-*judge* check (two graders, one rubric), which is the complementary axis. Both are needed: AN varies the prompt with one judge, we vary the judge with one prompt. → **P4**.

**B5a. Stability Gap.** AN:214 compares gpt-4o-mini and Qwen-2.5-3B. Nemori's format-error rate is 17.91% → 30.38%, and "graph-based and episodic architectures are highly sensitive" (AN:228). MemState's chat path is such an architecture (host-topic selection, field placement). R:304 says so from the survey; we have not measured a format-error rate. → **P5**.

**B6. Is Silent Failure handled by MemTX's transactions or MemState's transition policy? Neither, as written.**
- **GEM.** The only failure handling is the whole-transition abort when a postcondition fails: "the transition either commits atomically or aborts" (GEM:291), with P_t "evaluated against the proposed M_{t+1} … and a violating transition is rejected" (GEM:277). GEM is silent on malformed or misplaced LLM output (searched malformed, rollback, hallucinat, misplac).
  - The prototype has no transaction: no `BEGIN TRANSACTION` in `src/` (`2605.26252v1-alignment.md:86`).
  - We measured a partial commit: HTTP 400, yet the topic and its first field are stored (F23).
- **MemTX.** Validation (evidence, validity interval, semantic conflict, dependency stability; TX:136) puts failing records in QUARANTINED "with a machine-readable reason" (TX:138). It also has no handling for unparseable LLM output (searched malform, format, JSON, schema).
- **What each catches.** A transaction catches a write that is *invalid*: a policy violation, or a conflict. It catches nothing that is *absent* (no write issued) or *well-formed but wrong* (right shape, wrong topic or field). Our dominant failure was the absent write (F31, F37).
- **The missing piece is an acquisition check.** It is StateMemBench's "maintain vs. acquire" (SM:130) turned into a runtime signal: after an ingest-routed turn, did any write commit? A format-error rate per backbone (AN Table 4) plus a write-commit rate per turn would make silent failure visible. → **P5**.

**B7. Is MemState practical for interactive settings? Did GEM consider them?**
- **What GEM says.** "Ingestion and retrieval are client-facing and synchronous. Revision and forgetting run asynchronously as policy-triggered maintenance." (GEM:291). Its only latency claim is GEM:39 ("reduces inference cost and latency by avoiding repeated context injection"). It gives no latency budget, and "interactive" and "real-time" appear only in reference titles. So it does not treat interactive settings explicitly.
- **What we measured:**
  - Storage path (`/v1`, no LLM), F41: ingest 21–63 ms, query 86–393 ms from 100 to 2,000 topics. Query grows with topic count because retrieval is an exact full scan with no vector index (`schema.py:13` `VECTOR_INDEX_QUERIES = []`; `graph_store.py:348-356`; [INFERENCE] from code, growth measured).
  - Chat path with the LLM in the turn: 2–5 s thinking off, 16–37 s on, local 4B (F39); one Groq turn took 72 s (`journal.md:39`). That is MemoryOS territory (32 s, AN:253) once reasoning is on.
- **So:** the store is interactive-fast; the synchronous LLM placement is not. Revision is already asynchronous and cheap upstream (rule-based Reasoner, merge window ~5 ms, F41), which is AN:255's "robust asynchronous infrastructure" for maintenance, but not for ingestion.
- The practitioner rule (R:149) is the remedy: "a memory operation should be synchronous only if the current reply depends on its result".
- **Report:** R:139-149 and R:773 cover this. The chat-turn times and the store-vs-LLM split are not stated side by side. → **P9**.

---

## C. Graph-based Agent Memory [P3]

**C1. Latent links = Associative Memory.**
- GS:182: "Establishes latent links between different concepts or data points … acting as the connective tissue of the knowledge graph."
- MemState has the *slot*: association edges "support retrieval context expansion without propagation" (GEM:275). It has no *mechanism* to infer them (R:180).
- Our proposal (R:190) fits GS exactly: inferred links default to association (associative memory), and are promoted to extension (propagating) only with evidence.

**C2. Did our "Zep edition" add Episodic Memory? No.**
- GS:184 defines episodic memory as "the chronological sequence of past sessions … recall 'what happened and when'".
- The patch adds valid time and recorded time to *field histories*: when a value was true and when memory learned it. That is temporal grounding of semantic facts, not a record of sessions. The source message is not persisted: provenance is a string (`patches/0002` :973, [INFERENCE]).
- C4′ (provenance resolves to a stored source) is `absent` on upstream and on every patch step, and `pass` on the reference GEM (scorecard R:823, F32, F34).
- Zep's equivalent is the episode tier, which the report already calls "the foundation of its time model" (R:214). **C4′ is the step that would add an episodic tier to MemState**; the patch did not take it.

**C3. GS's unified perspective and MemState.**
- GS:1265-1293 formalises G_t = (V_t, E_t, X_t) with Construct, Retrieve: (q, G_t) → S_t, and Update: (G_t, Δ_t) → G_{t+1}.
- MemState in those terms: V = topics; X = title, summary, embedding and fields with value histories (GEM:246); E = typed extension and association edges (GEM:275).

GEM adds four things GS's general form lacks:
1. histories inside X (GEM:273);
2. propagation semantics on E (C3);
3. policies P_t as part of the state (GEM:156, :277);
4. Retrieve as a state transition, where GS's Retrieve is a pure function and GEM's C6 makes every read a write (GEM:345).

GS:211 also says "a vector memory can be interpreted as a fully-connected graph with similarity-weighted edges". MemState's retrieval is exactly that (exact cosine scan, top 8). Its explicit edges serve propagation and expansion, not search.
- **Report:** R:97-104 maps GS's CRUD definition, but not this formal model. → **P10**.

**C4. Is MemState a hypergraph? No.**
- Edges are pairwise and typed (GEM:275). A hypergraph needs "E ⊆ 2^V" (GS:1113).
- A topic *reifies* an n-ary relation: one node groups all fields of one concept (GEM:273), which does the job a hyperedge does in GS:330.
- The "rigid structure … overlapped or non-hierarchical" limitation (tree, per correction 2) does touch MemState. Each fact has one host topic: "LLM picks host topic τ" (GEM:304, :319). A fact shared by two concepts must be duplicated or promoted to its own topic and linked; GEM's answer is promotion (GEM:273).
- "Can a field belong to two topics?" Silent in GEM; single-owner is [INFERENCE] from H_{i,j} indexing.
- **Report:** R §7.8 covers the topic as atom, but not the overlap cost. → **P10**.

**C5. Multidimensional quality criteria. Does Hindsight meet them?**
- GS:665 asks for "structural, semantic, temporal, and operational" quality criteria and notes "a scarcity of metrics designed to explicitly evaluate the intrinsic quality of the memory graph".
- **Hindsight does not.** Its evaluation is a binary answer-correctness judge on LongMemEval and LoCoMo (HS:572-574, :543-547, :616). It has no link ablation and no measure of graph quality (searched quality, structural, coherence, redundan).
- **Our conformance suite is an instance of GS:665's missing metrics:**
  - structural: C3 flagging, C5 footprint, edges, archived flags;
  - semantic: C1 and C2 current values;
  - temporal: six time probes, C1′;
  - operational: latency, merge and staleness windows, reinforcement precision, C6.
- On the Hindsight decision: see correction 9. No recorded decision exists. The report's position is to take Hindsight's *mechanisms*, namely LLM-detects/rules-resolve (R:465-478) and visibility (C3′, R:176), and add no condition for epistemic separation (R:500). GS:665 supports that position: Hindsight supplies mechanisms without intrinsic quality criteria, and GEM supplies the criteria. If you remember deciding something stronger ("do not combine"), it should be recorded as a ticket comment. → **Q7 below**.

**C6. Quadratic complexity: does topic granularity solve it? Partly, and only for propagation.**
- GS:667: "graph operations exhibiting quadratic or worse complexity".
- GEM claims a small *propagation* frontier: "Topic granularity keeps this frontier far smaller than an entity-grain graph (Zep), so the walk terminates in few hops" (GEM:321). It gives no bound, and upstream has no propagation to measure (C3 absent, F7, F17).
- Two other operations scale with topic count:
  1. Retrieval: an exact scan, linear per query, measured 86→375 ms at 100→2,000 topics on LadybugDB (F41).
  2. Duplicate detection: written as a self-join over topic pairs, `MATCH (a:Topic), (b:Topic) WHERE a.id < b.id AND a.title = b.title` (`graph_store.py:1240-1241`), run after every ingest (`reasoner/engine.py:36-37`). Whether that is quadratic depends on the engine's join plan [INFERENCE]. It matches exact titles only, so its recall is low (F9 behaviour). Not measured at scale.
- Also, ingestion's LLM reads all titles and summaries to choose a host (GEM:319), so the prompt grows with topic count (R:141).
- **The honest answer:** granularity bounds hops, not the number of units scanned. The scan count is what C5's β(n) is meant to bound, and upstream does not enforce it: 2,000 active topics against a 500 soft limit (F10, F22).

**C7. Approximate retrieval trading precision for efficiency. Does MemState make that trade? The paper's design does; the prototype's `/v1` path does not. In GEM the trade is not free either way.** *(Corrected 2026-10-22 after a second-opinion review; the first version said "No" outright.)*
- **The paper makes three approximations:**
  - LLM routing over titles and summaries instead of exhaustive search: "it inspects titles and summaries, selects candidate topics, reads schemas, and reads required field values" (GEM:325).
  - Topic granularity: "Its boundary is a design decision" (GEM:182).
  - A lossy ladder: "Below θ_summary, a history is compressed" (GEM:323).
- **The prototype splits the two paths.** On `/v1` it uses exact top-8 with no ANN index (`MemState/src/memstate/schema.py:13` `VECTOR_INDEX_QUERIES = []`; `core/models.py:68` `top_k: int = 8`; [INFERENCE] from code), although its engine families offer vector indexes (R:251). The LLM walk is the chat layer's job (`2605.26252v1-alignment.md:75`).
- GS:667 recommends approximate retrieval. GS:386: "Scalability introduces noise".
- **The GEM-specific catch is C6.** Retrieval writes salience to every returned unit (GEM:345). An approximate miss therefore changes *state*: the wrong topics are reinforced, and the right one decays toward archiving under C5. In a read-only memory an ANN error costs one answer; in GEM it compounds over the trajectory.
- Our reinforcement precision of 0.125 = 1/8 (R:772, F20) already shows that 7 of every 8 increments go to topics that did not hold the answer, *with exact* retrieval.
- This is a concrete research item that combines GS, GEM's "unified indexing" (GEM:343) and C6. → **P11**.

**C8. Dynamic schema learning. Is MemState extensible?**
- GS:671: "Current graph schemas are often domain-specific … Future systems should pursue dynamic schema learning".
- **Yes, as an abstraction:**
  - D, S and P must be explicit, but "their realization varies by backend" (GEM:156).
  - "Policies can be added, modified, or replaced without changing operator code" (GEM:277).
  - Fields are created on demand ("append to H_{τ,f} or create f", GEM:304).
- **The cost of that freedom is schema drift.** GEM names drift as revision evidence but never defines it (R:233). The prompt tries to prevent synonyms by instruction ("rather than splitting across synonyms", `tools_schema.py:831`).
- So: extensible, yes; *learning* the schema, no; the LLM coins it field by field. R:233 already links this to GS.

**C9. Provenance tracking (GS:673).** GEM elevates it to a correctness condition (C4), which is ahead of GS's "critical directions". But π is shown only as "Provenance: Who? Why?" (GEM:256) and the prototype stores a label. C4′ (retained source) is our strengthening; `absent` on MemState, `pass` on the reference GEM. GS's other half, "interactive visualization interfaces" (GS:673), matches MemState's Graph Explorer. → **P10** (cite GS:673 beside C4′).

**C10. Memory coordination in multi-agent systems (GS:677). What do the three papers say?**
- GS:677: "memory is no longer an isolated component but a shared resource … Ineffective memory sharing or inconsistent memory updates can lead to conflicting decisions."
- GEM covers multi-*tenant* sharing only. It covers salience leakage (GEM:361), erasure (GEM:363) and "the consistency cost of retrieval-induced salience updates under concurrent access" (GEM:347). It says nothing on agents coordinating.
- MAFBench evaluates memory as a per-agent mechanism (MB:308) and deliberately excludes shared state from its topology study: "A globally readable shared state would make every structure equally dense and remove the variable under study" (MB:505). Its future work asks for "conflict resolution for concurrent agent writes" (MB:568).
- MemTX addresses multi-agent shared memory with permissions (R:336). Kuzu and LadybugDB allow a single writer (R:245, R:251).
- **The gap all four converge on:** GEM-governed memory shared by agents in a MAFBench topology. Under C6, every agent's read is a write to shared salience, which is GEM's own tenant-leakage path (GEM:361) arising *inside* one team. MAFBench's topology dimension is the controlled variable; GEM's conditions are the correctness criteria. → **P3** (direction candidate).

---

## D. StateMem / StateMemBench

**D1. Different layers? The full StateMem is the same layer as MemState; the wrapper is a different one.**
- StateMem has an LLM `TurnEncoder` per turn writing to its own `StateStore`, a deterministic `Rechecker` that "runs in O(|E|) and adds no LLM calls", and one answer call (SM:202, :233, :237-239, :245). That is a memory system competing with MemState at the storage layer.
- R:288 already concludes: "StateMem is close to a minimal, measured implementation of C1–C3 plus visible staleness, without governance".

**D2. Could StateMem wrap MemState? Mechanically yes; for GEM's purpose, no.**
- The wrapper is "a prompt-level transformation of the answer call, with none of its machinery" (SM:338). It needs only `ingest(text)` and `search(query, k)` → strings (SM:1033-1039), so MemState's `/v1/query` could serve it [INFERENCE].
- Four reasons it does not serve GEM:
  1. **It needs the full transcript** in the answer call: median 8.6k input tokens on StateMemBench, 87k on LongMemEval (SM:1052). That is the "repeated context injection" GEM:39 exists to avoid, and AN's context saturation.
  2. **It writes nothing back** ("no store, no per-turn processing", SM:950). Answers improve; state does not. In our bad merge, March 15 is gone from storage (F18, F29). Only the transcript could recover it, and then memory contributes nothing.
  3. **No graph or topic system was wrapped.** The hosts are Mem0, A-Mem, LightMem, MemOS, BM25 and Dense (SM:352-357).
  4. **It beat StateMem itself when the transcript fit** ("0.283 vs. ≥0.567 on Qwen. When the transcript fits in context, resolving state at answer time is good enough", SM:365). That is direct evidence for AN's saturation warning, not for a memory layer.
- **What to take from StateMem instead:** the deterministic Rechecker. It is C3′'s testable core (flag dependents at write time, show the flag at read time), which the reference GEM already scores. Add its over-propagation cost (−12.5 pp on anti-traps, SM:306), which R:200 already cites.
- **Report:** the wrapper result is not covered (only R:388). → **P12**.

---

## Proposed report changes (each needs your decision; none applied)

| # | Change | Where | Evidence it needs |
|---|---|---|---|
| P1 | State the bridge: MAFBench adopts MemoryAgentBench (MB:221); GEM says it "exercise[s] C1 only partially" ([16] = MemoryAgentBench, GEM:351, :404); the suite tests the rest | §8, §1 item 10, slide 2 | paper text only |
| P2 | Competency × condition grid: AR/TTL/LRU/SF rows × C1–C6 (+′) columns, graded at three levels; the MAFBench pipeline plus our state adapter as "a unified GEM evaluation suite" | §6.9 or new §6.10; §7.7 | paper text only |
| P3 | §7.9: map each direction to GEM §5's three directions (engine / correctness and evaluation / multi-tenancy); add "MemState as a backend in MAFBench's adapter interface (MB:227)" and "GEM-governed memory shared across agents in a MAFBench topology (GS:677, MB:505, MB:568, GEM:347, :361)" | §7.9 | paper text only |
| P4 | Judge practice: MAFBench's judge is unnamed and unvalidated (MB:217); order of grading tools: state read, closed pool + matcher (SM:548), validated judge (AN:187, F42) | §6.1 or §8 | paper text + F42 |
| P5 | Split "memory semantics" (LLM-free `/v1`, done) from "acquisition reliability per backbone" (route accuracy, write-commit rate, format-error rate); explain why MB:360's claim does not carry over to LLM-written memory (AN:227, F31, F37); report the Haiku row per subtask (MB:389) | §6.1, §9.2, §8 | paper text + F31/F37; any new *rate* needs a run |
| P6 | Tool invocation: MB:185/MB:276 + our router evidence (F31, F37); router as the architectural control MB:276 says frameworks lack | §8 or §9.7 | paper text + findings |
| P7 | AN's three saturation axes as workload design parameters; state-level verdicts immune to saturation | §6.1 | paper text only |
| P8 | Extend AN's Table 9 with a state column ("State masking"): F1, Sonnet, reviewer and state verdict on the 155 recorded turns | §9.7 | **new offline script + finding** |
| P9 | Interactive practicality: storage path (ms) vs. LLM chat path (s), side by side with AN Table 5 | §5.2 | F39, F41 (exist) |
| P10 | GS mapping: G_t = (V,E,X) with GEM's four additions; not a hypergraph (topic reifies n-ary); single-host overlap cost; GS:673 provenance beside C4′; patch is not episodic memory, C4′ would be | §4.2, §7.8 | paper text; single-host is [INFERENCE] |
| P11 | Approximate retrieval under C6: retrieval errors become state errors; reinforcement precision 0.125 with exact retrieval | §5.9 or §7.9 | F20 + paper text |
| P12 | StateMem wrapper: needs the transcript, writes nothing, beats StateMem when the transcript fits (SM:365): evidence for saturation, not a GEM layer | §5.11 | paper text only |
| P13 | Corrections 5–8: SF numbers, TTL claim, 103k vs 115k attribution, Δ never measured in [P2] | §6.4, §8 | paper text only |

## Ticket 32 round 1, re-grounded

**Q1 (lead claim).** The papers strengthen B2 and give D a sharper opening.
- **B2 (the gap is in the conditions):**
  - Definition 4 gives each entry "a timestamp t" without saying what it means (GEM:206), and C1 reads "the most recent non-archived value" (GEM:208).
  - The paper places bitemporality in the native engine, "first-class bitemporal attributes" (GEM:331), a section it calls research directions, not conditions.
  - Its success criterion (iii) is "measurable reductions in temporal-reasoning errors attributable to GEM-conformant memory" (GEM:373). The reference GEM is GEM-conformant in our checks and still errs on T4/T5 (F34), so the criterion cannot be met by C1–C6 as written. C1′ is the amendment that makes it reachable.
  - GEM's own closing analogy is stream processing, "once continuous state and event-time semantics moved from application code into the data model" (GEM:377). Valid time *is* event time.
- **D (open on MAFBench), sharpened by P1:**
  - MAFBench measures memory with MemoryAgentBench (MB:221) and finds multi-hop forgetting below 5.0 (MB:397).
  - GEM says that benchmark exercises C1 only partially (GEM:351).
  - The suite is the state-level evaluation both papers point to: GEM:351's trajectory benchmark and MB:568's call for versioned stores, whose concrete form is our versioned row.

**Q2 (decouple §7.9 from the slides).** This holds, and P3 adds a grounding: order §7.9 by research value, and tag each item with the GEM §5 direction it serves (GEM:339, :349, :359). The interviewer then reads his own agenda in our ranking.

**Q3 (pointer line).** Unchanged: one line above the §7.9 list.

## Second opinion (another agent, 2026-10-22), checked against the papers

The two answers agree on every main conclusion:
- MAFBench covers no C at state level.
- The four competencies are the answer layer and not enough on their own.
- An LLM judge goes last, after deterministic checks.
- Silent Failure is handled by neither GEM nor MemTX.
- MemState is not a hypergraph, and the "rigid structure" limitation belongs to trees.
- Granularity bounds hops only.
- StateMem is the same layer as MemState; only its wrapper is a different one.
- Saturation threatens the 500-turn plan.

Their additions below were verified and are adopted. Their errors are listed after them.

**Adopted (verified):**
1. **C6 depends on the read actually happening.** The chat path bumps field salience only after read tools, and only when the router classified the turn as `query` or `both` (`2605.26252v1-alignment.md:71`, [INFERENCE] from code). An agent that skips the read tool, or a misrouted turn, causes no C6 transition. Recommendation: in a benchmark, ingestion and retrieval are deterministic hooks, not agent-bound tools (MB:185, MB:276). → P6.
2. **MAFBench's *Residual*,** "framework time outside the model call" (MB:42; decomposition at MB:330). Port it: split MemState latency into LLM time and store time. Our `/v1` (store only, F41) and chat-turn (F39) numbers are the two halves, but no single turn has been decomposed. The store half measures GEM:331's "compatibility-layer cost". → P9.
3. **The GABM parallel.** MB:173 defines `T : E × {a_i} → E` over a shared environment E. GEM's transitions have the same shape, so MemState could serve as E, with P_t as the transition rules. This makes the multi-agent direction concrete. → P3.
4. **AN:259:** AMem's 15-hour build suggests "super-linear update complexity (e.g., pairwise consolidation)". That is precedent for the pairwise duplicate query (`graph_store.py:1240-1241`). → C6 above.
5. **Repeats:** MAFBench repeats planning five times (accuracy "varies by at most 4.1 points", MB:544) and lists "multi-run statistical reporting" as future work (MB:566). → P5.
6. **Design controls:**
   - Fix the writer LLM, reader LLM and judge separately; a 2×2 strong/weak writer × reader design shows which side breaks.
   - Use StateMem's length- and cost-matched control (SM:346).
   - Report rank stability (Kendall τ) for the sensitivity row. → P5.
7. **StateMem wrapper:** on the DeepSeek substrate the control recovers most of the lift and "structure adds only −5 to +5. This implies a strong answerer has less need for the state structure" (SM:346). → P12.
8. **The SF split itself is saturated.** Its context is 4–183k words, 63k on average (MB:236). MAFBench has no full-context row, so any MemState SF result needs one. → P7.
9. **C1's historical-query branch** ("prior values appear only when q explicitly requests historical context", GEM:208) is untested by MemoryAgentBench. → A5 table.
10. **Hindsight, from its own paper:** it has no controlled forgetting ("extending the opinion and belief layer to support controlled forgetting", future work, HS:645), and world facts are never superseded (ticket 11 note). This strengthens the report's position (correction 9). → Q6.
11. **Table 9, MemState-specific:** constructed Website Redesign rows ("April 20", "20/04", "moved to April 20, no longer March 15", "March 15") with F1, judge and closed-pool label, plus a "supersession trap" row. These are illustrative, not evidence, and are combined with P8's recorded rows, which are. → P8.

**Their errors (verified):**
- **"Visualization is the part still missing."** MemState ships the Graph Explorer (R:673), which is GS:673's "interactive visualization interfaces".
- **"C1 and C2 do not depend on the asynchronous revision step."** C2(a), the merge, runs in the asynchronous Reasoner, and that is where MemState fails: the merge makes the superseded March 15 current in 20 of 20 runs (F9, F29). *Round 2:* the other agent points out that GEM:319 claims "C1, C2, and C4 hold by construction" for ingestion. Agreed. But C2's second clause is about revision ("no revision produces a state in which a superseded value is returned as current", GEM:210), and our run arranges the duplicate with a labelled setup write (R:678). So the run shows revision itself violating C2. It does not show ingestion misplacing the update. That misplacement creates duplicates in practice (Figure 1, "stored twice") is plausible [INFERENCE] but not run. The paper-vs-prototype contrast is already in the report (R:131, R:693).
- **StateMemBench's "salience" is not GEM's salience.** In StateMemBench it is "a more frequently or more prominently mentioned competitor" in the dialogue (SM:169), and its authors call it "a substrate limit rather than a memory-design one" (SM:304). "MemState should pass because salience is per field and C1 returns the latest value" mixes the two terms. C1's latest-in-slot rule also fails on a mismatched slot or a duplicate topic (R:220).
- **Salience granularity:** per field in the paper (GEM:198, :323). In the prototype it is topic-level on `/v1` and field-level in chat, and a field write overwrites the topic value with the field average (`2605.26252v1-alignment.md:61`, `:71-74`).
- **"StateMemBench's ~600-turn scenarios meet the 500-turn target."** Set B is about 7–15k tokens (SM:1076), deep saturation by AN's criteria. It tests interaction depth, not volume.
- ~~"MAFBench tested windows up to 8,192 tokens." The unit of W is not stated.~~ **Our error (round 2):** Figure 4's x-axis is "Context Window (tokens)" at 50–8,192 (MB:405, the converter's figure description). Write "W up to 8,192, labelled tokens in Fig. 4".
- ~~TOKI is not in a converted paper.~~ **Partly our error (round 2):** TOKI is arXiv 2606.06240. Its abstract says "A tightness companion proves the sharp result: within the relational schedule model, keyed logging of the adjudicating judge is necessary for replay consistency". So "proves" is accurate *within that model*. *Done 2026-10-22:* converted to `docs/papers/2606.06240v1.md` (PDF beside it) and independently verified as faithful after two fixes (Table 4 row Zep-I; Table 23 T5 row).
- **Missing link:** they do not identify GEM:351's "[16]" as MemoryAgentBench (GEM:404). That makes P1 our addition.
- **Zep edition:** they could not answer. It adds no episodic memory: C4′ is `absent` on every patch step (R:823).
