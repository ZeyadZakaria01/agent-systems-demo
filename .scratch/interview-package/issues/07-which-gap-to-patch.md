# Which gap to patch

Type: grilling
Status: resolved
Blocked by: 04

## Question

The contribution includes one small patch measured before and after. Which gap?

## Answer

Resolved in the planning chat (backfilled 2026-10-11).

- **History-preserving merge that skips archived topics** (targets C2 and C4). Smallest patch with the clearest before/after; matches MAFBench §6's call for versioned fact stores.
- Measured as a separate patched copy; upstream stays measured unmodified.
- Rejected for now: stop field writes erasing salience bumps (partial C6), salience decay (needs a time model), extension-edge propagation (largest, new semantics).

**Superseded in part 2026-10-19 by [Report v2 redraws the demo](23-report-v2-redraws-the-demo.md):** the contribution is now a bitemporal extension of field histories (C1′) on LadybugDB; the history-preserving merge remains as its third commit, merging by valid time.
