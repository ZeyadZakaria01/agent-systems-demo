# Slide outline

Type: prototype
Status: closed
Blocked by: 32

## Question

What is the slide outline? A rough outline to react to: slide order and titles, one line of content per slide, which slides show screenshots of the scorecard or recordings and where the talk hands over to the live demo ("Interview-day delivery" fixes what runs live), and the slide tool and format.

The time split (slot length, talk, demo, Q&A) is not decided here: the user prepares it at the end (map, Not yet specified). The outline is drafted without it and fitted to it later.

## Comments

- 2026-10-21, Prep (agent; a draft to react to, not a decision; blocked by the research-direction decision, so drafted under its recommended option B with D's framing, "C1′ as built, C3′ next, MAFBench as the opening problem"; no time split):
  - **Fixed inputs.** "Interview-day delivery": the conformance suite and the Graph Explorer run live (offline, seconds; `python -m demo.run --mode live … --delay N`, Explorer at `http://127.0.0.1:8765/ui/`); the Ollama chat run is replayed from a recording; a full screen recording is the fallback. Static sources: `runs/record/20261021-194912/scorecard.md` (the run of record on the final commits; `runs/record/20261021-085949/` is the earlier run on the superseded commits), recordings in `runs/recordings/` and `runs/chat-series/`.
  - **Outline (slide: one line; S = screenshot).**
    1. Title and the question: "Is agent memory a database?" Who, what, why this pair of papers.
    2. MAFBench's problem: multi-hop selective forgetting < 5.0 in every framework; memory is append-only (report §8). S: MAFBench Table 10 crop.
    3. GEM in one picture: C1–C6, the three failure modes, MemState as the prototype.
    4. What the paper does not give: no evaluation, staleness detected but not bounded, recency as validity (report §1, items 1–5).
    5. Method: test stored state, not answers; verdicts pass/partial/fail/absent; seven systems (upstream, steps 1–3, reference GEM phases 1–2, versioned row).
    6. Baseline: a versioned row is MAFBench's own remedy; what it lacks (C2(c), C3, C5, C6). Short.
    7. Results on upstream MemState: the scorecard. S: `scorecard.md` verdict table, upstream column highlighted (C2(a) fail, C2(b) fail, C3 absent, C5 trajectory fail).
    8. Findings that surprised: partial commit on 400 (F23), merge drops the newer value 20/20 (F9, F29), 2,000 active topics against bound 500 (F10, F22).
    9. **Live demo handover:** run C2(a) and the time probes in live mode with the Explorer open (topic history growing, salience badge); upstream first, then patched server (alternative: replay the screen recording).
    10. The contribution C1′: valid-time and recorded-time field histories, three patch commits on LadybugDB, one amendment to GEM's C1. S: change table, step 1 → 2 → 3.
    11. Result: T1–T6 absent → pass, step 3 merge fix, no regressions, 39 upstream tests unedited. S: scorecard probe table, step 2/3 columns.
    12. Reference GEM: shows the time gap is in the conditions, not the prototype (phase 1 absent on T4/T5; phase 2 passes all). Declared simplifications on the slide.
    13. Answer-level contrast through chat: the bad merge looks right in 30 of 30 answers while the state is wrong (F37, F39); "two weeks ago": the router and model limits (F31, F38, F40). S: a chat recording frame (replayed, not live; GPU limit).
    14. Limits and honesty: n values, simplifications, what is not measured (graded by Sonnet and a blind reviewer agent, no hand grades; latency on a laptop).
    15. Next: C3′ first (C3 absent on every MemState system), then the retention score, trajectory benchmark, MAFBench–GEM drift labeling (report §7.9).
    16. Questions; backup slides: latency ramps (F33), C5/C6 details, over-flagging chain, reference GEM design, MAFBench table.
  - **Handover.** Live at slide 9 and again at slide 11 if time allows; slides 10–13 can be shown without the server, so the server can be stopped after the live part (6 GB GPU, little RAM; one machine lock).
  - **Under the other direction options.** A (C3′ first): slides 10–12 shrink to one slide; the lead becomes C3 (absent everywhere, F7/F17), reference GEM's one-hop flagging and the over-flagging chain become the climax, and C1′ moves to "also built". C (MAFBench–GEM first): slides 2 and 13 expand into the thesis (answer-level scoring hides state failures), slides 10–12 become one supporting slide, and slide 15 opens with direction 4.
  - **Tool and format options.** (1) Marp (Markdown slides → PDF/HTML via Node; not installed, fetch with `npx`; fits the repo's Markdown workflow, versioned, `scorecard.md` tables paste in); (2) reveal.js HTML (Node; live code blocks and iframes of the Explorer possible); (3) LibreOffice Impress (installed; manual, hard to diff); (4) Google Slides/PowerPoint (needs account; free). Recommendation (agent's): Marp, exported to PDF as the file brought to the interview, with PNG screenshots of the scorecard rendered from `scorecard.md` through the Chromium route that works locally (see "Report final form and sending", Prep). Not verified here: Marp's install and output.
- 2026-10-22, closed by the user: the user writes the slides themselves, from the revised report (ticket 33). The draft outline above stays as optional input.
