# Report final form and sending

Type: grilling
Status: resolved
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
- 2026-10-22, from the user: the paper questions given on 2026-10-22 (MAFBench, Anatomy, graph survey, StateMem; answered in [cross-paper grounding](../assets/cross-paper-grounding.md)) are input for grilling **this** ticket, i.e. the report's content, not ticket 32. The slides come after the report. So this ticket now covers the report's content revision (P1–P14 and §7.9's order and pointer, moved here from ticket 32) as well as its form and sending. Grilling round 1 starts on content; length, export and the cover note follow once the content is settled.
- 2026-10-22, **Round 1 decided (user):**
  - **Q1 (b):** §8 becomes "MAFBench: limitations and link to GEM", with its claims re-verified against the paper.
  - **Q2 (b):** §7.7 is rewritten as "A unified GEM evaluation suite", with all six components (grid, pipeline plus state adapter, grading order, writer × reader, saturation knobs with Δ and StateMemBench as the interaction-depth probe, Residual latency split).
  - **Q3 (a):** latency split in §5.2, hop-vs-scan cost in §5.5 (pairwise duplicate cost marked [INFERENCE] unless a scale run is added), approximate retrieval under C6 in §5.9.
  - **Q4 (a):** a compact graph-survey subsection in §4.2.
  - **Q5 (a):** §7.9 keeps its order, gains GEM §5 tags and the C1′ pointer line; MemState-through-MAFBench's-adapter goes into direction 4; shared multi-agent GEM memory becomes new item 5.
  - **Q6 (a):** offline state-masking script plus finding; constructed rows labelled as illustrations.
  - **Q7 (a):** record the Hindsight position.
  - Factual corrections (P13) and the TOKI conversion are applied without a decision.
- 2026-10-22, Q1 re-verification (agent, against `docs/papers/2602.03128v2.md`):
  - **Holds:**
    - one run per configuration ("To manage cost, each configuration runs once", :308), defended by five planning repeats within 4.1 points (:544);
    - "no seed is set" (:217);
    - a judge named nowhere, as "LLM-based semantic scoring" (:217);
    - one Haiku row on one framework (Table 10 last row, :389), whose stable AR (33.2→33.7) hides MH 24.0→8.0 and EventQA 63.3→82.5;
    - SF context 4–183k words, average 63k (:236), with no full-context baseline anywhere (searched "full context"). W tops out at 8,192 tokens (Fig. 4, :405), so even the largest accumulation window cannot hold an average SF context;
    - tool invocation not measured (:276);
    - shared state excluded from the topology study (:505);
    - plugin memories excluded (:227);
    - answer-level metrics only (:314).
  - **Three text-table mismatches, each confirmed against Table 10:**
    - :397 calls 20.2 "single-hop forgetting", but it is the SF average; FC-SH is 36.0.
    - :399 says "accumulation with a weaker LLM still outperforms retrieval-only with a stronger one" on TTL. Haiku retrieval-only scores 26.2, pure accumulation peaks at 20.7, and only hybrid scores more (28.9, 27.0).
    - :544 says "Retrieval dominates multi-hop retrieval and in-session learning", where §4.1.2 has hybrid best on AR (44.9) and "Retrieval-only memory performs poorly" on TTL (:395).
  - **Dropped as not a mismatch:** Table 1 omitting the Haiku row (Table 1 is "at fixed task and LLM").
- 2026-10-22, **Round 2 decided (user):**
  - **Q8 (c):** a one-page "Demo at a glance" directly after §1, linking into §9; no renumbering.
  - **Q9–Q11 (form, sending, repo link, PDF export):** dropped from this ticket. The user produces the final report document and the slides themselves from the Markdown report, which stays the single source.
  - **Repo:** the user will make it public later, so the report keeps repo-relative links, fixed to the current paths (`runs/record/...`).
  - **Scope left here:** the content revision decided in round 1, applied to `docs/report/gem-limitations-and-directions.md`.
- 2026-10-22, **Hindsight position (Q7 (a), recorded):** no decision to combine Hindsight with MemState was ever recorded. The report takes two of Hindsight's mechanisms: the LLM detects conflicts and rules resolve them (§7.2), and its visibility principle, enforced by the engine (C3′, §5.3). It adds no condition for epistemic separation (§7.3). It does not combine the systems:
  - Hindsight has no controlled forgetting (future work, `2512.12818.md:645`).
  - Its retrieval writes no salience (no C6).
  - World facts are never superseded.
  - It grades answers only (`2512.12818.md:572-574`).
  Hindsight stays a baseline and related work.
- 2026-10-22, **Answer (applied to `docs/report/gem-limitations-and-directions.md`).** Every draft was checked by a separate reviewer agent before it went in, and each fix the reviewers asked for was applied.
  - **Demo at a glance** after §1, with selected verdicts.
  - **§1:** item 10 extended (MAFBench limits, the MemoryAgentBench bridge); new item 15 (unified suite, F43).
  - **§4.2:** "Graph structure: where MemState sits in [P3]'s taxonomy".
  - **§5:** latency split (§5.2), hops vs units scanned (§5.5), approximate retrieval under C6 (§5.9).
  - **§7.7:** rewritten as "A unified GEM evaluation suite"; §7.3 points to it.
  - **§7.9:** tags, pointer line, the MAFBench adapter in item 4, shared multi-agent memory as item 5.
  - **§8:** "MAFBench: limitations and link to GEM" (8.1–8.3).
  - **§9.7:** state-masking paragraph (F43).
  - **Corrections:** Δ is not measured by [P2]; LongMemEval-S is 103k tokens in [P2]; scorecard links point to `runs/record/`.
  - **New evidence:** `demo/chat/lexical_grade.py`, F43, and the TOKI conversion `docs/papers/2606.06240v1.md` (verified faithful after two fixes).
  - **Checks:** ruff clean, 533 tests pass, report anchors and relative links resolve.
