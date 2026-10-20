# Merge history semantics for the patch

Type: grilling
Status: resolved
Blocked by: 07

## Question

When two duplicate topics both carry a field (e.g. `Deadline`), how does the patched merge combine their histories?

Options on the table: interleave both histories by `valid_from`, newest current, dropped-topic entries tagged `merged-from:<id>`; keep the survivor's history and append the dropped topic's entries as superseded; make the topic holding the newer value the survivor.

Recommendation so far: interleave by `valid_from` with provenance tags (only option satisfying both C2 and C4). The patch also skips archived topics and recomputes duplicate pairs after each merge so three duplicates lose nothing.

## Answer

Resolved 2026-10-11 (recommendation accepted with the review, ticket 21): interleave both histories by `valid_from`, newest entry current, entries from the dropped topic tagged with provenance `merged-from:<id>`. The patched merge also skips archived topics and recomputes duplicate pairs after each merge, so three duplicates lose nothing.

**Superseded in part 2026-10-19 by [Report v2 redraws the demo](23-report-v2-redraws-the-demo.md):** the merge becomes commit 3 of the bitemporal patch and interleaves by valid time; how this carries over is part of [Bitemporal history model and API](26-bitemporal-history-model-and-api.md).
