# 19: Run of record

**What to build:** The evidence of record. One command runs the whole suite on all five systems (upstream, steps 1–3, baseline) on the final commits. It prints the scorecard and every table the presenter cites, records both chat runs on the approved storyline, and turns the new results into findings. Spec: user stories 1, 43, 57; Testing Decisions "Smoke proof before done"; Further Notes.

**Blocked by:** 05 (C2(b), C2(c), C3), 07 (C6), 11 (storyline approved), 16 (live mode), 18 (two-weeks chat run); the rest transitively

**Status:** ready-for-agent

- [ ] One recorded command runs every check, time probe, storyline question and ramp (3×) on upstream, steps 1–3 and the baseline. Every server runs alone on a fresh absolute DB.
- [ ] The output holds the scorecard (four columns, verdicts with snapshot links, fail and absent counts), the per-step change table, the merge violation rate per system, both staleness windows, the storyline triage and reinforcement precision per system, the latency tables with median and range, the deviations table and both chat cases.
- [ ] Every `absent` carries its probe run, and no verdict rests on a setup write.
- [ ] Both chat runs are recorded on the final commits with the approved storyline, and replay renders them with no server running.
- [ ] Each result that proves or disproves MemState behaviour is appended to `docs/findings.md` with its command, DB path and key output. Code-reading claims keep `[INFERENCE]`.
- [ ] Difficulties met during the run are logged in `docs/journal.md`.
- [ ] `patches/` matches the final three commits and rebuilds `MemState-patched/`.
- [ ] The README covers the recorded, live and replay modes and `--patched` as built.
- [ ] Every MemState server, Ollama and the proxy are stopped at the end.
