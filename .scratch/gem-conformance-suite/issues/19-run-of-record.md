# 19: Run of record

**What to build:** The evidence of record. One command runs the whole suite on all seven systems (upstream, steps 1–3, reference GEM phase 1 and 2, versioned row) on the final commits. It prints the scorecard and every table the presenter cites, records both chat runs on the approved storyline, copies the run into the tracked `demo/record/<run-id>/` and turns the new results into findings. Spec: user stories 1, 43, 57, 73–76; Testing Decisions "Smoke proof before done"; Implementation Decisions "Scorecard output", "Run of record"; Further Notes.

**Blocked by:** 05 (C2(b), C2(c), C3), 07 (C6), 11 (storyline approved), 15 (patch step 3), 16 (live mode), 18 (two-weeks chat run), 20 (versioned-row baseline), 21 (verdict rules), 22 (revised checks), 23 (case-level change table), 24 (stricter C3 and C2(c)), 25 (C4′ probe), 26 and 27 (reference GEM), 28 (over-flagging), 29 (mutation tests), 30 (reference GEM workloads), 31 (scorecard layout), 32 (run-of-record folder and upstream tests); the rest transitively

**Status:** ready-for-agent

- [ ] One recorded command runs every check, time probe, storyline question and ramp on upstream, steps 1–3, the reference GEM (both phases) and the versioned row. Ramps run 3× if time allows; otherwise once, and the output labels them provisional with no "no measurable difference" claim. Every server runs alone on a fresh absolute DB. The reference GEM runs no ramps and no chat.
- [ ] The output holds the scorecard in three groups with the *claimed by [P1]?* column, the probes section with two cells per probe, both change tables (the two chains, with case-level changes), the merge result as existence with the natural 10/20 beside it, the over-flagging measurement, both windows (seconds on MemState, interactions on the reference GEM), the storyline triage and reinforcement precision per system, the latency tables (provisional if under three repeats), MemState's limits with their numbers, the deviations table, and both chat cases (ticket 17 wires them in).
- [ ] Every `absent` carries its probe run, and no verdict rests on a setup write.
- [ ] The pre-registered expected verdicts (spec, "Expected verdicts") are compared with the measured ones; each departure is logged in `docs/journal.md` and reported, not rewritten.
- [ ] Both chat runs are recorded on the final commits with the approved storyline, and replay renders them with no server running.
- [ ] The run is copied to the tracked `demo/record/<run-id>/` (ticket 32), with the 39 upstream tests' counts per system.
- [ ] Each result that proves or disproves MemState behaviour is appended to `docs/findings.md` with its command, DB path and key output. Code-reading claims keep `[INFERENCE]`. The reference GEM's results are marked as results on our own system, "passes the suite's checks, with declared simplifications".
- [ ] The summary says "no regressions on the rows the suite checks" only if the change table shows no row worse at step 3 than at step 1.
- [ ] Difficulties met during the run are logged in `docs/journal.md`.
- [ ] `patches/` matches the final three commits and rebuilds `MemState-patched/`.
- [ ] The README covers the recorded, live and replay modes, `--patched` and `demo/record/` as built.
- [ ] Every MemState server, Ollama and the proxy are stopped at the end.
