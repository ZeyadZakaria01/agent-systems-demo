<!-- Adversarial review, 2026-10-20, read-only except this file. Sources: main checkout (report, papers, tickets, ADRs, spec) and the `gem-suite` worktree `/home/zeyad/work/agent-systems-demo-wt/integration` @ 1ba8d31 (demo/, docs/findings.md F13-F22). Offline tests re-run: `pytest -q` -> 151 passed in 20.4 s. No server started. Graphiti read at commit 6e3e3cb via raw.githubusercontent.com (scratch copies deleted). Ids C/B/S/T are challenge ids; "F13-F22" are docs/findings.md entries; audit ids (suite-audit-vs-spec F1-F21, suite-audit-vs-report A1-A19) are cited as "audit F#" / "audit A#" and not repeated here. -->

# Challenge list: conditions change, baseline, conformance suite, time probes

How to read it. Each challenge is the objection as Prof. Mansour (database/benchmark professor) would phrase it, then **Evidence** (verified = read in a file or recomputed; `[INFERENCE]` = reasoning, not run), **Severity** (fatal / serious / minor), **Defuse** (the answer or change that removes it), **Ticket** (existing wayfinder or build ticket, or *new*). Report line numbers are the main checkout's `docs/report/gem-limitations-and-directions.md`; note the baseline is §9.3 there (the brief said §9.4, which is the conformance-tests table). Paper line numbers are `docs/papers/2605.26252v1.md`.

> **Triage (2026-10-20, after "Answer the challenge list").** Read this file as the reviewer's raw output. Only these items changed the plan: **C1/C2, C3, C4, C6/C7, B1, T1/T2, T4/T5/T7, S1**.
>
> - **Already covered elsewhere:**
>   - S2 → "Ratify verdict rules"
>   - S6, B4 → "Reference GEM design"
>   - S4 → audit F13
>   - S8, S9 → audits and the run of record
>   - S10 → ticket 37
>   - S11 → the storyline review
>   - S7, T8 → report :669, :542
>   - B2, B3, B5 → declared
> - **Weak, because the reviewer lacked context:**
>   - S3 missed `MemState/README.md:5` "NOT Full Implementation".
>   - C5's history-growth concern is mostly moot once an ordinary update stores no end date ("Close the suite audit's design gaps" Q1).
>   - T1's chat-with-dates variant was rejected.
>   - T3 and T6 are minor.

## 0. Steelman first (what the plan already gets right)

- It is honest about scale: verdicts are "a proof of concept measured as published" (scorecard text), `absent` is kept apart from `fail` (ADR 0002), every departure from Zep is listed with the condition that requires it (report:695-704), the one rule beyond Zep (override layering) is named (report:699), and the build audits found and logged their own problems.
- The central empirical result is real and cheap to defend: upstream gives the last-written value on all six time stories and ignores `valid_at`/`recorded_at` (F19), and C2(a) fails 20/20 under the F18 arrangement.
- Ticket 37 already anticipates "you built it to fail" and states the two preconditions that matter (stricter C3 and C2(c) checks before scoring; simplifications declared).
- C1′ is a coherent, small amendment; the report says plainly that it is "the first step of the bitemporal field histories §4.3 already calls for" (report:542).

The challenges below are what is left after those.

---

## Area C: the conditions change (C1′, C3′, C4′)

### C1. "C1′ is the precise reading of C1": it is an amendment, not a reading
- **Objection.** "My Definition 4 says an entry is `(v, t, π)` with one timestamp and C1 returns the most recent `v_k`; your C1′ adds a second timestamp, an interval end, a query-time bound, a recording axis and a layering rule. That is a different definition, not my definition read carefully."
- **Evidence.**
  - Verified, paper:206-208: `V_i = ⟨(v_1,t_1,π_1)…(v_k,t_k,π_k)⟩`, "a timestamp t", C1 returns "the most recent non-archived value v_k as current". `v_k` is the last element of a sequence, so C1 presupposes a total order and a point timestamp.
  - Verified, report:537: the report itself needs two reinterpretations ("reading `t` as valid time" and "'most recent' as most recent up to the query time"), then adds "valid time covers the query time and … has not expired" (an interval), "as of on both axes" (a second timestamp), and (report:699) "shorter validity wins" among overlapping values (a priority rule; with layering `V_i` is no longer a sequence with a unique last element).
  - Verified by computation (hand-coded rules over the suite's own stories, `demo/time_stories.py` shifted to 2026-10-20; not a system run). What each reading returns on the asked dates:

    | story, asked date | correct | `t` = recording time (upstream) | `t` = valid time, C1 literal | + "up to query time", point timestamps |
    |---|---|---|---|---|
    | T1 today | April 20 | March 1 ✗ | April 20 ✓ | ✓ |
    | T2 today | pro | basic ✗ | pro ✓ | ✓ |
    | T3 today | basic | premium ✗ | premium ✗ | basic ✓ |
    | T4 story 1 today | $50 | $80 ✗ | $80 ✗ | $80 ✗ (needs `invalid_at`) |
    | T4 story 2 Oct 5 | $80 | $100 ✗ | $100 ✗ | $80 ✓ |
    | T6 today | no value | premium ✗ | premium ✗ | no value ✓ |
    | T5 "believed on" | April 20 | ✗ | ✗ | ✗ (needs recording axis) |

    So "t is valid time" alone fixes only T1 and T2. T3/T6 need a query-time bound, T4 needs an interval end, T5 needs a second axis. These are three additions to Definition 4, not a reading of it.
  - Verified, report:537 drops "non-archived" from C1's wording (see C3 below).
- **Severity.** Serious. The §1 item 13 headline "refinements, no new ones" and §7.5 "precise reading" are the sentences a careful reader will quote back.
- **Defuse.** Say "amendment": Definition 4 underspecifies `t`; the minimal amendment is the table's three columns (query-time bound; interval end; recording axis); present the table as the justification of each addition. Reword report:40 and report:537 accordingly.
- **Ticket.** 26 and 25 (both resolved with "C1 reading (A)"); *new*: reword §1 item 13 and §7.5 and add the decomposition table to the report or slide.

### C2. The dilemma: "precise reading of C1" vs "the gap is in the conditions"; phase 1 depends on how `t` is read
- **Objection.** "Either C1′ is just C1 read properly, in which case your reference GEM that reads `t` as arrival time is a misreading of my paper and its failures are yours; or C1 as I wrote it really fails these stories, in which case C1′ is a change and you should call it that. You cannot have both."
- **Evidence.**
  - Verified: report:537 and §1 item 13 say "precise reading"; ticket 37 answer says "a system built to all six conditions gets them wrong, so the gap is in the conditions". Phase 1 is "one time axis; C1 = most recent value" (ticket 37, phase 1).
  - Verified: `docs/papers/2605.26252v1-alignment.md:33` maps the paper's `t` to MemState's `valid_from`, and `MemState/src/memstate/datamodel/fields.py:30` names the field `valid_from`; upstream stamps it `now` (`core/executor.py:122,156,196`). The authors' own schema name reads `t` as valid time, stamped at arrival.
  - Computed (table in C1): under the valid-time reading, phase 1 would pass T1, T2 and T4-story-2's plain read, and still fail T3, T4, T6, T5. Under the arrival-time reading it fails T1-T4, T6. So the phase-1 outcome "expected to fail the time probes" is a property of the reading the builder picks, not of the conditions.
  - Verified: ticket 37 ends "Expectations above are reasoning [INFERENCE]; nothing is built or run." Nothing is pre-registered.
- **Severity.** Fatal for the headline claim if left unresolved (it is exactly the "you built it to fail" objection); defusable cheaply.
- **Defuse.**
  1. Pre-register in the spec, before building the reference GEM, which reading each phase uses and the expected verdict per probe under each reading (the table above, extended).
  2. Run phase 1 under both readings (arrival-time `t`; valid-time `t` with C1 literal). The claim then becomes "even the generous reading of Definition 4 fails T3, T4, T6, T5" — which is true by the table, is not an artefact of the builder's choice, and keeps the amendment framing from C1.
  3. State that the finding is "Definition 4 underspecifies `t`", not "MemState or GEM is wrong".
- **Ticket.** 37/38 (reference GEM design); 39 (spec revision); *new* sub-item "pre-register phase-1 reading".

### C3. C1′ silently drops "non-archived", and "expired" is ambiguous; C1′ vs the forgetting ladder
- **Objection.** "My C1 says non-archived; yours says 'has not expired'. What does your system return when the valid value has been archived? And what is 'expired' — Zep's `expired_at` or `invalid_at`?"
- **Evidence.**
  - Verified: paper:208 "most recent non-archived value"; report:537 "the value whose valid time covers the query time and that has not expired" (no archive clause); report:700 repeats "valid now and not expired".
  - Verified: Zep/Graphiti `expired_at` is system-retirement (T′), `invalid_at` is valid-time end; report:697 relies on the distinction ("Graphiti marks such a fact expired on arrival") but C1′'s text uses one word. In Graphiti retrieval `expired_at` is only an optional filter (`search/search_filters.py:65`, scratch read), not a default exclusion, so "an October-only value would never be current in October" (report:697) is true only if "current" means `expired_at IS NULL`; Graphiti hands facts with date ranges to the LLM (Zep paper §3, context template) rather than defining "current". `[INFERENCE]` on retrieval behaviour; not run.
  - Verified, paper:323: forgetting is a ladder, "below θ_summary, a history is compressed". Compressing a field history destroys the closed entries that as-of answers (T5, "believed on") need; report §9.5 never says what an as-of read returns after compression or archiving, nor whether an as-of query counts as "explicit lookup" of archived content (paper:216, 323).
  - Verified, paper text alone: with an archived `v_k` and a live `v_{k-1}`, C1 as worded returns `v_{k-1}`, a superseded value as current (violates C2). The paper's own tension; C1′ neither fixes nor mentions it.
- **Severity.** Serious (a definition that omits one of the original clauses cannot be "the same condition made precise").
- **Defuse.** Write C1′ as: "the value whose valid interval covers the query time, among entries not archived; `expired` means retired from the belief timeline (`expired_at`), `invalid` means end of valid time"; add one sentence on archived-valid values (return none and flag, or return with an archive flag) and on as-of reads against compressed/archived history. The reference GEM can decide this cheaply (it has no compress rung, see S1).
- **Ticket.** *new* (report §7.5 wording; spec for reference GEM C5).

### C4. C1′ layering vs C2's "superseded value returned as current"
- **Objection.** "After October your system returns $50 as current although $80 was written later and superseded it in the record. That is literally my C2 violation."
- **Evidence.**
  - Verified: paper:210 "no revision produces a state in which a superseded value is returned as current"; T4 story 1 expects $50 on Nov 5 (`demo/time_stories.py` `LAPSED_OVERRIDE_1`); report:699 hard-codes layering and claims "it costs no condition".
  - Verified: the suite's own C2(a) defines the violation by write order: `OLDER`/`NEWER` in `demo/merge.py` and "the superseded value March 15 being current" (`checks/c2a_merge.py` docstring). On the patch, a dated merge (spec story 37) needs "superseded" defined by valid time; an undated one by recording time; the suite uses both without saying which C2 means.
  - `[INFERENCE]`: a C2 checker that reads "superseded" as "older write" flags the patch's T4 answer. The report says "a bitemporal system can satisfy all six conditions" (report:537), but no check combines time rules with C2.
- **Severity.** Serious (the report claims "costs no condition" for the one rule it adds).
- **Defuse.** Define in C1′/C2: a value is *superseded* only when a later statement closes its validity (valid interval ended or replaced); an override that lapses does not supersede the base. Say so explicitly as a C2 clarification and run a combined check (the lapsed-override story is one: $50 returned after $80 lapsed, with C2(a)'s definition of supersession pointed at valid intervals).
- **Ticket.** 26 (resolved: "costs no condition" decision); *new*.

### C5. C1′'s side effects on C4, C5, C6 are claimed away, not tested
- **Objection.** "You say the bitemporal system keeps all six. Show me. Your own keep-and-copy doubles history growth, and your history cap is 500."
- **Evidence.**
  - Verified: ADR 0005 last sentence, "Copies count toward MemState's 500-entry history cap, whose truncation already breaks C4 upstream"; F21: the 501-write case drops the oldest entry; audit A6: this case stays failing on every step. Each correction costs two entries (expire + copy), so C1′ brings the C4 violation forward. The report's goal line says "without regressions" (report:657, §1 item 11).
  - Verified: report:700 "as-of queries … raise salience like any read (C6)"; audit table: "as-of raises salience (C6): unmeasured". Salience is stored per field (`TopicField.salience`, `fields.py` ~line 67) and per topic; an as-of read of an expired entry reinforces the field holding the *current* value. Whether that is what C6 ("salience of u_i") means is unspecified.
  - Verified: C5 counts `|D_t^active|` (paper:216); the report never says whether expired and copied entries are active.
- **Severity.** Serious (the claim "no regressions" is exactly what the three-commit change table is for, but it only covers rows that exist; step 3's C4 improvement is not even visible there, audit A1).
- **Defuse.** (a) State the cap interaction as a known limit with a number (corrections per field before truncation); (b) add one row "as-of read raises salience" (audit already lists it as unmeasured); (c) say expired entries are history, not active state, and show C5's count excludes them. Or drop "no regressions" for "no regressions on the rows the suite covers".
- **Ticket.** 12, 15, 19 (build); report §9.5/§9.8 wording.

### C6. C3′ is a strengthening, its bound is unfalsifiable, and the reference GEM cannot satisfy it as simplified
- **Objection.** "My C3 says an update triggers *evaluation* of the dependent. You added a time bound, a visible flag on every read, policy-gated blocking and persisted repairs. That is a stronger condition. And your own reference system flags and never repairs, so it fails your condition."
- **Evidence.**
  - Verified, report:544: C3′ = bound (time or transitions, "policy-defined"), flag returned on every retrieval until re-evaluated, `P_t` chooses return-with-flag or block, "repairs are persisted". Paper:212: "triggers evaluation of `u_j` under `P_t`" — no bound, no visibility, no persistence.
  - Verified: ADR 0007 Consequences and ticket 38 item 1: reference GEM C3 is "flagging, no repair", one hop. A flag with no repair never clears, so "within a policy-defined bound … re-evaluated" is not met; either "flag" counts as "evaluation" (then C3′'s second half is empty) or the reference GEM fails C3′.
  - Verified: the bound is "policy-defined", like C5's β(n); a system that declares an infinite bound passes. The suite can only compare against a bound the system itself declares (MemState declares none, so C3 is `absent`, F17).
  - Verified: report:545 concedes the StateMem ablation gives flags alone "a mixed effect" and argues C3′ "from correctness".
- **Severity.** Serious.
- **Defuse.** Call C3′ a strengthening ("bounded and visible"), not a refinement; define the testable core: *a retrieval of a dependent between the update and its re-evaluation carries a flag that names the update*, which the reference GEM satisfies, and list the bound as a policy parameter with a stated default for the demo. Either give the reference GEM a minimal deterministic re-evaluation (clear the flag when the dependent is next written) or state C3′ is not scored on it.
- **Ticket.** 38 (reference GEM design item 1, 5), 39; report §7.5.

### C7. C4′ extends the state model, and C3′/C4′ are never demonstrated or tested
- **Objection.** "You promise three refinements, you demo one, and C4′ needs an episode store that is not in `M_t = (D_t, S_t, P_t)`."
- **Evidence.**
  - Verified: report:40 "Three refinements to GEM's conditions, no new ones"; spec:205 puts "C3′ propagation and bounded flags" out of scope for the patches; no check anywhere scores C4′ (grep of spec and `demo/` finds only C1′ in rows; the stricter C3 check of ticket 38 is the only C3′-adjacent test and is not built). Report:549 itself concedes C4′ "retain[s] more personal data, which works against the paper's verifiable-erasure direction".
  - Verified: C4′ (report:547) requires provenance to "resolve to retained source evidence", i.e. a source/episode tier (Zep's episodic subgraph, Zep paper §2.1; report:586, 587). Definition 4 and `M_t` have no such component (paper:150-160).
  - `[INFERENCE]`: the "stated / revised / compressed" labels are a data-model property rather than a trajectory-correctness property (nothing in the paper's three axes, paper:204, needs them); MemState already carries an optional `operation` tag on entries (`datamodel/fields.py:34`), used only for nested-topic links (`store/graph_store.py:641,830`).
- **Severity.** Serious for C4′ (a new component under a "no new conditions" banner); minor for the demo-vs-headline mismatch (the report does say "results pending" and ranks C3′ as future work §7.9).
- **Defuse.** Present C1′ as demonstrated and C3′/C4′ as proposals with one stated test each (C3′: flagged dependent read; C4′: provenance string resolves to a stored source, `absent` on upstream by probe). Say C4′ adds a component. Optionally add the C4′ probe to the suite (cheap: it is an `absent` probe on upstream).
- **Ticket.** *new* (report §7.5 wording; spec: add C4′ probe or label it unmeasured).

### C8. Necessity and testability per proposed condition (summary table, `[INFERENCE]` except where noted)

| | necessary? | testable as written? | consistent with Def. 4? |
|---|---|---|---|
| C1′ | Yes for T3, T4, T6, T5 (computed above); not for T1/T2 (valid-time reading suffices) | Yes: six probes exist; "has not expired" and archive clause untested | No: adds interval, second timestamp, priority (C1, C3, C4) |
| C3′ | Argued from correctness only (report:545); F7 shows the prototype lacks even C3 | Flag-on-read is testable; the bound is a policy parameter (C6) | Strengthens C3; compatible, not a reading |
| C4′ | Utility argument ("extraction errors cannot be repaired", report:548) rather than a trajectory-correctness argument | Resolve-to-source is testable only where a source store exists | Adds a state component (C7) |

---

## Area B: the baseline (last-write-wins row)

### B1. A dict is not "database guarantees": the baseline cannot test "necessary but not sufficient"
- **Objection.** "MAFBench called for versioned fact stores with MVCC, write-ahead logging and conflict resolution. Your 'database' baseline has no versions, no transactions, no log. Of course it fails history. That does not show database guarantees are insufficient."
- **Evidence.**
  - Verified: report:37, :649 and :677 state the claim "database guarantees are necessary but not sufficient" and say the baseline "tests this directly". MAFBench's call, report §8 (line 645): "versioned fact stores with multi-version concurrency control, write-ahead logging … conflict resolution".
  - Verified: `demo/baseline.py:1-12` docstring and F21: the baseline "keeps no history, salience, archived flag, edges or dates"; C4 `fail`: "No history (update, merge, cap)".
  - Verified: paper Table 1 lists "Temporal DB: Versioned histories" as a database-paradigm strength (paper:100) and paper:118 cites temporal databases; paper:230 (Observation 3a) is about *append-only* storage without semantic units. A last-write-wins upsert is neither of those.
- **Severity.** Serious (the sentence "database guarantees are necessary but not sufficient" is a headline of §8 and §1 item 10; the comparator does not support it). Fatal only if the claim stays in the headline.
- **Defuse.** Either add a **versioned-row baseline** (append-only history table with recording time, per-field transaction; a day of work, in-process like the baseline; it should pass C1, C4, and C1′ if given valid time, and fail C3, C5, C6) so the claim "versioning supplies C1/C2/C4, not C5/C6" is measured, or weaken the claim to "a plain row lacks history, salience and attenuation", which is what the baseline shows.
- **Ticket.** 05 (resolved), 02; *new*.

### B2. What the baseline lets us conclude, and what it cannot
- **Objection.** "The row answers 15/15 on your storyline too. What exactly did the baseline show?"
- **Evidence.**
  - Verified: F20: upstream 15/15 and baseline 15/15 on the storyline, so answer level cannot separate MemState from a row (audit A18).
  - Verified: baseline C2(a) is `pass` with 0 duplicates because it upserts (F18; audit A5 table), C1 is `pass (1 case n/a)` on one case (F13), C2(c) is `absent` on both upstream and baseline (F17), so "no policies `P_t`" does not separate them (audit A12).
  - Verified: the only rows that separate the baseline from upstream are existence-of-mechanism rows: C4 history (baseline has none), C5-1/C6 (baseline has no salience or archived flag).
- **What it does support:** that a row cannot pass C4, C5, C6 (by construction); that MemState adds history and salience machinery. **What it does not:** that MemState's machinery is correct (it is not, per C2(a), C4, C5-2); that GEM's conditions add value over a versioned store (B1); anything about C3 (both `absent`).
- **Severity.** Serious as framing; minor as science.
- **Defuse.** State in the scorecard what each baseline cell means (existence vs correctness); do not describe the baseline as showing "what MemState adds over a database" beyond history/salience existence.
- **Ticket.** 02/05; report §9.3 (audit A12 already asks for the wording).

### B3. Every baseline verdict was predictable from its docstring
- **Objection.** "You wrote the baseline, you predicted its verdicts in §9.3, and the run matched all of them. What was measured?"
- **Evidence.**
  - Verified: audit "Baseline vs §9.3": every row matches; C6 baseline `fail` ("reads change nothing") restates paper Observation 1 (a pure-function retrieval cannot satisfy C6, paper:226); C5 `absent` because no archived flag.
- **Severity.** Minor (it is a floor, and the report calls it one), serious only if it is shown as evidence about GEM.
- **Defuse.** Frame as "the floor, for contrast" in one sentence; spend interview time on the rows where the result was not predictable (C2(a), C4 cap, C5-2).
- **Ticket.** none needed; slide wording (34).

### B4. The reference GEM changes the baseline's role
- **Objection.** "Now you have three non-MemState systems. Which is the floor, which the ceiling, and why do I need the row?"
- **Evidence.**
  - Verified: ticket 38 item 6 (scorecard place: columns vs separate chain) and item 7 (which workloads run on the reference GEM) are open; spec is not yet revised (spec has five systems, no reference GEM; ticket 39 pending).
  - `[INFERENCE]`: the reference GEM's C4, C5, C6 pass by construction (ticket 37: "C5-2 passes by design"), so against the baseline it shows only that the conditions are implementable, not that implementing them is valuable; the baseline stays the only "what is lost without GEM" evidence, but B1 shows it is a weak one.
- **Severity.** Minor to serious (presentation).
- **Defuse.** Order the systems as a ladder on one table: last-write-wins row → versioned row (B1) → reference GEM → reference GEM + time → real MemState upstream → patch. Say which comparison answers which question.
- **Ticket.** 38 item 6, 39.

### B5. Baseline retrieval parameters differ from MemState's
- **Objection.** "Top-10 over a brute-force MiniLM scan versus MemState's top-8; the latency and reinforcement numbers are not comparable."
- **Evidence.** Verified: `demo/baseline.py` `TOP_K = 10`; `demo/triage.py` default `top_k` 8; F22: baseline query 0.5 s at 100 topics to 4.2 s at 2,000 (whole-store scan), baseline omitted from the latency table; deviations table row "Baseline retrieval settings" declares top-10. Baseline write validation copies MemState's rejection rules `[INFERENCE]` from reading the API code (`demo/baseline.py` docstring).
- **Severity.** Minor (declared).
- **Defuse.** Keep it declared; do not quote baseline latency.
- **Ticket.** none (already in deviations table, listed again under "already answered").

---

## Area S: the conformance suite

### S1. Circularity: the authors of the checks build the system that certifies them
- **Objection.** "You wrote the checks, then built a reference system to pass them, then told me it satisfies all six conditions. All you have shown is that you can write code that passes your tests."
- **Evidence.**
  - Verified: ADR 0007 Consequences: "The C3 and C2(c) checks need pass criteria strict enough to certify an implementation, not only to detect an absence, before the reference GEM is scored"; ticket 38 item 5: today the C3 check "passes on any change to B" and the C2(c) check "raises an error when it finds a policy surface" (also `checks/c2c_declarative_policies.py` docstring). So the certifying checks do not exist yet and will be written by the person building the system.
  - Verified: `verdict.py`: `pass` = every applicable case held; C3 has two cases (B→A, A→B); a `pass` is "no counterexample among n cases".
  - Verified: parameters the verdict depends on are chosen by the builder (ticket 38 item 3: λ, θ_archive, gate and β(n)). Paper:216 "policy-defined bound β": β(n) = n satisfies it. So C5 "passes by design" says nothing.
  - Verified: ticket 37 says C5/C6 follow "the paper's full wording … decay with disuse, archiving below a threshold", while ticket 38/out-of-scope says "decay with a single archive threshold", and paper:198, 323 describe a three-rung ladder (compress, hide, archive).
  - `[INFERENCE]`: the C3 flag check must read a flag field whose name the reference GEM defines (MemState's records have no such key, F7); a check shaped by the system under test is a fit, not a test.
- **Severity.** Serious (the most natural interview attack on the reference-GEM idea).
- **Defuse.** (1) Commit the stricter C3/C2(c) checks and the expected outcomes before writing the reference GEM (pre-registration, also answers C2). (2) **Mutation-test the checks**: build ≥ 1 deliberately broken variant of the reference GEM per condition (no propagation; flag on association edge; archived value returned; read does not bump; supersede by arrival; history dropped) and show each is caught. This is the standard answer to "can your checks fail". (3) Say "passes the suite's checks with these declared simplifications", never "satisfies all six". (4) Replace "full wording" by "wording with one archive threshold".
- **Ticket.** 37/38 preconditions; 39; *new* (mutant set, one per condition).

### S2. Verdict rules: counts, and rules invented after the result was seen
- **Objection.** "Partial means some cases held. Three of five sub-cases failing, including silent empty writes becoming current, and one of two holding gives the same 'partial' as a near-pass. And you wrote the rules after you saw the numbers."
- **Evidence.**
  - Verified, `demo/verdict.py:1-14,52-65`: `pass` all applicable cases, `partial` some, `fail` none; `not-scored` when every case is n/a; GLOSSARY "Fail: the system implements the capability … but behaves incorrectly".
  - Verified: F21 C4 upstream `partial` (update and archiving held; merge, `""`, `null`, cap broke); F18 C2(a) `fail` (20/20); the glossary's `fail` ("implemented but wrong") and the code's `fail` ("every case broke") differ.
  - Verified: ticket 35: C6-2 control-not-archived → `partial`, `not-scored` when no case applies, C2(b) outcome → `not-scored`, T5 → `absent`; each set during the build after upstream produced the situation (F17: C2(b) landed in the case the spec gave no verdict for).
- **Severity.** Serious for the method statement ("every verdict is read against the paper's claim"); minor for any single cell.
- **Defuse.** Publish the rules as a table before the run of record (pass/partial/fail defined by the count and by the severity of the broken case), mark the ticket-35 rules as post-hoc, and print `(k of n cases)` in every cell (the code already prints `(n case(s) n/a)`).
- **Ticket.** 35, 36; spec "Verdict model".

### S3. Is `absent` fair? It is a presentation choice written into the method
- **Objection.** "My paper says C3 holds by construction (§4 opening). If your run shows it does not, the claim is false. 'Absent' is a polite word for 'fail against the claim'."
- **Evidence.**
  - Verified: ADR 0002's rationale: scoring absent as fail "would fix the outcome before the run, inflate the fail count, and read to the paper's author as a gotcha rather than a map of open research" — an audience reason inside an evidence rule. Report:7 and §5 framing say §4's opening claims C3 "by construction" (ticket 25 resolution), and §4.3 does not list it.
  - Verified: C2(c) `absent` is established by `checks/c2c_declarative_policies.py`: searching OpenAPI paths, schema names and 15 guessed routes for whole words (policy, rule, constraint, invariant, trigger). It cannot see a policy surface that lives in code or config; it raises rather than scoring when it finds one (docstring).
  - Verified: C3 `absent` is established by "B unchanged within 15 s" (`checks/c3_propagation.py` `REVISION_WAIT_S`); F17 earlier used 5 s; the Reasoner interval is read from code only (`executor.py:345-350` per F7, `[INFERENCE]`).
- **Severity.** Serious (the interview is with the author of the claim).
- **Defuse.** Add a second column or marker, "claimed by [P1]? yes/no", so `absent` + "claimed" is displayed as "claimed but not delivered" (report §9.4 already says C3 "falls short of §4.2's flag-and-repair"); keep the count separate as ADR 0002 wants. For C2(c), say the probe is of the public API and the code-reading corollary (`Policies` is six numeric knobs) is `[INFERENCE]`.
- **Ticket.** 04 (resolved), ADR 0002; *new* (add the "claimed" marker).

### S4. Setup writes bias C2(a) and C4's merge case; ×20 is one deterministic scenario repeated
- **Objection.** "You retitled two topics through an editor endpoint so that the merge always drops the newer value, then report 20/20. That is an engineered state, and twenty repetitions of one deterministic scenario is n = 1."
- **Evidence.**
  - Verified: F18 and `demo/deviations.py:37-40`: the pair is arranged with a labelled setup `PATCH title`, so `dropped_held_newer` held 20/20 by construction; F9 on random ids gave stale-current 10/20 (8/20 on LadybugDB, F11). The merge keeps the lower id in 20/20 (F9), i.e. deterministic.
  - Verified: the paper's own duplicate (paper:67, Figure 1, "stored twice") carries the *same* value; two conflicting duplicates are what ingestion's host selection (Algorithm 1 line 4, paper:304) is meant to avoid by versioning, and `/v1 new_topic` bypasses that LLM step. "Acquisition perfect by construction" (report:669) is the reason the state exists at all.
  - Verified: report:731 still reports the 10/20 figure beside F18's 20/20; audit A5 notes stale wording remains in §9.2/§9.4/§9.5.
- **Severity.** Serious for the wording "violation rate 20/20"; minor for the existence claim (one reachable violating state refutes a universal "no revision produces…").
- **Defuse.** Report as existence ("a reachable state in which the merge returns the superseded value; the arrangement is two same-title writes with the older on the lower id, natural rate 10/20 on random ids"); drop "rate"; show that the arrangement is reachable without the editor (two `new_topic` writes in the right order, which F9 already does). Make report §9.2/§9.4/§9.5 consistent (audit A5).
- **Ticket.** 04 (build), 36; report edits (audit A5).

### S5. C5's construct: the check measures "something was archived", not `|D^active| ≤ β(n)`
- **Objection.** "My C5 says the active set is bounded by a bound the policy defines. Your check declares failure because nothing was archived at 2,000 topics. Where is the bound?"
- **Evidence.**
  - Verified: paper:216; `checks/c5_topic_ramp.py` docstring: C5-2 `fail` if "the system tracks archived and none were"; C5-1 has "no `fail` outcome" by construction; the count gate 500 (`FORGET_GATE`) and threshold 0.05 come from reading `Policies` ([INFERENCE] tags in `checks/c6_retrieval_adaptation.py` constants). The check never computes `|active|` against any β.
  - Verified: F22: 0 archived at n = 100 … 2,000.
  - `[INFERENCE]`: if upstream's declared `topic_count_soft_limit` (500) is read as β, 2,000 active topics exceed it, which is the right argument; the suite does not make it.
- **Severity.** Serious (the verdict is right but the stated reason is not the paper's wording).
- **Defuse.** State β explicitly: "MemState's declared soft limit is 500 topics; active count at n = 2,000 was 2,000 > 500; nothing falls under θ, so the forgetting pass cannot reduce it". Compute active vs declared limit in the C5-2 observation. Same for the reference GEM (S1: declare its β).
- **Ticket.** 08 (build); report §9.4 C5 row.

### S6. The C3 check cannot distinguish propagation from an unrelated edit, and the stricter version is system-specific
- **Objection.** "Your check passes if anything in B changes. Mine requires an entailed change; and your flag format is whatever your own system emits."
- **Evidence.** Verified: `checks/c3_propagation.py` docstring: "B 'reflects' the update when its title, summary, kind, archived flag or fields … changed … The check cannot judge a repair, only that B changed"; ticket 38 item 5 plans the association-edge control and the flag-because-of-edge criterion. Residual: the flag criterion needs a stored key; for MemState it is an `absent` probe (no key, F7), for the reference GEM it is the key the builder chose (S1).
- **Severity.** Minor once ticket 38 lands; serious until then.
- **Defuse.** Land the stricter check first, with a mutant "flags every linked topic regardless of edge kind" (S1).
- **Ticket.** 38 item 5.

### S7. LLM dependence, n and the chat runs
- **Objection.** "Everything runs through `/v1`, so the LLM never acquires anything. That is not how MemState is used. And your two chat runs are n = 1 with a 2B model."
- **Evidence.**
  - Verified: report:669 "On `/v1` the harness decides placement, so acquisition is perfect by construction"; chat runs are n = 1, hand-graded, `qwen3.5:2b` with thinking off through a proxy (deviations table; ADR 0003); the bad-merge run's arrangement is itself unspecified (audit F4) and would, with the F18 arrangement, give a *wrong* answer, not "an answer that looks right" (audit F4).
  - Verified: spec "Chat runs": n = 1 each, hand-graded.
- **Severity.** Minor to serious: declared limits, but the "answer looks right while state is violated" contrast (§1 item 14, report:671) rests on one case.
- **Defuse.** Call the chat runs illustrations; claim the three levels of evaluation from the state-level rows (C4/C5/C6) plus F20, not from the chat case. Fix the bad-merge arrangement so the answer is right and C4 is violated (survivor holds April 20, history loses March 15, report:671).
- **Ticket.** 17, 18; storyline review (11).

### S8. Repeats, determinism, timing
- **Objection.** "One run, laptop timings, a 15-second timeout as evidence of absence, 'no measurable difference' from one repeat."
- **Evidence.** Verified: F22 provisional, 1 repeat, 5 reads per ramp, one "no measurable difference" note printed at n = 2,000; audit F3/A8 (the note fires at 1 repeat) and A17 (C3 15 s wait and C6-1 not re-recorded); report:670 and spec story 43 say a single run is provisional with no such claim. Verified by re-run: 151 tests pass offline, so the logic is deterministic; the live numbers are not. Merge window median 0.083 s (F18).
- **Severity.** Minor (declared as provisional); serious if the latency table is quoted unqualified.
- **Defuse.** Run of record ×3, median/range, or quote none.
- **Ticket.** 19.

### S9. The contribution has no results yet
- **Objection.** "What have you measured of your own?"
- **Evidence.** Verified: map build state and audit "Still pending": patch steps 2 and 3, both chat runs, the dated merge case, the as-of timing, the reference GEM (both phases), ticket 11 storyline approval and the run of record are all unbuilt; report §9.8 is "results pending"; F19 shows only the upstream column.
- **Severity.** Serious as a schedule fact (not a design flaw).
- **Defuse.** Know exactly which numbers will exist by the interview and say "pending" for the rest; do not describe expected results as results (report:657 "designed to fix … without regressions").
- **Ticket.** 12-15, 17-19, reference-GEM build tickets (39).

### S10. Reinforcement precision is a constant of the configuration
- **Objection.** "1/8 is `1/top_k`. What did you learn?"
- **Evidence.** Verified: F20: 0.125 = Precision@8 with one labelled topic; ticket 37: the reference GEM "stays 1/8".
- **Severity.** Minor (the report already says no verdict, report:688, 673).
- **Defuse.** Present it as showing the gap between C6's wording (bump every accessed unit) and its motivation (reinforce useful ones, paper:73), not as a result about MemState.
- **Ticket.** 29 (resolved).

### S11. The scored storyline avoids the one place where answer level and state level diverge
- **Objection.** "Your storyline forbids duplicate titles, so the merge never happens there; the only contrast is one chat run."
- **Evidence.** Verified: `demo/storyline.py:35-36` (no re-explained duplicate "because a same-title topic would be merged and C2 tests that"); F20 15/15 on both; ticket 11 still open.
- **Severity.** Minor.
- **Defuse.** Say the claim "stored state catches what answers do not" is demonstrated by C4/C5/C6 rows plus the chat case, not by the storyline.
- **Ticket.** 11, 17.

---

## Area T: time probes and the Zep finding

### T1. The probes fail upstream by construction: upstream receives no dates, the patch receives oracle dates
- **Objection.** "You send upstream the writes with the dates stripped and ask it the same plain question on every date. Of course it answers with the last value. You do not test whether it orders by time; you test whether its API accepts a date."
- **Evidence.**
  - Verified: `demo/time_stories.py` docstring and `checks/time_probes.py` docstring: "Writes carry `valid_from` / `invalid_at` only for a system that accepts dates … the others get the same writes in the same order without dates", and every asked date is "the same plain read". Spec story 33: "so that the comparison isolates the time model".
  - Verified: dates reach the patch as structured API fields (`ingest_request`); the capability test is `{"valid_from","invalid_at"} ⊆ properties` in the OpenAPI schema (`demo/memstate_system.py:97-102`; audit F8), so which path a system takes depends on the names in its schema.
  - Verified: the controls ("recency expected") are right for upstream by definition (`Ask.recency`), so on upstream they cannot detect over-blocking (audit A10); over-blocking is only a patch risk.
  - Verified: T1's patch write invents a start for March 1 (Dec 1 of the previous year) that the story does not give (audit A16).
  - Consequence: any single-timestamp system (upstream, the baseline, the phase-1 reference GEM) fails T1-T4 and T6 whatever its logic. The scorecard cells say nothing about GEM's design intent, only about whether a dated API exists.
- **Severity.** Serious; fatal for "upstream gets the time cases wrong" if it is presented as a correctness failure.
- **Defuse.** (1) Say the time probes are *capability probes of C1′*, and show the answer on upstream when the story text (with the dates in words) goes through MemState's own chat/LLM path, so the LLM has a chance (n small, hand-graded, but it removes "you withheld the information"). (2) Separate two cells per probe: "accepts dates" and "orders correctly given dates" (the patch passes both, upstream fails the first). (3) Drop "wrong" for upstream and say "cannot express".
- **Ticket.** 27 (resolved) / 09 (build); *new*.

### T2. Inconsistent use of `fail` and `absent` for the same missing capability
- **Objection.** "ADR 0002 says a capability that does not exist is `absent`, not `fail`. Upstream has no valid-time capability, so T1-T4 and T6 should be `absent`, as T5 is."
- **Evidence.**
  - Verified: GLOSSARY "Fail: the system implements the capability the condition needs, but it behaves incorrectly"; "Absent: the system does not implement the capability, confirmed by a probe". F19: T1-T4, T6 `fail`, T5 `absent`, with the same probe evidence (`accepts_valid_time: false, accepts_recorded_at: false`).
  - If they become `absent`, the headline "a system built to all six conditions *fails* the time probes" (ticket 37) becomes "has no valid-time capability, which C1-C6 as worded do not require" — which is the professor's own defence (T3).
  - Verified: ticket 35 item 4 already proposes `absent` only when `recorded_at` is not accepted for T5; it does not touch T1-T4, T6.
- **Severity.** Serious (the verdict word carries the rhetoric).
- **Defuse.** Decide deliberately. Option A: keep `fail`, defined as "returns the superseded/invalid value as current on a dated story told in the system's own recording order" and say so in the glossary (departure from ADR 0002 stated); Option B: use `absent` and let the finding be "not required by the conditions as worded; required by C1′". The second is more honest and still supports the amendment case (C1/C2).
- **Ticket.** 35 (ratify), 27; ADR 0002.

### T3. Fairness to GEM, which never claimed bitemporality
- **Objection.** "My prototype stamps a time on each entry. I never claimed it handles retroactive statements or scoped overrides. Scoring it against probes of a capability I list as future work is unfair."
- **Evidence.**
  - Verified: paper:331 (§4.3): "A native engine would store field histories as first-class bitemporal attributes … These are not implementation gaps; they are research directions." Table 1 (paper:100, 105) puts versioned histories under Temporal DB and "Bi-temporal edges" under Zep as *substrate strengths*; paper:206 gives one timestamp; Figure 3(a) one Time column.
  - Verified, supports the plan: paper:373 success criterion (iii): "reductions in temporal-reasoning errors attributable to GEM-conformant memory", and paper:351 "the current value of each unit over time". The paper expects conformance to protect against temporal errors.
  - Verified: the scorecard's own claim column reads the time rows as "time probes under C1, read as C1′" (spec story 9), i.e. already not [P1]'s claim.
- **Severity.** Serious.
- **Defuse.** Put the time probes in their own section of the scorecard, "probes of the proposed C1′ — outside [P1]'s stated guarantees", and keep the "[P1]'s claim" rows (C1-C6 as claimed) in the main table. Cite success criterion (iii) as the paper's own mandate for caring.
- **Ticket.** 23/26; slides (34); report §9.8 layout.

### T4. "You implemented our future work, you did not find a gap"
- **Objection.** "§4.3 already calls for bitemporal attributes. You built that. Where is the gap?"
- **Evidence.**
  - Verified: report:542 "C1′ is the first step of the bitemporal field histories §4.3 already calls for"; report:661 "implementing the first step of the bitemporal attributes §4.3 calls for". The report concedes the premise.
  - Verified (by reading Graphiti at 6e3e3cb): Zep's own code does not cover T3, T4, T6 as the plan needs (T5 below). So "bitemporal attributes" taken literally from the paper (§4.3) and from Zep are *not* sufficient for the six probes: you also need a query-time bound with server-side current selection, interval layering, a future-dated policy, and a recording-axis read that survives corrections (keep-and-copy, ADR 0005).
  - Verified: ticket 37's claim is "the gap is in the conditions".
- **Severity.** Serious (this is the professor's most likely answer to the headline).
- **Defuse.** Concede the direction, claim the specification: "§4.3 says *store* bitemporal attributes; it does not say what a read returns. Storing four timestamps (Zep) still returns the wrong answer on T3, T4, T6 unless C1 is amended; we state the amendment and show it holds." This is also why T5's table matters. Do not say "found a gap in GEM"; say "found that the bitemporal direction needs a read semantics, and wrote one".
- **Ticket.** 37; slides; report §7.5 and §9.1.

### T5. Does plain Zep handle each probe? Mostly not as a server answer, and not T3/T4/T6 by design
- **Objection.** "Show me which of your six cases Zep itself passes. If Zep fails them, they are not Zep's cases and 'Zep's model fixes them' is false."
- **Evidence.** Zep paper (`docs/papers/2501.13956.md:63,89-91`, §3 context template) and Graphiti at commit 6e3e3cb (`graphiti_core/utils/maintenance/edge_operations.py`, `.../temporal_edge_utils.py`, `.../search/search_filters.py`, read-only). Code behaviour below is from reading, `[INFERENCE]` on end-to-end behaviour (Graphiti needs an LLM and a graph DB; not run).

  | probe | what Graphiti code does | plain Zep handles it? |
  |---|---|---|
  | T1 retroactive ("was March 1 before Jan 5") | If the LLM extracts `invalid_at` = Jan 5, `resolve_edge_contradictions` sees `edge.invalid_at ≤ resolved.valid_at` (or the reverse) and leaves both edges as dated ranges (`edge_operations.py:748-781`); the new edge, arriving with an end date, gets `expired_at = now` (`:726-728`). Both facts remain with ranges. | Data yes, if extraction and the contradiction LLM gate are right (paper:353: the gate "silently misses contradictions"); Zep hands the LLM a list of facts with ranges (paper §3 template) rather than choosing the current one. |
  | T2 out-of-order arrival | Code: a candidate that starts later ends the late-arriving edge at the candidate's `valid_at` (`:730-743`). Paper: "Following the transactional timeline T′, Graphiti consistently prioritizes new information" (paper:91). | Code yes, paper wording no; the report picks the code (report:695). |
  | T3 future-dated change | `normalize_future_temporal_bounds` sets `valid_at` to the reference time for facts matching a future-assertion pattern ("will", "scheduled to", "plans to"…) when the LLM-extracted `valid_at` is later (`temporal_edge_utils.py`, `apply_extracted_timestamps`). "From December you are on premium" has no such word, so its handling depends on phrasing `[INFERENCE]`. | By design Graphiti dates future-tense facts at the message time (report:701 names this and rejects it). Plain Zep fails T3 for "will"-phrased stories; phrasing-dependent otherwise. |
  | T4 lapsed override | New edge ($80, Oct 1-Nov 1) vs existing $50: `edge.valid_at < resolved.valid_at` → `edge.invalid_at = resolved.valid_at` (`:773-781`), closing $50 for good. | Fails: after Nov 1 no value is valid. The report says so (report:699). Layering is ours. |
  | T5 as-of | Four timestamps exist; search filters take `created_at`/`expired_at` (`search_filters.py:65`). But in-place edits of `invalid_at` (`:779-780`) lose the earlier belief state (ADR 0005). | Partly; "believed on" breaks after a correction. |
  | T6 future value, nothing before | As T3. | As T3. |

  So the cells that the plan will show passing on "adapted Zep" pass because of rules that are *ours*: a server-side current selector, layering, the T3 rule, keep-and-copy. Plain Zep passes none of the six as a server-chosen answer.
- **Severity.** Serious (it undermines "Zep's model fixes them").
- **Defuse.** Rename: "a bitemporal valid-time model of the kind Zep uses (four timestamps), with our rules"; add a "Zep as shipped" column by code reading with `[INFERENCE]` tags (T1, T2 data-wise; T3, T4, T6 no; T5 partly), clearly not a run. Cite Graphiti's future-tense rule as a documented design choice, not a bug.
- **Ticket.** 26 (resolved); report §9.5/§9.6 (a Zep column); slides.

### T6. Are the probes Zep's cases or ours?
- **Objection.** "Where in the Zep paper are these six stories? And StateMemBench's 'lapsed override' is about a reader, not a store."
- **Evidence.**
  - Verified: the Zep paper's only temporal examples are "I started my new job two weeks ago" and "next Thursday, in two weeks, last summer" (paper:63, 89) plus invalidation by a new edge (paper:91). T1-T4, T6 and the layering semantics are ours; report:717 calls T4 "modelled on StateMemBench's status-error mode ('a scoped override may lapse')" and T3 "its mirror image".
  - Verified: `docs/papers/2608.19652v1.md:167`: status errors occur "when a value changes … but a reader remains anchored on the earlier, louder commitment and thus answers with the superseded value". That is an answerer error with both values available; T4 is a store-level validity question.
- **Severity.** Minor to serious (a mis-citation can be caught in one line).
- **Defuse.** Say "ours, motivated by Zep's model and StateMemBench's taxonomy"; state the store-vs-reader difference once.
- **Ticket.** 27; report:717.

### T7. Is "adapted Zep" still Zep? And is the model new?
- **Objection.** "You changed six things and kept the field names. And slot-keyed fields remove the hard part of Zep, which is deciding what contradicts what."
- **Evidence.**
  - Verified: departures, report:695-702 and ticket 26: keep-and-copy (not edit-in-place), no LLM conflict judge (the field slot decides), server-chosen current value (Zep hands facts to the LLM), end-dated value stays current, override layering (beyond Zep), Graphiti's future-tense rule not adopted. What remains of Zep is four timestamp names and `t_ref`.
  - Verified: report §5.7 ("MemState's advantage, and its blind spot") already concedes that slots make supersession deterministic and that a mismatched slot defeats it.
  - Verified: paper:118 cites temporal databases; valid/transaction time is classical (bitemporal tables), so the model is not novel; report:692 attributes it to Zep.
  - Consequence: results say that an interval model works when conflicts are identified by a slot given to it; they say nothing about Zep in its own regime (free-text facts, LLM gate).
- **Severity.** Serious.
- **Defuse.** Call it "the standard bitemporal model, in the form Zep adopted for agent memory"; state the slot advantage as a scope limit ("conflict detection is solved by the field slot here; Zep's LLM gate is the open problem"); keep the contribution as "a read semantics (C1′) and its tests".
- **Ticket.** 26/25; report §9.5 intro.

### T8. Extraction noise: C1′ is measured only with correct dates
- **Objection.** "Your patch is right when you hand it correct dates. In use, a 2B model extracts them. Recency is robust to that; valid-time ordering is not. Where is the evidence that C1′ does not make things worse?"
- **Evidence.**
  - Verified: report:542 "extracting them from text ('two weeks ago') remains LLM-dependent"; ticket 27 Q5: one chat run, patch only, `qwen3.5:2b`, n = 1, hand-graded; the report's goal line says designed to fix cases "without regressions" (report:657).
  - Verified: Zep's own results: knowledge-update with gpt-4o-mini 76.9% full-context vs 74.4% Zep; the authors write "additional development may be needed to improve less capable models' understanding of Zep's temporal data" (`docs/papers/2501.13956.md`, §4.3.2 and Table 3). So a bitemporal layer does not improve every question type and depends on model strength.
  - `[INFERENCE]`: a mis-extracted `valid_from` in the future makes a current value invisible (T3 logic), so a wrong date can be worse than no date.
- **Severity.** Serious.
- **Defuse.** Add a small extraction set on the chat path (e.g. 15-20 dated utterances, with and without `reference_time`, 3 seeds, report recency vs valid-time errors) or state the claim as "given correct valid times" and the result as an upper bound.
- **Ticket.** 18, 14; *new*.

---

## Ranked top five (across areas)

1. **C2**: "precise reading" vs "gap in the conditions", with phase 1's outcome set by how `t` is read. Pre-register the reading, run phase 1 under both readings (the computed table shows valid-time `t` alone passes only T1, T2). This is the "you built it to fail" attack.
2. **T1 + T2**: the probes fail upstream by construction (no dates sent) and are scored `fail` where ADR 0002 says `absent`. Separate "accepts dates" from "orders correctly" and decide fail vs absent on purpose.
3. **T5 (+ T7, T4)**: "Zep's model fixes them" is not what the code says; Graphiti fails T3/T4/T6 by design and picks no current value. Reframe as "a read semantics for bitemporal fields", with a code-reading Zep column; answer "implemented your future work" with "§4.3 stores; it does not say what a read returns".
4. **B1**: the baseline is a dict, not the versioned database MAFBench asked for, so it cannot test "necessary but not sufficient". Add a versioned-row comparator or weaken the sentence.
5. **S1**: the reference GEM certified by checks the same authors wrote, with builder-chosen β, θ, λ. Pre-register the checks and mutation-test them (one mutant per condition), and say "passes the suite's checks, with declared simplifications".

Next in line: C1 (amendment, not reading), C4 (C1′ layering vs C2's "superseded"), T8 (extraction noise), S3 (`absent` is an audience choice), S4 (arranged merge, 20/20 is n = 1).

## Already answered in the repo (not counted above)

- "You built it to fail": ticket 37 names it and gives the line "built to the paper's definitions; its failure follows from C1's wording" (partly answered; C2 shows the line still depends on the reading).
- The tension between "precise reading" and "gap is in the conditions" is flagged in the brief; this list adds the decomposition and the dilemma.
- Keep-and-copy vs Graphiti's in-place edit: ADR 0005 and ticket 26, with verified citations (`edge_operations.py:779-780` and `:726-728`, `:730-743`, `:774-781`, all confirmed at 6e3e3cb).
- Zep orders by ingestion in the paper but by valid time in code: report:695 and ticket 26 supersession note.
- Layering is beyond Zep; departures from Zep listed with the condition each serves: report:695-702.
- C3 claimed by §4 opening but not §4.3: ticket 25 resolution, report §5 framing.
- Absent kept separate from fail: ADR 0002 (the rationale is the issue, S3).
- Setup-write arrangement for C2(a) and C4 merge: declared in `demo/deviations.py:37-40` and F18 (the wording of the rate is the issue, S4).
- MemState's slots avoid Zep's LLM contradiction gate but a mismatched slot defeats it: report §5.7 "MemState's advantage, and its blind spot".
- Extraction stays LLM-dependent: report:542 and §9.5 (the missing measurement is the issue, T8).
- Reinforcement precision = Precision@k, no verdict: report:673, :688, F20.
- Single-run latency is provisional: spec story 43, F22 note (the printed "no measurable difference" at 1 repeat is audit F3/A8).
- Reference GEM simplifications to be declared; stricter C3/C2(c) checks first: ticket 37 preconditions 1-2, ADR 0007 Consequences (the circularity of who writes the checks is S1).
- StateMem flags have a mixed effect, so C3′ is argued from correctness: report:545, ticket 25 (A5).
- C4′ conflicts with verifiable erasure: report:549 states the trade-off.
- Ratification of the build-time verdict rules: ticket 35 (open question; S2 asks for them to be published before the run of record).
- Everything in the two audits (audit F1-F21, A1-A19) is excluded, including: keep-and-copy on ordinary close, change-table granularity for C4, `current` on the patch's UI topic, "plain statement ends overrides" unmeasured, C2(b) verdict, T5 absent when `recorded_at` accepted, ramp note at 1 repeat.
