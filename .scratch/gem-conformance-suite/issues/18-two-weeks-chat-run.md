# 18: "Two weeks ago" chat run on step 3

**What to build:** One recorded Ollama chat run on step 3 showing relative time resolved against the request's date. "I started my new job two weeks ago" is sent on one day, and "how long have I been there?" two weeks later. It runs on step 3 only, because upstream's chat carries no date. Spec: user stories 53, 54; Implementation Decisions "Chat runs"; Further Notes.

**Blocked by:** 14 (chat `reference_time`), 15 (patch step 3), 17 (chat recorder and replay)

**Status:** ready-for-agent

- [ ] The run makes two separate chat requests on a step-3 server: `reference_time` Oct 6 with "I started my new job two weeks ago", and `reference_time` Oct 20 with "how long have I been there?". The dates are shifted so that Oct 20 is the run day.
- [ ] The recording holds the stored start date (ground truth Sep 22 ± 1 day, shifted) and the answer (ground truth: four weeks), each with an empty hand-grade slot.
- [ ] Replay renders it with no server running.
- [ ] MemState and Ollama are stopped when the run ends.
