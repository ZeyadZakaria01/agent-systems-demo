# 08: Topic ramp: C5 verdicts and latency ramps

**What to build:** One ramp generator of identical undated writes drives two things. The first is the two C5 rows: the forgetting mechanism, and the natural trajectory. The second is the latency ramps on upstream and on each patch step, so that upstream → step 1 shows the engine, step 1 → 2 Zep's model, and step 2 → 3 the merge change. Spec: user stories 26, 41, 43; Implementation Decisions "Workload", "Database freshness".

**Blocked by:** 01 (C1 tracer bullet), 03 (per-step runs)

**Status:** resolved

- [x] The workload's ramp generator produces identical undated writes and plain reads for every system.
- [x] C5 mechanism ramps past the 500-topic trigger with a field-less topic ingested at salience 0.01 and checks whether it is archived. The verdict is partial if only the count gate fires.
- [x] C5 natural trajectory counts the archived topics at each ramp step, with no setup.
- [x] The latency ramps run at 100 / 250 / 500 / 1,000 / 2,000 topics on upstream and each step, each on its own fresh DB. Each step logs the client latency of `/v1/query` and `/v1/ingest`, the Reasoner wait and the archived count.
- [x] A repeat flag runs each ramp 1× while building or 3× for the final run. The report gives the median and range and calls a difference inside the range "no measurable difference".
- [x] The suite's tests assert both C5 rows absent on the baseline.
- [x] Smoke run: one ramp each on upstream and step 1 prints both C5 rows and the latency table.

## Comments

Merged to `gem-suite` as `dea21ff`. Generator: `demo/ramp.py`. Checks: `demo/checks/c5_topic_ramp.py` (C5-1, C5-2). Latency table: `demo/latency_tables.py`. `--ramp-repeats` (default 1). Smoke F22: C5-1 **pass** on upstream and step 1 (0.01 canary archived at 501 topics); C5-2 **fail** (0 archived through 2,000); baseline both **absent**; step 1 vs upstream no change; LadybugDB ingest/query faster than Kuzu.

- 2026-10-21, spec revision (this ticket stays resolved): the "Reasoner wait" box no longer holds (the table prints a settle time, F11/F22); a ramp run once is labelled provisional and never prints "no measurable difference", and the ×3 run is "if time allows" (ticket 31); C5's verdict text states the declared bound beside the active count (ticket 22). The baseline's C5 rows are now the versioned row's (ticket 20).
