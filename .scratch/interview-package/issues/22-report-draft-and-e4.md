# Report draft, E4 mapping and staleness windows

Type: grilling
Status: resolved
Blocked by: 21

## Question

The user's report draft exists. Where does it live, how does its extension E4 relate to the demo's tests, and how does the demo report the staleness windows the draft discusses (§5.3, E3)?

## Answer

Resolved 2026-10-12.

- **Location**: `docs/report/gem-limitations-and-directions.md` (committed), the single source of truth for the report. Its §9 is the demo design and the input to `to-spec`. The former `~/Downloads/agent-systems.md` copy is stale.
- **E4 (non-destructive failure)** is field-level: a failed input must not overwrite a prior value, while valid parts of the same update may still commit. Report §7.5 notes the tension with GEM's all-or-nothing commit (Algorithm 1).
- **Test-to-claim mapping**: merge tests → C4 (+C2) and MAFBench §6; C2(b) (ingest with an edge to a non-existent topic) → GEM's atomic commit; **E4 probe** → store `Deadline: April 20`, then `/v1/ingest version_field` with `""` and separately `null`: rejected (e.g. 422) with April 20 still current → pass; empty value becomes current → fail.
- **Staleness windows** (report §9.2, linked to §5.3 and E3): merge revision window = measured Reasoner time (rule-based, local); dependent-topic staleness window = unbounded (C3 absent).
- Practitioner note in §7.5 reworded: the author's fix was E4's field-level rule, not GEM's whole-transition abort.

**Superseded in part 2026-10-19 by [Report v2 redraws the demo](23-report-v2-redraws-the-demo.md):** E3/E4 are replaced by refinements C1′/C3′/C4′; the empty/`null` probe is a case of the C4 row. Report v2 reverts the practitioner-note wording; see [Reconcile report v2 with earlier decisions and the source audit](25-reconcile-report-v2-with-earlier-decisions.md).
