"""The C4' provenance probe (report §7.5): does an entry's provenance resolve to a stored source message?

C4' extends C4 (provenance preserved) with a state component, the retained source. One write carries a source message
(`source_message` on the field write); the entry is read back and `resolve_source(entry)` must return that message.
- pass: the entry's provenance resolves to the message that was written;
- fail: the system accepts a source (`describe()["accepts_source"]`) and provenance does not resolve to it, or the
  write was rejected;
- absent: the system has no source store, confirmed by the schema probe (no request property and no endpoint for a
  source: `describe()["source_surface"]`); it is not sent a source message. A system that cannot say is refused.
The row sits in the probes section, outside [P1]'s claims; it is not a scorecard condition of the paper.
"""

from __future__ import annotations

from demo.adapter import Rejected
from demo.checks import Ctx, Row, check
from demo.verdict import Case, Verdict

SOURCE_MESSAGE = "Kickoff call, Mar 3: Dana said the deadline is March 15."
TITLE, FIELD, VALUE = "Provenance probe", "Deadline", "March 15"

ROWS = [Row("C4′", "Not claimed by [P1]: probe of the proposed C4' (C4 plus the retained source). An entry's "
                   "provenance resolves to the stored source message it was written with", probe=True)]


@check(rows=ROWS)
def c4_prime(ctx: Ctx) -> Verdict:
    s = ctx.system
    d = s.describe()
    if not s.source_accepted():
        return Verdict.absent("C4′", {
            "probe": "the schema: a source message among the properties of a write request, or a source endpoint "
                     "(describe()['accepts_source'], ['source_surface'])",
            "accepts_source": False, "source_surface": d["source_surface"], "accepts_error": d["accepts_error"],
            "writes_sent_with_source": False})
    name = "provenance resolves to the stored source message"
    try:
        topic_id = s.ingest({"placement": "new_topic", "title": TITLE, "summary": "source retention probe",
                             "fields": [{"name": FIELD, "value": VALUE, "provenance": "kickoff-notes",
                                         "source_message": SOURCE_MESSAGE}]})["topic_id"]
    except Rejected as e:
        return Verdict.from_cases("C4′", [Case(name, False, f"the write carrying a source message was {e}")])
    topic = s.read_topic(topic_id)
    entry = ((topic or {}).get("fields") or {}).get(FIELD, {}).get("current")
    if entry is None:
        return Verdict.from_cases("C4′", [Case(name, False, "the entry could not be read back after the write")])
    resolved = s.resolve_source(entry)
    return Verdict.from_cases("C4′", [Case(name, resolved == SOURCE_MESSAGE,
                                           f"wrote {VALUE!r} with source {SOURCE_MESSAGE!r}; "
                                           f"provenance resolved to {resolved!r}")])
