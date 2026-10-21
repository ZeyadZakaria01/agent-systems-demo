# 16: Live mode for the Graph Explorer

**What to build:** A live mode that drives a server already running, so that Prof. Mansour can watch field histories and salience change in MemState's Graph Explorer during the interview. Its output is labelled live and kept apart from the results of record. Spec: user stories 5, 6, 56; Implementation Decisions "Runner".

**Blocked by:** 01 (C1 tracer bullet)

**Status:** resolved

- [x] Live mode takes a server URL. It never starts or stops a server, and uses one DB with distinct titles per check.
- [x] Live verdicts are labelled live, written apart from recorded results, and never enter the scorecard of record.
- [x] Smoke run: during a live run against a running upstream server, the Graph Explorer shows a field history growing and salience changing. A browser screenshot is captured as evidence, and the server is stopped afterwards.
- [x] The README explains live mode.

## Comments

Merged as `5cd5c71`; reviewed and fixed in `467de6a` (live runner shares the check skeleton). Smoke F14.
