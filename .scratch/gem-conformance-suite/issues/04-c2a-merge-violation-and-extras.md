# 04: C2(a) merge violation rate, revision window and merge extras

**What to build:** The C2(a) superseded-value row, which reports how often the Reasoner's merge makes a superseded value current, plus the merge revision window. The merge extras are also run and recorded, so that MemState's "not what is permanently erased" promise is cited only after a run. Spec: user stories 20, 28, 29, 30 (merge window); report §9.4.

**Blocked by:** 01 (C1 tracer bullet)

**Status:** resolved

- [x] C2(a) creates two topics with the same title, where the one to be dropped holds the newer value. It triggers the Reasoner's merge through `/v1` only and checks which value is current. It repeats 20 times with random topic IDs and distinct titles, reports the violation rate, and gives a verdict on the scale.
- [x] Background effects are awaited by polling state with a timeout (`wait_until`). Each wait is logged apart from client latency.
- [x] The merge revision window (duplicate-creating ingest → merge visible) is reported as the median and range over the 20 repetitions.
- [x] The merge extras are run and recorded: three topics sharing one title; an active topic merged into an archived duplicate (archived by a labelled setup write); and whether the dropped topic is deleted, recorded as the observation "topic deleted on merge".
- [x] The suite's tests assert C2(a) value pass and a violation rate of 0/20 on the baseline.
- [x] Smoke run: a recorded upstream run prints the violation rate, the window and the extras, with snapshots.

## Comments

Merged as `5cd5c71`; reviewed and fixed in `467de6a` (dropped-holds-newer enforced, upserts counted apart, tests through the adapter with a generic stand-in). Smoke F18.

- 2026-10-21, spec revision (this ticket stays resolved): C2(a) is reported as existence, with the natural random-ID count (10/20, F9) beside it and not as a rate, and a lapsed-override read joins C2 as C2(d); both are ticket 22. The merge revision window is also measured in interactions on the reference GEM (ticket 30).
