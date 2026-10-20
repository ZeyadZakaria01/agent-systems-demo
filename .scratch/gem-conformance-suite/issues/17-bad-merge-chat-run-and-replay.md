# 17: Bad-merge chat run on upstream, and replay

**What to build:** One recorded Ollama chat run on upstream after a bad merge, showing an answer that looks right while the state violates C2 or C4. Also a replay mode that renders recordings with no server or GPU, so interview day does not depend on the laptop. The chat runs are MemState-only: the reference GEM has no LLM chat and gets none (ticket "Reference GEM design" item 8). Spec: user stories 7, 52, 54; Implementation Decisions "Chat runs"; ADR 0003.

**Blocked by:** 04 (merge check), 10 (storyline)

**Status:** ready-for-agent

- [ ] The state is built through `/v1` up to a bad merge. Then 2–3 storyline questions are asked through MemState chat with Ollama `qwen3.5:2b` via the think-off proxy and provider `ollama`, with no `intent_override`, no Groq and no judge.
- [ ] Each turn records the question, the ground truth, the answer, the route, the latency, the state violation present, and an empty hand-grade slot. The recording is saved under the demo's recordings.
- [ ] Replay mode renders the recording with no server, Ollama or GPU in use, which is shown by replaying with every server stopped.
- [ ] The recording is wired into `results.json` and `scorecard.md` as a chat case, so the run of record (ticket 19) prints it (suite audit F10).
- [ ] MemState and Ollama are stopped when the run ends.
- [ ] The README explains replay mode.

## Comments

- 2026-10-20, from the storyline review (ticket 11), decided by the user: the bad merge shows the "looks right" outcome (C4), not C2(a)'s stale-current outcome. The duplicate is the paper's re-explained Website Redesign (Figure 1, "stored twice"). The topic MemState keeps (lower id, F9) is the re-explanation holding Deadline = April 20. The topic it drops is the original Website Redesign, with its deadline history March 15 → April 20 and the "vendor delay" provenance. Fix the id order with the same labelled setup write C2(a) uses (`demo/merge.py`, retitle), and list it in the deviations table. Ask Q02 (deadline: should look right) plus questions on fields only the original held, and record per turn what the state lost. Report §9.2, "Answer-level contrast", states this.
- 2026-10-21, spec revision: the scored storyline stays duplicate-free (ticket 11); the duplicate exists only in this run. The merge result on the scorecard is reported as existence with the natural 10/20 beside it (ticket 22); this run is the answer-level contrast to it.
