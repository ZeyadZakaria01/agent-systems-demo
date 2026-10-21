# Report final form and sending

Type: grilling
Blocked by: —

## Question

In what form does the report reach Prof. Mansour? It runs to about 17,800 words. Is it sent whole, with a short cover summary, or cut to a target length with the rest in an appendix? Which export path produces the PDF (tables, math and links intact)? Since the plan is built in full (see Comments), the report goes out after the run of record, with §9.7 citing F13 onwards and §9.8 filled.

## Comments

- 2026-10-20: findings F13–F22 are recorded on `gem-suite` but not yet on `main`. Report §9.7 still cites only F7–F12.
- 2026-10-20, from the user: the plan is built in full whatever the interview date. The report is not sent half-filled.

- 2026-10-21, Prep (agent; facts and options for the grilling, no decision taken):
  - **Length (measured now, `wc -w` on `docs/report/gem-limitations-and-directions.md`).** 24,188 words in total (the ticket's 17,800 is stale), 23,550 before §10 References. By part: §1 summary about 1,070; §3–4 about 690+; §5 about 4,720; §6 about 3,240; §7 about 4,940 (§7.9 alone about 500); §8 about 500; §9 about 8,200 (§9.7 results is the longest part). Summary §1 has 14 numbered items. Counts will shift while ReportChat adds F38–F40.
  - **Export tools present locally.** No `pandoc`, no LaTeX engine (`xelatex`, `pdflatex`, `lualatex`, `tectonic`, `typst` all absent), no `wkhtmltopdf` or `weasyprint`. Present: Chromium (Playwright cache `~/.cache/ms-playwright/chromium-1228`), Firefox, Brave (snap), LibreOffice (does not read Markdown), `uv`, Node 22, `pdftotext`/`pdftoppm`/`pdfinfo`.
  - **Export tried (in `/tmp/mp`, nothing written in the repo).** `uv venv` + `markdown` (tables, toc) → HTML → `chrome --headless --no-sandbox --print-to-pdf` with the report as it stood at 2026-10-21. Result: 43 pages at US Letter, 967 KB. Observed: all 24 tables render with borders and fit the page in portrait, including the 8-column scorecard; Unicode (β, ′, §, →) renders (DejaVu, Noto Sans Math embedded); the report contains no LaTeX math (no `$$`; `$` only marks dollar amounts), so there is no math to lose; in-document anchors resolve (heading ids such as `1-summary-of-findings`; the PDF has 14 link annotations). Problems seen: (1) the references list collapses into one run-on paragraph in Python-Markdown (list lines lack a blank line before them; GitHub renders them as lists), so the source needs a blank line or a GFM-compatible renderer (e.g. markdown-it); (2) two relative links, `../../demo/record/20261021-085949/scorecard.md`, are dead in a PDF sent by mail; they need absolute URLs (the repo remote is `github.com/ZeyadZakaria01/agent-systems-demo`, visibility not checked) or the scorecard sent as an attachment; (3) no cover page, page numbers or headers (the CSS was minimal).
  - **Earlier decisions.** The user: plan built in full, report not sent half-filled (comment above); the map's "Out of scope" and standing preference "no gap reported without a reproducing run" mean a cut would have to keep §9's evidence; AGENTS.md: the report is the single source of truth, edited on `main` only, so a short version or appendix split must be generated from it or live in it, not forked.
  - **Option A, send whole, with a half-page cover note.** 24k words, 43 pages; the PDF carries the full evidence; the §1 summary (about 1,070 words) is already the executive summary. Cost: the interviewer must be willing to read 43 pages.
  - **Option B, send §1 summary plus §9 demo as the main PDF, rest as appendix in the same file.** Needs reordering the report (it breaks "single source of truth" unless done by the export script).
  - **Option C, cut to a target (say about 10k words).** Costs sections the report's claims rely on (§5–6 evidence) and a second text to maintain; against the user's "built in full" stance.
  - **Option D, send the PDF whole plus the repo link (README, scorecard, recordings).** Same as A, with the evidence one click away; fixes the dead relative links.
  - **Recommendation (agent's, user decides): A + D.** Whole report with a one-page cover note that points to §1 (read first), §9.8 (the scorecard) and the repo; PDF via the Chromium route from a small committed script after fixing the references-list blank line and link rewriting. Not decided: whether the repo is public by then.
