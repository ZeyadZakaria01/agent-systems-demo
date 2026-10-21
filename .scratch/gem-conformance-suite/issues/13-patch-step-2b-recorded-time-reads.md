# 13: Patch step 2b: recorded-time reads

**What to build:** The second axis of the as-of query. With `recorded_at`, `/v1/query` answers what memory believed at a past moment, using the entries' `created_at` and the expired entries that keep-and-copy preserved. The as-of probe flips from absent to pass on step 2. Because ordinary updates store no end date (ticket 12), "believed on Feb 10" returns April 20 from `created_at` alone; no expiry is involved. Spec: user stories 35, 36, 49, 77; Implementation Decisions "Patch, step 2" (queries), "Time-probe scoring".

**Blocked by:** 12 (dated field histories)

**Status:** resolved

- [x] `recorded_at` selects the value memory held at that time, counting entries that have since expired. It combines with `valid_at`, counts as a history request and raises salience like any read.
- [x] The server's OpenAPI schema declares `recorded_at` on the query model, so the suite's per-probe detection reads T5's needed dates (`valid_from`, `valid_at`, `recorded_at`) from it. T5 is absent only if `recorded_at` is not accepted; an accepted but wrong answer reads fail.
- [x] Developer tests cover `recorded_at` on its own and combined with `valid_at`, and show the hand-worked case [INFERENCE] that "believed on Feb 10" returns April 20 with no entry expired. Upstream's 39 tests pass unedited.
- [x] The work is amended into commit 2 and `patches/` is re-exported. The branch still has its commits in order.
- [x] Recorded run on step 2: the as-of probe passes ("true on Feb 10" → May 1, "believed on Feb 10" → April 20), the probes from ticket 12 still pass, and the as-of read raises salience (the C6 clause 1 case of ticket 22).

## Comments

2026-10-21: Built by amending commit 2 on `bitemporal` (now `1847882`, subject "…valid-time and recorded-time reads…"); `patches/0002-bitemporal-field-histories.patch` re-exported, `0001` unchanged; rebuilding from `patches/` (README's two commands, in a scratch worktree) gave a tree identical to `bitemporal`.
- Code: `datamodel/fields.py` (`believed_at`: entries with `created_at` <= moment and not expired by then, expired ones shown live; `current_entry(at, recorded_at)`), `core/models.py` (`QueryRequest.recorded_at`), `core/executor.py` (parse, reject non-dates, history request). `valid_at` defaults to now when only `recorded_at` is sent.
- Tests: 5 new in `tests/test_bitemporal_histories.py` (Feb 10 hand-worked case with no entry expired; combined with `valid_at`; entries that expired since still counted; salience; bad date; OpenAPI declares `recorded_at`). 62 passed with upstream's 39 unedited.
- Smoke (under `/tmp/gem-suite-live.lock`): `.venv/bin/python -m demo.run --systems step1,step2 --checks C1,T1,T2,T3,T4,T5,T6,C6-1 --results-root /tmp/t13-results` -> step 2: T5 pass (May 1 / April 20), T1-T4, T6, C1 pass, C6-1 as-of case held (0.500 -> 0.600). Recorded as F27.
- Departures: none. Note C6-1's as-of case sends `valid_at` when both dates are accepted, so the `recorded_at` salience path is covered by a developer test, not the live run. F26 still cites the old commit `7924760`.
