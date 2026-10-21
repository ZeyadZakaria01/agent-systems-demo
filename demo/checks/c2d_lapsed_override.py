"""C2(d), the superseded read on the lapsed-override story (spec story 66; "Stricter check pass criteria").

C2 reads "superseded" as "validity ended by a later statement": the value current today must not be one that a later
statement ended. The check runs the T4 stories (`demo/workloads/time_stories.py`, shifted so "today" is the run day, each in its
own fresh system) with the dates the system itself accepts (`describe()["accepts"]`: `valid_from` and `invalid_at` are
sent only when accepted; a system that accepts none gets the same writes undated), asks the plain "today" read, and
classifies the value current today:

- story 1 ($50 base, "$80 for October only", asked Nov 5): $50 or $80 holds. The override ended by its own date is
  ended, not superseded; returning it is a T4 error, not a C2 violation;
- story 2 (the same, then a plain "now $100" during the override): $100 holds; $80 or $50, both ended by the later
  statement, is a C2 violation (an observation `C2 violation`, the case broken); any other value, or none, also
  breaks the case but is not named a violation.

A lapsed override returning the base value is never a violation. A write the system rejects leaves the case n/a (there
is no read to classify; the T4 row counts it as over-blocking). The row never reads `absent`: it needs no date.
"""

from __future__ import annotations

from demo.checks import Ctx, check
from demo.systems.adapter import Rejected, System
from demo.systems.reads import NO_VALUE, current_value, field_in_response
from demo.verdict import Case, Verdict
from demo.workloads.time_stories import LAPSED_OVERRIDE_1, LAPSED_OVERRIDE_2, ingest_request, query_request, shift_story

CLAIM = (
    "C2 (transition soundness): no revision produces a state in which a superseded value is returned as "
    "current. Read on the lapsed-override story: the value current today is never one a later statement ended."
)

BASE, OVERRIDE, PLAIN = "$50", "$80", "$100"
_WRITE_DATES = ("valid_from", "invalid_at")


def _write_dates(system: System) -> frozenset[str]:
    return frozenset(d for d, accepted in system.dates_accepted(*_WRITE_DATES).items() if accepted)


def _today(ctx: Ctx, story, tag: str) -> tuple[dict, object]:
    """Write `story` and read the value current today. Returns the record for the evidence and the value (`None`
    marks a rejected write)."""
    shifted = shift_story(story, ctx.run_day)
    ask = next(a for a in shifted.asks if a.label == "today")
    with ctx.fresh_system(tag) as s:
        dates = _write_dates(s)
        record: dict = {"story": story.id, "write_dates": sorted(dates)}
        topic_id = None
        try:
            for i in range(len(shifted.writes)):
                response = s.ingest(ingest_request(shifted, i, topic_id, dates))
                topic_id = topic_id or response["topic_id"]
            request = query_request(ask, topic_id, send_valid=False)
            value = current_value(field_in_response(s.query(request), topic_id, shifted.field))
        except Rejected as e:
            record["rejected"] = str(e)
            return record, None
        record.update(request=request, current="NO_VALUE" if value is NO_VALUE else value)
        return record, value


@check(row="C2(d)", claim=CLAIM)
def c2d(ctx: Ctx) -> Verdict:
    cases, records, observations = [], [], []
    for story, accepted, violations, tag in (
        (LAPSED_OVERRIDE_1, {BASE, OVERRIDE}, set(), "story-1"),
        (LAPSED_OVERRIDE_2, {PLAIN}, {OVERRIDE, BASE}, "story-2"),
    ):
        record, value = _today(ctx, story, tag)
        records.append(record)
        name = f"story {tag[-1]}: the value current today is one of {sorted(accepted)}"
        if value is None:
            cases.append(Case(name, None, f"a write was {record['rejected']}; nothing to classify"))
            continue
        shown = "NO_VALUE" if value is NO_VALUE else value
        if value in accepted:
            cases.append(
                Case(name, True, f"current today={shown!r}; writes sent with {record['write_dates'] or 'no dates'}")
            )
            continue
        cases.append(
            Case(name, False, f"current today={shown!r}; writes sent with {record['write_dates'] or 'no dates'}")
        )
        if value in violations:
            observations.append(
                {
                    "name": "C2 violation",
                    "story": story.id,
                    "current": value,
                    "summary": f"{story.id}: {value} is current today although a later statement ended it",
                }
            )
    return Verdict.from_cases("C2(d)", cases, observations=observations, measurements={"stories": records})
