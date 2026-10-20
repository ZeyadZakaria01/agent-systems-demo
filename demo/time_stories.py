"""The time-probe stories (spec "Time-probe stories"; report §9.6), the story shift and the request builders.

Everything here is pure: no system is touched. A `Story` is told with calendar dates (reference year 2026) around its
own "today". `shift_story(story, run_day)` moves every date by one offset so that "today" is the run day and the
gaps between dates stay (a run on Oct 20 stores the budget story's Nov 5 as Oct 20 and Sep 1 as Aug 16).

Asking: "today" is a plain read with no date (the server answers against its own clock, hence the shift); every other
date is an as-of read with `valid_at`. Writes carry `valid_from` / `invalid_at` only for the dates the system accepts
(`describe()["accepts"]`, per date), and `valid_at` reads are sent only to a system that accepts `valid_at`; a system
that accepts none of a probe's needed dates gets the same writes in the same order without dates. The as-of probe
(`AS_OF`) is different: it sends `valid_at` and `recorded_at` to every system, because ignoring them is what it observes.

`Ask.correct` is the right answer (`NO_VALUE` = the field has no current value). `Ask.recency` is the answer of a
system whose current value is the last one written (the table's "upstream expected" column, which the baseline
also gives); `Ask.control` marks the date every system should get right.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from demo.reads import NO_VALUE, read_request

PLAIN, VALID, RECORDED = "plain", "valid", "recorded"  # how a date is asked: plain read, `valid_at`, `recorded_at`
YEAR = 2026


def _d(month: int, day: int, year: int = YEAR) -> date:
    return date(year, month, day)


@dataclass(frozen=True)
class Write:
    value: str
    valid_from: date
    invalid_at: date | None = None


@dataclass(frozen=True)
class Ask:
    label: str
    axis: str  # PLAIN | VALID | RECORDED
    when: date | None  # the asked date; None for RECORDED (a real moment noted at run time)
    correct: Any
    recency: Any
    control: bool = False


@dataclass(frozen=True)
class Story:
    id: str
    row: str  # scorecard row the story feeds
    title: str
    field: str
    today: date
    writes: tuple[Write, ...]
    asks: tuple[Ask, ...]


def _today(story_today: date, correct: Any, recency: Any, control: bool = False) -> Ask:
    return Ask("today", PLAIN, story_today, correct, recency, control)


RETROACTIVE = Story(
    "retroactive", "T1", "Retroactive fact", "Deadline", _d(2, 15),
    writes=(Write("April 20", _d(1, 5)),
            # "it was March 1 before it moved on Jan 5": valid until Jan 5. The story gives no start; Dec 1 of the
            # previous year is the implementer's addition, needed to place the entry on the patch (before Dec 20).
            Write("March 1", _d(12, 1, YEAR - 1), invalid_at=_d(1, 5))),
    asks=(_today(_d(2, 15), "April 20", "March 1"),
          Ask("Dec 20", VALID, _d(12, 20, YEAR - 1), "March 1", "March 1", control=True)))

OUT_OF_ORDER = Story(
    "out-of-order", "T2", "Out-of-order arrival", "Tier", _d(10, 20),
    writes=(Write("pro", _d(10, 1)), Write("basic", _d(8, 1))),
    asks=(_today(_d(10, 20), "pro", "basic"),
          Ask("Sep 1", VALID, _d(9, 1), "basic", "basic", control=True)))

FUTURE_DATED = Story(
    "future-dated", "T3", "Future-dated change", "Tier", _d(11, 20),
    writes=(Write("basic", _d(6, 1)), Write("premium", _d(12, 1))),  # "from December"
    asks=(_today(_d(11, 20), "basic", "premium"),
          Ask("Dec 5", VALID, _d(12, 5), "premium", "premium", control=True)))

_BUDGET = (Write("$50", _d(9, 1)), Write("$80", _d(10, 1), invalid_at=_d(11, 1)))  # "$80 for October only"

LAPSED_OVERRIDE_1 = Story(
    "lapsed-override-1", "T4", "Lapsed scoped override", "Budget", _d(11, 5),
    writes=_BUDGET,
    asks=(Ask("Oct 15", VALID, _d(10, 15), "$80", "$80", control=True),
          _today(_d(11, 5), "$50", "$80")))

LAPSED_OVERRIDE_2 = Story(
    "lapsed-override-2", "T4", "Lapsed scoped override, plain statement during the override", "Budget", _d(11, 5),
    writes=_BUDGET + (Write("$100", _d(10, 10)),),  # "now $100"
    asks=(_today(_d(11, 5), "$100", "$100", control=True),
          Ask("Oct 15", VALID, _d(10, 15), "$100", "$100"),  # "a plain statement ends the override"
          Ask("Oct 5", VALID, _d(10, 5), "$80", "$100")))

FUTURE_ONLY = Story(
    "future-value", "T6", "Future value, nothing before", "Tier", _d(11, 20),
    writes=(Write("premium", _d(12, 1)),),
    asks=(_today(_d(11, 20), NO_VALUE, "premium"),
          Ask("Dec 5", VALID, _d(12, 5), "premium", "premium", control=True)))

AS_OF = Story(
    "as-of", "T5", "As-of query", "Deadline", _d(2, 15),
    writes=(Write("April 20", _d(1, 5)), Write("May 1", _d(2, 1))),  # "moved to May 1 on Feb 1", told Feb 15
    asks=(Ask("true on Feb 10", VALID, _d(2, 10), "May 1", "May 1", control=True),
          Ask("believed on Feb 10", RECORDED, None, "April 20", "May 1")))

STORIES = (RETROACTIVE, OUT_OF_ORDER, FUTURE_DATED, LAPSED_OVERRIDE_1, LAPSED_OVERRIDE_2, FUTURE_ONLY, AS_OF)


def shift_story(story: Story, run_day: date) -> Story:
    """Every date of `story` moved by one offset so that its "today" is `run_day`; gaps between dates are kept."""
    offset = run_day - story.today

    def move(d: date | None) -> date | None:
        return None if d is None else d + offset

    return replace(
        story, today=run_day,
        writes=tuple(replace(w, valid_from=move(w.valid_from), invalid_at=move(w.invalid_at)) for w in story.writes),
        asks=tuple(replace(a, when=move(a.when)) for a in story.asks))


def iso(day: date) -> str:
    """The day as a UTC midnight timestamp, the form dates take in patch requests."""
    return datetime.combine(day, time.min, tzinfo=timezone.utc).isoformat()


def ingest_request(story: Story, index: int, topic_id: str | None, write_dates: frozenset[str] = frozenset()) -> dict:
    """Write number `index` of the story: the topic is created by the first, versioned by the rest.
    Same value, order and provenance for every system; a date is added only if its name (`valid_from`,
    `invalid_at`) is in `write_dates`."""
    write = story.writes[index]
    field: dict[str, Any] = {"name": story.field, "value": write.value, "provenance": f"time-probe:{story.id}"}
    if "valid_from" in write_dates:
        field["valid_from"] = iso(write.valid_from)
    if "invalid_at" in write_dates and write.invalid_at is not None:
        field["invalid_at"] = iso(write.invalid_at)
    if index == 0:
        return {"placement": "new_topic", "title": f"Time probe: {story.title}", "topic_kind": "time-probe",
                "fields": [field]}
    return {"placement": "version_field", "topic_id": topic_id, "fields": [field]}


def query_request(ask: Ask, topic_id: str, *, send_valid: bool, send_recorded: bool = False,
                  recorded_at: str | None = None) -> dict:
    """The read for one asked date: a plain read for "today", and `valid_at` / `recorded_at` on the same read
    otherwise when the flag for that axis is set (otherwise the plain read, whatever the date)."""
    request = read_request(topic_id)
    if ask.axis == VALID and send_valid:
        request["valid_at"] = iso(ask.when)
    elif ask.axis == RECORDED and send_recorded:
        if recorded_at is None:
            raise ValueError("a recorded_at ask needs the noted moment")
        request["recorded_at"] = recorded_at
    return request


def history_intact(story: Story, field: dict | None) -> tuple[bool, str]:
    """The patch's history check against its entry model (spec, step 2), on the stored field: every entry has the
    `expired_at` key (None while live), no written value is lost, and every entry with `expired_at` set has a copy
    with the same value pointing back at it through `replaces_entry_id`."""
    history = (field or {}).get("history")
    if not history:
        return False, "no history returned"
    unshaped = [e.get("id") for e in history if "expired_at" not in e]
    if unshaped:
        return False, f"entries without an expired_at key (not patch-shaped): {unshaped}"
    kept = {e.get("value") for e in history}
    lost = [w.value for w in story.writes if w.value not in kept]
    ids = {e.get("id") for e in history}
    uncopied = [e.get("value") for e in history if e.get("expired_at")
                and not any(c.get("replaces_entry_id") == e.get("id") and c.get("value") == e.get("value")
                            for c in history)]
    dangling = [c.get("replaces_entry_id") for c in history
                if c.get("replaces_entry_id") and c["replaces_entry_id"] not in ids]
    problems = ([f"lost values {lost}"] if lost else []) + \
               ([f"expired entries without a linked copy: {uncopied}"] if uncopied else []) + \
               ([f"copies replacing unknown entries: {dangling}"] if dangling else [])
    if problems:
        return False, "; ".join(problems)
    return True, f"{len(history)} entries; every written value kept; {sum(1 for e in history if e.get('expired_at'))} expired, each copied"
