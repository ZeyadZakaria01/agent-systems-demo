# Close the suite audit's design gaps before the patch tickets

Type: grilling
Status: resolved
Blocked by: —

## Question

The audits of `gem-suite` @ 467de6a ([vs. spec](../assets/suite-audit-vs-spec.md), [vs. report](../assets/suite-audit-vs-report.md)) found design questions that the spec and report §9.5 leave open. Build tickets 12, 15, 17 and 19 cannot be scored as the report describes until they are decided:

1. **Keep-and-copy on an ordinary close** (A2 / spec-audit F1). Does closing an open entry (setting `invalid_at`) expire and copy it? If it does, C1's exact history check and upstream's `history_count == 2` test break. If it does not, T5's "believed on Feb 10" loses the pre-close entry. Do default history views hide expired entries?
2. **Per-step change table granularity** (A1 / F2). C4 on upstream is `partial` from four cases. Step 3 fixes only the merge case, so the row-level table shows no change, while §9.5 says "the merge tests flip". Options: a case-level diff, splitting C4 into rows, or rewording §9.5.
3. **The stored current value on the patch** (A3 / F6). The adapter reads `current` from `/api/ui/topics/{id}` or falls back to `history[0]`. Must the patch expose `current`, or order history newest-first by valid time?
4. **"A plain statement ends overrides" is unmeasured** (A4). Add an Oct 15 → $100 ask to the lapsed-override probe's story 2.
5. **C4 "survives archiving" uses an editor write** (A7), while the spec says no verdict rests on a setup write. Options: archive through the forgetting transition (as C5-1 does), or accept the editor write and declare it as a deviation.
6. **Where the run of record lives** (A13, A14). `runs/results/` is git-ignored, but §9.2 and §9.8 promise snapshot links. The "39 upstream tests at every commit" claim has no run-of-record step.

The bad-merge chat run's arrangement (F4) is decided in the storyline review (build ticket "Review the storyline content").

## Answer

Resolved 2026-10-21 with the user. The answers were checked against the documents: the Zep paper `2501.13956.md:91`, Graphiti `edge_operations.py:779-780`, MemState's `docs/data-model/fields.html:37-55`, and GEM `2605.26252v1.md:273, 319`.

1. **Ordinary updates store no end date.**
   - **Rule.** An entry is valid until the next entry's `valid_from`, unless it carries its own end ("for October only"). This is MemState's own model: a stack of revisions where writes append and nothing is edited.
   - **Why it departs from Zep.** Zep stores `t_invalid` on the old fact, in place in Graphiti's code, because its facts are unordered edges. In a field slot the order already says what replaced what, the same reason ticket 26 dropped Zep's LLM judge.
   - **Keep-and-copy (ADR 0005)** applies only when a stored end date changes or a value is retracted.
   - **Expired entries** are hidden unless history is explicitly requested (`explain`, temporal stages, or a "true on" / "believed on" date), as MemState's docs state. In history reads they are shown with their `expired_at`.
   - **Effect.** One undated update leaves exactly two entries. That keeps the C1 check, and upstream's `test_field_history_tools.py:27-49` (`history_count == 2`) unedited. T5 "believed on Feb 10" still returns April 20 (hand-worked [INFERENCE]; the patch tests must show it).
   - **Rewording.** Report §9.5's "that entry's `invalid_at` = the new `valid_from`" changes in the spec revision; ADR 0005 is reworded now.
2. **Change table:** each row also lists the cases whose outcome changed between steps. Example: `C4: partial → partial` · *merge keeps history: broken → fixed*.
3. **Current value on the patch:**
   - The patch returns `current` on every field (`null` when nothing is valid), on `/v1/query` and on the UI topic read.
   - The adapter refuses the newest-entry fallback for any system that accepts dates, so a missing `current` raises an error instead of producing a silent wrong verdict.
4. **Lapsed-override story 2** gets an **Oct 15** ask, with correct answer $100 ("a plain statement ends the override"). Of the two rules, it is the only date where "shorter validity wins" would answer $80.
5. **C4 "history survives forgetting"** uses real forgetting only, never the editor archive write.
   - On upstream the case is **n/a**, because a topic with fields is never forgotten (F24, measured on `gem-suite`). F24 also becomes an observation on C5.
   - The reference GEM runs the case through its own decay.
6. **Run of record:**
   - It is copied into a tracked `runs/record/<run-id>/` (scorecard, `results.json`, snapshots; databases stay in `.runtime/`, with their paths cited).
   - The run-of-record command also runs MemState's 39 upstream tests at upstream and at each patch step, and records the counts.

All six land in "Revise the spec and build tickets for the reference GEM and the suite audit", affecting build tickets 12, 15, 06, 09, 03 and 19 and report §9.2, §9.5 and §9.8.
