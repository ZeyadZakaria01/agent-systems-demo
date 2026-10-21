"""The "two weeks ago" chat run (spec stories 53, 54; ticket 18): relative time resolved against the request's date.

Two separate chat requests on a fresh step-3 server (patch step 3, ticket 15: the chat request's `reference_time`, ticket
14), through the system adapter. It runs on step 3 only because upstream's chat carries no date and its prompt contains
none (spec "Further Notes"). The story is told around Oct 20 and shifted so that its last day is the run day, as the
time-probe stories are (`demo.time_stories`, spec "Time-probe stories"):

1. `reference_time` Oct 6: "I started my new job two weeks ago". Ground truth: the start date Sep 22, +- 1 day.
2. `reference_time` Oct 20: "How long have I been at my new job?" in a request of its own. Ground truth: four weeks.

Nothing else is written by default: no `/v1` events, no seeded topic, no setup write. Each request is `provider: ollama`
with no `intent_override`, no `model`, no Groq and no judge: MemState's router decides each route. Two opt-in variants
exist because a 2B model rarely does what the case wants (F31): `first_intent_override="ingest"` forces request 1's
route (the router sent the statement to `query` in every take, whatever the model then did), and `seed=True` writes one
profile topic through `/v1` first. Both are deviations from the spec's design and are stated in the recording. A turn
records what it wrote
(entries that were not in the stored state before it) and its route; the first turn also reads the stored start date
out of those entries (the value text and `valid_from`), the second whether the answer says four weeks. Both are hints
printed beside the grades, never grades: the graders read the stored entries and the answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from demo.adapter import System
from demo.chat_recording import LEFT_UNSET, chat_provider, new_recording
from demo.time_stories import iso

CASE = "two-weeks"
CASE_TITLE = 'Two weeks ago on step 3: "I started my new job two weeks ago", then "How long have I been at my new job?"'
FIRST_MESSAGE = "I started my new job two weeks ago"
SECOND_MESSAGE = "How long have I been at my new job?"
ABILITY = "temporal reasoning"
FIRST_INTENT_OVERRIDE = "ingest"  # the opt-in variant that forces W1's route
TOLERANCE_DAYS = 1

STORY_YEAR = 2026
STORY_FIRST_DAY = date(STORY_YEAR, 10, 6)
STORY_RUN_DAY = date(STORY_YEAR, 10, 20)  # the day the story ends on; the run day replaces it
WEEKS_AGO = 2
FOUR_WEEKS_HINT = "the answer says four weeks (\"four weeks\", \"4 weeks\" or \"28 days\")"


@dataclass(frozen=True)
class Plan:
    """The story's three dates for one run day."""

    run_day: date
    first_day: date  # reference time of the first request: two weeks before the run day
    second_day: date  # reference time of the second request: the run day
    start_date: date  # when the job started: two weeks before the first request
    shift_days: int  # how far the story moved from its Oct 6 / Oct 20 telling


def plan(run_day: date) -> Plan:
    offset = run_day - STORY_RUN_DAY
    first = STORY_FIRST_DAY + offset
    return Plan(run_day=run_day, first_day=first, second_day=run_day, start_date=first - timedelta(weeks=WEEKS_AGO),
                shift_days=offset.days)


# -- reading dates out of what the model stored

MONTHS = {name: number for number, names in enumerate(
    (("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",), ("june", "jun"),
     ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"), ("october", "oct"), ("november", "nov"),
     ("december", "dec")), start=1) for name in names}
_MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"
_ORDINAL = r"(?:st|nd|rd|th)?"
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTH_FIRST = re.compile(rf"\b{_MONTH}\.?\s+(\d{{1,2}}){_ORDINAL}\b(?:,?\s+(\d{{4}})\b)?", re.IGNORECASE)
_DAY_FIRST = re.compile(rf"\b(\d{{1,2}}){_ORDINAL}\s+(?:of\s+)?{_MONTH}\b\.?(?:,?\s+(\d{{4}})\b)?", re.IGNORECASE)


def _day(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def dates_in_text(text: str, default_year: int) -> list[date]:
    """Calendar dates written in `text`, in the order they appear: `2026-09-22`, `Sep 22`, `September 22nd, 2025`,
    `22 September 2026`. A date with no year takes `default_year`; an impossible date (`May 32`) is skipped."""
    found: list[tuple[int, date]] = []
    for m in _ISO.finditer(text):
        d = _day(int(m[1]), int(m[2]), int(m[3]))
        if d:
            found.append((m.start(), d))
    for m in _MONTH_FIRST.finditer(text):
        d = _day(int(m[3]) if m[3] else default_year, MONTHS[m[1].casefold()], int(m[2]))
        if d:
            found.append((m.start(), d))
    for m in _DAY_FIRST.finditer(text):
        d = _day(int(m[3]) if m[3] else default_year, MONTHS[m[2].casefold()], int(m[1]))
        if d:
            found.append((m.start(), d))
    return [d for _, d in sorted(found)]


def states_four_weeks(answer: str) -> bool:
    """Does the answer say four weeks (4 weeks, four weeks, 28 days)? A hint printed beside the grade slot."""
    return re.search(r"\b(?:4|four)\s+weeks?\b|\b28\s+days?\b", answer, re.IGNORECASE) is not None


def _valid_from_day(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


# -- what a turn wrote

COMPARED_ENTRY_KEYS = ("value", "valid_from", "invalid_at", "provenance", "created_at", "why_changed")  # an entry is the same entry before and after a turn


def _entries(state: dict) -> dict[tuple, dict]:
    """Every history entry of every topic, keyed so that an entry is the same entry before and after a turn."""
    found: dict[tuple, dict] = {}
    for topic_id, topic in state["topics"].items():
        for name, slot in topic["fields"].items():
            for entry in slot.get("history") or []:
                key = (topic_id, name, *(repr(entry.get(k)) for k in COMPARED_ENTRY_KEYS))
                found[key] = {"topic_id": topic_id, "title": topic.get("title"), "field": name,
                              **{k: entry.get(k) for k in COMPARED_ENTRY_KEYS}}
    return found


def written_by(before: dict, after: dict) -> tuple[list[dict], list[dict]]:
    """(entries, topics) in `after` that `before` did not hold."""
    old = _entries(before)
    entries = [e for key, e in _entries(after).items() if key not in old]
    topics = [{"topic_id": tid, "title": t.get("title")} for tid, t in after["topics"].items() if tid not in before["topics"]]
    return entries, topics


def read_start_date(written: list[dict], truth: date, default_year: int) -> dict:
    """The start date as the turn's stored entries give it: dates in each value's text and each `valid_from`."""
    candidates = []
    for e in written:
        for d in dates_in_text(str(e["value"]), default_year):
            candidates.append({"source": "value", "topic_id": e["topic_id"], "field": e["field"], "date": d.isoformat(),
                               "from": e["value"]})
        vf = _valid_from_day(e.get("valid_from"))
        if vf:
            candidates.append({"source": "valid_from", "topic_id": e["topic_id"], "field": e["field"],
                               "date": vf.isoformat(), "from": e["valid_from"]})
    return {"truth": truth.isoformat(), "tolerance_days": TOLERANCE_DAYS, "candidates": candidates,
            "within_tolerance": any(abs((date.fromisoformat(c["date"]) - truth).days) <= TOLERANCE_DAYS for c in candidates)}


# -- the optional seed

SEED_TITLE, SEED_FIELD, SEED_VALUE = "Me", "job", "analyst at Acme"
SEED_VALID_FROM = date(2025, 1, 1)


def seed_request() -> dict:
    """The profile topic of a user who already has a job, so that "my new job" has a topic and a field to land in."""
    return {"placement": "new_topic", "title": SEED_TITLE, "topic_kind": "person", "summary": "The user's own profile",
            "fields": [{"name": SEED_FIELD, "value": SEED_VALUE, "valid_from": iso(SEED_VALID_FROM),
                        "provenance": "seed"}]}


def write_seed(system: System) -> dict:
    request = seed_request()
    return {"request": request, "topic_id": system.ingest(request)["topic_id"]}


# -- the turns


def left_unset(first_intent_override: str | None) -> list[str]:
    """What the run leaves to MemState's defaults, as the recording states it."""
    if first_intent_override is None:
        return list(LEFT_UNSET)
    return [f"`intent_override: {first_intent_override}` on W1 only (W2's route is the router's)", *LEFT_UNSET[1:]]


def take_turn(system: System, *, question: str, text: str, reference_day: date, ground_truth: str,
              graded_on: str, intent_override: str | None = None) -> dict:
    """One chat request; the turn keeps what the replay prints."""
    request = {"messages": [{"role": "user", "content": text}], "provider": chat_provider(), "reference_time": iso(reference_day)}
    if intent_override:
        request["intent_override"] = intent_override
    before = system.read_state()
    response = system.chat(request)
    after = system.read_state()
    entry = next(e for e in reversed(system.log.entries) if e["kind"] == "chat")
    written, created = written_by(before, after)
    return {"question": question, "ability": ABILITY, "text": text, "graded_on": graded_on,
            "reference_time": request["reference_time"], "ground_truth": ground_truth, "request": request,
            "answer": response.get("reply") or "",
            "route": {"intent": response.get("intent"), "intent_source": response.get("intent_source"),
                      "tool_calls": [t.get("tool") for t in response.get("tool_log") or []]},
            "latency_ms": entry["latency_ms"], "model": response.get("model"), "provider": response.get("provider"),
            "tool_log": response.get("tool_log") or [], "written": written, "topics_created": created}


def record_two_weeks(system: System, *, run_id: str, recorded_at: str, run_day: date, command: str = "",
                     ollama_base_url: str | None = None, snapshot: str | None = None,
                     extra: dict | None = None, first_intent_override: str | None = None, seed: bool = False) -> dict:
    """Ask the two questions, return the recording (a plain dict; `save_recording` writes it). Both routes are the
    router's unless `first_intent_override` forces the first request's (`FIRST_INTENT_OVERRIDE`). With `seed`, one
    profile topic is written through `/v1` first (`seed_request`), so the model has a topic to write the job into."""
    p = plan(run_day)
    seeded = write_seed(system) if seed else None
    first = take_turn(system, question="W1", text=FIRST_MESSAGE, reference_day=p.first_day, graded_on="the stored start date",
                      intent_override=first_intent_override,
                      ground_truth=f"{p.start_date.isoformat()} (two weeks before the reference time "
                                   f"{p.first_day.isoformat()}), +- {TOLERANCE_DAYS} day")
    first["stored_start_date"] = read_start_date(first["written"], p.start_date, p.first_day.year)
    second = take_turn(system, question="W2", text=SECOND_MESSAGE, reference_day=p.second_day, graded_on="the answer",
                       ground_truth="four weeks")
    second["answer_contains_ground_truth"] = states_four_weeks(second["answer"])
    second["hint_rule"] = FOUR_WEEKS_HINT
    turns = [first, second]
    return new_recording(
        system.describe(), case=CASE, title=CASE_TITLE, run_id=run_id, recorded_at=recorded_at, command=command,
        snapshot=snapshot, ollama_base_url=ollama_base_url, left_unset=left_unset(first_intent_override), turns=turns,
        extra=extra,
        state={"fresh_db": True, "seeded_topics": 1 if seeded else 0, "seed": seeded, "events_played": 0,
               "setup_writes": [], "first_intent_override": first_intent_override,
               "dates": {"run_day": p.run_day.isoformat(), "first_reference_time": p.first_day.isoformat(),
                         "second_reference_time": p.second_day.isoformat(), "start_date": p.start_date.isoformat(),
                         "shift_days": p.shift_days, "story_first_day": STORY_FIRST_DAY.isoformat(),
                         "story_run_day": STORY_RUN_DAY.isoformat()}})
