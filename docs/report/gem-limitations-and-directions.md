# Is Agent Memory a Database? — Limitations, Gaps, and Research Directions

**Report on:** *Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory* (Orogat & Mansour, arXiv:2605.26252, May 2026)
**Prepared by:** Zeyad Zakaria Mohamed, for the interview with Prof. Essam Mansour
**Date:** October 2026

> **Scope.** This report focuses on the MemState / GEM paper. The MAFBench paper (*Architectural Design, Not Only Model Intelligence, Governs Multi-Agent LLM Performance*, arXiv:2602.03128) is covered in a short section on its memory results and how they connect to GEM (Section 8). The released MemState code is a proof-of-concept, so the analysis argues from the paper. Statements about MemState's runtime behaviour enter this report only after a recorded run reproduces them (Section 9). Section 4 of [P1] states which guarantees the prototype provides (its opening and Section 4.3 differ on C3; see Section 5), and Section 4.3 names several items as native-engine research directions; the prototype is tested against those stated guarantees, and points that fall within the paper's own agenda are presented as extending it, not as gaps.

---

## Contents

1. [Summary of findings](#1-summary-of-findings)
2. [Sources](#2-sources)
3. [The paper in brief](#3-the-paper-in-brief)
4. [Positioning MemState in the two surveys](#4-positioning-memstate-in-the-two-surveys)
5. [Limitations and gaps of the paper](#5-limitations-and-gaps-of-the-paper)
6. [Evaluation gaps](#6-evaluation-gaps)
7. [Ideas to develop](#7-ideas-to-develop)
8. [Link to the MAFBench paper](#8-link-to-the-mafbench-paper)
9. [Demo: time-correct governed memory](#9-demo-time-correct-governed-memory)
10. [References](#10-references)

---

## 1. Summary of findings

1. **No empirical evaluation.** The paper reports no accuracy, latency, or cost numbers. Its three structural observations are explicitly "claims, not theorems," and the 500-turn adversarial workload is listed only as a future target.
2. **Cost and latency are discussed only qualitatively.** Ingestion is synchronous and puts an LLM inside the user's turn; retrieval is also a write (C6). For real-time agents (e.g., voice), synchronous ingestion is not viable.
3. **Staleness is detected but neither surfaced nor bounded.** At ingestion, Listing 1 flags dependent topics for revision, and revision repairs them later, asynchronously. But retrieval never consults the flag, and C3 sets no time bound, so a read before revision returns the stale value as current. In the public prototype, neither the flag nor the repair exists: a dependent topic stays stale even after revision (recorded run, Section 5.3).
4. **Link discovery is unspecified.** The paper never says how the extension edges that C3 depends on are created in general; its one example (Figure 3b) is an edge to a topic that revision split out. Hindsight builds links at write time; StateMem records dependencies with its ingestion LLM, which is one concrete answer for MemState, though its benchmark states every dependency explicitly (Section 5.4).
5. **Recency is treated as validity.** C1 returns the most recent value as current (in the prototype even an empty string or `null`, F21), and field histories carry a single timestamp, so retroactive, out-of-order, future-dated, and temporarily scoped facts break it. Zep's bitemporal model, which depends on retained source episodes with reference timestamps, separates when a fact was true from when it was recorded.
6. **The substrate has no upstream, but a successor works.** Kuzu was archived in October 2025; the prototype requires `kuzu>=0.11.0`, which now resolves to the final release, 0.11.3 (pinned in our environment). The prototype runs on LadybugDB, a maintained community fork of Kuzu, after a one-line import change plus installing the `ladybug` package: all 39 upstream tests pass and our probes give identical verdicts on both engines (recorded runs, Section 5.10). A native engine remains the paper's long-term direction.
7. **The benchmark landscape has moved.** C2 and C3 are now measured by several 2025–2026 benchmarks (HaluMem, MemoryAgentBench, STALE, StateMemBench) and a pilot evaluation contract (AOEP-v0), but separately, mostly on synthetic data. [P1] already cites MemoryAgentBench as exercising C1 only partially, and HaluMem and STALE predate [P1]. **No benchmark measures C5 and C6 together, and C6 appears entirely unmeasured.** No benchmark ties correctness to write-to-visible latency or staleness; at most, write cost is reported beside accuracy (HaluMem, [P2]).
8. **Two measures GEM implies are missing from every benchmark:** *write-to-visible latency* and the *staleness window*. Both belong on an accuracy–latency–tokens Pareto plot rather than a single accuracy score.
9. **Related systems omitted.** Hindsight and Supermemory implement parts of GEM's revision machinery without formal correctness conditions. StateMem, which does not cite [P1], independently converges on GEM's core ideas (state over recall, non-destructive supersession, typed dependency propagation) but lacks forgetting, salience, and formal conditions. MemTX evaluates a reimplementation of MemState, cross-checked against the official code (Sections 5.11 and 6.2).
10. **MAFBench motivates GEM from the framework side.** It finds that multi-hop selective forgetting stays below 5.0 (out of 100) in every memory architecture it evaluates and that all of them treat memory as append-only, and it calls for versioned fact stores with multi-version concurrency control, write-ahead logging and conflict resolution, plus dependency tracking across stored facts. The demo's baseline is that concrete solution: a versioned row (append-only history with recorded time, one transaction per write, empty and null values rejected). Our claim, which the baseline tests, is that database guarantees are **necessary but not sufficient** for agent memory. Measured in the run of record: the versioned row passes C1, C2(b) (atomic commit), C2 on the lapsed override and C4, and is absent on declarative policies (C2(c)), dependency tracking (C3), forgetting (C5) and reinforcement (C6), each confirmed by a probe; it answers all 15 storyline questions, as MemState does, so the difference shows in stored state, not in answers (F34, Section 9.7).
11. **Demo: conformance testing, a reference GEM and a bitemporal amendment.** A conformance suite checks MemState's *stored state* against the guarantees Section 4 of [P1] claims, beside the versioned-row baseline and a **reference GEM**: our own small system built to the paper's definitions of C1–C6, with its simplifications declared. Its result is worded "passes the suite's checks, with declared simplifications", never "satisfies C1–C6". The reference GEM is scored in two phases. Phase 1 reads Definition 4's timestamp as kindly as its words allow (when the value became true); it passes every conformance row and is absent on two of the six time probes (T4 needs an end date, T5 a recorded time). Phase 2 adds C1′ and passes all six; no other row moves (F34). C1′ is the standard bitemporal model in the form Zep uses; our contribution is the read rule and its tests. The same fix is applied to MemState's field histories, on LadybugDB, in three commits: the port changes no verdict, the bitemporal histories flip all six time probes from absent to pass, and merging by valid time flips the superseded-value merge (C2(a)) from fail to pass, with no regressions on the rows the suite checks and MemState's 39 upstream tests passing at every step (F41, Sections 9.7 and 9.8). Commit 2 also resolves relative dates in chat writes by rule against the message's reference time; on a 4B model with reasoning on, the stored start date for "two weeks ago" was right in 10 of 10 takes, against 1 of 10 without the rule and with reasoning off (F37, F40), and the model's own arithmetic in its answer remains the failure (F40).
12. **The field has moved since May 2026.** Transactional and belief-revision memory papers (MemTX, MemTxn, TOKI) now cover much of C2–C4, and MemTX cites [P1]. GEM's distinctive contributions remain C5 (relevance-driven forgetting), C6 (retrieval-induced adaptation), and the native-engine agenda (Section 6.2).
13. **Refinements to GEM's conditions: one amendment, one strengthening, one extension, no new conditions.** C1′ amends C1 (one clarification: `t` is when a value became true and "current" is judged at the asked date among non-archived entries; two additions: an end date per value and a recorded time). C3′ strengthens C3 (bounded, visible dependency consistency, with a testable core: a read of a dependent before it is re-checked carries a flag naming the update). C4′ extends C4 (evidence-backed provenance, which adds a state component: the retained source). Each is built from the paper's own machinery (Section 7.5).
14. **Three levels of evaluation.** Answer accuracy, labeled behaviour, and stored state each catch failures the previous level cannot. MAFBench and StateMemBench apply the same principle of isolating causes on different axes (Section 6.9).

---

## 2. Sources

| ID | Paper | Role in this report |
|---|---|---|
| **[P1]** | Orogat & Mansour, *Is Agent Memory a Database?* (2026) | The paper under review |
| **[P2]** | Jiang et al., *Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitations* (2026) | Taxonomy; evaluation and system-cost limitations |
| **[P3]** | Yang et al., *Graph-based Agent Memory: Taxonomy, Techniques, and Applications* (2026) | Lifecycle taxonomy; graph memory; open challenges |
| **[P4]** | Rasmussen et al., *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* (2025) | Bi-temporal graph memory; DMR vs LongMemEval; latency reporting |
| **[P5]** | Latimer et al., *Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects* (2025) | Four-network memory; rule- and LLM-driven (non-RL) updates |
| **[P6]** | Orogat, Rostam & Mansour, *Architectural Design, Not Only Model Intelligence, Governs Multi-Agent LLM Performance* (MAFBench, 2026) | Framework-level memory results; call for versioned fact stores (Section 8) |

Additional sources (benchmarks, documentation, system reports) are listed in [Section 10](#10-references).

---

## 3. The paper in brief

The paper argues that long-term agent memory is a **new data-management workload** whose correctness is a property of the **state trajectory**, not of individual records. Record-level CRUD inherited from databases produces four recurring failures: unregulated growth, missing semantic revision, capacity-driven forgetting, and read-only retrieval.

**Governed Evolving Memory (GEM)** models memory as `M_t = (D_t, S_t, P_t)`:

- `D_t`: content, organized as semantic units with value histories and salience
- `S_t`: structure (typed edges)
- `P_t`: declarative policies `⟨event, condition, action⟩`

Four **state-level operators** replace CRUD: ingestion, revision, forgetting, and retrieval. Six **correctness conditions** govern the trajectory:

| Condition | Meaning |
|---|---|
| C1 Query soundness | Queries return the most recent non-archived value as current; prior values only when the query asks for history |
| C2 Transition soundness | Every transition respects `P_t`; no revision returns a superseded value as current |
| C3 Dependency consistency | Updating a unit triggers evaluation of units linked by propagation-bearing edges |
| C4 Provenance preservation | Revision and forgetting preserve the provenance chain of reachable units |
| C5 Bounded active state | The active footprint is bounded by a policy-defined `β(n)`; archived content stays recoverable |
| C6 Retrieval-induced adaptation | Every retrieval updates the salience of the units it accesses; repeated retrieval strictly reduces their eligibility for attenuation |

**MemState** realizes GEM on the Kuzu embedded property-graph engine. Topics are self-contained units with fields and value histories; extension edges carry propagation and association edges do not; policies are evaluated before an atomic commit. The paper closes with three research directions: a native engine, trajectory-level correctness and evaluation, and privacy under multi-tenancy.

---

## 4. Positioning MemState in the two surveys

### 4.1 Anatomy taxonomy [P2]

[P2] classifies systems by their *primary* organizing structure into four families: Lightweight Semantic, Entity-Centric and Personalized, Episodic and Reflective, and Structured and Hierarchical.

**MemState is primarily Structured and Hierarchical (graph-structured), built from entity-centric units.** Its substrate is a typed property graph and topic promotion creates parent/child structure, but each topic is an attribute–value record with per-field histories, which is the shape [P2] calls entity-centric.

[P2]'s Appendix B formalizes updates as `M_{t+1} = T(M_t, u_t)` with actions such as STORE, UPDATE, SUMMARIZE, LINK, EVICT, and DELETE. GEM's Definition 2 has the same form; its additions are trajectory-level correctness conditions and retrieval as a transition.

### 4.2 Graph-based survey [P3]

**CRUD vs. GEM operators.** [P3]'s Definition II.2 defines the basic memory operations as Write, Read, Update, and Delete, which is exactly the abstraction [P1] argues against:

| CRUD ([P3]) | GEM operator ([P1]) | What changes |
|---|---|---|
| Write | Ingestion | Integrates into an existing unit instead of appending |
| Update | Revision | Propagates along typed edges; keeps the prior value with provenance |
| Delete | Forgetting | Graded and recoverable instead of binary |
| Read | Retrieval | Becomes a state transition (salience update) |

[P3] treats evolution as a post-processing stage of the lifecycle; GEM places evolution inside every operator.

**Lifecycle vs. implementation view.** [P3] organizes memory by lifecycle (extraction, storage, retrieval, evolution) and gives only a one-paragraph "alternative view from implementation" (Section III-F). The lifecycle says *which stages exist*, not *what guarantees hold* or *what the engine must provide*. [P1] effectively supplies the missing systems view. A useful systems-level taxonomy would compare designs along database axes: unit granularity, versioning model (single-time vs. bi-temporal), consistency model (sync vs. async maintenance), LLM calls per write, index types, and isolation under retrieval-as-write.

**Knowledge vs. experience memory.** MemState mainly targets *experience* memory (dynamic, personalized interaction state such as deadlines and preferences). Topic promotion partly turns experience into more stable, knowledge-like units. The gap is that one policy regime governs both. [P3] describes knowledge memory as stable, verifiable, and suited to relational graphs, and experience memory as dynamic and often better served by temporal or trajectory graphs; Hindsight separates objective world facts from the agent's own first-person experiences (world vs. experience networks), which only loosely matches [P3]'s split.

**Is MemState graph-based? Is Hindsight?** Both are, at different grains. MemState is a graph of *topics*, not of entities or triples; inside a topic, fields form a key-value record. Hindsight is a graph `G = (V, E)` of narrative facts connected by entity, temporal, semantic, and causal links; graph retrieval, one of four parallel retrieval channels, uses spreading activation.

**"No single paradigm fits all."** [P3] concludes that different memory types need different graph constructions. MemState does not contradict this, because the two address different problems: [P3]'s claim concerns representation choice, while GEM concerns correctness of state evolution, and [P1] states that the realization of `D`, `S`, and `P` varies by backend. The tension is in the prototype, which uses one granularity (topics) for everything. Topics suit stateful entities and projects; they suit event sequences, trajectories, and procedural skills less well. A natural extension gives each topic kind (event, skill, knowledge) its own structure and policies, with GEM acting as a governance layer over heterogeneous substrates.

**Internal self-evolving vs. external self-exploration ([P3] Section VII).**

| [P3] mechanism | Covered by MemState? |
|---|---|
| Internal: memory consolidation | Yes: revision merges duplicates and splits topics |
| Internal: conflict resolution | Yes: superseded values are marked with provenance, not deleted (in the prototype, merge deletes the dropped topic and its values, and the history keeps only the newest 500 entries; F18, F21) |
| Internal: graph reasoning (latent link prediction, inductive enrichment) | **No** (see Section 5.4) |
| Internal: reorganization (significance-based pruning) | Yes: the salience-driven forgetting ladder |
| External: feedback-driven adaptation | Partly: only access frequency via salience, not task success or failure |
| External: active inquiry | **No**: e.g., asking the user when C3 flags an uncertain dependent |

---

## 5. Limitations and gaps of the paper

**Framing.** Section 4.3 of [P1] states that C1, C2, and C4 hold by construction in the prototype and that C5 and C6 hold under transitions; it does not list C3. Section 4's opening, however, says "the data model supplies C1, C3, and C4 by construction," and Section 4.2 describes the mechanism: Listing 1 flags dependent topics, and revision walks extension edges and repairs them. Section 4.3 also names first-class bitemporal attributes, propagation semantics in the schema, compiled policy postconditions, salience as a read-modify-write primitive, and forgetting scheduled like index maintenance as research directions for a native engine, explicitly "not implementation gaps." Points below that fall within that list are presented as extending the paper's direction.

### 5.1 No empirical evaluation

[P1] is a vision paper. It reports no accuracy, latency, cost, or scalability measurements, and it labels its three structural observations (Section 3.4) as "structural claims, not theorems." The first concrete evaluation, a 500-turn adversarial workload scoring Mem0, Zep, and MemState on answer- and trajectory-level metrics, appears only as a future target. Section 6.1 discusses how that workload should be designed in light of [P2]'s evaluation critique.

### 5.2 Cost and latency

**What is synchronous and what is not.** Section 4.2 of [P1] states that ingestion and retrieval are client-facing and synchronous, while revision and forgetting run asynchronously as policy-triggered maintenance. Concretely:

- **Ingestion runs inside the user's turn, in one transaction.** An LLM reads topic titles and summaries to select a host topic (a prompt that grows with the number of topics), reads the topic schema to place the value, appends to the field history, refreshes the topic embedding, flags extension-linked topics, and evaluates policy postconditions before commit. The user waits for all of it.
- **Retrieval is also a write.** Every read increments salience (C6), so every client-facing operation is a write transaction.
- **Revision and forgetting are deferred.** Repair (merging, conflict repair, propagation) and attenuation run later in the background; [P1] does not say which of these steps call an LLM.

**Effect on write cost.** Deferring revision removes the most expensive LLM work from the user's path, but two costs remain on it: LLM routing at ingestion, and a write on every read. Write-on-read also rules out cheap read replicas and caching, and creates contention under concurrency. The paper itself lists "the consistency cost of retrieval-induced salience updates under concurrent access" as an open target.

**Comparison with measured systems.** [P2]'s efficiency profiling ("the Agency Tax") shows how large these costs can be: per-turn latency ranges from about 0.3 s (MemSkill) to 32.4 s (MemoryOS), and index construction ranges up to 15 hours (A-Mem) and 7.04M tokens (Nemori). [P2] also omits maintenance cost from its measurements because it is "often handled asynchronously," which is exactly where GEM's revision and forgetting live.

> **Practitioner note.** In building real-time voice agents with long-term memory, I found that any memory write on the live turn was a direct latency cost the user could hear. We moved writes after the conversation and kept only operations whose result the reply depends on, such as confirming a deletion the user requested. This suggests a general rule: **a memory operation should be synchronous only if the current reply depends on its result.** GEM makes ingestion synchronous in all cases.

### 5.3 Eventual consistency: staleness is detected, but neither surfaced nor bounded

[P1] never uses the term, but synchronous ingestion plus asynchronous revision makes C3 and C5 **eventually consistent**, while C1, C2, and C4 are claimed to hold at commit.

| Pros | Cons |
|---|---|
| Low write latency on the user's path | **Staleness window:** a read between ingestion and revision can return a dependent topic that has not been updated yet |
| LLM repair calls can be batched | **Races:** asynchronous revision can conflict with new ingestion |
| Higher throughput | **Throughput collapse:** [P2] warns maintenance can lag behind interaction until memory goes stale |
| | **Nondeterministic, harder-to-test behaviour** |

**What the paper specifies.** Staleness is *detected*: at ingestion, extension-linked topics are flagged for revision (Listing 1: `flag_for_revision(dependent_topic)` with evidence `{updated_field, timestamp}`), and revision later walks extension edges and applies a repair. But the retrieval operator, as described, routes the query, reads field values, and increments salience; it never consults the flag. C3 requires only that dependents be *evaluated*, with no time bound. So when B depends on A and A changes, nothing in retrieval, as described, blocks on or checks the flag: a read of B before revision would return B's old value as current, with no indication that it is pending revision. [P1] does not discuss reads in this window; this is our reading.

**What the prototype does (recorded run).** In the public prototype (commit `945d7c4`), B → A was linked with an `extension` edge (and, in a second pair, A → B), A's deadline was updated through `/v1/ingest`, and B was read right after the update and again after the background Reasoner had run. The read did not block and returned B's old value; B's stored record carries no flag (it has no field for one); and revision made no change to B (no revision event in its history), so **B stayed stale after revision as well**. The `/v1/query` result lists A as a neighbour of B but omits the edge kind, so a reader of the query result cannot tell the link is a dependency (the UI graph does show it). This matches §4.3, which does not list C3 among what the prototype validates, but falls short of §4's opening claim and §4.2's flag-and-repair mechanism: C3 is *absent* in the public prototype. The conformance suite reproduced it (F17): B was unchanged after a 5 s polled wait in both edge directions, so the window is unbounded within the wait.

**Three designs compared.**

| Step (B depends on A; A is written) | MemState (paper) | MemState (prototype) | Hindsight | StateMem |
|---|---|---|---|---|
| Write time | B flagged by policy | Nothing | Consolidation queued (backlog grows; Hindsight blog, June 2026) | Rechecker marks B `needs_recheck`, deterministic, O(\|E\|), no LLM |
| Read before repair | Non-blocking; stale and **silent** (implied) | Non-blocking; stale and silent | Reflect reports a bank-level backlog grade (not a per-dependent flag); a **prompt** tells the agent to verify against raw facts (Hindsight blog) | Non-blocking; B returned **with its flag and trigger**; the answering LLM recomputes |
| Repair | In storage, by asynchronous revision (eventually correct) | **None**: stale permanently | In storage: observations regenerated asynchronously | **None described in storage**: recomputed at answer time |

**The design space for a read during the window.** (1) Silent stale read (the paper, implicitly); (2) visible stale read: return the value plus the flag and its trigger (StateMem); (3) blocking or read-repair: wait for, or trigger, revision of that unit before answering (correct but puts LLM repair on the user's path); (4) exclude or abstain. The choice belongs in `P_t`, per field or topic: hard constraints (a medication, a legal deadline) block or force repair; soft facts return with the flag visible. StateMem's hard/soft priority is a ready-made basis for that policy.

MemState's design is eventually correct in storage but silent in the window; StateMem is visible in the window but does not write the recomputed value back to storage. Refinement C3′ (Section 7.5) combines the two: persist the repair as MemState intends, surface the flag as StateMem does, and bound the window. That is Hindsight's visibility principle, enforced by the engine rather than left to an agent prompt.

### 5.4 No graph reasoning; who creates extension edges?

A full-text search of [P1] finds no mechanism that infers new edges. Ingestion assumes extension edges already exist and only flags topics linked by them; the only edge-creating mechanism described is topic splitting during revision (Alice promoted out of Website Redesign). Yet **C3 is only as good as the extension edges**, and the paper never says who creates them.

Hindsight builds edges at write time:
- **Causal links**, extracted by the LLM and up-weighted during traversal
- **Entity links**, from entity resolution
- **Temporal links**, between facts close in time, with weight decaying with distance
- **Semantic links**, when embedding similarity exceeds a threshold

It then uses spreading activation for multi-hop retrieval. Supermemory's "derives" relation similarly captures inferences from combinations of memories. Inferring entailment (extension) edges with an LLM and validating them is a concrete research item, and corresponds to [P3]'s "latent link prediction."

**StateMem's answer.** StateMem's ingestion LLM records dependencies while it extracts units (`derived_from`, `coupled_with`), which maps onto MemState's extension edges and gives one concrete answer to who creates them, although StateMemBench states every dependency explicitly, so inferring unstated links is untested. **Proposal:** inferred links default to *association* edges, which help retrieval but cannot trigger revision; promotion to *extension* requires evidence or a confidence threshold. That keeps C3 precise (Section 5.5).

**How much do latent links matter?** Hindsight's multi-session gains over full context are large, but its paper has no ablation isolating the links from its other retrieval channels. EMem, which ablates its graph step (retrieval-time Personalized PageRank, not inferred links), finds mixed, backbone-dependent effects: the graph adds 4.5 points on LoCoMo multi-hop with gpt-4o-mini (0.747 vs. 0.702) but 0.6 with gpt-4.1-mini, and on LongMemEval knowledge-update it adds 6.9 points with gpt-4o-mini (94.4% vs. 87.5%) but costs 1.0 with gpt-4.1-mini. Graph retrieval therefore helps multi-hop recall by a modest margin, and its effect on update correctness depends on the backbone. Existing datasets that require implicit connections (ImplexConv) or hidden dependencies (STALE, FactConsolidation-MH) score answers only; none checks whether the memory stored the right link.

### 5.5 Dependency propagation: is a graph required, and how many hops?

**Is a graph required?** C3 requires a *typed dependency relation with propagation semantics*, not a graph database. A relational table plus triggers could store the edges; [P1] itself notes that active-database ECA rules propagate updates but are not content-aware. The hard parts are discovering the edges (Section 5.4) and evaluating each dependent unit, which also needs an LLM. Observation 3b claims only that *untyped* propagation cannot satisfy C3. A graph is the natural logical model; the physical store need not be one. Conversely, a graph database is not sufficient: MemState already runs on Kuzu, an embedded property-graph DBMS, yet [P1] describes this substrate as a compatibility layer on which propagation semantics must be rebuilt above the engine. Kuzu stores and traverses typed edges; it does not know that an extension edge should trigger re-evaluation.

**How many hops?** [P1] gives no number. It argues that topic granularity keeps the propagation frontier small, so the walk "terminates in few hops," halting where a policy condition does not fire. In the worst case propagation is the transitive closure over extension edges, which requires cycle detection and a depth or cost budget. In practice, one hop covers direct entailment (deadline → milestone) and two cover knock-on effects (milestone → meetings). The real distribution of propagation depth is an empirical question a trajectory benchmark could answer.

**Propagation has a precision cost.** StateMem, which implements deterministic propagation over a dependency graph, reports that propagation helps the failure modes it targets but over-propagates on "anti-trap" cases (−12.5 points on StateMemBench Set B); removing propagation entirely left its DeepSeek result slightly *better* overall (0.373 vs. 0.363); the authors read these margins as an upper bound. C3 is therefore only as good as the edges it walks: wrong or overly broad extension edges trigger false revisions. This strengthens the case for confidence-weighted extension edges and for flagging dependents for review rather than auto-revising them when edge confidence is low (Section 5.4). More generally, C3 requires dependents to be *evaluated*, not changed, so it says nothing against **spurious revision**; StateMemBench's anti-trap cases (an over-eager invalidation changes a value that should have stayed) show this failure is real. Precision currently rests entirely on how `P_t` is written, so C3 needs a precision counterpart, or `P_t` needs an explicit no-spurious-revision requirement.

**Relation to Zep.** Zep propagates zero hops: when an LLM finds that a new edge contradicts an existing one, only the contradicted edges are invalidated, and dependent edges are not re-evaluated. Zep's breadth-first search within *n* hops is used for retrieval, not propagation. Because Zep stores knowledge at entity grain, one concept is spread across many nodes, which is [P1]'s argument that topic granularity compresses the hop count. This can be tested on equal footing because Graphiti (Zep's open-source engine) still ships a Kuzu backend, now marked deprecated (Section 5.10).

### 5.6 Relevance-driven retention: does it require LLM-as-a-judge?

No. MemState's relevance signal is behavioral (access-driven salience), which is cheap. An LLM judging importance at ingestion (as in Generative Agents) is possible but costly, and [P2] shows that LLM-judge scores shift with prompt strictness (although rankings stay stable) and that LLM-driven memory operations fail more often on weaker backbones. A better design is hybrid: cheap signals (access, recency, dependency centrality; [P3] mentions PageRank-style significance pruning) carry most of the load, and LLM judgment is reserved for ambiguous cases or batch consolidation. It is also worth separating two uses of an LLM judge: as an *evaluation* tool, and as a *policy component* inside memory.

A further limitation: **access frequency is popularity, not importance.** A rarely accessed but critical fact (an allergy, a hard constraint) would decay. Retention needs importance priors or explicit pinning.

### 5.7 Recency treated as validity

C1 returns the most recent non-archived value as current, and each history entry `(v, t, π)` carries a single timestamp. Zep tracks four timestamps that separate when a fact held true (valid time) from when the system learned it (transaction time). With a single timestamp, a later message about the past ("the deadline *was* March 1") or a hypothetical can be stored as the current value. In the prototype, "most recent" even includes an empty string or `null`: both were accepted and became current (recorded run, F21). [P1]'s native-engine section calls for "first-class bitemporal attributes," but the correctness conditions themselves are stated over a single time axis.

**Why Zep keeps episodes.** Zep's episode tier is the foundation of its time model, not an add-on. Each message carries a reference timestamp `t_ref`, which lets extraction turn "next Thursday" or "two weeks ago" into actual valid times; the valid-time timeline is therefore derived from episodes, while the transaction timeline comes from ingestion. Episodes are also a non-lossy store from which facts are extracted (and so could be re-extracted), and bidirectional indices let every fact be traced to its source for citation. The four timestamps answer two different questions: what the system *believed* at a given time (`t′_created`, `t′_expired`) and what was actually *true* (`t_valid`, `t_invalid`), which matters for accountability when an agent acted on a wrong value. A MemState history entry `(v, t, π)` has one timestamp and a provenance label, so "two weeks ago" is stored with `t` = now, extraction errors cannot be repaired from the source, and provenance is a label rather than verifiable evidence.

**How Zep and Hindsight handle invalidation.** In Zep, invalidation is *recorded by* the temporal structure but *decided by* an LLM: when a new fact edge arrives, an LLM compares it with related existing edges, and if they contradict, the old edge's `invalid_at` is set to the new edge's `valid_at` while the old edge is kept. Retrieved facts carry their `t_valid` and `t_invalid`, so a reader can tell which were valid at a given time, but detection remains an LLM judgment, which is the weakness [P1] points out (contradictions can be silently missed). Hindsight never invalidates raw facts automatically (per its consolidation documentation; users can invalidate them manually through curation): world facts are kept with their time ranges, and contradictions are resolved one level up, in consolidated observations (both states kept as a timeline, the most recent treated as current) and in opinion confidence.

**What MemState can take from Zep.** (1) *Bitemporal field histories:* store valid time (when the value was true) alongside the recorded time, so a message about the past no longer becomes the current value. (2) *Explicit end times at write time:* when a field value is superseded, record when it stopped being true, not only that it is older, so "as of date X" queries become exact. MemState would add what Zep lacks: propagation to dependent topics (C3) and declarative rules instead of an LLM deciding the resolution (Section 7.2).

**MemState's advantage, and its blind spot.** Because a topic's fields are fixed slots, supersession needs no LLM when the field matches: a new `Deadline` entry in the same topic replaces the old one deterministically, whereas Zep needs an LLM to notice the contradiction. The blind spot is the mismatched slot. If the update lands under `Due date` instead of `Deadline`, or in a duplicate topic, nothing is superseded and two "current" deadlines coexist. Recency-based supersession is only as reliable as field and topic identity, which ties C1/C2 to schema drift (Section 5.8) and duplicate detection. Two further caveats apply to any bitemporal extension (Section 9.5): supersession is deterministic *given* valid times, but extracting valid times from text remains LLM-dependent, as in Zep; and a *scoped override* ("for October only") must layer over the base value rather than close its validity, or the base value is lost when the override lapses.

### 5.8 Conflict resolution and schema drift

**Rule-based conflict resolution.** [P1] criticizes Mem0's overwrite-on-conflict and Zep's LLM gate (which it says silently misses contradictions), and proposes a declarative policy language instead. That approach has its own weaknesses:

- **Detection comes first.** Rules match on field names, so implicit or cross-field contradictions escape ("I moved to Montreal" vs. a `city: Cairo` field).
- **Recency-wins is often wrong** for hypotheticals, corrections of the past, reported speech, and legitimately multi-valued attributes.
- **Cascading rules may not terminate, or may depend on execution order.** [P1] cites Widom & Ceri for ECA propagation; their active-database work also studies exactly these termination and confluence problems for ECA rules.
- **Maintenance burden** grows per domain, and rules carry no notion of uncertainty or source trust.

Section 7.2 proposes a hybrid that keeps the advantages.

**Schema drift.** [P1] lists schema drift as a type of evidence revision should detect, but does not define it or say how it is detected. A reasonable reading: the same concept appears under different field names or types ("Deadline" vs. "Due date"; string vs. date), or a topic's schema diverges from its siblings. Detection could combine field-name similarity, value-type checks, and co-occurrence. In the prototype, the database engine plays no role: Kuzu has no catalog of per-topic field schemas, so drift handling would happen at the application layer. A native engine could make field schemas first-class and schedule drift detection like index maintenance. This connects to [P3]'s "Dynamic Schema Learning" challenge.

### 5.9 Multi-hop retrieval and precision

[P1]'s retrieval routes queries to topic-based, temporal, or structural modes, and association edges support context expansion. Multi-hop retrieval is possible through traversal along these edges, or agentically by chaining reads. Additional hops raise recall but bring in distractors ([P3] notes noise grows with memory size), and at topic granularity each hop pulls in a whole topic. Mitigations: field-level reads (which the paper's topic mode already uses), per-hop activation decay as in Hindsight, edge-type weights, and reranking.

There is also an interaction with forgetting: under C6, every topic visited during traversal gets a salience increase, so multi-hop retrieval protects intermediate topics from forgetting even when they were not useful. Salience should increase only for units that contributed to the answer.

### 5.10 Substrate risk: Kuzu is archived

Kuzu is the engine; MemState is a GEM data model on top of it, which [P1] itself calls a compatibility layer. **Kuzu's repository was archived on October 10, 2025, with 0.11.3 as its final release** (reportedly following an acquisition of Kùzu Inc. by Apple); community forks such as Ladybug, RyuGraph, and a Vela Partners fork continue development. The prototype depends on `kuzu>=0.11.0`, so it necessarily runs on the archived final version. This strengthens [P1]'s case for a native engine: the current substrate has no upstream.

It also matters for C6. Kuzu enforces a single writer (one write transaction at a time), and one maintained fork exists specifically to add concurrent multi-writer support for multi-agent systems. Under retrieval-as-write, every read becomes a write, so reads would effectively be serialized.

**Replacement candidates.** Three groups are worth distinguishing:

| Engine | What it offers MemState | Gap |
|---|---|---|
| **LadybugDB**, **RyuGraph** (Kuzu forks) | Near drop-in continuations: same property-graph model and Cypher, with vector and full-text indexes. LadybugDB allows one write transaction at a time alongside concurrent read transactions within one read-write database object (read-only processes cannot coexist with a writer) | Nothing GEM-specific; a single writer still serializes retrieval-as-write |
| **SurrealDB 3** | `DEFINE EVENT ... WHEN ... THEN` triggers that see before/after values (an ⟨event, condition, action⟩ form for policies and propagation); first-class field schemas in schemafull mode; graph relations; HNSW and BM25 indexes; embedded mode | No native bitemporal model confirmed; no salience primitive |
| **XTDB v2** | Every table bitemporal (valid time and system time, SQL:2011), i.e. field histories with both time axes for free | Not graph-native; embeddable only in JVM processes (from Python it runs as a separate server); needs a separate vector index |
| **CozoDB** (and maintained forks) | Datalog with recursive rules, plus relational, graph, and vector models and time-travel queries, embedded. Datalog makes termination of a policy set analyzable (Section 5.8) | Upstream maintenance uncertain; time travel is not fully bitemporal |
| **Minigraf** | Single-file embedded graph database with bitemporal Datalog queries | Very young; no vector index |

**LadybugDB tested.** MemState imports Kuzu in exactly one module (`kuzu_adapter.py`). Replacing `import kuzu` with `import ladybug as kuzu` and installing package `ladybug` 0.21.2 beside `kuzu` (no other dependency changes; the older `real_ladybug` package, 0.15.x with module `real_ladybug`, is a separate distribution and was not used) leaves all 39 upstream tests passing. The whole conformance suite gives identical verdicts on both engines (upstream against step 1 of the patch, which changes only the import and the dependency; F32). Over three repeats in the run of record, LadybugDB was faster at every size: `/v1/ingest` median 17.9 vs. 30.3 ms at 100 topics, with non-overlapping ranges, and 45.1 vs. 54.9 ms at 2,000; `/v1/query` median 79.3 vs. 146.9 ms at 100 and 343.1 vs. 377.5 ms at 2,000, where slow outliers make the query ranges overlap (F33; one laptop, cause not isolated). In an earlier single run the upstream test suite, by contrast, took 11.5 s on LadybugDB vs. 2.8 s on Kuzu. Database files are not interchangeable (LadybugDB rejects a Kuzu file), and `ladybug.__version__` fails because the wheel lacks the C-API library its version getter uses (MemState never calls it). The chat tools have run on LadybugDB in the patch's chat runs (F28, F31, F35), on two patch steps, not on the unmodified port. A pragmatic path is to move the prototype to LadybugDB now, and to treat a Datalog engine or SurrealDB as the research substrate in which GEM policies become engine-level rules. None of these candidates provides salience as a read-modify-write primitive or forgetting scheduled like index maintenance; those remain the native-engine research agenda (Section 7.6).

**Zep vs. Graphiti.** For comparison, Zep is a managed memory service and Graphiti is the open-source temporal-graph engine at its core. Graphiti's README lists Neo4j, FalkorDB, Kuzu 0.11.2, and Amazon Neptune as backends (the Kuzu backend is now marked deprecated). Running Graphiti-on-Kuzu against MemState-on-Kuzu would hold the engine constant and isolate the data-model difference (entity grain vs. topic grain).

### 5.11 Related systems omitted from Table 1

| System | Relevance retention | Dependency propagation | Graded attenuation | State-modifying retrieval | Substrate strength |
|---|---|---|---|---|---|
| **Hindsight** [P5] | None in the paper (controlled forgetting for the opinion/belief layer listed as future work) | Partial: observations are regenerated asynchronously when their source facts change; mental models and tag-scoped refresh come from the Hindsight docs | None | Partial: reflect may form or reinforce *opinions*, so a read can write new beliefs (not salience) | Separates evidence from belief, with confidence scores; tiered synthesis (facts → observations → mental models → knowledge pages, per the Hindsight docs) |
| **Supermemory** | Claimed in documentation | Partial: typed **updates / extends / derives** relations between memories, giving version chains | Unclear | Not described | Relational versioning |
| **StateMem / CUPMem** (2026) | Not the focus | **Yes:** a deterministic rechecker follows dependency links (StateMem); topology-triggered propagation search (CUPMem) | Not the focus | No | State-first memory with explicit supersession |

Supermemory's relations map closely onto MemState's field histories, extension edges, and graph reasoning. StateMem's deterministic propagation over explicit dependency links is the closest existing realization of C3. Both weaken the paper's claim that no system family covers these capabilities; Supermemory's results are self-reported and its design is not peer-reviewed. The paper's descriptions of Mem0 and Zep are also based on their 2025 papers; Mem0 has since added memory history and expiration dates, and Zep's bitemporal invalidation was already in its 2025 paper.

**Who cites [P1].** MemTX cites it and reimplements MemState as a baseline, cross-checked against the official implementation, and the *Always-On Agents* survey lists it among its closest neighbours. StateMemBench (three months later) and TOKI (ten days later) do not; both are independent work that converges on parts of GEM.

**StateMem vs. MemState (methods, not benchmarks).**

| | MemState ([P1]) | StateMem |
|---|---|---|
| Unit | Topic: one concept, typed fields, per-field value history | State unit: (id, free-form content, priority hard/soft, source, deps), statement-level |
| Ingestion | LLM picks host topic and places values (deterministic on `/v1`) | One LLM call per turn, with a rendering of *all* active units as context; records dependencies |
| Supersession | Append to field history; newest is current (slot-based) | Encoder LLM marks units at risk; store sets them *superseded* |
| History | Full per-field history with provenance π | Superseded units kept for audit, withheld from answering; `source` links to the originating turn and speaker |
| Dependencies | Extension edges between topics; creation unspecified | `derived_from`, `coupled_with`, recorded at ingestion |
| On a dependency change | Flag at write time; repair in storage by asynchronous revision | Flag at write time (`needs_recheck`); recomputed by the answering LLM at read time; the paper describes no write-back of recomputed values |
| Staleness visibility | Detected, not surfaced | Flag and trigger shown at read time |
| Importance | Salience (behavioural) | Hard/soft priority |
| Forgetting, salience (C5, C6) | Yes | None: all active units rendered every turn |
| Correctness framing | Formal conditions, policies, atomic commit | Empirical; StateMemBench results with ablations |

StateMem is close to a minimal, measured implementation of C1–C3 plus visible staleness, without governance; MemState is the governance framework StateMem lacks. MemState can take from StateMem the answer to edge creation, per-unit flag visibility, and hard/soft priority as an importance prior; StateMem would need MemState's forgetting and grouping to scale beyond rendering every active unit.

**TOKI** (Wang, 2026), concurrent with [P1], models agent memory as bitemporal subject–predicate–object facts and treats contradiction resolution as write-time concurrency control. It types four production resolution strategies (last-writer-wins, evidence-weighted merge, await-confirmation, per-rule policy) as isolation-indexed operators over a dual-row schema that keeps losing facts in an audit row, identifies three anomalies an LLM judge introduces on the write path (replay inconsistency, belief-drift skew, audit erasure), and proves that, within its relational schedule model, keyed logging of the judge is necessary for replay consistency. Its subject–predicate key plays the role of MemState's field slot and its audit row the role of the field history. This report's bitemporal extension (Section 9.5) shares TOKI's time model and non-destructive treatment of superseded values, but differs in placement and scope: it adds bitemporal histories to GEM's topic model and correctness conditions (C1′), resolves supersession deterministically given timestamps (TOKI's contribution is keeping an LLM judge on the write path safely), and is evaluated against GEM's conditions on its prototype. TOKI was read at the level of its abstract, introduction, and conclusions; a deeper comparison is future work.

---

## 6. Evaluation gaps

### 6.1 The 500-turn workload and [P2]'s evaluation limitations

[P2] identifies four problems with current agent-memory evaluation. The planned 500-turn workload should address each explicitly:

| [P2] limitation | Implication for the 500-turn workload |
|---|---|
| **Benchmark saturation:** many benchmarks fit inside modern context windows, so external memory is not needed to solve them. [P2] proposes reporting the Context Saturation Gap `Δ = Score_MAG − Score_FullContext`. | 500 turns at roughly 100–200 tokens each is 50–100k tokens, which fits in a 128k window: high saturation risk by [P2]'s criteria. Report Δ against full context, and/or use longer turns. State-tracking metrics remain meaningful even when the history fits, since full context fails at state tracking (Section 6.3). |
| **Metric validity:** lexical metrics (F1) diverge from semantic correctness and rank systems differently. Across three judge-prompt protocols, absolute LLM-judge scores fluctuate, but the *ranking* of systems stays highly consistent. | Use closed-pool or deterministic state-snapshot grading where possible; where a judge is needed, report rankings under several judge prompts rather than one absolute score, and avoid F1 for free-form answers. |
| **Backbone sensitivity:** structured memory operations fail silently on weaker models (Nemori's format-error rate: 17.9% with gpt-4o-mini vs. 30.4% with Qwen-2.5-3B). | Run at least one API model and one small open model, and log the format-error rate per operation. MemState's LLM routing is exposed to the same silent corruption. |
| **System cost ("Agency Tax"):** [P2] measures per-turn latency and construction cost, but excludes maintenance cost, which it calls "often-overlooked." | Report read, generation, and write latency, construction tokens, and maintenance backlog, which is where GEM's revision and forgetting live. |

### 6.2 The benchmark landscape: C2 and C3 are now measured; C5 and C6 are not

[P1] states that no existing benchmark provides ground truth at all three levels: the current value of each unit over time (C2), the dependents that change after each update (C3), and the active footprint (C5). That remains true, but a wave of state-level benchmarks now covers parts of it:

| Benchmark | What it measures | Closest GEM condition |
|---|---|---|
| **HaluMem** (Nov 2025) | Operation-level evaluation of memory extraction, updating, and QA (inspects the store, not only answers); reports that most existing systems suffer update omission rates above 50% | C2 |
| **MemoryAgentBench / FactConsolidation** (2025) | Conflict resolution under incremental multi-turn input; the GPT-4o long-context agent reaches 60% single-hop but 5% multi-hop; apart from GPT-5-mini (28%), no evaluated agent exceeds 7% multi-hop | C3 (multi-hop dependencies), answer-level |
| **STALE + CUPMem** (May 2026, concurrent with [P1]) | Whether systems detect implicit invalidation of old beliefs and propagate revisions to dependent memories | C2, C3 |
| **StateMemBench + StateMem** (Aug 2026) | 234 multi-session scenarios; closed-pool grading distinguishes current-state, superseded-state, and other answers | C1, C2, and C3 via explicit dependencies |
| **Jung et al.** (2026) | Whether updates and deletions propagate to dependent entries (reported Cascade 3%, Absence 1%) | C3, deletion |
| **RECON** (Jul 2026) | Memory as a provenance graph: which conclusions lose support when evidence is invalidated | C4 |
| **AOEP-v0** (*Always-On Agents* survey, Jun 2026) | An evaluation protocol that scores state mutation and recovery obligations rather than answer quality alone | C2–C4 (protocol level) |

**Current picture.** C2 and C3 are now measured, but in separate, mostly synthetic benchmarks. **No benchmark measures C5 (bounded footprint) and C6 (retrieval-induced adaptation) together, and none ties correctness to write-to-visible latency or staleness** (at most, write cost is reported beside accuracy: HaluMem, [P2]). C6 appears to be entirely unmeasured. That is the defensible gap.

The *Always-On Agents* survey lists [P1] ("Governed evolving memory," Orogat and Mansour 2026) among its closest neighbors, credited with formal operators and correctness conditions. It also quantifies how thin the governance literature is: across 435 coded works, authority is the rarest axis (72) and rollback the rarest lifecycle stage (27).

**Transactional and belief-revision memory since May 2026.** Several systems papers now overlap directly with GEM:

| Paper | Contribution | Relation to GEM |
|---|---|---|
| **MemTX** (Jul 2026; cites [P1]) | "A memory write is not a belief commit." Records carry evidence, an authority-weighted source, permissions, derived-from provenance, a validity interval, and a type separating beliefs from summaries. Writes are staged in snapshot-isolated transactions; an eight-state lifecycle (RAW → TENTATIVE → VALIDATED → COMMITTED → ACTION-SAFE, plus QUARANTINED, SUPERSEDED, REVOKED) rejects any other transition; retracting a belief triggers typed cascading repair of derived records. Two invariants are machine-checked over 5.5M protocol states | Implements C2 (fixed transitions), C3 (cascading repair), C4 (superseded kept), and precedents for C3′-style visibility, authority separation, rebuildability, and non-destructive failure |
| **MemTxn** (Jul 2026) | A transaction boundary deciding which proposed memory state may commit and which conflicting version is visible, with complete-state recovery | C2, C4 |
| **TOKI** (Jun 2026) | Contradiction resolution as write-time concurrency control, with a bitemporal operator algebra and soundness theorems; superseded facts are marked, not deleted | C1, C2, bitemporality (Section 5.7) |
| **Park** (2026) | Graph-native versioned memory whose update operations are proven to satisfy the basic AGM belief-revision postulates (K\*2–K\*6) and Hansson's Relevance and Core-Retainment | Formal revision semantics for C2 |
| ***Are We Ready For an Agent-Native Memory System?*** (Jun 2026) | Data-management study of 12 memory systems and two baselines on 11 datasets, with ablations on update correctness and long-horizon stability | Evaluation from the same perspective as [P1] |

**MemTX evaluates MemState.** MemTX reimplements MemState as one of its eight baselines and runs the authors' official implementation, vendored unmodified, through the same interface as a check on that reimplementation; the scores below are the reimplementation's. On MemTX's 90-case suite, MemState has the lowest task success of the nine methods on all five backbones (0.333–0.411, against 0.756–0.956 for MemTX), and second lowest, ahead only of TOKI, on the 56-case hardened suite on three of five backbones (0.321–0.500 across backbones). Its per-case cost (11.5k–18.2k tokens, 6.8–24.4 s) sits inside the same band as the other methods. Two qualifications matter:
- **Scope.** The suite targets multi-agent shared memory, permissions, and gating of irreversible tool calls, which GEM does not claim to address. MemTX characterizes GEM as single-tenant, with no lifecycle separating a write from an actionable commit, no permissions, and no repair of derived effects; the single-tenant point matches [P1]'s own privacy and multi-tenancy direction.
- **Evidence for C3.** On rollback recall, MemState's revision re-evaluation scores 0.915–0.926, above the 0.833 of every baseline without a repair mechanism; only the two methods with cascading repair reach 1.0, and only on four of the five backbones (0.959 and 0.963 on the weakest, Qwen2.5-14B). MemTX attributes this to MemState's revision re-evaluation, as reimplemented from the paper's description, so the score does not describe the public prototype. The public prototype shows no propagation along extension edges (recorded run, Section 5.3), so MemTX's effect comes from its reimplementation of the paper's revision step, not from the released code.

These papers validate GEM's database framing, but they also make "transactions for agent memory" a crowded area. **None addresses C5 or C6**: they govern what may be trusted and acted on, not what should fade or how reads should reshape the state. Those conditions, together with the native-engine agenda, are where GEM remains distinctive.

### 6.3 What is the baseline? Full context is necessary but not sufficient

Full context is the standard reference ([P2]'s Δ; Zep: full context 55.4% vs. Zep 63.8% with gpt-4o-mini on LongMemEval-S; Hindsight: full context 39.0% vs. 83.6% with an OSS-20B backbone). On state tracking, however, it is not even an upper bound: on StateMemBench with the same DeepSeek backbone, **the full-context baseline scores 0.149, below dense retrieval (0.205)**; StateMem reaches 0.363. Having the right facts in context does not mean the model resolves which one is current. The contrast is sharpest within the same paper: on LongMemEval, the same long-context baseline is strong (0.666 on DeepSeek, 0.550 on Qwen), yet on StateMemBench it drops to 0.149 on both backbones (even the best long-context model tested, GPT-5.4-Nano, reaches only 0.277), and the authors note that long context ceases to be the strong baseline once answers must reflect the current state rather than a recalled fact. This is the strongest external evidence for [P1]'s claim that larger context windows do not solve the problem.

A defensible baseline set for a GEM evaluation:

| Baseline | Role |
|---|---|
| No memory | Floor |
| Full context | Whether the history needs external memory at all ([P2]'s Δ) |
| Dense RAG | Simple retrieval reference |
| Mem0 | Overwrite on conflict |
| Zep / Graphiti | Edge-by-edge bi-temporal invalidation |
| Hindsight | Asynchronous consolidation with tiered synthesis |
| StateMem, CUPMem | Closest state-first competitors |
| Oracle current state | Upper bound for C1 |

### 6.4 Is LongMemEval good enough?

**Why Zep prefers LongMemEval to DMR [P4].** DMR has 500 conversations, each with 5 sessions of at most 12 messages (about 60 messages), which fits easily in context; full-context baselines score 94.4–98%. Its questions are single-turn fact retrieval, some are ambiguous, and they poorly represent enterprise use. LongMemEval-S averages about 115k tokens, has six question types including knowledge-update, temporal-reasoning, and multi-session, and uses question-specific judge prompts that correlate with human judgment.

**Versions.**
- **LongMemEval-S** (~115k tokens, ~40–50 sessions), **-M** (~1.5M tokens, ~500 sessions), and **Oracle** (evidence sessions only). The official repository notes that S and Oracle fit in a 128k context while M does not.
- A **cleaned release** is now the standard split: 500 questions, of which 78 are knowledge-update questions (StateMemBench, Table 11).
- **LongMemEval-V2** (2026) targets web agents: 451 curated questions over histories of 25M–115M tokens, including a dynamic state-tracking category, and it reports query latency. Frontier LLMs score at most 14.1% without trajectory evidence.

**Context windows.** GPT-4o (default snapshot 2024-08-06; the model page lists 2024-11-20 without separate limits) has a 128,000-token context window and 16,384 max output tokens. LongMemEval-S therefore fills about 90% of the window, which is why Zep could run a full-context baseline and why [P2] rates S as borderline saturated. Only LongMemEval-M (over 1M tokens) structurally requires external memory, yet Zep, Hindsight, and AMB all report only S.

**Limitations per [P2] and [P1].** S is at borderline saturation; scoring is answer-level with a prompt-sensitive LLM judge; results depend on the backbone; system cost is not measured. [P1] adds that answer-level recall exercises C1 only partially: a system that overwrites history or never forgets can still score well. Further, each LongMemEval history carries a single question, asked at its end, and only 78 of the 500 questions are knowledge-update questions (StateMemBench, Table 11).

**Verdict.** LongMemEval-S is a useful regression test, not evidence for GEM. Use M to force external memory, Oracle to separate retrieval failures from reading failures, the state-level benchmarks of Section 6.2 for C2/C3, and V2 for agentic settings.

### 6.5 Needle-in-a-Haystack (NIAH)

NIAH plants a single fact in a long context and asks for it once, with no writes. [P3] notes that many long-context suites, including the NIAH-style RULER, BABILong, and MM-Needle, remain single-turn and do not require writing to persistent memory, potentially conflating long-context processing with memory. [P4] criticizes memory benchmarks that default to NIAH-style fact retrieval. NIAH is relevant to GEM mainly as a negative control (C1 recall in a world without updates). The useful variants are **versioned needles** (plant v1, later v2, add paraphrased distractors) for C1/C2, and **dependent needles** for C3. LongMemEval and LongMemEval-V2 are themselves built haystack-style.

### 6.6 StateMemBench vs. the 500-turn workload

StateMemBench's 234 is a number of *scenarios*; each is its own conversation. Set A has 190 scenarios of 18 sessions (median 165 turns, ~3k tokens); Set B has 44 scenarios of ~38 sessions (median 599 turns, ~7–15k tokens) probed by a three-part question.

| | StateMemBench Set B | [P1]'s planned 500-turn workload |
|---|---|---|
| Turns per conversation | ~600 (median) | 500+ |
| Tokens per conversation | ~7–15k: fits in any context window (high saturation risk per [P2]) | Unspecified; must be reported |
| When it probes | Once, at the final turn | Paper calls for answer- and trajectory-level metrics |
| Dependencies | Stated explicitly; no inference required | Unspecified; C3 depends on who creates edges |
| Measures C5, C6 | No | Should |
| Reports cost and latency | No (only wrapper token overhead) | Should |

Set B matches the target turn scale but not the rest. The 500-turn workload therefore remains novel **if** it probes throughout the trajectory, grows past the context window (or reports Δ), requires dependencies to be discovered rather than stated, and measures footprint, retrieval-induced adaptation, and cost.

### 6.7 Challenging the benchmarks behind Hindsight's results (agentmemorybenchmark.ai)

The Agent Memory Benchmark (AMB) is an open harness built by the Hindsight team, covering LoCoMo, LongMemEval-S, LifeBench, PersonaMem, BEAM, PrecisionMemBench, and SDEBench. Its manifesto itself argues that LoCoMo and LongMemEval date from an era of 32k context windows and that "dump everything into context" now scores competitively. Inspecting the harness and its published result manifest shows further issues:

1. **Context sizes are not normalized.** On LongMemEval-S, Hindsight passes 43,624 tokens per query to the answer model (about 38% of the 115k history), while Zep's reported context is 1.6k tokens. On LoCoMo, Hindsight passes 36,235 tokens per query, more than an entire LoCoMo conversation (about 9.2k tokens per Hindsight's own dataset table, or ~26k per Mem0's full-context figure). Accuracy comparisons across systems are therefore not token-matched.
2. **Ingestion cost is large.** Ingesting LongMemEval-S took about 30,090 s (~8.4 h).
3. **No full-context baseline.** The harness includes a no-memory baseline but no full-context provider, so [P2]'s Δ cannot be computed.
4. **Only LongMemEval-S is included**, the split [P2] rates as borderline saturated.
5. **Single judge, single prompt.** Scoring defaults to one binary "strict" prompt on one judge model. [P2] shows absolute judge scores move with the prompt while rankings stay stable, so a single-prompt leaderboard supports ranking claims at best, not absolute ones.
6. **The maintainer is also a competitor.**
7. **Latency logging is inconsistent** across runs (e.g., ingestion times are non-monotonic across BEAM sizes: 21,788 s at 500k vs. 348 s at 1m, suggesting cached or partial runs).
8. **Answer-level only.** No dataset measures C2–C6. PrecisionMemBench (in AMB's catalog; 77 cases specifying which memories must and must not surface) is the closest to C1.
9. **Comparability issues in [P5].** Baselines are copied from Supermemory's and Backboard's reports (as [P5] states; Backboard's is its published LoCoMo results page), and Supermemory's used a different judge (GPT-4o), and the retrieval token budget is still a literal `<add>` placeholder in the arXiv version.
10. **Near-ceiling claims.** Supermemory reported near-perfect LongMemEval-S accuracy with an experimental agentic retrieval method and asked whether agent memory is "solved," in a post it later labelled "a big social experiment… a parody" and has since taken down; it is not evidence of saturation.

### 6.8 Quality vs. latency: report a Pareto curve, not a single score

A memory system that is accurate but slow is unusable for interactive agents. Public evidence of the trade-off:

| Source | What is measured | Numbers |
|---|---|---|
| Zep [P4] (LongMemEval-S) | Response latency, IQR, context tokens | Full context 31.3 s vs. Zep 3.2 s (gpt-4o-mini); 115k vs. 1.6k tokens. Zep was measured over a network to AWS, the baseline was not; ingestion cost not reported |
| Mem0 (LoCoMo; vendor-reported) | p95 latency, tokens per call | p95 1.44 s vs. 17.12 s for full context; ~1.8k retrieved tokens per query vs. ~26k for full context (memory store ≈7k tokens per conversation) |
| LightRAG | Tokens and API calls for retrieval and incremental update (not wall-clock) | Under 100 tokens and 1 API call per query vs. 610×1,000 tokens for GraphRAG (Table 2, legal dataset) |
| [P2] Table 5 | Per-turn read + generation; construction hours and tokens | Full context 1.73 s; MemoryOS 32.4 s; A-Mem 15 h construction; Nemori 7.04M tokens; maintenance excluded |
| LongMemEval-V2 | Query latency | Coding-agent memories 140–186 s per query on the Medium tier (108–177 s on Small) vs. 25.8 s for the retrieval agent |
| AMB | Ingestion time, retrieval time, context tokens | Logged per run (Section 6.7) |

**Specification.**
- **One point per (system × configuration).** Vary backbone, retrieval budget *k*, single-query vs. agentic mode, and sync vs. async maintenance.
- **Plot accuracy against three cost axes:** p50/p95 user-path latency per turn (read + generation); tokens per turn; tokens per write, including deferred revision and forgetting.
- **Include the full-context baseline** as a point on every chart.
- **Decision rule:** a system is interesting only if it sits on the Pareto front. A 2-point accuracy gain at 10× p95 latency is a loss for a real-time agent.

**Two GEM-specific measures that no benchmark reports.** None of the benchmarks examined (LongMemEval, LoCoMo, AMB, StateMemBench, MemoryAgentBench, HaluMem) reports either:

1. **Write-to-visible latency:** the time from when a write is acknowledged to when the new value can be retrieved through the normal read path. This is the measurable form of C1/C2 under asynchronous ingestion.
2. **Staleness window:** the time, or number of transitions, from an update until every *dependent or derived* unit reflects it. This covers extension-linked topics (C3) and synthesized tiers such as Hindsight observations and mental models. Hindsight's consolidation backlog is a proxy for it; MemState's asynchronous revision implies one but neither defines nor measures it.

Both should be reported as p50/p95 distributions and added as axes on the Pareto plot.

> **Practitioner note.** With an asynchronous memory provider, I observed that the time to acknowledge a write and the time until it could be retrieved were different, and varied by the type of content written (seconds apart for some types). A user who corrects a fact and immediately asks about it can receive the superseded value. No benchmark reviewed here measures this gap.

### 6.9 Three levels of evaluation

Memory evaluation can isolate causes at three levels, and each catches failures the previous one cannot:

| Level | Example | What it detects |
|---|---|---|
| Answer accuracy | MAFBench's memory dimension, LongMemEval, LoCoMo | Whether the answer is right |
| Labeled behaviour | StateMemBench | *Why* it is wrong: state drift vs. retrieval vs. other failures |
| Stored state | GEM's conditions; this work's conformance suite | Whether the memory itself is right, even when the answer looks right |

StateMemBench argues that failing to *maintain* state is distinct from failing to *acquire* it, since better retrieval does not fix the former: on LongMemEval's oracle setting, where every gold fact is in the prompt, 44.4% of confirmed failures are drift, and in a separate 50-item A/B, enabling the model's reasoning trace does not help (accuracy 84% → 76%, not significant). MAFBench and StateMemBench apply the same principle, isolate the cause before attributing a result, on different axes: MAFBench controls the *independent variable* (fix the LLM and task, vary one architectural dimension, with a minimal reference implementation separating paradigm cost from implementation cost), while StateMemBench decomposes the *dependent variable* (label the failure type, with closed-pool grading that scores the superseded value as its own outcome). MAFBench's finding that schema-constrained planning loses accuracy for weaker models through formatting failures, not reasoning errors, is the closest it comes to StateMemBench's style.

---

## 7. Ideas to develop

### 7.1 Applying Zep's future directions to MemState

[P4] names several future directions, mostly in its conclusion (§5), and describes two capabilities it leaves unevaluated or already offers (§2.1, §3.1). Each maps onto a concrete extension of MemState:

| Zep future direction [P4] | Application to MemState |
|---|---|
| Integrate other GraphRAG approaches (Zep notes its community search parallels LightRAG's high-level key search) | Add a community/summary tier above topics. LightRAG's dual-level keys map loosely onto MemState's topic-mode routing (LightRAG attaches high-level theme keys to relations and low-level keys to entity names): topic titles and summaries would play the high-level role; entity keys would be the low-level ones. A dual-level router is a clean experiment. |
| Fine-tuned models for entity and edge extraction | Distill host-topic routing, field placement, and conflict-relation classification into a small fine-tuned model. Targets both latency/cost (Section 5.2) and [P2]'s silent format-error problem. |
| Domain ontologies | Typed field schemas per topic kind. They enable schema-drift detection (Section 5.8) and give rule-based conflict detection field types to match on. |
| Benchmarks with structured business data | MemState's field-structured topics fit structured data naturally. Ingest JSON alongside conversation, as Zep supports. |
| Cost and latency reporting (following LightRAG) | Adopt Zep's reporting format (latency, IQR, context tokens, against a full-context row) and add write-path and maintenance cost (Section 6.8). |
| Episode ↔ fact bidirectional indices (implemented in Graphiti; their evaluation is deferred to future work in [P4] §2.1) | Point MemState's provenance `π` at a non-lossy episode store, so C4 has a source to trace back to. |
| Breadth-first search seeded from recent episodes (an existing Graphiti capability, [P4] §3.1) | Expand retrieval context from recently touched topics along association edges. |

### 7.2 Hybrid conflict resolution: the LLM detects, rules resolve

**What Hindsight does.** Hindsight's consolidation (per its engineering blog on conflict resolution, February 2026, and its observations documentation):
- finds candidate conflicts by semantic recall over existing observations, limited by a token budget and by strict tag matching (a security boundary);
- uses a single LLM call, given proof counts and a dated timeline of sources, to classify the new fact against existing observations (as described in February 2026; later versions batch several memories per call);
- applies three merge rules written in the prompt: redundant facts are merged; direct contradictions keep both states as a temporal narrative, with the most recent treated as current when no explanation exists; state updates are rewritten as explicit transitions ("changed from X to Y");
- merges temporal metadata deterministically (earliest start, latest end and mention time);
- appends each change to a per-observation history (previous text, timestamp, reason, source memory), which is C4 in practice;
- filters ephemeral state from durable knowledge, which reduced false conflicts;
- when source memories are deleted, deletes the observations derived from them and resets the consolidation state of their remaining source memories, so the observations are re-derived, a one-level form of dependency propagation.

**Lesson.** Hindsight splits detection and resolution, but its "rules" are text in a prompt, so they cannot be checked or verified. StateMem goes the other way, with a deterministic, LLM-free rechecker over dependency links.

**Proposal.** The LLM classifies the relation (redundant, contradiction, or state update); declarative `⟨event, condition, action⟩` rules perform the resolution; the rule set over extension edges is analyzed for **termination and confluence**, the classic active-database problem (Widom & Ceri) that [P1] already cites. Hindsight runs the classification step in production; MemState would make the resolution step verifiable.

### 7.3 Lessons from Hindsight's synthesis tiers

In its current product documentation (v1.0), rather than its paper [P5], Hindsight organizes memory into raw facts, observations (auto-consolidated), mental models (curated, pre-computed reflect answers), and knowledge pages (a wiki-like tree of mental models built from observations). Reads check mental models first, then observations, then raw facts as ground truth; mental models return cached content with no LLM call at read time, which is the right pattern for latency-sensitive agents. Several mental-model mechanics map onto GEM:

1. **Delta refresh ≈ field-level revision (C2).** Refresh emits typed operations (add section, append bullet, replace block, remove stale paragraph), and untargeted sections are copied byte-identical: update the targeted unit without rewriting the rest.
2. **Never overwrite with empty ≈ a transition postcondition.** If the LLM call fails or returns empty, the existing content is preserved. MemState's abort-on-postcondition-violation also protects the prior value, but aborts the whole transition; Hindsight's guard leaves only the failed item untouched (Section 7.5, notes on C2 and C4).
3. **Drift from incremental revision is acknowledged.** Hindsight recommends periodic clear-and-rebuild because many small delta refreshes accumulate inaccuracies. GEM has no notion of drift accumulated across many revisions; the trajectory benchmark should test whether field state after *N* revisions still matches a fresh rebuild.
4. **Scoped, asynchronous propagation.** Consolidation refreshes only mental models whose tags overlap with the memories it processed, both for performance and as a tenant boundary; refreshes run asynchronously. This is an analogous mitigation, for a related side channel (refresh signals rather than salience, which Hindsight lacks), to [P1]'s concern about salience leaking across tenants, at the cost of a wider staleness window.
5. **Versioned history and provenance** per document (prior versions plus the accumulated facts and observations each version was built on) cover C4.

| Hindsight tier | Closest MemState concept | Gap |
|---|---|---|
| Raw facts | Field-history entries with provenance | Hindsight does not invalidate raw facts automatically (per its consolidation docs, conflicts are resolved in derived observations; the paper's observation prompt likewise resolves conflicts in the summary); MemState marks superseded values |
| Observations | Revision's merge/consolidation output | Hindsight's run asynchronously and report backlog; MemState detects staleness (Listing 1's flag) but does not surface it |
| Mental models / knowledge pages | A topic: a self-contained unit with structure | Topics have typed fields; pages are prose trees with typed edit operations |
| Tag-scoped refresh triggers | Policy-gated propagation along extension edges | Scoped by tags vs. by edge type; neither proves termination |
| *(no equivalent)* | Forgetting ladder and salience (C5, C6) | Hindsight has no relevance-driven forgetting; this is MemState's main differentiator |

**Why Hindsight needs its tiers, and which roles MemState already covers.** Hindsight's paper motivates its design with three problems: preserving and accessing long-term information, distinguishing what the agent observed from what it believes (*epistemic clarity*), and keeping a consistent viewpoint. Its tiers serve three roles:
- **Concept-level views** ("tell me about Alice" without retrieving every underlying fact): Hindsight needs observations because its base unit is a fine-grained narrative fact. MemState's topic *is* the concept-level unit, built structurally: field values are read directly, with no summarization call on the read path (the topic summary used for routing can still lag its fields), so this role is covered, with one trade-off: until promotion, facts about a sub-concept sit inside other topics.
- **Epistemic separation** of evidence, beliefs (with confidence), and summaries: needed because Hindsight *forms beliefs* through reflection. MemState does not, so this is a design difference rather than a gap, and no new condition is proposed. The derived content MemState does produce (revision outputs, compressed histories) is handled by C4′ (Section 7.5).
- **Pre-computed answers** for latency: an engineering choice. For cross-topic synthesis, query-time reasoning over retrieved topics is the default; precomputed views pay off only for predictable, repeated questions (sleep-time compute reports about 5× less test-time compute for equal accuracy on two stateful reasoning benchmarks, Stateful GSM-Symbolic and Stateful AIME, with effectiveness correlated with query predictability), and if kept they are derived units governed by C3′ and C4′.

**Takeaway.** Hindsight has independently built much of GEM's revision machinery (versioned derived state, typed incremental edits, failure-safe transitions, scoped propagation), but as prompts and product engineering, without formal correctness conditions and without relevance-driven forgetting. GEM supplies those conditions.

### 7.4 Salience, Hindsight's RL-free confidence, and learned policies

**Salience vs. reinforcement learning.**

| | Salience (MemState) | RL (Mem-α, Memory-R1) |
|---|---|---|
| Mechanism | Hand-designed online rule: rises on access, decays on disuse | Learns update policies from answer-quality rewards |
| Training | None | Required; long-horizon credit assignment is hard |
| Interpretability | Transparent | Opaque, backbone-specific |
| Main weakness | Access is only a proxy for utility; threshold-sensitive | Could learn to violate correctness (e.g., overwrite history if that raises QA scores), since answer-level rewards do not penalize it ([P1] §5); hypothetical, not shown |

**Hindsight's RL-free policy.** Opinion confidence follows a fixed rule: the LLM classifies new evidence as reinforce, weaken, contradict, or neutral; confidence moves by +α, −α, or −2α respectively, clamped to [0, 1]. Retrieval is likewise not trained on memory feedback: rank fusion uses a fixed constant, spreading activation a fixed decay and link-type multipliers, and reranking an off-the-shelf MS MARCO cross-encoder. [P5] lists an RL loop over retain, recall, and reflect as future work.

**Adapting it to MemState: confidence becomes corroboration.** In Hindsight the rule applies to *opinions*. MemState stores stated facts, so the analogous signal is **corroboration** of a field value: *reinforce* when the same value is confirmed again, *weaken* for a hedged or partial signal, *contradict* when a new value arrives (a supersession). No new epistemic types are needed. With bitemporal histories (Section 9.5), re-confirmations are history entries with their own recorded times, so corroboration can be counted from the history itself.

**The two signals are orthogonal.** Salience records whether a unit was *used*; corroboration records whether it was *confirmed*.

**Proposal.** Give each field a retention score combining:
1. salience from **attributed** use (only units that contributed to an answer), with decay on disuse;
2. corroboration, using Hindsight's update rule;
3. proof count (number of supporting statements);
4. dependency centrality;
5. an importance prior, such as StateMem's hard/soft priority, so a rarely accessed hard constraint (an allergy) is never forgotten for lack of use.

The forgetting ladder then acts on this combined score. One rule follows directly: a frequently accessed but *contradicted* value is the most dangerous kind of stale fact, so a contradiction should move the old value into history and reset its salience rather than letting access frequency keep protecting it. [P1]'s constrained learned controller can later tune the weights within C2–C5, with this RL-free version as its baseline.

**Two cautions.** (1) [P1] defines the salience increment on *every accessed unit* as part of the retrieval operator's semantics, so attributed salience is a refinement of how C6 is realized, presented as an open design question motivated by measurement (the prototype bumps every returned candidate; measured reinforcement precision is 0.125 = 1/8, the ceiling: the labelled topic was bumped on 15 of 15 questions and 7/8 of the increments went to other topics, F20), not as a correction. (2) StateMemBench's *salience errors*, where a more frequently mentioned competitor wins, are a warning: if salience ever influences what is returned, access-driven reinforcement could amplify a popular stale value. The contradiction rule above guards against this.

### 7.5 Proposed refinements to GEM's conditions

The proposal refines three existing conditions rather than adding new ones: one amendment (C1′), one strengthening (C3′) and one extension (C4′). Each builds on machinery the paper already has, and each is motivated by a measured or documented gap.

**C1′ — Valid-time query soundness (an amendment of C1).** One clarification and two additions.
- *Clarification.* Definition 4's timestamp `t` is when the value became true (its valid time), and "current" is judged at the asked date (by default, now) among **non-archived** entries: the value with the latest `t` not after that date. [P1] says that each entry carries a timestamp but not what it means, and no reading of one timestamp handles all six time stories (Section 9.6).
- *Addition 1: an end date per value*, so that a value which holds for a period only ("for October only") can end.
- *Addition 2: a recorded time*, when memory learned the entry, so that "what did memory believe on Feb 10?" is answerable beside "what was true on Feb 10?" ("as of" queries on both axes).

Two words are kept apart. A value is **ended** when its valid time is over; memory still holds it as true for its own period. An entry is **expired** when memory stopped holding it (a correction replaced it). If the valid value is archived, a read returns no current value plus a note that an archived value exists, rather than falling back to an older value. The model is the standard bitemporal model, in the form Zep uses for agent memory; the contribution is the read rule and its tests. §4.3 asks for bitemporal values, not for what a read returns.
*Motivation:* read with `t` as recording time, as the prototype implements it, C1's recency rule fails for retroactive statements, out-of-order arrival, future-dated changes, and temporarily scoped overrides (Section 5.7). Read as kindly as possible, with `t` as valid time, it still has no place for an end date or for what memory believed earlier, so two of the six time probes need the additions: the reference GEM's phase 1 passes the C1–C6 checks and is absent on exactly those two, T4 and T5 (F34, Section 9.7). Out-of-order arrival is the realistic case: any system that writes memory after the conversation ingests facts late.

> **Practitioner note.** In building real-time voice agents with long-term memory, I moved memory writes off the live turn and into post-conversation extraction. That keeps latency down, but it means facts reach memory late and in batches, which is exactly when recording order stops matching real-world order.

*Caveats:* supersession is deterministic *given* valid times. A rule can turn a relative phrase ("two weeks ago") into one against the message's reference time, and in the demo's chat series the stored start date was then right in every take (F40); vague phrases ("a few weeks ago", "since the reorg") and dates a model writes into free text remain LLM-dependent (F40). A scoped override must layer over the base value rather than close its validity. C1′ is the first step of the bitemporal field histories §4.3 already calls for; the demo implements it (Section 9.5). TOKI is the closest formal treatment (Section 5.11).

**Clarification of C2 (superseded).** C2 forbids returning a superseded value as current. A value is **superseded** only when a later statement ends its validity. A scoped override that has lapsed ends by its own date, so the base value returning is not a C2 violation; an ended override returned as current is a C1′ error, not a C2 violation. The suite reads C2 this way on the lapsed-override story (Section 9.4).

**C3′ — Bounded, visible dependency consistency (a strengthening of C3).** An update to a unit triggers evaluation of its dependents *within a policy-defined bound* (a time limit or a number of transitions). Until a dependent is re-evaluated, every retrieval of it returns the revision flag and its evidence. `P_t` decides whether a read of a flagged unit returns it with the flag (soft facts) or blocks or forces repair first (hard constraints). Repairs are persisted in storage.
*Testable core (scored on the reference GEM):* an update to A flags each direct extension-edge neighbour, naming the update (the field and its time, as Listing 1's `flag_for_revision(dependent_topic) WITH evidence`); a read of the dependent before it is re-checked returns that flag; a topic linked only by an association edge is not flagged; the flag clears when the dependent is next written. The bound and the repair are not tested.
*Motivation:* the paper already detects staleness (Listing 1's flag) but neither surfaces nor bounds it, and the prototype has neither flag nor repair (Section 5.3, recorded run). StateMem shows per-unit flags are cheap (deterministic, O(|E|), no LLM call). Its ablations give the flags alone a mixed effect (without them: 0.222 vs. 0.233 on Qwen, 0.373 vs. 0.363 on DeepSeek), while the prompt that guides the answering model in using them is worth 2.5–6.2 points (0.208 and 0.301 without it), margins its authors read as an upper bound. The case for C3′ therefore rests on correctness: a stale value should never be returned silently. Hindsight computes staleness structurally (a stale mental model stops short-circuiting retrieval) but leaves verification to the reflect agent's prompt. C3′ keeps MemState's repair in storage and adds StateMem's visibility and a bound. It should be paired with the precision requirement in Section 5.5, so that flags do not become over-eager revisions.

**C4′ — Evidence-backed provenance (an extension of C4).** Provenance must resolve to retained source evidence, and must record how each entry came to exist: *stated* (from a message), *revised* (by merge, conflict resolution, or reorganization), or *compressed* (a summary replacing earlier entries under the forgetting ladder). It adds a state component, the retained source, that C4 does not have. The suite's C4′ probe checks whether provenance resolves to a stored source (Section 9.6).
*Motivation:* π is currently a label (who, why); without the source, extraction errors cannot be repaired and provenance cannot be verified (Section 5.7). MemState also produces content nobody stated (revision outputs, compressed histories), and C4′ marks it as such.
*Trade-off:* retaining raw sources retains more personal data, which works against the paper's verifiable-erasure direction. Sources sit outside the active set (C5 is unaffected), and erasure must cascade to them and to everything derived from them.

**Notes on related principles.**
- *Non-destructive failure* (a transition whose input fails validation commits nothing for the affected fields) is expressible under C2 (as a policy postcondition) but not implied by C2 or C4 as stated; C4 covers only forgetting and revision. It is worth stating at field granularity: Hindsight independently guards mental models against being overwritten with empty content, and MemTX's QUARANTINED state keeps invalid records apart. GEM's commit is all-or-nothing, while per-field isolation avoids losing a whole batch to one bad item; which granularity a governed memory should adopt is an open question. In the prototype, `version_field` with `""` and with `null` was accepted and became the current value (recorded run, F21).

> **Practitioner note.** I encountered this failure in practice: an extraction that failed to parse was treated as an empty result and overwrote the previous session summary. The fix was to abort the write on failure and never replace an existing value with nothing. That is a field-level version of the rule; GEM's Algorithm 1 would instead abort the whole transition.

- *Authority separation and rebuildability* (derived content never silently overrides evidence; every derived unit can be rebuilt from its sources or is flagged unrecoverable) belong under the paper's privacy and verifiable-erasure direction, as future work. MemTX's typed records with authority weights and its derived-from graph with cascading repair are working precedents.
- *No new condition for epistemic separation.* Hindsight separates evidence from beliefs because it forms beliefs; MemState does not (Section 7.3).

### 7.6 Requirements for the native engine

**Specified in [P1] (Sections 4.3 and 5):**
- field histories as first-class bitemporal attributes;
- propagation semantics attached to extension edges in the schema;
- policy postconditions compiled into the commit protocol;
- retrieval-induced salience updates as a single read-modify-write primitive;
- relevance-driven forgetting scheduled like index maintenance;
- a storage layout co-locating topics, field histories, and embeddings to reduce I/O;
- one index serving semantic similarity, history predicates, and structural queries;
- a buffer strategy keeping hot topics and their dependency context resident;
- the consistency cost of salience updates under concurrent access (with the page layout and joint index, one of the paper's three first targets);
- per-tenant isolation of salience (Section 5, Privacy and Multi-Tenancy);
- erasure that also removes derived salience and provenance traces (Section 5).

**Added by this review:**
- concurrent writes, given retrieval-as-write and the Kuzu situation (Section 5.10);
- an asynchronous maintenance scheduler that reports its backlog per unit (C3′);
- write-to-visible latency as a service-level objective;
- rebuildability of derived units (Section 7.5);
- accounting of LLM calls and tokens per operation;
- a session-level read-your-writes path, so asynchronous ingestion does not break C1 within a conversation.

**Could Graphiti serve as this engine?** Partly. Graphiti (Zep's open-source temporal-graph engine) is a library running on top of an external graph database (Neo4j, FalkorDB, Amazon Neptune; Kuzu is still shipped but deprecated, because upstream Kuzu is unmaintained), so it covers the temporal and provenance requirements well but not the GEM-specific ones, and the engine-level items are outside its scope.

| Requirement | Graphiti |
|---|---|
| Bitemporal field histories | **Covered**, its strongest point: each fact edge carries `valid_at` / `invalid_at` (when it was true) and `created_at` / `expired_at` (when it was recorded or retired); superseded edges are kept |
| Provenance (C4) | **Covered**: facts link back to the episodes they were extracted from |
| Concurrent writes, per-tenant isolation | **Partly covered:** data is partitioned by `group_id`, but there is no access control (the reference servers let any caller touch any `group_id`); concurrency is whatever the backend database provides. Salience isolation does not apply, because Graphiti has no salience |
| Propagation semantics on edges (C3) | **Limitation:** invalidation affects only the contradicted edge; dependent facts are not re-evaluated (zero-hop, Section 5.5) |
| Policy postconditions in the commit (C2) | **Limitation:** no declarative policies; contradictions are detected and resolved by an LLM prompt, so they can be silently missed |
| Salience as a read-modify-write primitive (C6) | **Limitation:** retrieval is read-only; reads never change state |
| Relevance-driven forgetting (C5) | **Limitation:** nothing decays or is archived by relevance; content leaves only through explicit deletion (`remove_episode`) |
| Backlog-reporting maintenance scheduler (C3′) | **Limitation:** ingestion runs a multi-step LLM pipeline per episode, with no staleness signal for derived data |
| LLM cost per write | **Limitation:** several LLM calls per episode (entity and fact extraction, resolution, deduplication, temporal extraction, invalidation); [P4] does not report ingestion cost |
| Storage layout, unified index, buffer strategy | **Out of scope:** these belong to the database underneath; Graphiti combines the backend's separate indexes in hybrid search |

Graphiti is therefore a good reference for how bitemporal history should look, and a natural baseline (Graphiti-on-Kuzu vs. MemState-on-Kuzu isolates the data model, while Graphiti's deprecated Kuzu driver lasts, Section 5.10). It is not a candidate for the native engine itself: what [P1] asks for has to live inside the database, below a library like Graphiti. Candidate database engines are compared in Section 5.10.

### 7.7 A GEM trajectory benchmark

Rather than starting from scratch, build on existing work:

- **Reuse** StateMemBench's closed-pool grading (reduces judge sensitivity: a judge only maps answers onto a fixed pool) and AOEP-v0's event-stream-plus-snapshot schema.
- **Probe throughout the trajectory**, not only at the final turn.
- **Two length tracks:** a short track (state tracking is hard even in context, Section 6.3) and a long track that exceeds the context window, reporting Δ in both.
- **Implicit dependencies** that must be discovered, alongside explicit ones.
- **Ground truth at three levels:** current value per unit over time (C2), dependents that should change after each update (C3), and active footprint per interaction count (C5), as specified by [P1], Section 5.
- **New measures:** C6 effects (does repeated access protect a unit, and does it protect the *right* units?), propagation depth, write-to-visible latency, staleness window, and cost per operation.
- **Revision drift:** compare field state after *N* revisions against a fresh rebuild.
- **At least one real-transcript track**, since synthetic traps tend to mirror the method designed to beat them (a caveat StateMemBench's own authors raise).
- **Systems:** the baseline set of Section 6.3, reported on the Pareto plot of Section 6.8.

### 7.8 Topic granularity: why dependencies stop at the topic boundary

**The topic is the atom.** [P1] calls the semantic unit the atom of `D_t`, with its boundary chosen so that one read reconstructs one concept. That choice has three consequences:
1. **Inside the atom there are no hops.** The "few hops" claim counts hops *between* topics; topic grain beats entity grain precisely because everything about one concept sits in one unit. Adding dependency edges inside a topic would rebuild an entity graph inside the atom.
2. **Consistency inside a unit is C2's job, not C3's.** C3 governs pairs of different units connected by propagation-bearing edges; C2 governs whether any transition, including on the updated unit itself, satisfies `P_t`, and policies can reference the memory state directly. Revision also lists conflicting field values among the evidence it repairs.
3. **If two fields evolve independently, the boundary is wrong.** A field that acquires its own lifecycle is a separate concept (MemState's own modelling guidance). [P1]'s remedy is promotion once enough knowledge accumulates: Alice splits out of Website Redesign once enough interactions reference her, and C3 then applies across the new edge.

**What remains.** Two small points, neither a structural gap: the promotion threshold ("sufficient knowledge") is unspecified and should be a measurable policy; and cross-topic triggers can target specific fields (`Website Redesign.Deadline → Milestone.Date`) through policy conditions on `updated_field`, which Listing 1 already records, improving precision without adding structure.

**Relation to LightRAG and hierarchical graphs.**
- **LightRAG** builds one flat graph of entities and relations, each with an LLM-written profile, and retrieves with *dual-level keys*: low-level keys match specific entities; high-level keys match relations whose index keys carry broader themes. MemState's topic-mode routing over titles and summaries resembles high-level key retrieval; adding entity-level keys gives a dual-level router.
- **Hierarchical graphs** stack derived levels over a base graph. Zep has three tiers: episodes, then entities and facts, then communities (entity clusters with summaries). MemState's topics resemble Zep's communities, with one difference: in Zep, episodes are the non-lossy ground truth, entities and facts are extracted from them and hold the current state, and communities are summaries derived from entity clusters; in MemState, the topic *is* the authoritative unit. MemState makes a community-like unit the source of truth.

### 7.9 Ranked future directions

1. **Implement C3′.** Listing 1's `propagate-on-change` plus surfaced, bounded flags; measure the staleness window, and pair it with the precision requirement of Section 5.5.
2. **An RL-free retention score** (Section 7.4): attributed salience, corroboration counted from bitemporal histories, proof count, dependency centrality, and an importance prior, as the baseline for the paper's constrained learned controllers.
3. **A GEM trajectory benchmark** (Section 7.7), adding StateMemBench's closed-pool grading and failure labeling, and latent-link probes scored on link precision and recall rather than answers.
4. **Link MAFBench and GEM:** apply StateMemBench's drift labeling to MAFBench's selective-forgetting failures, to determine whether frameworks fail to retrieve updates or fail to maintain state, which tells whether the remedy is better retrieval or GEM-style governance.
5. **Further ideas:** TOKI's isolation and keyed-logging analysis applied to MemState's LLM-driven revision and to concurrent retrieval-induced salience updates; hybrid conflict resolution with termination and confluence analysis (Section 7.2); link discovery with confidence-gated promotion to extension edges (Section 5.4); Zep's directions applied to MemState (Section 7.1); engine candidates for the native engine (Section 5.10).

---

## 8. Link to the MAFBench paper

MAFBench [P6], from the same lab, evaluates multi-agent *frameworks* (LangGraph, CrewAI, AutoGen, Agno, the OpenAI Agents SDK and others) across five architectural dimensions. Its memory dimension adopts MemoryAgentBench's four competencies: Accurate Retrieval, Test-Time Learning, Long-Range Understanding, and **Selective Forgetting** (controlled revision through counterfactual updates, the FactConsolidation tasks).

**Memory results relevant to GEM.**
- Frameworks fall into three memory designs: retrieval-centric (CrewAI), accumulation-based (Agno, OpenAI SDK), and hybrid (LangGraph, evaluated in retrieval-only and hybrid modes across context windows).
- **Selective forgetting is largely unsupported.** Retrieval-centric designs partially support single-hop forgetting (retrieval-only LangGraph reaches the best Selective Forgetting average, 20.2, with single-hop FC-SH 36.0 and multi-hop 4.5; Table 10), but **multi-hop forgetting stays below 5.0 across all architectures**. Accumulation-based designs perform worse even with large context windows, and hybrid designs collapse because outdated information persists in both the retrieval store and the accumulated context.
- **Every evaluated framework treats memory as append-only.** None provides explicit revise or remove operations.

**MAFBench's future direction (Section 6).** Memory architectures should support explicit revise, remove, and invalidate operations with dependency tracking across stored facts. MAFBench proposes versioned fact stores with multi-version concurrency control, write-ahead logging for reversible updates, and conflict resolution for concurrent writes, i.e., the transactional, versioning, and consistency guarantees databases already provide.

**How this connects to GEM.**
- MAFBench's failures are GEM's failure modes ① (unregulated growth) and ② (missing semantic revision), measured at the framework level. Multi-hop forgetting below 5 is consistent with a C3 (dependency consistency) failure, though answer-level scores cannot confirm it.
- MAFBench calls for database guarantees; GEM answers its title question with a flat "no": agent memory is a new data-management workload, not a database problem. The two are compatible under **our claim (not GEM's wording): database guarantees are necessary but not sufficient.** A versioned row (MAFBench's concrete solution: versioned fact stores with multi-version concurrency control, write-ahead logging and conflict resolution, `2602.03128v2.md:568`) gives C1, C2's atomic commit and current-value rule, and C4. It lacks declarative policies (C2(c)), dependency tracking (C3, which MAFBench itself also asks for: "dependency tracking across stored facts"), forgetting (C5) and reinforcement (C6), scored absent. The demo's versioned-row baseline (Section 9.3) tests this directly, and the run of record bears it out: pass on C1, C2(b), C2 on the lapsed override and C4; absent on C2(c), C3, C5 and C6 (F34).
- MAFBench's memory metrics are accuracy, F1 and Recall@5 (its Table 8), with answers graded by "LLM-based semantic scoring" (its Section 3). They grade answers and retrieved evidence; none reads the stored state, so they cannot see whether a correct answer comes from a correct stored state. The demo therefore inspects MemState's stored state.
- MAFBench attributes the collapse of hybrid memory designs to outdated information persisting in both stores, but its answer-level scoring cannot separate a failure to *retrieve* the update (acquisition) from a failure to *use* it (maintenance), the distinction StateMemBench draws (Section 6.9). Applying that labeling to MAFBench's selective-forgetting failures is future direction 4 (Section 7.9).

---

## 9. Demo: time-correct governed memory

> **In one line:** a conformance suite tests MemState against the guarantees its own paper claims, beside a versioned-row baseline and a reference GEM built to the paper's definitions; C1′, the standard bitemporal model in the form Zep uses, added to MemState's field histories on LadybugDB (a maintained community fork of Kuzu), fixes the time-dependent cases the published prototype gets wrong, with no regressions on the rows the suite checks (run of record, Sections 9.7 and 9.8).

### 9.1 Goal

Three parts. **(1) A baseline**: GEM's first evaluation target is a trajectory-level benchmark (Section 6.2), and the demo builds a small version of it, a *conformance suite* that inspects MemState's stored state (current values, field histories, salience, archived flags, edges), not only its answers, and tests the prototype against the guarantees Section 4 of [P1] states, beside a versioned-row baseline. **(2) A reference GEM**: our own small system built to the paper's definitions of C1–C6, with declared simplifications, scored in two phases beside MemState (Sections 9.2 and 9.5). It answers the objection that the prototype fails the time cases only because it is incomplete. The claim moves from "the published prototype gets the time cases wrong" to a testable one: a system that passes the suite's checks still cannot answer all six time stories under the kindest reading of Definition 4's one timestamp, so the gap is in the conditions (Section 5.7), and C1′ closes it without breaking the other rows. The run of record confirms both halves on our own system: phase 1 is absent on T4 and T5, and phase 2 passes them with no other row moving (F34). **(3) The contribution**: C1′, the amendment of Section 7.5 (one clarification, two additions), applied to MemState's field histories, implementing the first step of the bitemporal attributes §4.3 calls for. The model is the standard bitemporal one, in the form Zep uses; the contribution is the read rule and its tests.

### 9.2 Method

- **Systems.** Seven, in three groups. *MemState:* upstream, unmodified, on `kuzu` 0.11.3 (the final release; the published `pyproject.toml` requires `kuzu>=0.11.0`), driven over HTTP (`/v1/ingest`, `/v1/query`) with the Graph Explorer open; and a patched copy on LadybugDB at each of its three commits (steps 1–3). *Reference:* the reference GEM (Section 9.5), in-process, in two phases: phase 1 reads Definition 4's timestamp as kindly as its words allow (a value's one timestamp is when it became true; "current" is judged at the asked date among non-archived entries; no end date, no recorded time), and phase 2 adds C1′. *Baseline:* the versioned row (Section 9.3). MiniLM embeddings, and top 8 for every in-process system (MemState's default `top_k`), so that C6 and the triage numbers are comparable.
- **Evidence rule.** A behaviour enters this report only after a recorded run on a fresh database reproduces it; every verdict saves a raw-state snapshot. Claims from reading code alone are labelled as such.
- **Verdict scale.** *pass*; *partial*; *fail* (the capability exists but behaves incorrectly); *absent* (the capability is missing, confirmed by a probe); *not-scored* (no case could run). A verdict rests only on the cases that could run: a case that needs a capability belonging to another condition is n/a, and the cell says how many were skipped (for example `pass (1 case n/a)`). Absent differs from not-scored: absent means the whole condition's capability is missing. Each verdict is read against the paper's own claim for that condition, and a *claimed by [P1]?* column shows whether the paper makes one.
- **Controls.** C1 and the update path of C4 should pass, showing the harness can detect a pass; every trap probe has a paired control (an ordinary update that *should* replace a value), following MemTX's conformance-suite design, so over-blocking is caught too.
- **Two write paths as a control.** On `/v1` the harness decides placement, so acquisition is perfect by construction and any failure belongs to the store's maintenance, the analogue of the perfect-retrieval (LongMemEval-oracle) analysis in the StateMemBench paper (Section 6.9). On the chat path, LLM placement can add acquisition failures; it is used for one recorded example.
- **Repeats.** Deterministic tests once. The merge test (C2(a)) is reported as **existence**: with the dropped topic holding the newer value (arranged by a labelled setup write), does the merge make the superseded value current? On upstream it did in 20 of 20, so the number is not a rate; the natural count on random IDs, where which copy survives depends on ID order, is shown beside it and is not compared between systems: it is a random draw (10 of 20 in F9; 11, 10 and 9 of 20 on upstream, step 1 and step 2 in the run of record, F32). Latency ramps run on MemState's four systems with the same undated writes and reads (steps 2 and 3 also time 20 as-of reads at 2,000 topics). The run of record repeats each ramp three times on the final commits, and the report gives the median and range; the suite calls a difference of medians no larger than the larger sample range "no measurable difference", a rule that query outliers make generous (Section 9.7, F33). The reference GEM runs C5-2's topic counts once per size with no timing, because its C5 verdict rests on the active and archived counts at 2,000 topics; it has no latency rows (in-process milliseconds are not comparable with an HTTP server, and the ramps measure the engine swap and the patch) and no chat run (it has no LLM chat).
- **Answer-level contrast (n = 1).** After a bad merge, questions asked through MemState's chat show an answer that looks right while the stored state violates C4. The paper's own re-explained duplicate (Figure 1, "stored twice") is merged so that the original Website Redesign topic is dropped: the deadline answer is still April 20, while the deadline's history and its "vendor delay" provenance are gone.
- **Search vs. memory, per question.** Each storyline question is labelled with the topic that holds its answer. A wrong answer is sorted by StateMemBench's first triage question ("is the gold fact in context? (no → retrieval failure)", its Appendix A.1): if `/v1/query` did not return the labelled topic, it is a *search failure*; if it did and the stored value is wrong, a *memory failure*. This extends the write-path control above to the read side: placement is perfect on `/v1`, retrieval is not. Every storyline answer is one stored value, so its questions are LongMemEval knowledge-update and information-extraction questions. Time is tested separately by the six time probes and the "two weeks ago" chat run, which measure whether stored values are valid at a date, not LongMemEval's temporal-reasoning questions; multi-session reasoning and abstention are not measured (an abstention question has no answer topic to triage).
- **Measurements.** Query and ingest latency at 100 to 2,000 topics on both engines, with and without the bitemporal extension (the ramp's settle time is not a Reasoner wait, F22; the only Reasoner timing is the merge revision window); the merge revision window and the dependent-topic staleness window, in seconds on MemState and in interactions on the reference GEM (Section 6.8 defines the staleness window as "the time, or number of transitions"); reinforcement precision for C6: the share of salience increments that went to the labelled topic. Because MemState bumps every returned candidate, this equals the retrieval's Precision@*k*: measured 0.125 = 1/8, the ceiling for one labelled topic at the default `top_k` of 8 (F20). MemState's built-in limits are stated with their numbers: the 500-entry history cap (a correction uses two entries; 501 writes to one field leave 500 entries and the oldest is gone, F21) and C5's 500-topic soft limit against 2,000 active topics after 2,000 ingests (F10, F22).
- **Grading our own work.** The same authors write the checks, build the reference GEM and choose its parameters. So the stricter C3 and C2(c) checks, the parameters (θ, λ, β) and each probe's expected verdict are written in the suite's spec before the reference GEM is built; each check is run against one deliberately broken reference GEM per condition and must fail it; and the result is worded "passes the suite's checks, with declared simplifications", never "satisfies C1–C6".

### 9.3 Baseline: versioned row

An append-only history per (title, field) with the time each value was recorded, one transaction per write, in-process, MiniLM embeddings with top 8. Empty and `null` values are rejected, as a NOT NULL / CHECK constraint would (`Rejected`, nothing saved). MAFBench asks for versioned fact stores with database guarantees (multi-version concurrency control, write-ahead logging, conflict resolution; `2602.03128v2.md:568`); this is one. It answers the paper's title question with measurements: what does MemState provide that a versioned database row does not? Measured (F34): it passes C1 (the read returns the latest recorded value), C2(b) (a write with a missing reference is rejected whole), C2 on the lapsed override, and C4 (history kept, empty and `null` writes rejected with nothing saved, the 501-write cap held; 3 cases n/a). A second same-title `new_topic` appends to the same topic, so no merge occurs and C2(a)'s arrangement cannot be met: the row is not-scored (20 merges seen, 20 with the arrangement not met). It lacks declarative policies `P_t` (C2(c)), edges and dependency tracking (C3), and salience and forgetting (C5, C6); each is absent, confirmed by a probe (no edges, no archived flag, salience reads none). It records only its own clock, so the time probes are absent on all six; it accepts `recorded_at`, so T5's "accepts dates" cell reads partly. This tests our claim that database guarantees are necessary but not sufficient (Section 8). It answers the 15 storyline questions 15/15, as every MemState system does, so the difference shows in stored state (C3, C5, C6), not in answers.

### 9.4 Conformance tests against the paper's claims

| Condition | [P1]'s claim (§4, §4.3) | Test | Interpretation |
|---|---|---|---|
| **C1** Query soundness | By construction | Store `Deadline: March 15`, update to `April 20`; default and temporal queries | Control: should pass |
| **C2** Transition soundness | By construction | (a) **Superseded value:** merge two same-title topics where the dropped one holds the newer value, reported as existence with the natural random-ID count beside it; and the superseded read on the lapsed-override story (the value returned today must not be one that a later statement ended). (b) **Atomic commit:** one `new_topic` ingest with a valid first field and a second field whose `ref_topic_id` points to a missing topic. (c) **Declarative policies:** a policy added at runtime ("Deadline not before Start") must reject a violating write with nothing saved, while an ordinary write still commits (control) | A fail contradicts a stated claim. (b) On upstream the request is rejected (HTTP 400) yet the topic and its first field stay stored: a partial commit, fail (F23). An edge to a missing topic is a separate soundness observation, not the C2(b) input: ingest reports `edge:<id>` applied but stores no edge (F17), so atomicity is never exercised. (c) Absent on upstream: its API exposes no policy surface, only six internal numeric knobs (F17). On the lapsed-override story the base value returning is not a C2 violation: a value is superseded only when a later statement ends its validity (Section 7.5) |
| **C3** Dependency consistency | §4 opening: by construction; §4.3: not listed | B depends on A via an extension edge; update A; read B before and after revision. A system that propagates must flag B because of the extension edge, naming the update, must not flag a topic linked to A only by an association edge (control), and must clear the flag when B is next written | *Absent* matches §4.3 but falls short of §4.2's flag-and-repair |
| **C4** Provenance preservation | By construction | History survives updates, merges, and forgetting (real forgetting only, never an editor archive write); the 500-entry history cap (501 writes to one field: is the first value still readable?); an empty or `null` write must not replace an existing value (implied by C2/C4, not part of C4's definition) | History loss on merge contradicts a stated claim. On upstream the cap drops the oldest entry (F21), and the forgetting case is n/a: a topic with fields is never forgotten through `/v1` (F24). The verdict rests on the cases that could run |
| **C5** Bounded active state | Under transitions | **Mechanism:** a topic created with `salience=0.01`, checked past the 500-topic trigger; **natural trajectory:** no setup, count archived topics as the store grows. C5 counts topics, not history entries, and the verdict text states the system's declared bound beside the active count | The forgetting pass runs at the 500-topic gate and archives a topic below 0.05 (mechanism pass, salience 0.01 → 0.005, F22). With no decay, nothing falls below 0.05 naturally: 0 archived through 2,000 topics against the 500-topic soft limit (natural trajectory fail, F22). F24 is also a C5 observation: a topic with fields is reset to salience 1.0 by any field write and is never forgotten through `/v1` |
| **C6** Retrieval-induced adaptation | Under transitions | **Clause 1:** retrieval raises salience (and which candidates), including an as-of read where the system accepts dates; **clause 2:** a topic at 0.03 queried rises above 0.05, and the check stops at the first forgetting pass: the never-read control must be archived and the read topic must not be; reinforcement precision | If the control is not archived, no forgetting pass was shown to run and the target's survival cannot be judged: not-scored, with the observation "forgetting was not shown to run" (that is C5's failure). A field write resetting salience is a durability observation, not a clause-2 failure: one field write set a reinforced 0.13 to 1.0, so salience is overwritten, not accumulated (cause [INFERENCE], F15). Over-reinforcement: 3 of 3 unrelated topics rose exactly as far as the target (1.0 → 1.3, F15). Reinforcement precision carries no verdict: C6's wording requires a bump on every accessed unit ([P1] §3.3), while its motivation is reinforcing *useful* facts ("User interaction patterns cannot reinforce useful information", [P1] §1, failure ④), so the number measures the gap between the two |

### 9.5 The contribution: C1′, on the reference GEM and on MemState

**Framing.** C1′ is an amendment of C1 (Section 7.5): one clarification (a value's timestamp is when it became true, and "current" is judged at the asked date among non-archived entries) and two additions (an end date per value, and a recorded time). The model is the standard bitemporal model, in the form Zep uses for agent memory. Our contribution is the read rule and its tests, not the model. It is applied twice, so that the fix is shown both on a system built to meet the conditions and on the authors' own system: to the reference GEM (phase 1 → phase 2) and to MemState's field histories (three commits).

**Model on MemState.** Zep's time model is added to MemState's field histories while C1–C6 keep holding: Zep's behaviour is the default, and each departure below names the condition that requires it. Each history entry carries Zep's four timestamps: `valid_from` and `invalid_at` (when the value was true; Zep's `t_valid` and `t_invalid`; `valid_from` is MemState's existing field) and `created_at` and `expired_at` (when memory recorded the entry and when it stopped holding it; `t′_created` and `t′_expired`). A write with no dates is valid from the moment it is recorded and carries no end date, so undated writes behave exactly as upstream.

**Rules.**
- *Ordinary update:* entries are ordered by `valid_from`. An entry is valid until the next entry's `valid_from`, unless it carries its own end ("for October only"). An ordinary update therefore stores no end date on the entry it replaces and does not expire or copy it: one undated update leaves exactly two entries. This is MemState's own model, a stack of revisions where writes append and nothing is edited (`MemState/docs/data-model/fields.html`), and it keeps upstream's history-count test (`test_field_history_tools.py:27-49`, `history_count == 2`) unedited. A late-arriving older value ends where the later one begins, with no stored end; on equal `valid_from`, the later-recorded value wins. Graphiti's code orders a late-arriving older fact the same way (`edge_operations.py:730-743`, commit `6e3e3cb`), although the paper's wording ("Graphiti consistently prioritizes new information") suggests the transaction timeline decides. Expired entries are hidden unless history is explicitly requested (`explain`, temporal stages, or a "true on" / "believed on" date), as MemState's docs state; history reads show them with their `expired_at`. Worked by hand [INFERENCE]: in the as-of probe, "believed on Feb 10" still returns April 20, because nothing expired it; the patch's tests must show it. The patch departs from Zep in four places, each required by a condition:
  - *Ordinary updates store no end date (C1, C4).* Zep stores `t_invalid` on the old fact, edited in place in Graphiti's code (`edge_operations.py:779-780`), because its facts are unordered edges. In a field slot the order already says what replaced what, the same reason Zep's LLM judge is dropped; storing the end again would add an entry per update and break upstream's history-count test.
  - *Corrections keep and copy (C4; ADR 0005), only when a stored end date changes or a value is retracted.* The entry is not edited: it is marked `expired_at` = now, and a corrected copy is appended with the original provenance (`operation: "interval_corrected"`, `replaces_entry_id`, `corrected_by_entry_id`). Graphiti edits the old fact in place, which loses what memory believed before and breaks [P1]'s "updates append a new entry rather than overwrite".
  - *A value with an end date stays current until it ends (C1).* Graphiti marks such a fact expired on arrival (`edge_operations.py:726-728`), so an October-only value would never be current in October.
  - *No LLM judge (C1, C2).* Values in the same field compete, so MemState's field slot identifies conflicts; Zep asks an LLM, the gate [P1] says "silently misses contradictions". Supersession is deterministic *given* timestamps, and the demo resolves relative date phrases into them by rule (*Reference time* below; F40); vague phrases, and dates the model writes into free text, stay LLM-dependent.
- *Scoped override:* a value written with its own end date ("for October only") layers over the base value instead of closing it; when several values are valid at the query time, the one with the shorter validity wins; a later plain statement ends every value whose validity contains its start, overrides included (C2). Ending an override that carries a stored end changes that stored end, so keep-and-copy applies. Layering is the one rule beyond Zep, whose code would close the base value for good (`edge_operations.py:774-781`); it costs no condition. It is hard-coded, standing in for the declarative conflict-resolution policy [P1] calls for.
- *C1′ query:* a default query returns only the value valid now and not expired; history appears only on request (C1). Every field carries `current` (`null` when nothing is valid) on `/v1/query` and on the UI topic read. *As-of* queries work on either axis ("what was true on Feb 10?" vs. "what did memory believe on Feb 10?") and raise salience like any read (C6; the suite checks it). The server selects the current value, where Zep hands the model facts with date ranges.
- *Reference time:* a chat message may carry a reference time (default: now). It is given to the model, as Zep's `t_ref` is; it is the default `valid_from` of values written from that message and the as-of time of its reads. Relative dates in a chat write are resolved against it by rule, not left to the chat model (commit 2; F38, final rules F40): a relative phrase ("two weeks ago", "yesterday", "next month") in the value is replaced by its date, unless the value already states that date, in which case the value is kept as written; else the message's one phrase sets `valid_from`, over a different date the model computed; a single ISO date in the value that differs from the resolved one is replaced; the phrase and the model's dates go into the provenance. Two phrases, or a vague one ("a few weeks ago"), resolve nothing (F38, F40). Graphiti's code-level rule that dates a future-tense fact ("will be on premium from December") at the message time is not adopted; it would make the future value current early.
- *Merge by valid time:* merging duplicate topics interleaves both histories by valid time; entries from the dropped topic keep their provenance and are tagged (`operation: "merged"`, `merged_from_topic_id`); entries whose validity changes are expired and copied; archived topics are skipped and duplicate pairs recomputed after each merge; the survivor records one merge event. This fixes the merge's history loss (C2, C4). The dropped topic's summary, topic events, and salience are still lost. Zep avoids merging altogether by resolving duplicates at ingestion and adding each new source to the fact's episode list.

**The reference GEM.** An in-process system of ours behind the suite's system adapter, like the baseline. The method is MemTX's (Section 6.2): a small reimplementation that implements what the paper claims, with deliberate absences declared, scored beside the authors' own system. MemTX's own MemState baseline has no topics, salience, decay, edges or merge, so we copy its method, not its code. The design is written before the build:
- *C1, C2(a) and the two phases.* Phase 1: one timestamp per value, meaning when it became true; the current value is the one with the latest timestamp not after the asked date among non-archived entries; no end date and no recorded time. Phase 2 adds C1′ with the rules above. Merge (revision) runs after every ingest, as MemState's Reasoner does (`MemState/src/memstate/reasoner/engine.py:36-37`), as a separate step after the write commits ("Revision and forgetting run asynchronously", [P1], `2605.26252v1.md:291`); the survivor keeps both histories with their provenance, and the current value is the later write in phase 1 and the later valid date in phase 2. Until revision has run, a read can see both copies; the merge revision window is reported in interactions.
- *C2(b), C2(c).* A transition is validated against the proposed next state and commits all or nothing. Policies are ⟨event, condition, action⟩ rules stored in the state as data and addable at runtime; conditions come from a small fixed vocabulary (field comparisons on the topic being written; "a neighbour exists via an extension or association edge"); actions are *reject* (a postcondition checked before commit) and *flag for revision*. A default policy rejects empty and null values.
- *C3.* C3 runs as the paper's Listing 1 policy, one hop and undirected, as C3's own wording is ("for every pair connected by a typed edge, an update to one triggers evaluation of the other", `2605.26252v1.md:212`; "a change in one can entail a change in the other", `:275`): an update flags every topic connected to the updated one by an extension edge, whatever the edge's direction, with its evidence (`{updated_field, timestamp}`); association edges never flag; the flag clears when the flagged topic is next written, and that write flags its own neighbours. Both pairs of the C3 check (B → A and A → B) are scored. There is no repair. A transitive walk is measured on one chain scenario with one anti-trap (a dependent that does not actually change) and reports flags raised against flags needed, for Section 5.5's "how many hops" and StateMem's over-propagation cost. The dependent-topic staleness window is reported in interactions.
- *C4.* The history is capped at 500 entries as in MemState, but overflow is archived, not deleted: it leaves the active history and stays readable by id ("archived content remains recoverable", [P1], `2605.26252v1.md:216`). Each write stores its source message, so provenance resolves to it (the C4′ probe). If the valid value is archived, a read returns no current value plus a note that an archived value exists.
- *C5.* MemState's behaviour is reused wherever its code has it: threshold θ_archive = 0.05, the declared bound β = 500 active topics (its `topic_count_soft_limit`), and halving a topic's salience when it is archived (`executor.py:360`). Added, because the paper requires it and the code lacks it: decay on disuse (`2605.26252v1.md:323`; MemState's docs, `docs/operations/forget.html`, describe decay but its code has none, F10, F24), per interaction (each ingest and each query counts as one), with an untouched topic at 1.0 falling below θ after 400 interactions (λ ≈ 0.9925, computed lazily), and a forgetting check after every interaction (MemState's runs only at the soft limit). Decay accrues during disuse: a read or write of a topic restarts the count but restores nothing, so a write gives no extra life and a retrieval keeps a topic alive only through its +0.1 bump (with exponential decay, restoring the stored value instead would let every returned topic recover a different amount, and reinforcement precision would no longer be 1/8).
- *C6.* +0.1 per returned topic, as MemState's `query_salience_bump`; as-of reads count as reads. Reinforcement precision therefore stays 1/8. C6 clause 2 seeds the target and the control at 0.06 on the reference GEM, a declared per-system test setting (upstream keeps 0.03 and 0.01), because a seed below θ would be archived by its own interaction.
- *Retrieval.* MiniLM, top 8.

**Declared simplifications.** One-hop flagging with no repair (repair belongs to the revision operator, which is not built); a restricted policy vocabulary (conditions over the whole state, the paper's open "policy language", `2605.26252v1.md:353`, are out); one archive threshold, with the compress and hide rungs of the forgetting ladder (`2605.26252v1.md:323`) out of scope; revision after every ingest, as MemState's Reasoner does; no LLM, so no chat and no extraction. The result is worded "passes the suite's checks, with declared simplifications". Pre-registered in the suite's spec and measured in the run of record (F34): phase 1 passes all 12 conformance rows and the time probes that need only a start date (T1, T2, T3, T6), and is absent on T4 (no end date) and T5 (no recorded time); phase 2 passes all of them. One departure from the spec's request shape: phase 1 accepts `valid_at` as well as `valid_from`, because without an as-of read the probes' control dates become plain reads and T1–T3 and T6 could not be answered at all; it still accepts neither `invalid_at` nor `recorded_at`, so T4 and T5 stay absent.

**Structure.** Three commits on MemState, so each effect is attributable to one change: (1) the port to LadybugDB (the import plus the dependency line; no behaviour change, so verdicts must be identical, while counts from the random-ID merge test may differ between runs); (2) bitemporal histories and C1′ queries (the time probes flip); (3) merging by valid time (the merge case flips). The conformance suite runs on each commit, so commit 1 → 2 isolates the effect of Zep's model on MemState with the engine held constant; commit 3 is measured on top of commit 2, so its effect is incremental. On the reference GEM, phase 1 → phase 2 isolates C1′ on a system that meets the conditions; the other rows did not move, at verdict or case level (F34). MemState's 39 upstream tests pass unedited at upstream and at every commit (a value whose date cannot be parsed keeps arrival order, as today), counted by the run of record (F30, F41). Commit 2 was amended once to resolve relative dates in chat writes (Section 9.7); the final commits `089b823` (step 1), `4272a07` (step 2) and `9bd471e` (step 3) are on the patched copy's `bitemporal` branch, exported as `patches/0001`–`0003`, and the run of record measured exactly these (F41). An earlier run of the same command, on the superseded `2cfabee` and `cb5d48c`, gave the same verdicts (F32). Upstream stays measured unmodified.

### 9.6 Probes of the proposed refinements (time probes and the C4′ probe)

| Probe | Scenario | Correct answer | Dates it needs | Upstream (F19, F41) | Reference phase 1 (F34) | Reference phase 2 and patch steps 2–3 (F41, F34) | Zep as written (code reading, [INFERENCE]) |
|---|---|---|---|---|---|---|---|
| T1 Retroactive fact | "The deadline *was* March 1 before the change" arrives last | April 20 stays current | `valid_from` | Absent: accepts no dates; the last write is current (March 1) | ✓ | ✓ | Data yes |
| T2 Out-of-order arrival | An older update is ingested after a newer one | Newer value | `valid_from` | Absent; the older value is current | ✓ | ✓ | Data yes |
| T3 Future-dated change | "From December you are on premium," asked Nov 20 | Old tier | `valid_from` | Absent; premium is current | ✓ | ✓ | No |
| T4 Lapsed scoped override | Budget $50 (Sep 1); "$80 for October only"; asked Nov 5 | $50 | `valid_from`, `invalid_at` | Absent; $80 is current | Absent (no end date) | ✓ | No |
| T5 As-of query | "What was true on Feb 10?" vs. "what did memory believe on Feb 10?" | Both answerable | `valid_from`, `valid_at`, `recorded_at` | Absent: both questions get the same answer | Absent (no recorded time) | ✓ | Partly |
| T6 Future value, nothing before | "From December you are on premium" is the field's only value, asked Nov 20 | No current value | `valid_from` | Absent; premium is current | ✓ | ✓ | No |

*Zep as written.* From reading Graphiti at `6e3e3cb`; nothing was run. "Data yes": the stored facts carry what the probe needs, and Graphiti orders a late-arriving older fact like the patch (T1, T2). "No": it dates a future-tense fact at the message time, so a future value is current early (T3, T6), and it marks an end-dated fact expired on arrival and would close the base value for good (T4). "Partly": it has both time axes, but a correction edits the old fact in place, so "believed on" is lost after one (T5). Zep hands the model facts with date ranges, so the answer is the model's.

The probes are ours, motivated by Zep's time model and by StateMemBench's status errors; they are not taken from either. Each probe is a short story told with calendar dates and asked on more than one date. One of the dates is a control that every system should get right, so a patch that rejects a legitimate update is caught (for example, the override asked on Oct 15 must return $80 in every column, and asked on Nov 5 must return $50). One extra story checks that a plain statement during an override ends it: "$100" stated on Oct 10 is current on Nov 5, the answer on Oct 15 is $100 (the one date where "the shorter validity wins" alone would answer $80), and the patch still answers $80 for Oct 5. The lapsed-override probe is modelled on StateMemBench's status-error mode ("a scoped override may lapse"); the future-dated probe is its mirror image (a change applied before it takes effect). The StateMemBench paper states that the benchmark is released but gives no download link, and no official data release could be found at the time of writing. Results assume correct dates: each system is given the story's true dates, a best case; extracting dates from text is LLM-dependent and is tested only by the chat example.

*How the stories are run.* Each story has its own topic on a fresh database per system, apart from the storyline, so a failure is attributable to the time logic. The question on the story's "today" is a plain read with no date, answered against the server clock, so the suite shifts each story so that its today falls on the day of the run; the other dates are as-of reads. The patch and the reference GEM receive the dates they accept through their APIs; a system that accepts none of the dates a probe needs receives the same writes in the same order and answers every asked date with the same plain read, since its current value depends only on insertion order (from code). The time when memory recorded a value is always the real clock, so in the as-of probe "what did memory believe on Feb 10" is asked at a real moment between the two writes.

*Scoring: two cells per probe.* **Accepts dates:** does the system accept the dates this probe needs, detected per probe and not all-or-nothing (T1, T2, T3, T6: `valid_from`; T4: `valid_from` and `invalid_at`; T5: `valid_from`, `valid_at` and `recorded_at`)? **Answers correctly given dates:** the probe passes when every asked date is right and, on the patch, the full history is kept (no value lost; where a stored end date changed or a value was retracted, the original is kept as an expired entry with a linked copy). A probe is **absent** when a needed date is not accepted, confirmed by the schema probe, and **fail** when the dates are accepted and an answer is wrong (labelled over-blocking when the control is the date that fails). T5 is absent when any of its three dates is missing: the versioned row accepts `recorded_at` alone and reads absent, with the answer it gives to "believed on" kept as an observation. Upstream is never called wrong: it cannot express these cases. The probes sit in their own scorecard section, "probes of the proposed C1′ and C4′, outside [P1]'s claims", so that absent is not read as a failure against the paper. A one-line **C4′ probe** joins them: does provenance resolve to a stored source message? Measured as pre-registered: pass on the reference GEM, which stores the source with each write; absent on upstream, every patch step and the versioned row (F32, F34).

*Chat and merge.* One chat example, on the patch only (upstream's chat request carries no date, from code [INFERENCE]), tests whether the chat model resolves "two weeks ago" against the message's reference time, as Zep's extraction does (the later series add a rule-based resolver, F38–F40): a message dated Oct 6 says "I started my new job two weeks ago", and a separate request dated Oct 20 asks how long the job has lasted (both dates are shifted so that the last falls on the run day). It is graded twice, n = 1: the stored start date (about Sep 22, not Oct 6) and the answer (four weeks, by hand). The result with the 2B model is negative (Section 9.7). The merge test keeps its 20 undated runs in every column and adds one dated case on the patch: the duplicate topic written later holds the value with the earlier date, and the merged topic must answer by date with both values in its history.

### 9.7 Results of record

One recorded command ran every check, time probe, storyline question and ramp on all seven systems, recorded both chat cases, and copied the results to the tracked [`demo/record/20261021-194912/`](../../demo/record/20261021-194912/scorecard.md) (2026-10-21, 57 min 7 s, ramps repeated three times; F41) on the final commits `089b823`, `4272a07` and `9bd471e`. Every MemState server ran alone on a fresh database, upstream on Kuzu 0.11.3 at `945d7c4` and the patch on LadybugDB 0.21.2 at the final commits; each verdict links its raw-state snapshot. Every verdict matched the expected verdicts written in the suite's spec before the build; the departures are in counts and case-level detail, listed at the end of this section. Earlier smoke runs (F7–F31) found the same behaviour; their finding numbers are kept below where they add detail.

**MemState, upstream to step 3 (F41).**
- **C1:** the control passes on all four.
- **C2(a), the merge:** in the arranged case the dropped topic holds the newer value; the merge made the superseded March 15 current in 20 of 20 repetitions on upstream, step 1 and step 2 (fail), and in 0 of 20 on step 3 (pass), because step 3 interleaves both histories by valid time (F29). The topic with the lower ID always survives (F9), so the natural count on random IDs is a draw: 11, 11, 11 and 0 of 20 on the four systems (11, 10, 9 and 0 in the earlier run on the superseded commits, F32), shown and not compared.
- **C2(b), atomic commit:** fail on all four. A `new_topic` ingest whose second field points to a missing `ref_topic_id` returns HTTP 400, yet the topic and its first field stay stored: a partial commit (F23). An edge to a missing topic is reported applied and stored nowhere (F17), a separate soundness observation.
- **C2(c), declarative policies:** absent on all four: the API exposes no policy surface (F17).
- **C2 on the lapsed override:** pass on all four. Upstream returns the last-written value, which in this story is never a value a later statement ended; its error on the override belongs to T4, where it reads absent.
- **C3:** absent on all four. B carries no flag and does not change within the 15 s polled wait in either edge direction, so the dependent-topic staleness window is unbounded (Section 5.3, F7, F17).
- **C4:** partial on all four, for different reasons. On upstream and step 1 history survives an update, while the merge drops the dropped topic's history, empty and `null` writes are accepted and become current, and the 501st write to one field drops the first (F21). Step 2 makes the dated merge case runnable, and it breaks. Step 3 fixes both merge cases; the empty, `null` and cap cases stay broken, since the patch does not touch them. The forgetting case is n/a on every MemState system: a field write resets a topic's salience to 1.0, so a topic with fields is never forgotten through `/v1` (F24).
- **C5:** the mechanism passes (a topic created at salience 0.01 is archived at the 500-topic gate, F22). The natural trajectory fails: 0 topics archived at any size, so 2,000 topics are active against the declared bound of 500, four times over (F10, F22).
- **C6:** clause 1 passes; every returned topic is bumped, including unrelated ones (3 of 3 unrelated topics rose as far as the target, F15). On steps 2 and 3 an as-of read also raises salience (0.500 → 0.600, F27). Clause 2 passes: the read topic survives the forgetting pass while the never-read control is archived. A field write then overwrites a reinforced salience with 1.0 (F15), a durability observation.
- **Time probes:** absent on all six on upstream and step 1 (no date is accepted; every control date answered right, F19); pass on all six on steps 2 and 3, with the full history kept (F26, F27). **C4′:** absent on all four.
- **Change tables:** step 1 changes nothing; step 2 flips T1–T6 from absent to pass; step 3 flips C2(a) from fail to pass, and C4's two merge cases from broken to fixed while the row stays partial. No row of the 18 measured at step 1 is worse at step 3, at verdict or case level, so the summary reads "no regressions on the rows the suite checks". MemState's 39 upstream tests pass unedited at upstream and at each step (F30).

**The reference GEM and the versioned row (F34).** These are results on our own systems: the reference GEM passes the suite's checks, with declared simplifications (Section 9.5); that shows the checks can be passed, not that GEM is implementable as the paper describes it. Both phases pass all 12 conformance rows: the merge leaves the superseded value current in 0 of 20; C3 flags in both edge directions within 0 interactions; C5's natural trajectory holds 396 active topics at 2,000 against β = 500. Phase 1 is absent on T4 and T5 and passes T1–T3, T6 and C4′; phase 2 passes all of them, and nothing else changes. The versioned row passes C1, C2(b), C2 on the lapsed override and C4 (3 cases n/a); C2(a) is not-scored because no merge ever occurs; C2(c), C3, both C5 rows and both C6 rows are absent, as are the six time probes and C4′.

**Measurements.**
- *Windows.* The merge revision window has a median of 0.005–0.007 s on the four MemState systems (F41); the dependent-topic window is unbounded there (C3 absent). On the reference GEM both windows are 0 interactions, because revision runs after every ingest and flagging happens in the write itself.
- *Over-flagging* (one chain A ← B ← C ← D on the reference GEM, beside C3; no verdict): one hop flags B and misses C; the transitive walk flags B and C and also D, which did not need it. Each choice costs a different error, which is Section 5.5's "how many hops" question, measured. No MemState system propagates, so none is measured.
- *Storyline:* 15 of 15 on all seven systems, with 0 search failures and 0 memory failures. Reinforcement precision is 0.125 = 1/8 on every system with salience, equal to Precision@8 because every returned topic is bumped (F20); n/a on the versioned row.
- *Latency* (F41; three repeats, medians with ranges in the scorecard). Ingest at 100 topics: 33.9 ms on Kuzu against 20.9 ms on LadybugDB, with non-overlapping ranges; at 2,000 topics, 63.1 against 55.4 ms. Query latency grows with topic count on both engines (a brute-force vector scan): 151.4 → 393.1 ms on Kuzu and 86.3 → 375.1 ms on step 1, from 100 to 2,000 topics. The three patch steps differ from each other by at most 0.9 ms at ingest at 100 topics and 2.4 ms at 2,000, and stay within the sample range for queries; at 2,000 topics an as-of read costs about what a plain read does (373.1 against 336.3 ms on step 2, 353.6 against 354.6 ms on step 3). The run on the superseded commits (F33) read about 12–23% faster at ingest with the same ordering, so the figures belong to the run. The suite labels every upstream-vs-step-1 query difference "no measurable difference", but the label rests on slow outliers widening the ranges (step 1 at 100 topics: 80–156 ms), not on matching medians (151.4 against 86.3 ms). The cause of the engine gap is not isolated beyond step 1 changing only the import and the dependency [INFERENCE]; n = 3 repeats on one laptop.
- *Limits, with their numbers:* the 500-entry history cap (501 writes leave 500 entries, the oldest gone; a correction uses two entries, F21); the forgetting gate at the 500-topic soft limit against 2,000 active topics with none archived (F10, F22).

**Answer-level contrast, through chat (n = 1 each; F25, F31, F41).** Both cases ran on Ollama `qwen3.5:2b` through the think-off proxy, with MemState's own router choosing each route and no intent override.
- *Bad merge on upstream.* The re-explained Website Redesign is merged over the original: the merge drops the original's Deadline history (March 15, and April 20 with its "vendor delay" provenance), so March 15 exists nowhere. Fields only the original held (Team, Status) are copied to the survivor with their histories, so the loss is confined to fields both topics hold. Asked through chat, the model still answers April 20, the full team, and Complete (every answer contains the ground-truth words in the take of record): the answer looks right while the stored state violates C4. An earlier session recorded three takes of this case; in two of them the model failed one of the questions (F25).
- *"Two weeks ago" on step 3.* Negative. In the take of record the router sent the statement to `query`, nothing was stored (so the resolver of commit 2 never ran), and the follow-up request said it did not know when the job started instead of answering four weeks. Across 7 earlier takes run as specified, the router chose `query` every time, one take stored the right start date (in the value text, while `valid_from` was the reference time), and no take answered four weeks (F31). The plumbing works (the reference time reaches the prompt, the default `valid_from` and the provenance, F28); a 2B model with MemState's router does not use it reliably.
- *A series of 10 takes per case on `qwen3.5:4b`, graded by Sonnet (F37).* The n = 1 run of record could not tell a model limit from a test that cannot pass, so both cases were repeated on the largest qwen3.5 that loads on the GPU. The bad merge looks right in 30 of 30 answers (Sonnet: correct) while every take's state has lost the deadline history. For "two weeks ago", 4b routed the statement to a write 10 of 10 times, so the router was a 2B limit; the spec's follow-up "how long have I been there?" had no referent in a request without history and read no memory in 6 of 6 pilot takes, so it was reworded to "How long have I been at my new job?" (13 of 13 then read memory). With both fixed, the case measures the date itself: the model stored the literal "two weeks ago" (with `valid_from` defaulting to the message date) in 4 takes, a wrong date in 2, nothing in 4, and the right date once; Sonnet graded that one take correct on both turns (1 of 10). C1′'s reference time reaches the model and the default `valid_from`, but turning a relative phrase into a date is left to the chat model, which fails 9 times in 10 here; Zep runs a dedicated date-extraction step for this [INFERENCE: from its paper, not run], and a deterministic resolver is the next step for the patch (next bullet). Hosted models were out of reach without payment: Groq's free tier caps every chat model at 8,000 tokens per minute, below one MemState chat request (8,515 tokens, mostly its system prompt and tool list).

- *A rule-based resolver, then reasoning on, then final rules (F38, F39, F40; "two weeks" only, 10 takes each, `qwen3.5:4b`, graded by Sonnet and, from F39, also by a reviewer subagent; hand grades not yet done).* With relative dates resolved by rule in chat writes (commit 2), every write stored the right start date, but only 6 of 10 takes wrote (the other 4 stored nothing) and the follow-up answer computed the duration wrong in 10 of 10, even when it quoted both dates (F38). The model not writing came from the demo's own setting: its reasoning had been turned off for speed (ADR 0003). With reasoning on, 10 of 10 takes wrote, but the first resolver left the date wrong in some (the model's own wrong date kept, the phrase left in the value beside a date, a second wrong date in the value), so the start date was right in 8 of 10 within a day (F39). The final rules (Section 9, *Reference time*), checked offline on 13 recorded model writes before any live take, were run on 10 fresh takes, not the ones they were tuned on (F40):

| `qwen3.5:4b`, two weeks | W1 wrote | W1 correct (Sonnet / reviewer) | W2 correct |
|---|---|---|---|
| reasoning off (F37) | 6/10 | 1/10 | 1/10 |
| reasoning off + resolver (F38) | 6/10 | 6/10 | 0/10 |
| reasoning on + first resolver (F39) | 10/10 | 6/10 + 2 partial | 3–4/10 |
| reasoning on + final resolver (F40) | 10/10 | 10/10 / 9/10 + 1 partial | 6/10 + 3 partial + 1 wrong (both graders) |

  `valid_from` is 2026-09-23 in 10 of 10 final takes. The three partial W2 answers give Sep 23 and 28 days or a month but also a wrong figure ("a week and a half", "just under three weeks"): arithmetic slips with nothing in the stored data behind them. The wrong W2 read a second date the model had written into its own value, so two dates and no rule applied. One take stored an employer the user never named (F40). Memory now stores the right start date whenever the model writes; what remains is the model's arithmetic and the dates it writes into free text. The two graders agreed on 19 of 20 (F40); turns took 16–37 s with reasoning on, against 2–5 s off (F39). One 4B model on one laptop; the pilot's 3 of 3 in F39 did not hold at 10 takes.

**Departures from the expected verdicts.** Every verdict cell matched. Four details did not, and each is reported here as measured, not rewritten in the spec:
- C4's not-applicable count is 2 on upstream and step 1, and 3 on the versioned row, against 1 and 2 expected: the dated merge case needs `valid_from`, which those systems do not accept.
- The natural merge counts are 11, 11 and 11 of 20 on upstream, step 1 and step 2, against the 10 of 20 the design quoted from F9 (the earlier run drew 11, 10 and 9): they are random draws, not rates.
- Two case-level changes at step 2 were not predicted: C4's dated merge case goes n/a → broken, and C6 clause 1's as-of case goes n/a → held, because both become runnable once the system accepts dates. The row verdicts do not move.
- The scored "two weeks" take stored no start date, whereas the take recorded as F31's take of record had stored one; the run takes the newest take run as specified, and the typical take stores nothing (both recorded runs, F41).

### 9.8 Scorecard

The full scorecard, with a raw-state snapshot behind every cell, is [`demo/record/20261021-194912/scorecard.md`](../../demo/record/20261021-194912/scorecard.md) (F41). The verdicts:

| Row | Claimed by [P1]? | Upstream | Step 1 | Step 2 | Step 3 | Ref. phase 1 | Ref. phase 2 | Versioned row |
|---|---|---|---|---|---|---|---|---|
| C1 (control) | yes (§4.3) | pass | pass | pass | pass | pass | pass | pass |
| C2(a) merge (existence) | yes (§4.3) | fail | fail | fail | pass | pass | pass | not-scored |
| C2(b) atomic commit | yes (§4.3) | fail | fail | fail | fail | pass | pass | pass |
| C2(c) declarative policies | yes (§4.3) | absent | absent | absent | absent | pass | pass | absent |
| C2 lapsed override | yes (§4.3) | pass | pass | pass | pass | pass | pass | pass |
| C3 | §4 opening; not in §4.3 | absent | absent | absent | absent | pass | pass | absent |
| C4 | yes (§4.3) | partial (2 n/a) | partial (2 n/a) | partial (1 n/a) | partial (1 n/a) | pass | pass | pass (3 n/a) |
| C5 mechanism | yes (§4.3) | pass | pass | pass | pass | pass | pass | absent |
| C5 natural trajectory | yes (§4.3) | fail | fail | fail | fail | pass | pass | absent |
| C6 clause 1 | yes (§4.3) | pass (1 n/a) | pass (1 n/a) | pass | pass | pass | pass | absent |
| C6 clause 2 | yes (§4.3) | pass | pass | pass | pass | pass | pass | absent |

The probes of the proposed C1′ and C4′, outside [P1]'s claims:

| Probe | Upstream | Step 1 | Step 2 | Step 3 | Ref. phase 1 | Ref. phase 2 | Versioned row |
|---|---|---|---|---|---|---|---|
| T1, T2, T3, T6 | absent | absent | pass | pass | pass | pass | absent |
| T4 lapsed override | absent | absent | pass | pass | absent | pass | absent |
| T5 as-of query | absent | absent | pass | pass | absent | pass | absent |
| C4′ provenance | absent | absent | absent | absent | pass | pass | absent |

C5's natural-trajectory cells state the declared bound beside the active count in the full scorecard: 2,000 active against 500 on MemState, 396 against β = 500 on the reference GEM. Fail and absent on MemState mark gaps its README states ("Proof-of-Concept, NOT Full Implementation"), not defects.

---

## 10. References

**Project papers**
- [P1] A. Orogat, E. Mansour. *Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory.* arXiv:2605.26252, 2026. Code: https://github.com/CoDS-GCS/MemState
- [P2] D. Jiang et al. *Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitations.* arXiv:2602.19320, 2026.
- [P3] C. Yang et al. *Graph-based Agent Memory: Taxonomy, Techniques, and Applications.* arXiv:2602.05665, 2026.
- [P4] P. Rasmussen et al. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* arXiv:2501.13956, 2025.
- [P5] C. Latimer et al. *Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects.* arXiv:2512.12818, 2025.
- [P6] A. Orogat, A. Rostam, E. Mansour. *Architectural Design, Not Only Model Intelligence, Governs Multi-Agent LLM Performance* (MAFBench). arXiv:2602.03128, 2026. Accepted to SIGMOD 2027.

**Benchmarks and evaluation**
- D. Wu et al. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025. https://github.com/xiaowu0162/LongMemEval
- D. Wu et al. *LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues.* arXiv:2605.12493, 2026.
- Y. Hu, Y. Wang, J. McAuley. *Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions (MemoryAgentBench).* ICLR 2026, arXiv:2507.05257.
- D. Chen et al. *HaluMem: Evaluating Hallucinations in Memory Systems of Agents.* arXiv:2511.03506, 2025.
- A. Maharana et al. *Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo).* ACL 2024, arXiv:2402.17753.
- X. Fan, M. Liu, R. Yang, S. Ouyang, J. Han. *Can Agent Memory Systems Track Evolving State? (StateMemBench, StateMem).* arXiv:2608.19652, 2026.
- Chao et al. *STALE: Can LLM Agents Know When Their Memories Are No Longer Valid? (CUPMem).* arXiv:2605.06527, 2026.
- M. S. Arya. *RECON: Benchmarking Agent Memory for Compositional Reasoning over Long Contexts.* arXiv:2607.16716, 2026.
- T. Ding et al. *Always-On Agents: A Survey of Persistent Memory, State, and Governance in LLM Agents (AOEP-v0).* arXiv:2606.30306, 2026.
- X. Li et al. *MemTX: Transactional Belief Commit for Stateful Agent Memory.* arXiv:2607.23929 (v2), 2026.
- H. Cui et al. *MemTxn: A Transaction Boundary for Source-Supported Updates and Complete-State Recovery in Agent Memory.* arXiv:2607.27834, 2026.
- Y. B. Park. *Graph-Native Cognitive Memory for AI Agents: Formal Belief Revision Semantics for Versioned Memory Architectures* (Kumiho). arXiv:2603.17244, 2026.
- W. Zhou et al. *Are We Ready For an Agent-Native Memory System?* arXiv:2606.24775, 2026.
- Z. Guo et al. *LightRAG: Simple and Fast Retrieval-Augmented Generation.* arXiv:2410.05779, 2024.
- Z. Wang. *TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory.* arXiv:2606.06240, 2026.
- S. Zhou, J. Han. *A Simple Yet Strong Baseline for Long-Term Conversational Memory of LLM Agents (EMem).* arXiv:2511.17208, 2025.
- X. Li et al. *Toward Multi-Session Personalized Conversation: A Large-Scale Dataset and Hierarchical Tree Framework for Implicit Reasoning (ImplexConv).* EMNLP 2025, arXiv:2503.07018.
- K. Lin et al. *Sleep-time Compute: Beyond Inference Scaling at Test-time.* arXiv:2504.13171, 2025.
- Agent Memory Benchmark (AMB). https://agentmemorybenchmark.ai/ · https://github.com/vectorize-io/agent-memory-benchmark · Manifesto: https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark . PrecisionMemBench and SDEBench are datasets in AMB's catalog.

**Systems and documentation**
- Hindsight: conflict resolution — https://hindsight.vectorize.io/blog/2026/02/09/resolving-memory-conflicts ; staleness-aware memory — https://hindsight.vectorize.io/blog/2026/06/17/freshness-aware-memory ; mental models — https://hindsight.vectorize.io/blog/2026/06/05/mental-models-deep-dive ; knowledge pages (v0.9.0) — https://hindsight.vectorize.io/blog/2026/08/07/version-0-9-0 ; docs (v1.0): observations — https://hindsight.vectorize.io/developer/observations ; mental models — https://hindsight.vectorize.io/developer/api/mental-models ; knowledge pages — https://hindsight.vectorize.io/developer/api/knowledge-pages ; memory curation — https://hindsight.vectorize.io/developer/api/memories
- Supermemory LongMemEval report: https://supermemory.ai/research/longmembench ; "~99% SOTA" post, later labelled a parody and taken down (archived): https://web.archive.org/web/2026/https://supermemory.ai/blog/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/
- Graphiti (Zep's open-source engine): https://github.com/getzep/graphiti
- Mem0 latency and token figures (vendor-reported): https://mem0.ai/guide/benchmarking-cost-difference-full-llm-context-compressed-memory ; P. Chhikara et al. *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory.* arXiv:2504.19413, 2025.
- Backboard LoCoMo results: cited as reported in [P5] ("as claimed on the official Backboard LoCoMo benchmark results"); no independent source checked.
- Kuzu archival and forks: https://www.puppygraph.com/blog/what-is-kuzudb ; https://github.com/vela-engineering/kuzu
- GPT-4o context window (128k; 16,384 output tokens): OpenAI model documentation, https://platform.openai.com/docs/models/gpt-4o
- Kuzu successors and alternative engines: LadybugDB — https://github.com/LadybugDB/ladybug ; RyuGraph — https://github.com/predictable-labs/ryugraph ; SurrealDB — https://surrealdb.com/features ; XTDB — https://docs.xtdb.com/intro/what-is-xtdb ; LadybugDB concurrency — https://docs.ladybugdb.com/concurrency ; CozoDB — https://hexdocs.pm/cozodb/cozodb.html ; Minigraf — https://docs.rs/crate/minigraf
