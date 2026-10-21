# 27: Reference GEM, phase 2 (phase 1 plus C1′)

**What to build:** Phase 2 adds C1′ to the reference GEM, with the same rules as the real patch (report §9.5, ADR 0005 as narrowed): end dates, recorded time, ordinary updates that store no end date, keep-and-copy only on a changed stored end or a retraction, scoped overrides, and as-of reads on both axes. Phase 1 → phase 2 isolates C1′ on a system that meets the conditions: expected [INFERENCE] to change exactly T4 and T5 (absent → pass) and no other row. Spec: user stories 59, 60; Implementation Decisions "Reference GEM", "Expected verdicts".

**Blocked by:** 26 (reference GEM phase 1)

**Status:** resolved

- [x] Phase 2 is a mode of the same adapter (one code path for what phases share). `describe()["accepts"]` is true for all four dates.
- [x] Entries carry `valid_from`, `invalid_at`, `created_at` and `expired_at`. An entry is valid until the next entry's `valid_from` unless it carries its own end; an ordinary update stores no end date and does not expire or copy; one undated update leaves exactly two entries.
- [x] Keep and copy runs only when a stored end date changes or a value is retracted (`operation: "interval_corrected"`, `replaces_entry_id`, `corrected_by_entry_id`, original provenance on the copy). Expired entries are hidden unless history is requested.
- [x] A scoped override layers over the base value; the shorter validity wins; a plain statement ends every value whose validity contains its start, overrides included.
- [x] `valid_at` and `recorded_at` reads work on both axes, count as history requests and raise salience; no value valid → `current: null`.
- [x] Merge: the current value is the later valid date; entries keep provenance and are tagged as on step 3.
- [x] Suite tests pin the phase 2 column of "Expected verdicts" and assert the chain phase 1 → phase 2 changes exactly T4 and T5 and no other row. A departure is logged in `docs/journal.md` and reported.

## Comments

2026-10-21: Built on `gs-27-ref-gem-p2`. Phase 2 is `ReferenceGem(phase=2)`, the same class (`_live`/`_resolve`/`_valid_entry`, `Entry.view(phase)`, `_describe`, `_corrected_copy`, `retract`, `_end_overrides_across`); the rules are ported from `patches/0002-bitemporal-field-histories.patch`. Tests: `tests/systems/test_reference_gem_phase2.py` (phase 2 column of "Expected verdicts", every row passes with no n/a case; the chain phase 1 → phase 2 changes exactly T4 and T5, absent → pass, and no case of any other row). No departure from the pre-registered column; build decisions are in `docs/journal.md`.

For tickets 29–31: register with `partial(ReferenceGem, phase=2)` (label "reference GEM (phase 2)"); mutant seams for 29 are the phase 1 ones plus `_resolve` (layering, shorter wins), `_corrected_copy`, `_live` (recorded axis) and `_end_overrides_across` (merge). A retraction has no adapter request, only `retract(topic_id, field, entry_id)` (not an interaction). A `valid_at`/`recorded_at` read returns the field history; phase 1's entry shape is unchanged.
