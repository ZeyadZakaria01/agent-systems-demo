# Corrections keep and copy field-history entries

An ordinary update stores no end date on the entry it replaces. An entry is valid until the next entry's `valid_from`, unless it carries its own end ("for October only"). This is MemState's existing model: "a stack of revisions… Writes append" (`MemState/docs/data-model/fields.html:53`).

When a later write changes an entry's **stored** end date, or retracts a value, the patched MemState does not edit the entry:
- it keeps the old entry and marks it `expired_at`;
- it appends a corrected copy (`operation: "interval_corrected"`, `replaces_entry_id`, `corrected_by_entry_id`) carrying the original provenance.

Graphiti, whose time model the patch adopts, does it differently:
- **It edits the old fact in place** (`graphiti_core/utils/maintenance/edge_operations.py:779-780`, commit `6e3e3cb`). That loses what memory believed before, so "what did memory believe on Feb 10?" returns nothing after a correction. It also breaks GEM's append-not-overwrite rule for C4 (2605.26252 lines 214, 273).
- **It stores an end on every invalidated fact** (`t_invalid`, `2501.13956.md:91`). Its facts are unordered edges. In a MemState field slot, the order already says which value replaced which, so storing the end again would add an entry per update and break upstream's own history-count test (`MemState/tests/test_field_history_tools.py:46`).

Expired entries are hidden unless history is explicitly requested. They count toward MemState's 500-entry history cap, whose truncation already breaks C4 upstream.

## Considered Options

- Edit in place, as Graphiti does: rejected for the reasons above.
- Keep and copy on every update, ordinary closes included: rejected. It stores three entries per update instead of two, breaks the C1 check and upstream's test, and gives the same answers as the chosen rule.
