# 06: C4 history survival, empty writes and the history cap

**What to build:** The C4 row. It checks that a field history survives an update, a merge and archiving with provenance intact, and that empty and null writes do not replace the current value. A run settles the 500-entry history cap. Spec: user stories 12 (update path as control), 24, 25; report §9.4.

**Blocked by:** 04 (reuses its merge trigger and wait)

**Status:** ready-for-agent

- [ ] A field history survives a value update, a merge and archiving (archived by a labelled setup write), with provenance intact on every entry.
- [ ] `version_field` is sent once with `""` and once with `null`. Rejection with April 20 still current holds the case; an empty current value breaks it.
- [ ] The history-cap case makes 501 updates to one field, then records whether the first value is still in the history. This decides the `[INFERENCE]` that the cap drops the oldest entry.
- [ ] The update path of C4 is marked as a control.
- [ ] The suite's tests assert C4 fail on the baseline, with the lost earlier value and the empty value becoming current as observations.
- [ ] Smoke run: a recorded upstream run prints the C4 row with every case and the cap result, with snapshots.
