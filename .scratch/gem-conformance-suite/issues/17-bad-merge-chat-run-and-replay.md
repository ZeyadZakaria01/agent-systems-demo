# 17: Bad-merge chat run on upstream, and replay

**What to build:** One recorded Ollama chat run on upstream after a bad merge, showing an answer that looks right while the state violates C2 or C4. Also a replay mode that renders recordings with no server or GPU, so interview day does not depend on the laptop. Spec: user stories 7, 52, 54; Implementation Decisions "Chat runs"; ADR 0003.

**Blocked by:** 04 (merge check), 10 (storyline)

**Status:** ready-for-agent

- [ ] The state is built through `/v1` up to a bad merge. Then 2–3 storyline questions are asked through MemState chat with Ollama `qwen3.5:2b` via the think-off proxy and provider `ollama`, with no `intent_override`, no Groq and no judge.
- [ ] Each turn records the question, the ground truth, the answer, the route, the latency, the state violation present, and an empty hand-grade slot. The recording is saved under the demo's recordings.
- [ ] Replay mode renders the recording with no server, Ollama or GPU in use, which is shown by replaying with every server stopped.
- [ ] MemState and Ollama are stopped when the run ends.
- [ ] The README explains replay mode.
