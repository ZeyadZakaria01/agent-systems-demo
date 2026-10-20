# Report fixes (group 1): `docs/report/gem-limitations-and-directions.md`

| audit item | report section | before (short) | after (short) |
|---|---|---|---|
| 18 | §1 item 3 | "(run-verified, Section 5.3)" | "(in a sandbox run, to be reproduced by the conformance suite; Section 5.3)" |
| 20, 22 | §1 item 4 | "never says who creates the extension edges"; StateMem "a direct answer" | "never says how … are created in general; its one example (Fig. 3b) is an edge to a split-out topic"; "one concrete answer …, though its benchmark states every dependency explicitly" |
| 9, 18, 30 | §1 item 6 | "prototype pins its final release"; "runs unchanged on LadybugDB, Kuzu's maintained successor, with a one-line change: all 39 pass" | "requires `kuzu>=0.11.0`, which now resolves to 0.11.3 (pinned in our environment)"; "In a sandbox run, to be reproduced …, ran on LadybugDB, a maintained community fork, after a one-line import change plus the dependency swap" |
| 19 | §1 item 7 | AOEP-v0 as a benchmark; "C5 and C6 remain unmeasured"; "no benchmark ties correctness to write cost, latency" | AOEP-v0 "a pilot evaluation contract"; [P1] already cites MemoryAgentBench, HaluMem/STALE predate [P1]; "No benchmark measures C5 and C6 together; C6 appears entirely unmeasured"; "write-to-visible latency or staleness; write cost at most reported beside accuracy (HaluMem, [P2])" |
| 7 | §1 item 9 | "MemTX evaluates MemState directly" | "evaluates a reimplementation of MemState, cross-checked against the official code" |
| intro minor | §1 item 10 | "below 5 in every evaluated framework" | "below 5.0 (out of 100) in every memory architecture it evaluates" |
| 3 | §1 item 11 | "shown to fix … without regressions (Section 9)" | "designed to fix … without regressions (results pending, Section 9.8)" |
| intro minor | §2 [P5] row | "RL-free update policy" | "rule- and LLM-driven (non-RL) updates" |
| intro minor | §3 C1, C6 rows | dropped clauses | added "prior values only when the query asks for history"; "repeated retrieval strictly reduces eligibility for attenuation" |
| intro minor | §4.2 knowledge vs experience | [P3] "correctness and consistency above all"; Hindsight "separates the two explicitly" | [P3] stable/verifiable/relational vs dynamic/temporal; Hindsight world vs first-person experience "only loosely matches" |
| intro minor | §4.2 graph-based | "retrieved via spreading activation" | "graph retrieval, one of four parallel channels, uses spreading activation" |
| 23 | §5.2 | "LLM-heavy repair work (… attenuation)" | "[P1] does not say which of these steps call an LLM" |
| 23 | §5.2 | [P2] excludes maintenance "*because* it runs asynchronously" | "because it is 'often handled asynchronously'" |
| 21 | §5.3 What the paper specifies | "a read of B … does not block and returns B's old value" (as fact) | "nothing in retrieval, as described, blocks on or checks the flag: a read … would return …; [P1] does not discuss reads in this window; this is our reading" |
| 18 | §5.3 heading | "(run-verified)" | "(in a sandbox run, to be reproduced by the conformance suite)" |
| 21, 25 | §5.3 table | Hindsight cells unattributed; MemState paper cell; StateMem "None in storage: recomputed on every read" | "(Hindsight blog, June 2026)"; "bank-level backlog grade (not a per-dependent flag)"; "(implied)"; "None described in storage: recomputed at answer time" |
| 21 | §5.3 closing | StateMem "never corrected in storage"; "enforced by the engine rather than by a prompt" | "does not write the recomputed value back to storage"; "rather than left to an agent prompt" |
| 22 | §5.4 StateMem's answer | "maps directly … answers the open question" | "gives one concrete answer …, although StateMemBench states every dependency explicitly, so inferring unstated links is untested" |
| 11 | §5.4 EMem | "helps multi-hop slightly, adds little on knowledge-update" | backbone-dependent: MH +4.5 (gpt-4o-mini) / +0.6 (gpt-4.1-mini); KU +6.9 (94.4 vs 87.5) / −1.0; graph is retrieval-time PPR, not inferred links |
| 23 | §5.5 | "Observation 3b establishes" | "claims" |
| 23 | §5.5 precision | no hedge | "the authors read these margins as an upper bound" |
| 15 | §5.5 Zep | "only that edge"; "Graphiti has supported Kuzu" | "only the contradicted edges"; "still ships a Kuzu backend, now marked deprecated" |
| 23 | §5.6 | "[P2] shows LLM judgments are sensitive to prompt and backbone" | judge scores shift with prompt strictness (rankings stable); operations fail more on weaker backbones |
| limits-b minor | §5.7 | "re-extracted"; "Queries can then filter …" | "extracted (and so could be re-extracted)"; "Retrieved facts carry `t_valid`/`t_invalid` …" |
| 25 | §5.7 Hindsight | "per its paper and consolidation documentation, does not invalidate raw facts" | "never invalidates raw facts automatically (per its consolidation docs; users can invalidate manually through curation)" |
| limits-b minor | §5.8 | Widom & Ceri cited for termination | "cites … for ECA propagation; their work also studies …" |
| limits-b 245 | §5.10 | "implies the original engine handled concurrent writers poorly" | "Kuzu enforces a single writer (one write transaction at a time)" |
| 13 | §5.10 table | "one writer plus many read-only readers" | one write transaction plus concurrent reads within one read-write object; read-only processes cannot coexist with a writer |
| limits-b 253 | §5.10 table XTDB | "server rather than embedded" | "embeddable only in JVM processes (from Python a separate server)" |
| 18 | §5.10 LadybugDB tested | stated as results; `real_ladybug` "conflicts" | labelled "In a sandbox run, to be reproduced by the conformance suite"; "`real_ladybug` (0.15.x, module `real_ladybug`) is an older, separate distribution" |
| 15 | §5.10 Zep vs Graphiti | "README listed … Kuzu 0.11.2" | "lists … (the Kuzu backend is now marked deprecated)" |
| 25 | §5.11 Hindsight row | mental models, tag-scoped refresh, tiers as [P5] | attributed to Hindsight docs; forgetting future work "for the opinion/belief layer" |
| limits-b 269 | §5.11 | "both products have since added versioning and expiry" | Mem0 added history/expiration; Zep's bitemporal invalidation already in its 2025 paper |
| 7 | §5.11 Who cites [P1] | MemTX "runs the official implementation as a baseline" | "reimplements MemState as a baseline, cross-checked against the official implementation" |
| 21 | §5.11 StateMem table | "never repaired in storage; recomputed on every read" | "recomputed at read time; the paper describes no write-back" |
| limits-b 290 | §5.11 TOKI | "proves keyed logging … necessary" | "within its relational schedule model" |
| eval 305 | §6.1 Agency Tax | "latency and construction cost are rarely reported" | "[P2] measures per-turn latency and construction cost, but excludes maintenance cost" |
| 24 | §6.2 intro | [P1] "no benchmark provides ground truth for C2, C3, C5"; "roughly accurate" | "no existing benchmark provides … all three levels … That remains true, but … covers parts of it" |
| 12 | §6.2 HaluMem | "correct updates below 50%" | "update omission rates above 50%" |
| 12 | §6.2 MemoryAgentBench | "GPT-4o-based agents ~60% SH, ≤7% MH" | GPT-4o long-context agent 60 / 5; GPT-5-mini 28%; others ≤7% |
| eval 319 | §6.2 AOEP-v0 | "rather than answer quality" | "… alone" |
| 19, 24 | §6.2 Corrected claim | "Corrected claim"; "No benchmark jointly measures C5 or C6 … write cost, latency" | "Current picture"; "C5 and C6 together"; "write-to-visible latency or staleness (write cost at most beside accuracy)" |
| eval 332 | §6.2 Park | "the AGM postulates" | "basic AGM postulates (K*2–K*6) and Hansson's Relevance and Core-Retainment" |
| 7 | §6.2 MemTX paragraph | "evaluates MemState directly"; "second lowest on hardened suite" | reimplementation, official code as a check, scores are the reimplementation's; "second lowest, ahead only of TOKI, on three of five backbones" |
| 6, 7 | §6.2 Evidence for C3 | "only the two methods with cascading repair reach 1.0" | "… and only on four of the five backbones (0.959 and 0.963 on the weakest, Qwen2.5-14B)"; score is of the reimplementation; prototype finding "from reading the code and a sandbox run" |
| 24 | §6.4 Versions | 78 KU unsourced | "(StateMemBench, Table 11)" |
| eval 367 | §6.4 Context windows | "both 2024-08-06 and 2024-11-20" | default 2024-08-06; 11-20 listed without separate limits |
| 24 | §6.4 Limitations | 78-updates sentence under "[P1] adds"; "final state only" | separate sourced sentence: "each LongMemEval history carries a single question, asked at its end; 78 of 500 are KU (StateMemBench, Table 11)" |
| 23 | §6.5 NIAH | "are single-turn, never write, therefore conflate" | "many long-context suites … remain single-turn … potentially conflating" |
| eval 388 | §6.6 table | "No" | "No (only wrapper token overhead)" |
| 12 | §6.7 AMB | "LoCoMo, LongMemEval, LifeBench, MemBench, MemSim, PersonaMem, BEAM, and others" | "LoCoMo, LongMemEval-S, LifeBench, PersonaMem, BEAM, PrecisionMemBench, SDEBench" |
| eval 396 | §6.7 item 1 | "25k+ per Mem0" | "~26k per Mem0" |
| eval 401 | §6.7 item 6 | "Hindsight's results are designated as the reference point" | removed (unverifiable) |
| eval 402 | §6.7 item 7 | "one BEAM run logs 0 s" | "21,788 s at 500k vs. 348 s at 1m" |
| 31 | §6.7 items 8–9 | PrecisionMemBench, Backboard unsourced | "(in AMB's catalog …)"; Backboard "as [P5] states"; Supermemory judge GPT-4o |
| 30 | §6.7 item 10 | Supermemory as saturation evidence | "later labelled 'a big social experiment… a parody' and taken down; not evidence of saturation" |
| 12 | §6.8 Mem0 row | "under 7k vs. 25k+ tokens" | "~1.8k retrieved tokens per query vs. ~26k (store ≈7k per conversation)" |
| eval 415 | §6.8 LightRAG | "Commonly cited … (to be verified)" | "Under 100 tokens and 1 API call vs. 610×1,000 (Table 2, legal dataset)" |
| eval 417 | §6.8 LME-V2 | "140–186 s vs under 30 s for RAG" | Medium tier; 108–177 s on Small; 25.8 s retrieval agent |
| eval 445 | §6.9 | reasoning trace "does not reduce them"; MAFBench formatting | separate 50-item A/B, 84% → 76%, not significant; "for weaker models" |
| 16 | §7.1 intro | "[P4] closes with several future directions" | "names several, mostly in its conclusion (§5), and describes two capabilities it leaves unevaluated or already offers (§2.1, §3.1)" |
| ideas-a 457 | §7.1 LightRAG row | "map directly" | "map loosely … (high-level keys attach to relations)" |
| 16 | §7.1 rows 6–7 | bidirectional provenance "deferred"; BFS as a future direction | "indices implemented in Graphiti; their evaluation deferred ([P4] §2.1)"; "an existing Graphiti capability ([P4] §3.1)" |
| 25 | §7.2 | "per its engineering documentation" | "per its engineering blog on conflict resolution, Feb 2026, and its observations documentation"; batching note |
| 17 | §7.2 deletion bullet | "resets consolidation of the affected observations" | "deletes the observations derived from them and resets the consolidation state of their remaining source memories" |
| ideas-a 478 | §7.2 Proposal | "works at production scale" | "runs the classification step in production" |
| 25 | §7.3 tiers | tiers stated as Hindsight (implicitly [P5]) | "In its current product documentation (v1.0), rather than its paper [P5], …" |
| ideas-a 487 | §7.3 item 4 | "addresses [P1]'s concern about salience leaking" | "an analogous mitigation, for a related side channel (refresh signals; Hindsight has no salience)" |
| ideas-a 488 | §7.3 item 5 | "provenance of the last refresh" | "accumulated facts and observations each version was built on" |
| 25 | §7.3 table raw facts | "per its paper and consolidation docs" | "automatically (per its consolidation docs …; the paper's observation prompt likewise …)" |
| ideas-a 499 | §7.3 concept-level views | "no summarization call and no staleness window" | "no summarization call on the read path (routing summary can lag)" |
| 30 | §7.3 sleep-time | 5× unscoped | "on two stateful reasoning benchmarks, Stateful GSM-Symbolic and Stateful AIME" |
| ideas-a 514 | §7.4 table | RL "Can learn to violate correctness" | "Could …; hypothetical, not shown" |
| ideas-a 516 | §7.4 | reranking "hand-set" | "reranking an off-the-shelf MS MARCO cross-encoder" |
| 18, 21 | §7.5 C3′ motivation | "(Section 5.3, run-verified)"; Hindsight "only through a prompt" | sandbox label; "computes staleness structurally … but leaves verification to the reflect agent's prompt" |
| 26 | §7.5 Notes | non-destructive failure "already implied by C2 and C4" | "expressible under C2 … but not implied by C2 or C4 as stated; C4 covers only forgetting and revision" |
| 14 | §7.6 | "(first target)"; salience isolation and erasure under "Added by this review" | "one of the paper's three first targets"; both moved to [P1] list; review list keeps "rebuildability of derived units (Section 7.5)" |
| 15 | §7.6 Graphiti | "older versions also Kuzu"; tenant isolation "Covered"; "graph only grows"; baseline | "Kuzu still shipped but deprecated"; "Partly covered … no access control … no salience"; "only through explicit deletion (`remove_episode`)"; "while Graphiti's deprecated Kuzu driver lasts" |
| ideas-b 602, 606 | §7.7 | "avoids judge sensitivity"; three-level ground truth unattributed | "reduces judge sensitivity …"; "as specified by [P1], Section 5" |
| 27 | §7.8 item 3 | promotion trigger = "own lifecycle" | "(MemState's own modelling guidance). [P1]'s remedy is promotion once enough knowledge accumulates" |
| ideas-b 622 | §7.8 LightRAG | high-level keys "match broader themes"; "essentially" | "match relations whose index keys carry broader themes"; "resembles" |
| 10 | §7.8 hierarchical | entity level authoritative, "wins conflicts"; "promotes the middle tier" | episodes are the non-lossy ground truth …; "makes a community-like unit the source of truth" |
| 8 | §8 | "retrieval-only LangGraph reaches 20.2" (single-hop) | "best SF average, 20.2, with single-hop FC-SH 36.0 and multi-hop 4.5; Table 10" |
| 28 | §8 | "is a C3 failure" | "is consistent with a C3 failure, though answer-level scores cannot confirm it" |
| 3, 30 | §9 one-liner | "Kuzu's maintained successor, then fixes …" | "LadybugDB, a maintained community fork of Kuzu, is designed to fix … (results pending, Section 9.8)" |
| 9 | §9.2 Systems | "`kuzu==0.11.3` (as published)" | "`kuzu` 0.11.3 (final release; published `pyproject.toml` requires `kuzu>=0.11.0`)" |
| 30 | §9.2 two write paths | "StateMemBench's perfect-retrieval setting" | "perfect-retrieval (LongMemEval-oracle) analysis in the StateMemBench paper" |
| 26 | §9.4 C4 row | empty/`null` write as part of C4 | "(implied by C2/C4, not part of C4's definition)" |
| 18 | §9.6 header | "Upstream (recency) / Bitemporal" | "… ; expected" / "Bitemporal (expected)" |
| 29 | §9.6 note | both probes "modelled on status-error"; "not publicly available" | lapsed-override modelled on it, future-dated its mirror image; paper says released but gives no link, none found |
| 18 | §9.7 C6 | "including unrelated topics" | "not only the best match's" |
| 31 | §10 | missing LoCoMo, Park author, metadata, sources | added LoCoMo (ACL 2024, 2402.17753); Y. B. Park (Kumiho); SIGMOD 2027 for [P6]; ICLR 2026 MemoryAgentBench; 2025 HaluMem; authors for LME-V2, RECON, MemTxn, EMem; GPT-4o URL; PrecisionMemBench/SDEBench via AMB; Backboard via [P5]; Mem0 paper (2504.19413); Supermemory archived post; Hindsight docs URLs; LadybugDB concurrency docs |

## Not applied

- **A1** (C3 framing): line 7 scope note, §5 Framing C3 sentence, §5.3 "consistent with §4.3 … C3 is *absent*" sentence, §9.4 C3 row. Excluded by user decision; byte-identical (only the §5.3 heading's "run-verified" was relabelled).
- **A2** (supersession rule): §9.5 "Ordinary update" bullet and §9.6 out-of-order row, including demo-refs' optional "t′_expired per Zep's definition" note. Excluded.
- **A4** (practitioner note, "same rule"): §7.3 item 2 and §7.5 practitioner blockquote. Excluded.
- **A5** (StateMem ablation sentence in C3′ motivation). Excluded; other parts of that line were fixed.
- **Item 18, other §9.7 bullets** (C3, C5, merge, engines) and the §5.3 table's prototype column: kept, since §9.7 is already headed "Preliminary results (sandbox runs)" and says the harness will confirm them; only the C6 sub-claim the audit marked unsupported was changed.
- **Optional rows not applied:** §1 item 3 "retrieval never consults the flag" (verdict ok); §5.2 "prompt grows with topics" (reasonable inference); §5.3 "only with the structural stage"; §5.10 RyuGraph last-push date; §6.2 naming Jung et al. as MEME; §6.3 baseline predictions; §6.8 practitioner write-to-visible observation (personal observation, not a source claim); "cited via [Pn]" notes for other benchmarks reached through [P1]–[P5].
- No audit row was found wrong on re-check (spot-checked MemTX Tables 12/hardened suite and :170, MAFBench Table 10).
