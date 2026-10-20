# 03: Per-step runs and the change table

**What to build:** The runner measures each commit of the patch from the one branch. For every commit of `bitemporal` it checks the commit out in `MemState-patched/` and starts the `--patched` server. The scorecard gains the per-step change table, which shows which rows each step flipped. Step 1 → step 2 holds the engine constant. Spec: user stories 4, 13; Solution (the change table); Implementation Decisions "Patch packaging", "Runner", "Scorecard output".

**Blocked by:** 01 (C1 tracer bullet), 02 (patch step 1)

**Status:** resolved

- [x] The runner resolves the steps with `git -C MemState-patched rev-list --reverse 945d7c4..bitemporal` and checks out each one detached. It starts a `--patched` server per check on a fresh DB and returns to `bitemporal` when done, including on error. Until step 3 lands it measures the commits that exist; ticket 15 enforces exactly three.
- [x] `describe()` labels each step (step 1/2/3) with its commit hash.
- [x] The change table lists the upstream, step 1, step 2 and step 3 verdicts per row and marks the changed cells. Step 1 is compared with upstream verdict for verdict. Counts from random-ID tests are shown but not compared.
- [x] The scorecard's patch column shows the last step measured.
- [x] Smoke run: a recorded run of C1 on upstream, step 1 and the baseline prints the change table with no change for step 1, with the engine line of each server in its evidence.

## Comments

Merged as `48eda0d`; reviewed and fixed in `16f2bd5` (teardown returns to `bitemporal` whenever setup completed the checkout; step names derive from the registry). Smoke F16.
