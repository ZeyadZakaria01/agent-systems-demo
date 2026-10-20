# Source audit of report v2

Audit of `docs/report/gem-limitations-and-directions.md` as installed on 2026-10-19 (identical to `~/Downloads/README (2).md`; line numbers refer to it) against `docs/papers/`, primary web sources, and MemState source read-only. Nothing was run. Full claim-by-claim tables, with quotes and `file:line` or URL per row, are in [report-v2-audit/](report-v2-audit/): `intro` (lines 1–128), `limits-a` (129–209), `limits-b` (210–293), `eval` + `eval-web` (294–448), `ideas-a` (449–558), `ideas-b` (559–653), `demo-refs` (654–764 and §10).

Below: every non-`ok` item, most serious first. `P1` = `docs/papers/2605.26252v1.md`.

## A. Changes the demo's framing

1. **The paper does claim C3.** P1:240: "The data model supplies C1, C3, and C4 by construction and lifts C2 to a data-model guarantee." §4.2 describes flagging and extension-edge repair as realized (P1:279, :321); §4.3 (P1:331) defers only the *native* placement of propagation semantics. Affected: scope note (line 7), §5 Framing "it does not claim C3" (131), §5.3 "C3 is *absent* in the prototype, not a contradicted claim" (164), §9.4 C3 row "Not claimed … *Absent* is consistent with the paper" (683). An absent C3 contradicts §4's opening claim; only §4.3's validation sentence omits C3. [verified by hand: P1:240, :329, :331]
2. **Out-of-order rule is inconsistent and not Zep's.** §9.5 (693) closes the previous entry with the new `t_valid`, which breaks the out-of-order probe that §9.6 (705) marks "ordered by valid time ✓". Zep resolves conflicts by recency of ingestion ("Graphiti consistently prioritizes new information", `2501.13956.md:91`), so ordering by valid time is the report's own rule, not "Zep's rule made deterministic".
3. **Results stated before runs.** Summary item 11 (38) and §9 one-liner (656) say the patch "fixes" the time cases "without regressions"; §9.8 says results are pending.
4. **Practitioner note, "same rule as MemState's abort-on-postcondition-violation"** (485, 554): Algorithm 1 aborts the whole transition when a policy fails (P1:314: "commit if all postconditions hold, else abort"); a parse failure is input validation before any proposed state exists; the code has no postcondition check (`2605.26252v1-alignment.md:86, :104`). §7.5 itself (552) calls GEM all-or-nothing vs per-field. Ticket 22's wording was the accurate one.
5. **StateMem ablation misread** (545): 0.233 → 0.208 removes the *recompute guidance prompt*, not per-unit visibility. Removing the flagging (rechecker) gives 0.222 on Qwen and a *better* DeepSeek score (0.373 vs 0.363); the authors call these margins an upper bound.

## B. Wrong facts

6. **MemTX qualifier** (337): restore "only on four of the five backbones (0.959 and 0.963 on the weakest, Qwen2.5-14B)" (`2607.23929v2.md:470, :492-493`).
7. **MemTX ran a reimplementation** (36, 335, 337): MemTX scores its own faithful reimplementation of MemState; the official code runs only as a check, with no separate numbers (`2607.23929v2.md:170`). "Second lowest on the hardened suite" holds on three of five backbones only (:225-229).
8. **MAFBench single-hop** (641): the prose says single-hop reaches 20.2 (`2602.03128v2.md:397`), but Table 10 gives retrieval-only LangGraph FC-SH 36.0, FC-MH 4.5, SF average 20.2 (:372). The paper's prose mislabels the average. Cite the table. Multi-hop < 5.0 everywhere holds. Ticket 21 and the 2026-10-11 journal entry repeat "single-hop reaches 20.2".
9. **"The prototype pins Kuzu's final release"** (33, 664): upstream requires `kuzu>=0.11.0` (`MemState/pyproject.toml:13`); the `==0.11.3` pin is this repo's (ADR 0004). Item 6 also says "runs unchanged … with a one-line change" (contradiction; the dependency swap is a second change).
10. **Zep authority** (623): in Zep, episodes are the non-lossy ground truth (`2501.13956.md:53`); entities do not "win conflicts" (recency does, :91). "MemState promotes the middle tier" contradicts the same paragraph's analogy to communities, the top tier (:55).
11. **EMem** (192): with the graph, knowledge-update rises 6.9 points on gpt-4o-mini (94.4 vs 87.5) and drops 1.0 on gpt-4.1-mini; multi-hop +4.5 / +0.6 (arXiv 2511.17208, Tables 2, 3, 6). "Adds little on knowledge-update" is contradicted; the effect is backbone-dependent. EMem's graph is retrieval-time PageRank, not inferred links.
12. **Benchmark numbers** (313, 314, 394, 414): HaluMem says update *omission* above 50% for most systems, not "correct updates below 50%"; MemoryAgentBench: only the long-context agent uses GPT-4o (60.0 SH, 5.0 MH), GPT-5-mini reaches 28.0 MH; AMB's catalog has no MemBench/MemSim; Mem0's "under 7k" is the store per conversation, per-query context is ~1.8k vs ~26k (see `eval.md`, `eval-web.md`).
13. **LadybugDB concurrency** (251): "one writer plus many read-only readers" holds only per transaction inside one read-write database object; read-only processes cannot coexist with a writer.
14. **Native-engine list** (576, 577): per-tenant salience isolation and erasure of derived salience/provenance are [P1]'s own items (P1:361, :365), not "added by this review".
15. **Graphiti/Kuzu** (581, 202, 259): Graphiti still ships a Kuzu driver, marked deprecated; "graph only grows" ignores `remove_episode` (591); `group_id` partitions but does not access-control (587).
16. **Zep future directions** (462, 463): BFS from recent episodes is already in Zep (`2501.13956.md:134`); bidirectional indices are built, only their evaluation is deferred (:65).
17. **Hindsight deletion** (474): deleting sources deletes derived observations and resets consolidation of remaining sources.

## C. Needs a run in this repo (evidence rule)

18. §5.3 "run-verified" C3 staleness (30, 164, 545); §5.10 LadybugDB: 39 tests, identical verdicts, 321 vs 392 ms, DB files not interchangeable (33, 257); §9.7 all bullets except the part of C6 that F2 covers. F2 covers "every returned candidate", not "unrelated topics" (717), which may be a hash-embedding artifact. `real_ladybug` "conflicts" (257): both exist on PyPI with different module names; no conflict found by reading. → ticket "Reproduce the C3 staleness run and the LadybugDB port".

## D. Overstated, understated, misattributed

19. Summary item 7 (34): HaluMem and [P2] Table 5 do report write time/cost; AOEP-v0 is "a pilot evaluation contract", not a benchmark; [P1] already cites MemoryAgentBench as C1-only (P1:351); HaluMem and STALE predate [P1].
20. Summary item 4 (31): Figure 3(b) shows an extension edge to a split-out topic; say "never says how extension edges are created in general".
21. §5.3 line 162 states an inference as paper fact ([P1] is silent on reads in the window); line 176/282 "never corrected in storage" goes beyond StateMem's text; Hindsight's staleness signal is a bank-level backlog grade from a 2026-06-17 blog post, not the paper, and enforcement is partly in code (170–171, 545).
22. §5.4 (190): StateMemBench states every dependency explicitly (`2608.19652v1.md:194`); inferring unstated links is untested, so StateMem does not yet "answer" who creates them.
23. §5.2 (143) "LLM-heavy" revision/forgetting unsupported (P1:309, :323); §5.6 (206) [P2] does not show judge sensitivity to prompt (`2602.19320.md:208`); §5.5 (196) "establishes" vs "claims, not theorems" (135); dropped hedges at 147, 200, 290, 375.
24. §6 (309, 369): [P1] says no benchmark provides *all three* ground-truth levels (P1:351); the 78-updates figure is StateMemBench's (`2608.19652v1.md:1129`), not [P1]'s.
25. §7.3 (482–492, 265): the four Hindsight tiers, delta refresh, never-overwrite-with-empty and tag-scoped refresh come from Hindsight docs/blogs, not [P5]; cite them. "Raw facts always preserved" is the docs', and manual invalidation exists (216).
26. §7.5 (552): C2 and C4 do not *imply* non-destructive failure; §9.4 C4 row (684) should label the empty/`null` probe "implied by C2/C4", not part of C4's definition.
27. §7.8 (617): [P1]'s promotion trigger is accumulated knowledge (P1:273); "own lifecycle" is MemState's code guidance (`datamodel/topic.py:28-30`) [INFERENCE].
28. §8 (647): "multi-hop forgetting below 5 is a C3 failure" → "is consistent with"; line 650 itself says answer scores cannot separate causes.
29. §9.6 (710): the future-dated probe is not a status error (`2608.19652v1.md:167`); only the lapsed override matches. StateMemBench says "We release StateMemBench" (:161) with no link found; say that.
30. §9.2 (668): the perfect-retrieval setting is LongMemEval-oracle as analysed in the StateMemBench paper. LadybugDB is one of several community forks (656, 243). Sleep-time compute's 5× is measured on Stateful GSM-Symbolic/AIME only. §6.7 (405): the Supermemory post was later labelled a parody and taken down.

## E. References

31. LoCoMo (7 body uses) has no §10 entry; PrecisionMemBench and Backboard have no source; the Graph-Native Cognitive Memory entry lacks its author (Y. B. Park). Other metadata gaps in `demo-refs.md` item 13. All 26 §10 URLs load.

## Confirmed (sample)

Author names/titles/years of P1–P6; §4.3 wording ("not implementation gaps", native-engine list incl. "first-class bitemporal attributes", P1:331); Listing 1 identifiers; retrieval never consulting the flag; no time bound on C3; StateMem mechanics, −12.5 Set B, 0.373 vs 0.363; MemTX numbers in Tables 2, 3, 12, 13; dates (P1 2026-05-25, TOKI 2026-06-04, StateMemBench 2026-08-20; Kuzu archived and 0.11.3 released 2025-10-10); MemTX cites [P1], StateMemBench and TOKI do not; `import kuzu` only in `kuzu_adapter.py:10` [INFERENCE]; 39 upstream tests; sleep-time 5× and predictability correlation.
