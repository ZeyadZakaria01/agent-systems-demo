# Revise the spec and build tickets for the reference GEM and the suite audit

Type: task
Status: resolved
Blocked by: 35, 36, 38, 40

## Question

Bring `.scratch/gem-conformance-suite/spec.md` and its build tickets (on branch `gem-suite`) in line with:
- [Reference GEM: show the time gap is in the conditions, not the prototype](37-reference-gem-locates-the-time-gap-in-the-conditions.md) and [Reference GEM design](38-reference-gem-design.md): new user stories, a new system in the adapter section, the stricter C3 and C2(c) checks, new build tickets for both reference GEM phases;
- [Ratify verdict rules set during the build](35-ratify-verdict-rules-set-during-the-build.md);
- [Close the suite audit's design gaps before the patch tickets](36-close-the-suite-audits-design-gaps.md);
- [Answer the challenge list](40-answer-the-challenge-list.md): probe design (dates vs ordering), the framing of C1′ and Zep, the baseline's claim;
- the outcome of build ticket "Review the storyline content" (whether the scored storyline gets the re-explained duplicate).

Apply the report changes these tickets list (§9.1, §9.2, §9.4, §9.5, §9.8) in the same pass. Set the spec back to `ready-for-agent` when done.

## Answer

Resolved 2026-10-21. Applied by a single agent, with the user settling its open conflicts.

- **Spec** (`.scratch/gem-conformance-suite/spec.md` on `gem-suite`, status ready-for-agent):
  - stories 58–78;
  - the reference GEM design, with a parameter table separating what is reused from MemState's code (threshold 0.05, +0.1, halve on archive, β 500, revision after every ingest) from what is added from the paper (decay on disuse, a forgetting check after every interaction; a read or write resets the clock);
  - stricter pass criteria (C3 undirected per `2605.26252v1.md:212, 275`, both pairs scored, association-only control; C2(c) runtime policy);
  - a pre-registered expected-verdicts table (7 systems × every row);
  - mutation tests;
  - run of record and story 43 from `main`.
- **Settled during the revision:**
  - the versioned row rejects empty and null values, so C4 is expected to pass;
  - its missing capabilities are `absent` (C2(c), C3, C5, C6), each confirmed by a probe; C2(a) is n/a, since no merge occurs [INFERENCE];
  - C6-2 seeds of 0.06 on the reference GEM are a declared per-system test setting.
- **Build tickets:**
  - 12, 13, 15, 17 and 19 rewritten;
  - pointer comments on resolved tickets 01 and 03–10;
  - new tickets 20–32: versioned-row baseline, verdict rules and per-probe date detection, revised checks, case-level change table, stricter C3 and C2(c), C4′ probe, reference GEM phases 1 and 2, over-flagging measurement, mutation tests, reference GEM workloads and windows, three-group scorecard, run-of-record folder and upstream tests.
- **Report** (`main`):
  - §1 items 5, 10, 11 and 13;
  - §4.2; §5.3; §5.7; §7.4; §7.5 (C1′ as an amendment);
  - §8, with the corrected MAFBench claim: a versioned row gives C1, C2's atomic commit and current-value rule, and C4; it lacks C2(c), C3 (MAFBench also asks for "dependency tracking across stored facts", `2602.03128v2.md:568`), C5 and C6;
  - §9.1–§9.8.
- **Coverage:** the agent's table maps every decision of tickets 35, 36, 38 and 40 (and 37's comments) to a spec section, build ticket or report section. A final grep for the stale wordings found none: "writes whatever arrives", "last-write-wins baseline", "precise reading".
