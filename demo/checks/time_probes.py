"""The six time-probe rows (report §9.6; story table in `demo/time_stories.py`), read as C1' (the value valid on a date).

Seven stories, each on its own topic in its own fresh system (`ctx.fresh_system`); the lapsed-override row is stories
4 and 5 together. Each probe has two cells, kept in the verdict: "accepts dates" (`measurements["accepts_dates"]`: yes,
no or partly, with the dates and the schema evidence beside it) and "answers correctly given dates" (the verdict).
The verdict uses pass / fail / absent only:
- pass: every asked date right and, on a system that keeps dated history, the history intact;
- fail: the needed dates are accepted and an asked date is wrong (or a write the system rejected), with the
  observation `"over-blocking"` when a control date is the wrong one (a legitimate update or date blocked);
- absent: a needed date is not accepted (`NEEDS`, per probe). The evidence is the schema reading
  (`describe()["accepts"]`) and the answers the system gave to the same writes and asks. A system is never called wrong
  for a date it cannot take (upstream reads absent on all six, F19). T5 on a system that accepts all three of its dates
  and answers the "true on" and "believed on" questions identically is `fail`, not absent.

A system receives the writes with the dates it accepts among the probe's needed ones, and `valid_at` reads if it
accepts `valid_at`; a system that accepts none of the needed dates gets the same writes undated and the same plain
read for every date. The as-of probe sends `valid_at` and `recorded_at` to every system (ignoring them is what it
observes). The flags that applied are in every row's `measurements`. Dated paths are proven by the patch smoke runs
(tickets 12/13), never by a MemState mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from demo.adapter import DATES, Rejected, System, utc_now
from demo.checks import Ctx, Row, check
from demo.reads import current_value, field_in_response
from demo.time_stories import (
    AS_OF,
    FUTURE_DATED,
    FUTURE_ONLY,
    LAPSED_OVERRIDE_1,
    LAPSED_OVERRIDE_2,
    OUT_OF_ORDER,
    RETROACTIVE,
    Ask,
    Story,
    history_intact,
    ingest_request,
    query_request,
    shift_story,
)
from demo.verdict import FAIL, PASS, Case, Verdict

AS_OF_GAP_S = 1.0  # between noting the moment after the first write and the second write

_C1 = "C1 read as C1': the value valid on the asked date is returned, not merely the last one written"
ROWS = [
    Row(
        "T1",
        f'{_C1}. Retroactive fact: "the deadline was March 1 before the change" arrives last; April 20 stays current',
        probe=True,
    ),
    Row(
        "T2",
        f"{_C1}. Out-of-order arrival: an older update is ingested after a newer one; the newer value stays current",
        probe=True,
    ),
    Row(
        "T3",
        f'{_C1}. Future-dated change: "from December you are on premium", asked Nov 20, still the old tier',
        probe=True,
    ),
    Row(
        "T4",
        f'{_C1}. Lapsed scoped override: $50, "$80 for October only", asked Nov 5 returns $50 (and a plain '
        "statement during the override still wins)",
        probe=True,
    ),
    Row(
        "T5",
        f'{_C1}. As-of query: both "what was true on Feb 10" and "what did memory believe on Feb 10" answerable',
        probe=True,
    ),
    Row(
        "T6",
        f'{_C1}. Future value, nothing before: "from December you are on premium" as the only value, asked Nov 20, '
        "no current value",
        probe=True,
    ),
]


NEEDS = {
    "T1": ("valid_from",),
    "T2": ("valid_from",),
    "T3": ("valid_from",),
    "T6": ("valid_from",),
    "T4": ("valid_from", "invalid_at"),
    "T5": ("valid_from", "valid_at", "recorded_at"),
}
_WRITE_DATES = ("valid_from", "invalid_at")


@dataclass(frozen=True)
class Caps:
    needed: tuple[str, ...]
    accepts: dict
    accepts_error: str | None
    keeps_history: bool

    @property
    def missing(self) -> list[str]:
        return [d for d in self.needed if not self.accepts[d]]

    @property
    def dated(self) -> bool:
        """At least one needed date is accepted; otherwise the writes go undated and every ask is a plain read."""
        return len(self.missing) < len(self.needed)

    @property
    def write_dates(self) -> frozenset[str]:
        return frozenset(d for d in _WRITE_DATES if self.dated and d in self.needed and self.accepts[d])

    @property
    def send_valid(self) -> bool:
        return self.dated and bool(self.accepts["valid_at"])

    @property
    def accepts_dates(self) -> str:
        return "yes" if not self.missing else "no" if not self.dated else "partly"

    def measurements(self) -> dict:
        return {
            "accepts_dates": self.accepts_dates,
            "dates_needed": ", ".join(self.needed),
            "dates_missing": ", ".join(self.missing) or "none",
        }

    def evidence(self) -> dict:
        return {
            "probe": "the schema's date fields (describe()['accepts']) against the dates this probe needs",
            "needed": list(self.needed),
            "accepts": dict(self.accepts),
            "missing": self.missing,
            "accepts_error": self.accepts_error,
        }


@dataclass
class Outcome:
    caps: Caps
    cases: list[Case] = field(default_factory=list)
    stories: dict = field(default_factory=dict)  # per story id: the writes' fate and every answer, for the evidence
    observations: list[dict] = field(default_factory=list)


def _capabilities(system: System, row: str) -> Caps:
    d = system.describe()
    needed = NEEDS[row]
    system.dates_accepted(*needed)  # refuses a system whose schema could not be read
    return Caps(needed, {k: d["accepts"][k] for k in DATES}, d["accepts_error"], bool(d["keeps_history"]))


def _answer(system: System, topic_id: str, name: str, request: dict) -> Any:
    return current_value(field_in_response(system.query(request), topic_id, name))


def _write_story(
    system: System, story: Story, write_dates: frozenset[str], pause_after_first: bool = False
) -> tuple[str | None, str | None]:
    """The story's writes in order. Returns (topic id, the moment noted after the first write). A rejected write
    raises `Rejected` to the caller."""
    topic_id, noted = None, None
    for i in range(len(story.writes)):
        response = system.ingest(ingest_request(story, i, topic_id, write_dates))
        topic_id = topic_id or response["topic_id"]
        if i == 0 and pause_after_first:
            noted = utc_now()
            time.sleep(AS_OF_GAP_S)
    return topic_id, noted


def _history_case(system: System, story: Story, topic_id: str) -> Case:
    """The patch's history-intact case, read from the stored topic's entries (`read_topic`), not from a query
    response, which need not carry `expired_at` or `replaces_entry_id`."""
    stored = ((system.read_topic(topic_id) or {}).get("fields") or {}).get(story.field)
    intact, why = history_intact(story, stored)
    return Case("history intact: no value lost, expired entries copied and linked", intact, why)


def _case_name(ask: Ask) -> str:
    """The case's name (and so its id) is the ask, whether or not the system took the story's writes."""
    when = f"{ask.when.isoformat()} " if ask.when else ""
    return f"{ask.label}: {when}-> {ask.correct!r}"


def _believed_on_observation(asks: tuple[Ask, ...], answers: list[dict]) -> dict:
    """A system that takes `recorded_at` but not `valid_at` cannot be scored on T5 (absent), but its answer to the
    "believed on" question is still a finding: recorded here beside the verdict, not scored."""
    ask, answer = next((a, r) for a, r in zip(asks, answers) if "recorded_at" in r["request"])
    got = f"rejected ({answer['rejected']})" if "rejected" in answer else repr(answer["answer"])
    return {
        "name": "believed-on half",
        "asked": ask.label,
        "answer": answer.get("answer"),
        "correct": ask.correct,
        "summary": f"the system takes recorded_at but not every date T5 needs (so T5 is absent); asked "
        f"{ask.label!r} it answered {got}, the correct answer is {ask.correct!r}",
    }


def _run_story(ctx: Ctx, story: Story, row: str, as_of: bool = False) -> Outcome:
    """One story in a fresh system. The as-of story sends `valid_at` and `recorded_at` on every ask, to every system."""
    shifted = shift_story(story, ctx.run_day)
    with ctx.fresh_system(story.id) as s:
        caps = _capabilities(s, row)
        out = Outcome(caps)
        record = out.stories[story.id] = {"write_dates": sorted(caps.write_dates), "asked": []}
        path = "dated path" if caps.dated else "plain path"
        try:
            topic_id, noted = _write_story(s, shifted, caps.write_dates, pause_after_first=as_of)
        except Rejected as e:
            record["write_rejected"] = str(e)
            out.cases = [
                Case(
                    _case_name(a),
                    False,
                    f"[{path}] a write was {e}; the legitimate update was blocked",
                    control=a.control,
                )
                for a in shifted.asks
            ]
            return out
        if as_of:
            record.update({"noted_moment_after_first_write": noted, "gap_s": AS_OF_GAP_S})
        answers = []
        for ask in shifted.asks:
            request = query_request(
                ask, topic_id, send_valid=as_of or caps.send_valid, send_recorded=as_of, recorded_at=noted
            )
            result = {"asked": ask.label, "control": ask.control, "request": request}
            try:
                result["answer"] = _answer(s, topic_id, shifted.field, request)
            except Rejected as e:
                result.update(rejected=str(e), answer=None)
            record["asked"].append(result)
            answers.append(result)
        if caps.missing:  # absent: the answers are the evidence, not cases
            if as_of and caps.accepts["recorded_at"]:  # the half the system can answer is an observation (spec "T5")
                out.observations.append(_believed_on_observation(shifted.asks, answers))
            return out
        for ask, r in zip(shifted.asks, answers):
            name = _case_name(ask)
            if "rejected" in r:
                out.cases.append(Case(name, False, f"[{path}] the read was {r['rejected']}", control=ask.control))
                continue
            how = (
                "recorded_at"
                if "recorded_at" in r["request"]
                else "valid_at"
                if "valid_at" in r["request"]
                else "plain read"
            )
            out.cases.append(
                Case(
                    name,
                    r["answer"] == ask.correct,
                    f"[{path}] asked {ask.label} ({how}): got {r['answer']!r}, correct {ask.correct!r}",
                    control=ask.control,
                )
            )
        if as_of and answers[0].get("answer") == answers[1].get("answer"):
            out.observations.append(
                {
                    "name": "identical answers",
                    "summary": 'the "true on" and "believed on" questions got the same answer '
                    "although the system accepts recorded_at",
                }
            )
        if caps.dated and caps.keeps_history:
            out.cases.append(_history_case(s, shifted, topic_id))
    return out


def _verdict(row: str, outcomes: list[Outcome], cases: list[Case] | None = None) -> Verdict:
    """The row's verdict from one or more stories (all in the same kind of system, so the same capabilities)."""
    caps = outcomes[0].caps
    stories = {k: v for o in outcomes for k, v in o.stories.items()}
    if caps.missing:
        return Verdict.absent(
            row,
            {**caps.evidence(), "stories": stories},
            measurements=caps.measurements(),
            observations=[o for out in outcomes for o in out.observations],
        )
    cases = cases if cases is not None else outcomes[0].cases
    v = Verdict(
        row=row,
        verdict=PASS if all(c.held for c in cases) else FAIL,
        cases=cases,
        measurements=caps.measurements(),
        observations=[o for out in outcomes for o in out.observations],
    )
    if any(c.control and not c.held for c in cases):
        v.observations.append(
            {"name": "over-blocking", "summary": "a control date failed: the system blocks reads it should answer"}
        )
    return v


def _prefixed(prefix: str, cases: list[Case]) -> list[Case]:
    return [Case(f"{prefix}: {c.name}", c.held, c.observation, c.control, f"{prefix}: {c.id}") for c in cases]


@check(rows=ROWS)
def time_probes(ctx: Ctx) -> list[Verdict]:
    t1, t2, t3 = (
        _run_story(ctx, st, row) for st, row in ((RETROACTIVE, "T1"), (OUT_OF_ORDER, "T2"), (FUTURE_DATED, "T3"))
    )
    t4a, t4b = _run_story(ctx, LAPSED_OVERRIDE_1, "T4"), _run_story(ctx, LAPSED_OVERRIDE_2, "T4")
    t5 = _run_story(ctx, AS_OF, "T5", as_of=True)
    t6 = _run_story(ctx, FUTURE_ONLY, "T6")
    return [
        _verdict("T1", [t1]),
        _verdict("T2", [t2]),
        _verdict("T3", [t3]),
        _verdict("T4", [t4a, t4b], _prefixed("story 1", t4a.cases) + _prefixed("story 2", t4b.cases)),
        _verdict("T5", [t5]),
        _verdict("T6", [t6]),
    ]
