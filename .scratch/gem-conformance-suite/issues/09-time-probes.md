# 09: Time probes and the story shift

**What to build:** The six time-probe rows. Each is a dated story, shifted so that its "today" falls on the run day, and asked on "today" plus at least one other date, one of which is the control. They are scored on upstream and the baseline now. The patch receives the dated writes and as-of reads, so steps 2 and 3 can flip the rows later. Spec: user stories 12 (control dates), 31–36; Implementation Decisions "Time-probe stories" (the table is the content), "Time-probe scoring"; report §9.6.

**Blocked by:** 01 (C1 tracer bullet)

**Status:** resolved

- [x] The seven stories of the spec's table are implemented as six rows. The lapsed-override row passes only if both of its stories pass.
- [x] The story shift maps "today" to the run day and keeps the story's gaps. A suite test checks this with a fixed run day.
- [x] "Today" is asked as a plain read with no date, and the other dates as as-of reads. Patch writes carry the shifted `valid_from` / `invalid_at`. Upstream and the baseline receive the same writes in the same order with no dates, and answer every asked date with the same plain read.
- [x] Each story runs on its own topic and its own fresh DB per system, apart from the storyline.
- [x] The as-of probe notes the time after the first write, waits 1 s, then sends the second write. "Believed on Feb 10" is asked with `recorded_at` at that noted moment.
- [x] Scoring: a probe passes only when every asked date is right and, on the patch, the history is intact (no value lost; shortened entries carry `expired_at` with a copy linked by `replaces_entry_id`). Any wrong date fails, with the observation "over-blocking" when the control date is wrong. The as-of probe is absent when the system returns the same answer to both questions after receiving `valid_at` / `recorded_at`.
- [x] The control date of each probe is flagged as a control.
- [x] The suite's tests assert, on the baseline, that the time probes fail with the wrong date observed and that the as-of probe is absent with identical answers.
- [x] Smoke run: a recorded upstream run prints all six rows. Any verdict that departs from the table's "upstream expected" column is logged in `docs/journal.md`.

## Comments

Merged as `e80bc58`; reviewed and fixed in `16f2bd5` (history read from `read_topic` and requires `expired_at`; control flag in the T5 absent evidence). Smoke F19; dated/recorded-time paths still unproven until tickets 12/13.
