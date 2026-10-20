# Reconcile report v2 with earlier decisions and the source audit

Type: grilling
Status: resolved

## Question

Report v2 was written from an export that predates two repo edits, and it reverses or drops points earlier tickets decided. A source audit of v2 against the papers (linked below; 31 non-`ok` items) found more. Which fixes go into the report, and does any change the demo's framing?

- **C3 is claimed by the paper** (audit A1): P1:240 "The data model supplies C1, C3, and C4 by construction". v2's framing that C3 is "not claimed" and that *absent* is "consistent with the paper" (lines 7, 131, 164, 683) holds only for §4.3's validation sentence. If C3 is absent in the prototype, that contradicts §4's own claim. This changes §9.4's C3 row and how the demo presents C3 to the paper's author.
- **MemTX qualifier** (audit B6): the repo version said cascading-repair methods reach 1.0 "only on four of the five backbones (0.959 and 0.963 on the weakest, Qwen2.5-14B)"; v2 dropped it. The audit confirms the qualifier (`2607.23929v2.md:470, :492-493`). MemTX also scores a reimplementation, not the official code (B7).
- **Practitioner note** (audit A4): [Report draft, E4 mapping and staleness windows](22-report-draft-and-e4.md) reworded it to "E4's field-level rule; GEM's Algorithm 1 would instead abort the whole transition"; v2 reverts to "the same rule as MemState's abort-on-postcondition-violation", which the audit finds inaccurate (P1:314; §7.5 line 552 contradicts it).
- **Results stated before runs** (audit A3, C18): §5.3 "run-verified", §5.10 LadybugDB numbers, §9 "fixes … without regressions". Keep with a sandbox label, or wait for [Reproduce the C3 staleness run and the LadybugDB port](24-reproduce-c3-staleness-and-ladybugdb-port.md).
- **MAFBench single-hop** (audit B8): Table 10 gives FC-SH 36.0 and SF average 20.2 for retrieval-only LangGraph; the paper's prose (and ticket 21, the journal) call 20.2 "single-hop".
- **The rest of the audit**: wrong facts B9–B17, overstatements D19–D30, references E31.

**Applied 2026-10-19 at the user's request:** every factual item (A3, B6–B17, C18 as sandbox labels, D19–D30, E31) is fixed in the report; see [report-v2-fixes.md](../assets/report-v2-fixes.md). Still open, for the user: A1 (C3 framing), A2 (supersession rule; shared with [Bitemporal history model and API](26-bitemporal-history-model-and-api.md)), A4 (practitioner note and "same rule" in §7.3), A5 (StateMem ablation in C3′'s motivation).

## Assets

- Source audit of report v2: [report-v2-audit.md](../assets/report-v2-audit.md)
- Fixes applied: [report-v2-fixes.md](../assets/report-v2-fixes.md)

## Answer

Resolved 2026-10-19. All factual audit items are applied (see the fixes asset). The user accepted the four recommendations, now in the report:

- **C3 (A1):** the report states both: §4's opening claims C3 by construction and §4.2 describes flag-and-repair; §4.3 does not list C3; the public prototype has neither, so C3 is *absent*, matching §4.3 but short of §4.2. Changed: scope note, §1 item 11, §5 Framing, §5.3, §9.1, the §9.4 claim column ("[P1]'s claim (§4, §4.3)") and C3 row, §9.8 columns.
- **Supersession rule (A2):** values are inserted into the field's timeline by valid time (close the entry containing the new `t_valid`; end at the next later entry; retired entries re-recorded with corrected intervals; ties go to the later ingestion), stated as this report's rule on Zep's four timestamps, since Zep orders by ingestion (`2501.13956.md:91`). §9.5 and §1 item 11.
- **Practitioner note (A4):** "a field-level version of the rule; GEM's Algorithm 1 would instead abort the whole transition" (§7.5); §7.3 item 2 contrasts whole-transition abort with Hindsight's per-item guard.
- **StateMem ablation (A5):** C3′ is argued from correctness. Flags are cheap; flags alone have a mixed effect (0.222 vs 0.233 Qwen, 0.373 vs 0.363 DeepSeek); the guidance prompt is worth 2.5–6.2 points; authors read margins as an upper bound (`2608.19652v1.md:270-290, :306`).

**Superseded in part 2026-10-20 by [Bitemporal history model and API](26-bitemporal-history-model-and-api.md):** the A2 claim that Zep orders by ingestion holds for the paper's wording only; Graphiti's code orders a late-arriving older fact by valid time (`edge_operations.py:730-743`, commit `6e3e3cb`). Report §9.5 now says so, and the retired entries are named `expired_at`.
