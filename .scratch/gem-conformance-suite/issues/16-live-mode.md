# 16: Live mode for the Graph Explorer

**What to build:** A live mode that drives a server already running, so that Prof. Mansour can watch field histories and salience change in MemState's Graph Explorer during the interview. Its output is labelled live and kept apart from the results of record. Spec: user stories 5, 6, 56; Implementation Decisions "Runner".

**Blocked by:** 01 (C1 tracer bullet)

**Status:** ready-for-agent

- [ ] Live mode takes a server URL. It never starts or stops a server, and uses one DB with distinct titles per check.
- [ ] Live verdicts are labelled live, written apart from recorded results, and never enter the scorecard of record.
- [ ] Smoke run: during a live run against a running upstream server, the Graph Explorer shows a field history growing and salience changing. A browser screenshot is captured as evidence, and the server is stopped afterwards.
- [ ] The README explains live mode.
