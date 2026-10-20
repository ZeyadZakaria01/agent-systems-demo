# 17: Bad-merge chat run on upstream, and replay

**What to build:** One recorded Ollama chat run on upstream after a bad merge, showing an answer that looks right while the state violates C2 or C4. Also a replay mode that renders recordings with no server or GPU, so interview day does not depend on the laptop. The chat runs are MemState-only: the reference GEM has no LLM chat and gets none (ticket "Reference GEM design" item 8). Spec: user stories 7, 52, 54; Implementation Decisions "Chat runs"; ADR 0003.

**Blocked by:** 04 (merge check), 10 (storyline)

**Status:** resolved

- [x] The state is built through `/v1` up to a bad merge. Then 2–3 storyline questions are asked through MemState chat with Ollama `qwen3.5:2b` via the think-off proxy and provider `ollama`, with no `intent_override`, no Groq and no judge.
- [x] Each turn records the question, the ground truth, the answer, the route, the latency, the state violation present, and an empty hand-grade slot. The recording is saved under the demo's recordings.
- [x] Replay mode renders the recording with no server, Ollama or GPU in use, which is shown by replaying with every server stopped.
- [x] The recording is wired into `results.json` and `scorecard.md` as a chat case, so the run of record (ticket 19) prints it (suite audit F10).
- [x] MemState and Ollama are stopped when the run ends.
- [x] The README explains replay mode.

## Comments

- 2026-10-20, from the storyline review (ticket 11), decided by the user: the bad merge shows the "looks right" outcome (C4), not C2(a)'s stale-current outcome. The duplicate is the paper's re-explained Website Redesign (Figure 1, "stored twice"). The topic MemState keeps (lower id, F9) is the re-explanation holding Deadline = April 20. The topic it drops is the original Website Redesign, with its deadline history March 15 → April 20 and the "vendor delay" provenance. Fix the id order with the same labelled setup write C2(a) uses (`demo/merge.py`, retitle), and list it in the deviations table. Ask Q02 (deadline: should look right) plus questions on fields only the original held, and record per turn what the state lost. Report §9.2, "Answer-level contrast", states this.
- 2026-10-21, spec revision: the scored storyline stays duplicate-free (ticket 11); the duplicate exists only in this run. The merge result on the scorecard is reported as existence with the natural 10/20 beside it (ticket 22); this run is the answer-level contrast to it.
- 2026-10-21, built (branch `gs-17-bad-merge-chat`). `demo/chat_run.py` (scenario, recorder, replay CLI), `demo/chat_recording.py` (save/load/render, scorecard section; JSON only), `System.chat` on the adapter (`MemStateSystem` posts `/api/llm/chat`; a system without chat raises `NotImplementedError`), wiring in `demo/run.py` (`chat_cases` in `results.json`, "Chat cases" section in `scorecard.md`, newest recording per case from `demo/recordings/`), a deviations row, README "Chat runs and replay", finding F25, journal entry. Ticket 18 records into the same format: its turns add their own evidence key (the renderer prints only the keys a turn carries) and `System.chat` takes `reference_time` in the request body as the server defines it.
  - State: all 29 storyline events on the original; a re-explanation topic with `Deadline = April 20` only; ids arranged as C2(a) does (two placeholder topics, lower id = re-explanation, labelled setup `PATCH title` on both, field-less `extend_topic` as trigger). Questions Q02, Q06, Q11, one chat request each, provider `ollama`, no `intent_override`/model/Groq/judge.
  - Smoke: `flock /tmp/gem-suite-live.lock .venv/bin/python -m demo.chat_run record bad-merge` (3 takes; kept `demo/recordings/bad-merge-20261021-014605.json`, the others disclosed in the journal and `attempts/`). Merge 0.086 s after the trigger, survivor = re-explanation, original deleted; Deadline history `[April 20 (chat-reexplanation)]`, so "March 15" and the "vendor delay" entry are gone (C4 on Deadline); the answers to Q02/Q06/Q11 were right (4.6/4.9/5.1 s, route `query`). Replay with nothing listening on 8765/11434/11435: `.venv/bin/python -m demo.chat_run replay` prints all three turns. MemState, Ollama and the proxy were stopped by the run (ports free afterwards).
  - Departure from the comment: fields only the original held (`Team`, `Status`) are copied to the survivor by upstream's merge (F25), so Q06 and Q11 record no state violation; the contrast rests on Q02's field. The recording says so per turn.
  - n = 1 per take and the 2B model's answer varied across takes (journal); the kept take is the one showing "looks right".
