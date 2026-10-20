# Paper conversions verified

Type: task
Status: resolved
Blocked by: —

## Question

Are the Markdown versions of the papers and the repo's analysis docs faithful enough to cite?

## Answer

Done (backfilled 2026-10-11). Each was audited by an independent agent against the PDF page images or the MemState source, then fixed:

- `docs/papers/2602.03128v2.md` (MAFBench): converted, pass-with-fixes (Figure 1 tool placement, bold, italics).
- `docs/papers/2602.19320.md` (survey): pass-with-fixes, formatting only; all numbers correct.
- `docs/papers/2605.26252v1.md` (GEM): **failed** first audit (redrawn figures wrong, paraphrased prose, invented §5.1–5.4 numbering, condensed references); rewritten, second audit pass-with-fixes; GitHub render check: 88/88 math spans render.
- `README.md` and `docs/papers/2605.26252v1-alignment.md`: 23 factual corrections from code (forget gate at 500 topics, salience overwritten by field writes, recovery paths, stale line numbers).

Added 2026-10-12 for the report's related-work checks (PDFs in `docs/papers/`), each converted then independently audited and fixed:

- `docs/papers/2501.13956.md` (Zep, 12 pp): pass-with-fixes (9 bold Delta cells leaking `**` on GitHub; `LongMemEval_s` subscript lost).
- `docs/papers/2512.12818.md` (Hindsight, 28 pp): pass-with-fixes (misplaced italics, monospace model names, two heading capitalisations, Figure 2 arrow source). Converter's note for the report: no explicit forgetting or deletion; world/experience facts never superseded; only opinions (confidence) and background (merge) change; Recall read-only in the formal definition.
- `docs/papers/2602.05665.md` (Graph-based Agent Memory survey, 29 pp): body pass; references pass-with-fixes (one broken accent in ref 58). Figure 6 row/content mismatch is in the PDF itself and kept as printed.
- None of the three is cited by GEM except Zep.
