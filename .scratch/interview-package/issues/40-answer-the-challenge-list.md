# Answer the challenge list

Type: grilling
Status: resolved

## Question

An adversarial review (agent ChallengePlan, 2026-10-20) attacked the conditions change, the baseline, the conformance suite and the time probes as Prof. Mansour might. Its full list is [challenge-conditions-baseline-suite-probes.md](../assets/challenge-conditions-baseline-suite-probes.md), with a triage at its top. Statements about Graphiti's code come from reading it at `6e3e3cb` and are [INFERENCE].

The objections that changed the plan:

1. **C1, C2:** "precise reading of C1" contradicts "the gap is in the conditions", and phase 1's result depends on how Definition 4's `t` is read.
2. **T1, T2:** the time probes give upstream no dates, then score `fail` where ADR 0002 says `absent`.
3. **T5, T7, T4:** plain Graphiti fails T3, T4 and T6, so "Zep's model fixes them" overclaims. And "you implemented our future work".
4. **B1:** a dict baseline cannot back "database guarantees are necessary but not sufficient" (MAFBench asked for versioned stores).
5. **C4:** override layering vs C2's "superseded value returned as current".
6. **C3:** C1′ dropped "non-archived"; "expired" is ambiguous.
7. **S1:** the same authors write the checks and build the reference GEM.
8. **C6, C7:** C3′ is a strengthening, and C4′ adds a state component; neither is demonstrated.

Not taken up here. These were already covered elsewhere, or they rested on context the reviewer lacked:
- S2 → "Ratify verdict rules set during the build"
- S6 → "Reference GEM design"
- S8, S9 → the audits and the run of record
- S10 → ticket 37
- S11 → build ticket "Review the storyline content"
- S7, T8 → already caveated in the report (:669, :542)
- B2–B5 → declared or covered by B1
- S3, C5, T3, T6 → see the triage

## Answer

Resolved 2026-10-20 with the user.

- **C1′ is an amendment** (1, 6):
  - It makes one clarification: `t` is when a value became true, and "current" is judged at the asked date, among non-archived entries.
  - It adds two things: an end date per value, and a recorded time.
  - It uses two words: **ended** (valid time over) and **expired** (memory stopped holding the entry). When the valid value is archived, the read returns no current value plus a note that an archived value exists.
  - The report's line becomes "**one amendment (C1′), one strengthening (C3′), one extension (C4′)**".
  - Ticket 37, ADR 0007, the map line and the approved claim are reworded to match.
- **Reference GEM phase 1** (1) is built once, on the **kindest reading**, with each probe's expected verdict written in the spec before building. Expected [INFERENCE]: correct on T1, T2, T3 and T6; `absent` on T4 (no end date) and T5 (no recorded time), per "Ratify verdict rules set during the build". Upstream stands for the arrival-time reading.
- **Time probes** (2):
  - They get their own scorecard section, "probes of the proposed C1′, outside [P1]'s claims".
  - Each probe gets two cells: "accepts dates" and "answers correctly given dates".
  - Upstream "cannot express" these cases, and is never called "wrong".
- **Zep's credit** (3):
  - The model is "the standard bitemporal model, in the form Zep uses for agent memory". The contribution is the read rule (C1′) and its tests.
  - The report gets a "Zep as written" column, from code reading and marked [INFERENCE].
  - The probes are ours, motivated by Zep and StateMemBench.
  - Answer to "you implemented our future work": §4.3 says to store bitemporal values, not what a read returns.
- **Baseline** (4): replaced by a **versioned row** (append-only history with recorded time, one transaction per write, in-process). Expected [INFERENCE]: passes C1 and C4, fails C3, C5 and C6.
- **Superseded** (5): a value is superseded only when a later statement ends its validity. A lapsed scoped override returning the base value is not a C2 violation. One check reads C2 this way on the lapsed-override story.
- **Grading our own work** (7):
  - Checks, parameters and expected verdicts are written before the build, and each check is tested against a deliberately broken version ("Reference GEM design" item 10).
  - The wording is "**passes the suite's checks, with declared simplifications**", never "satisfies C1–C6".
- **C3′ and C4′** (8):
  - C3′'s testable core is scored on the reference GEM: a read of a dependent before it is re-checked carries a flag naming the update. The flag clears when the dependent is next written.
  - A C4′ probe checks whether provenance resolves to a stored source. The reference GEM stores the source message with each write. Upstream, the patch and the versioned row are expected `absent` [INFERENCE].
- **Smaller decisions taken in the same session:**
  - **MemState's built-in limits are stated with their numbers:**
    - the 500-entry history cap: a correction uses two entries;
    - C5's 500-topic soft limit against 2,000 active topics (F10).
  - **Related wording and checks:**
    - "no regressions **on the rows the suite checks**";
    - C5 counts topics, not history entries;
    - one check that an as-of read raises salience (report :700 states it).
  - **Other decisions:**
    - Results assume correct dates (a best case).
    - `absent` stays beside a "claimed by [P1]?" column; ADR 0002 cites `MemState/README.md:5` "NOT Full Implementation".
    - The merge is reported as **existence**, not a rate, with the natural 10/20 (F9) beside it.

**Applied now:** ticket 37, ADRs 0002 and 0007, the map, the glossary ("Current value", "Ended value", "Superseded value", "Baseline"), and "Reference GEM design".

**Left to "Revise the spec and build tickets for the reference GEM and the suite audit":**
- the report changes in §1 item 13, §7.5, §9.3, §9.5, §9.6 and §9.8;
- the new checks (C2 on the lapsed override, as-of salience, C4′ probe);
- the C2(a) wording.
