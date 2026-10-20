# Time probes and their controls

Type: grilling
Status: resolved
Blocked by: 26

## Question

How is each of report §9.6's five time probes (retroactive fact, out-of-order arrival, future-dated change, lapsed scoped override, as-of query) and its paired control encoded as `/v1` transitions, and how is it scored?

- The concrete events, timestamps and query times per probe, and whether they join the storyline workload.
- The verdict per probe (pass/fail per case, or the four-level scale) on each column, including the last-write-wins baseline.
- How the "two weeks ago" chat example is produced: which column, which model, recorded and replayed like the bad-merge chat run.

## Comments

- 2026-10-20, input from [Bitemporal history model and API](26-bitemporal-history-model-and-api.md) (resolved). T = run start; dates are relative to T.
  - **Time control:** the patch gets dates through its API (`valid_from`/`invalid_at` on writes, as-of dates on queries, chat `reference_time`). Upstream and the baseline get the same events in the same order with no clock control: their current value depends only on insertion order (`fields.py:77`, from code; the run confirms). Each probe has one plain-query test so the default "now" path is exercised. No fake system clock (libfaketime not installed and not needed).
  - **Future value with no earlier value:** `Tier: premium`, `valid_from` T+10d, the field's only entry. Probe: plain query at T gives `current: null` (patch) vs premium (upstream, baseline; expected fail). Controls: history at T lists premium from T+10d; as-of T+15d gives premium.
  - **Lapsed override:** $50 from T−65d; $80 from T−50d to T−20d. Probe: plain query at T gives $50 vs $80. Control: as-of T−35d gives $80.
  - **Plain statement during an override:** add $100 at T−40d. Plain query at T gives $100 in all columns (upstream only because it was written last). Control: as-of T−45d gives $80 (patch).
  - **As-of query:** deadline April 20 from Jan 5; later "moved to May 1 on Feb 1". Believed on Feb 10: April 20; true on Feb 10: May 1. Upstream cannot separate the two.
  - **"Two weeks ago" chat:** message at `reference_time` T0 "I started my new job two weeks ago"; message at T0+14d "how long have I been there?"; correct answer four weeks. Answer-level, hand-graded, n=1.
  - **Merge (commit 3):** the 20 repeated merges keep both values with `merged_from_topic_id` and original provenance; current value follows valid time; survivor has a "merged" event.

## Answer

Resolved 2026-10-20 (Q1–Q6 accepted). Facts from MemState `945d7c4` code: no endpoint accepts a date (`executor.py:122,156,196`; extra keys dropped); `/v1/query` has no as-of option and keeps only top-8 semantic matches unless `stages=["temporal"]` with `topic_ids` (`executor.py:252-265,297-299`); chat carries no date (`chat_api.py:41-52`).

- **Stories asked on several dates (Q1).** Each probe is a story with report §9.6's calendar dates, asked on its "today" and on at least one other date; the date every system should get right is the control (replaces separate control topics).

  | Probe | Told, in order | Asked → correct (upstream) |
  |---|---|---|
  | Retroactive fact | Jan 5 "deadline April 20"; Feb 15 "it was March 1 before Jan 5" | today Feb 15 → April 20 (March 1 ✗); Dec 20 → March 1 (March 1) |
  | Out-of-order arrival | "pro since Oct 1" arrives first; "basic since Aug 1" arrives after | today Oct 20 → pro (basic ✗); Sep 1 → basic (basic) |
  | Future-dated change | Jun 1 "basic"; Nov 20 "premium from December" | today Nov 20 → basic (premium ✗); Dec 5 → premium (premium ✓) |
  | Lapsed override | Sep 1 "$50"; Oct 1 "$80 for October only" | Oct 15 → $80 ($80 ✓); today Nov 5 → $50 ($80 ✗) |
  | Plain statement during override | as above, plus Oct 10 "now $100" | today Nov 5 → $100 ($100 ✓); Oct 5 → $80 ($100 ✗) |
  | Future value, nothing before | Nov 20 "premium from December", only value | today Nov 20 → no current value (premium ✗); Dec 5 → premium (premium ✓) |
  | As-of query | Jan 5 "deadline April 20"; Feb 15 "moved to May 1 on Feb 1" | true on Feb 10 → May 1; believed on Feb 10 → April 20 (upstream cannot ask) |

  The "today" question is a plain read (no date, server clock); the suite shifts each story so its today is the run day (report shows story dates). Other dates are as-of reads on the patch; upstream and the baseline get the same writes in the same order and answer every date with the same plain read. Reads use `/v1/query` with `stages=["temporal"]`, `topic_ids=[id]`; history checks add `explain=true`; snapshots from `GET /api/ui/topics/{id}`.
- **Separate from the storyline (Q2).** One topic per story, unique title, fresh DB per column; the storyline may narrate a story but the scored test stays separate. Answers the map's open "how the time probes sit in the storyline".
- **Recorded time (Q3).** Recorded time is the real clock, so "believed on Feb 10" is a real moment between the two writes (note time, wait 1 s, send the second write). Query options on the patch: `valid_at` (true on) and `recorded_at` (believed on).
- **Scoring (Q4).** Pass: every asked date right, and for the patch the history intact (no value lost; shortened values kept as expired entries with copies linked by `replaces_entry_id`, ADR 0005). Fail: any date wrong; labelled over-blocking when the control date fails. Absent: no way to ask about a date, confirmed by sending `valid_at` and seeing it ignored (upstream and baseline on the as-of probe).
- **"Two weeks ago" chat (Q5).** Patch only. Two separate chat requests, no shared conversation: dated Oct 6 "I started my new job two weeks ago"; dated Oct 20 "how long have I been there?". Patched `memory_append_field` takes an optional model-filled `valid_from` (Zep's extraction), with `reference_time` as fallback. Grades, n=1: stored start ≈ Sep 22 (±1 day), and the answer says four weeks (by hand). `qwen3.5:2b` via the think-off proxy; recorded to `demo/recordings/`, replayed like the bad-merge run. `scripts/run_memstate.sh` now exports `MEMSTATE_OLLAMA_MODEL=qwen3.5:2b` (journal 2026-10-20).
- **Merge (Q6).** The 20 undated runs stay unchanged for every column. One dated case on the patch: topic A "deadline April 20 since Jan 5"; duplicate B, written later, "March 15 since Dec 1"; after the merge, today → April 20, both values in history, B's tagged `merged_from_topic_id`.

Applied: report §9.6; `GLOSSARY.md` (Time probe, Over-blocking); `scripts/run_memstate.sh`; journal entry; map.
