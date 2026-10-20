# Bitemporal history model and API

Type: grilling
Status: resolved

## Question

How do report §9.5's bitemporal rules map onto MemState's field-history storage and its `/v1` API?

- Where `t_valid` / `t_invalid` come from on `/v1/ingest` (a new request field, or reuse of today's `valid_from`), and what is assumed when a write gives none.
- How a scoped override ("$80 for October only") is stored, and how "the more specific one wins" is decided when several entries are valid at the query time.
- What `/v1/query` gains for as-of queries on the valid-time and system-time axes, and what the default query returns, so C1 and the 39 upstream tests do not regress.
- Whether the chat path's extraction resolves relative times against the message's reference time (`t_ref`) in the patch, or the "two weeks ago" example stays outside the patch.
- How merge-by-valid-time (commit 3) carries over [Merge history semantics for the patch](17-merge-history-semantics.md): interleave key, `merged-from:<id>` tag, skipping archived topics.
- The supersession rule is settled (insert by valid time; report §9.5, decided in [Reconcile report v2 with earlier decisions and the source audit](25-reconcile-report-v2-with-earlier-decisions.md)). Open: where the re-recorded entries live in MemState's history storage, and how `/v1` reads expose retired versus current entries.

## Comments

- 2026-10-20, Q3 accepted (corrections keep and copy): when a later write shortens an entry's validity, the old entry stays unchanged except for a `retired_at` mark (named `expired_at` in the Answer), and the corrected interval is appended as a new entry in the same field history. The copy keeps the original value's provenance and points to the entry it replaces and to the correcting write. Reason: GEM's append-not-overwrite rule for C4 (2605.26252 lines 214, 273, 321); editing in place, as Graphiti does (`edge_operations.py:779-780`, commit `6e3e3cb`), would lose what memory believed before and fail the as-of-query probe.

## Answer

Resolved 2026-10-20. Framing (user): Zep's time model is added to MemState while C1–C6 keep holding. Zep's behaviour is the default; every departure names the condition that requires it. Evidence: Zep paper (`docs/papers/2501.13956.md`), Graphiti `main` at `6e3e3cb` (2026-10-19), MemState at `945d7c4`, GEM (`docs/papers/2605.26252v1.md`, cited by line).

- **Entry model.** Each field-history entry gains Zep's four timestamps: `valid_from` (Zep `t_valid`; MemState's existing field, kept because upstream tests use it), `invalid_at` (`t_invalid`), `created_at` (`t′_created`), `expired_at` (`t′_expired`, in the paper's sense: when memory stopped holding the entry). Entries stay in the existing field history in `Topic.fields_json`.
- **Writes (Q2).** `FieldWrite` on `/v1/ingest` takes optional `valid_from` and `invalid_at` per field. Without dates, `valid_from` = `created_at` = write time and no end, so undated writes behave exactly as upstream (C1 and the 39 upstream tests unaffected).
- **Ordering.** A new entry is placed by `valid_from`; a late-arriving older value ends where the later one begins. This is Zep's behaviour in code (`edge_operations.py:730-743`).
- **Corrections keep and copy (Q3, R1; ADR 0005).** An entry whose validity changes is not edited: it gets `expired_at` = now, and a corrected copy is appended with the original provenance, `operation: "interval_corrected"`, `replaces_entry_id`, `corrected_by_entry_id`. Departure from Zep (in-place edit, `edge_operations.py:779-780`), required by C4 (GEM 214, 273). Copies count toward MemState's 500-entry cap.
- **Conflict detection.** Values in the same field compete; no LLM judge. Departure from Zep's LLM comparison, required by C1/C2 (GEM 353: an LLM gate "silently misses contradictions").
- **Values with an end date.** Stay current until their end. Departure from Graphiti, which expires them on arrival (`edge_operations.py:726-728`), required by C1.
- **Scoped overrides (Q4, B).** A write with `invalid_at` layers over the base value; when several values are valid at the asked time, the shorter validity wins; a plain new statement ends every value whose validity contains its `valid_from`, overrides included (C2; Graphiti's code agrees, `edge_operations.py:757-781`). Layering is the one rule beyond Zep (Zep would close the base for good, `:774-781`); it costs no condition. Hard-coded, named in the report as a stand-in for GEM's declarative policies (GEM 353).
- **Queries (Q5, Q5a).** Default `/v1/query` returns only the value valid now and not expired; history only on request (C1). Optional as-of dates on both axes ("true on X", "believed on X"), counted as history requests, raising salience like any read (C6). The server picks the current value (C1; Zep leaves it to the LLM). No value valid at the asked time: field listed with `current: null`.
- **C1 reading (A).** The report treats C1′ as the precise reading of C1 once values carry two times: Definition 4's `t` is valid time and "most recent" means most recent up to the asked time. Under it the patch keeps all six conditions; upstream fails C1 on the time probes because it records one time.
- **Chat reference time (Q6).** Optional `reference_time` on the chat request (default now): in the system prompt so relative dates resolve as with Zep's `t_ref`; default `valid_from` for `memory_append_field`; as-of time for that message's reads; stored in provenance. Graphiti's future-tense rule (`temporal_edge_utils.py`) is not adopted: it would make "will be premium from December" current on Nov 20.
- **Merge, commit 3 (Q7, R1).** Interleave both histories by valid time; dropped-topic entries keep their provenance and get `operation: "merged"`, `merged_from_topic_id`; entries whose validity changes are expired and copied; archived topics skipped; pairs recomputed after each merge; one "merged" event on the survivor. Dropped summary, topic events and salience remain lost (report limitation). Checked against Zep (duplicates resolved at ingestion, sources accumulated in `episodes`) and GEM (196, 214, 321).
- **Report fix (Q1).** Report §9.5 no longer says Zep orders by ingestion; it cites Graphiti's code and lists the three condition-driven departures plus the override rule. This supersedes in part the supersession item (A2) of [Reconcile report v2 with earlier decisions and the source audit](25-reconcile-report-v2-with-earlier-decisions.md).
- **Conformance suite (Q8, R2, Q5a test).** Handed to [Time probes and their controls](27-time-probes-and-controls.md) (comment there): dates through the patch's API, same events in the same order for upstream and baseline, plain-query tests with dates relative to run start, no fake clock; new cases "future value with no earlier value" and "plain statement during an override", plus the two-message "two weeks ago" chat case.

Applied with this resolution: report §1 item 13, §7.5 C1′, §9.5, §9.6; `GLOSSARY.md`; `docs/adr/0005-corrections-keep-and-copy.md`; journal entry.
