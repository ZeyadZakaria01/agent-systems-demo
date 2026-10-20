# 01: Tracer bullet: C1 control scored on upstream and baseline

**What to build:** The first end-to-end path through the conformance suite. One command runs the C1 control on upstream MemState and on the baseline, then prints the scorecard row C1 under the columns [P1]'s claim | upstream (Kuzu) | bitemporal patch | baseline. Upstream runs on a fresh absolute database, started with the run script and stopped afterwards. The baseline runs in-process. The patch column stays empty until ticket 03. Every later check plugs into the system adapter built here. Spec: user stories 1–3, 10–12, 15–16, 18–19, 44–45, 55–56; Implementation Decisions "System adapter", "Reads used by checks", "Baseline", "Verdict model", "Database freshness", "Runner", "Scorecard output".

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] The system adapter offers `ingest`, `query`, `read_state` / `read_topic`, `setup_write`, `wait_until` and `describe`. A missing capability (salience, edges, as-of) comes back as an explicit nothing-value, never as an error.
- [x] The MemState adapter speaks `/v1/ingest`, `/v1/query` and the UI read endpoints. A missing topic reads as "deleted". It keeps every extra field the patch returns.
- [x] The baseline is a last-write-wins row keyed by (title, field). It accepts `""` and `null`, and a second `new_topic` with the same title upserts. It keeps no history, salience, archived flag, edges or dates. Its query uses MiniLM with top-k 10, and a read changes nothing.
- [x] The verdict model records pass / partial / fail / absent / not-scored, cases, observations, the probe evidence for an absent verdict, a snapshot reference and a control flag.
- [x] The C1 check stores `Deadline: March 15`, updates it to `April 20` through `version_field`, and confirms the default read returns only April 20 and a temporal read returns the full history. The row is marked as a control.
- [x] The recorded runner runs one server at a time on a fresh absolute DB per check per system and waits for `/health`. It stops the server when the check ends, including on error. It never opens `MemState/memstate.kuzu`.
- [x] Each verdict saves its requests and responses, the full state (every topic including archived ones, plus edges), timestamps, the DB path, the system label, the MemState commit and the engine line. Setup writes are labelled and kept apart from scored transitions.
- [x] Each run writes its own results directory with a machine-readable results file. The printed scorecard shows the claim column, each cell's verdict with its snapshot link, fails and absences counted separately, and the deviations table.
- [x] Each run prints the command, the DB path and the key output in a form that can be pasted into `docs/findings.md`.
- [x] The suite's pytest runs C1 in-process against the baseline and asserts pass. It needs no server, uses no MemState mocks or HTTP fixtures, and pins no MemState verdict.
- [x] Smoke run: a recorded run on upstream plus the baseline prints the C1 row with a verdict and snapshot link for each.
- [x] The README explains how to run the suite in recorded mode and no longer says that no demo code exists. "System adapter" is added to `GLOSSARY.md`.

## Comments

Merged as `fc5215b`; reviewed on both axes and fixed in `16f2bd5` (adapter split into `demo/adapter.py` + `demo/memstate_system.py`, echo tests removed). Smoke F13.
