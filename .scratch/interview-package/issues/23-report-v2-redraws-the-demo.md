# Report v2 redraws the demo

Type: grilling
Status: resolved
Blocked by: 22

## Question

The user revised the report outside the repo (`~/Downloads/README (2).md`, 2026-10-19). Which earlier decisions does the revision change, and what does the plan now have to decide?

## Answer

Resolved 2026-10-19. The revision was installed as `docs/report/gem-limitations-and-directions.md` (single source of truth). The user's report decides the following; the details still open are new tickets.

**Contribution changes** (report §1 items 6, 11; §9.5):
- The demo's contribution is a **bitemporal extension of MemState's field histories** (Zep's four timestamps, deterministic supersession given timestamps, scoped overrides, as-of queries on both axes), implementing refinement **C1′** (§7.5).
- It runs on **LadybugDB**, Kuzu's maintained successor (`import ladybug as kuzu`, package `ladybug` 0.21.2), not on `kuzu==0.11.3`. Upstream is still measured unmodified on Kuzu.
- **Three commits**, each attributable: (1) LadybugDB port, verdicts must be identical; (2) bitemporal histories and C1′ queries, the time probes flip; (3) merge by valid time, the merge tests flip. The history-preserving merge survives as commit 3, keyed on valid time.

**Suite changes** (§9.2, §9.4, §9.6, §9.8):
- Verdicts are read against the paper's own §4.3 claim per condition (C1, C2, C4 by construction; C5, C6 under transitions; v2 treats C3 as not claimed, so *absent* is consistent with the paper). *The source audit contradicts the C3 part: P1:240 claims C3 by construction; see [Reconcile report v2 with earlier decisions and the source audit](25-reconcile-report-v2-with-earlier-decisions.md).*
- Five **time probes** with paired controls: retroactive fact, out-of-order arrival, future-dated change, lapsed scoped override, as-of query; one chat example resolving "two weeks ago" against the message's reference time.
- Every trap probe gets a paired control (MemTX's design). The `/v1` path is framed as the perfect-acquisition control; the chat path gives one recorded example.
- The **E4 row is gone**: the empty/`null` write probe is a case of the C4 row. E3/E4 are replaced by refinements C1′, C3′, C4′ (§7.5); C3′ is ranked future direction 1 (§7.9), not built.
- New measurements: latency on both engines with and without the extension; **reinforcement precision** for C6.
- Scorecard columns: **§4.3 claim | upstream (Kuzu) | bitemporal patch (LadybugDB) | last-write-wins baseline**, plus the five time-probe rows.

**Supersedes in part**: [Which gap to patch](07-which-gap-to-patch.md), [Merge history semantics for the patch](17-merge-history-semantics.md), [Patch packaging](18-patch-packaging.md), [Report draft, E4 mapping and staleness windows](22-report-draft-and-e4.md), ADR 0004 for the patched column. The spec `.scratch/gem-conformance-suite/spec.md` is stale until revised.

**Evidence gap**: §5.3 calls the C3 staleness result "run-verified" and §5.10 reports the LadybugDB port (39 tests, identical verdicts, 321 vs 392 ms), but these came from a sandbox run with fallback hash embeddings; none is in `docs/findings.md`. Reproducing them is a ticket.
