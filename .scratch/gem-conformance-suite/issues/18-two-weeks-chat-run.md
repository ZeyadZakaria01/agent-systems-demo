# 18: "Two weeks ago" chat run on step 3

**What to build:** One recorded Ollama chat run on step 3 showing relative time resolved against the request's date. "I started my new job two weeks ago" is sent on one day, and "how long have I been there?" two weeks later. It runs on step 3 only, because upstream's chat carries no date. Spec: user stories 53, 54; Implementation Decisions "Chat runs"; Further Notes.

**Blocked by:** 14 (chat `reference_time`), 15 (patch step 3), 17 (chat recorder and replay)

**Status:** resolved

- [x] The run makes two separate chat requests on a step-3 server: `reference_time` Oct 6 with "I started my new job two weeks ago", and `reference_time` Oct 20 with "how long have I been there?". The dates are shifted so that Oct 20 is the run day.
- [x] The recording holds the stored start date (ground truth Sep 22 ± 1 day, shifted) and the answer (ground truth: four weeks), each with an empty hand-grade slot.
- [x] Replay renders it with no server running.
- [x] MemState and Ollama are stopped when the run ends.

## Comments

2026-10-21: Built on `gs-18-two-weeks-chat`. `demo/chat_two_weeks.py` (scenario: date plan, two requests, what each turn wrote, start-date reading), recording fields and rendering in `demo/chat_recording.py`, `python -m demo.chat_run record two-weeks` (checks step 3 out in `MemState-patched` for the run through the step's own setup/teardown, then back on `bitemporal`), 34 tests in `tests/test_chat_two_weeks.py`, README "Chat runs and replay", a deviations row, F31, a journal entry.
- Run (live, under `/tmp/gem-suite-live.lock` and `server.lock`): the take of record is `demo/recordings/two-weeks-20261021-033752.json`; 12 other takes in `demo/recordings/attempts/`. Dates: the story is shifted so its last day is the run day, so the run on Oct 21 sent `reference_time` Oct 7 and Oct 21 and grades the start date against Sep 23 (± 1 day); the recording states the shift. Replay with nothing listening on 8765/11434/11435 prints both turns and the two empty grade slots. Each run stopped MemState, Ollama and the proxy (ports free, `MemState-patched` clean on `bitemporal`).
- Observed (F31): the router sends W1 to `query` in every router-decided take (9/9); one of 7 spec-faithful takes stored a start date, the right one (2026-09-23 in the value; `valid_from` is the reference time); no take answered "four weeks" (13/13), and W2 never read what W1 stored. The take of record is that one take, picked from 7 and disclosed; it shows a correct stored date and a failed answer, not a success. A `query`-routed turn executed write tools.
- Departures: the spec asks for no `intent_override`, and the case follows it. Because the router makes that rarely store anything, two opt-in variants exist (`--no-router-decides` forces W1 to `ingest`; `--seed-profile` writes one profile topic through `/v1`); their takes are attempts, not the case. The answer hint is a word match ("four weeks", "4 weeks", "28 days"); the start-date hint reads dates out of the value text and `valid_from`; neither is a grade.
- For ticket 19: the report can say, from one recording, that relative time resolves in the value only when the 2B model computes it (it did once), that the patch stores the reference time as `valid_from` (so "how long have I been there" has no start date to read unless the model passes `valid_from`), and that W2 failed on retrieval (it called no tool), not on the date. `results.json` carries `chat_cases` with this case; the scorecard prints it after the bad merge. The grade slots are empty: grading is the person's.
