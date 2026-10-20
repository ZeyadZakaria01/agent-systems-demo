# 06: C4 history survival, empty writes and the history cap

**What to build:** The C4 row. It checks that a field history survives an update, a merge and archiving with provenance intact, and that empty and null writes do not replace the current value. A run settles the 500-entry history cap. Spec: user stories 12 (update path as control), 24, 25; report §9.4.

**Blocked by:** 04 (reuses its merge trigger and wait)

**Status:** resolved

- [x] A field history survives a value update, a merge and archiving (archived by a labelled setup write), with provenance intact on every entry.
- [x] `version_field` is sent once with `""` and once with `null`. Rejection with April 20 still current holds the case; an empty current value breaks it.
- [x] The history-cap case makes 501 updates to one field, then records whether the first value is still in the history. This decides the `[INFERENCE]` that the cap drops the oldest entry.
- [x] The update path of C4 is marked as a control.
- [x] The suite's tests assert C4 fail on the baseline, with the lost earlier value and the empty value becoming current as observations.
- [x] Smoke run: a recorded upstream run prints the C4 row with every case and the cap result, with snapshots.

## Comments

Merged to `gem-suite` as `76082e6`. Check: `demo/checks/c4_history.py`. Smoke F21: upstream **partial** (update and archive hold; merge drops the dropped value; empty and null writes become current; 501 updates leave 500 entries, `v000` gone). Baseline **fail**.


[You have received this identical output 3 times. Re-reading '/home/zeyad/work/agent-systems-demo-wt/integration/.scratch/gem-conformance-suite/issues/06-c4-history-survival.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]