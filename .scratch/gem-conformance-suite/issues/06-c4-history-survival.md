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

Merged to `gem-suite` as `5cd5c71`. Check: `demo/checks/c4_history.py`. Smoke F21: upstream **partial** (update and archive hold; merge drops the dropped value; empty and null writes become current; 501 updates leave 500 entries, `v000` gone). Baseline **fail**.

- 2026-10-21, spec revision (this ticket stays resolved): C4's "survives archiving" case, which used an editor archive write, is replaced by "survives real forgetting", n/a on upstream (F24); the cap case counts archived overflow readable by id as holding; the verdict rests on the cases that could run (ticket 22). The cases are given stable ids so the change table can show "merge keeps history: broken → fixed" at step 3 (ticket 23).
- 2026-10-21: The baseline described here is the old last-write-wins row; ticket 20 (versioned row) supersedes it.