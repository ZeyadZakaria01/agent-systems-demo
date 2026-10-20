"""The six time-probe rows (report §9.6; story table in `demo/time_stories.py`), read as C1' (the value valid on a date).

Seven stories, each on its own topic in its own fresh system (`ctx.fresh_system`); the lapsed-override row is stories
4 and 5 together. Time probes use pass / fail / absent only:
- pass: every asked date right and, on a system that keeps dated history, the history intact;
- fail: any date wrong (or a write the system rejected), with the observation `"over-blocking"` when a control date is
  the wrong one (a legitimate update or date blocked);
- absent (as-of probe only): the system answered "true on Feb 10" and "believed on Feb 10" identically after
  receiving `valid_at` / `recorded_at`; the probe evidence is both requests and answers.

A system receives dated writes and `valid_at` reads only if `describe()["accepts_valid_time"]` (the patch); the others
get the same writes in the same order and the plain read for every date. The flags that applied are in every row's
`measurements`. The as-of probe sends its dates to every system: ignoring
them is what it observes. Dated paths are proven by the patch smoke runs (tickets 12/13), never by a MemState mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from demo.checks import Ctx, Row, check
from demo.adapter import Rejected, System, utc_now
from demo.reads import current_value, field_in_response
from demo.time_stories import (AS_OF, FUTURE_DATED, FUTURE_ONLY, LAPSED_OVERRIDE_1, LAPSED_OVERRIDE_2, OUT_OF_ORDER,
                               RETROACTIVE, Story, history_intact, ingest_request, query_request, shift_story)
from demo.verdict import FAIL, PASS, Case, Verdict

AS_OF_GAP_S = 1.0  # between noting the moment after the first write and the second write

_C1 = "C1 read as C1': the value valid on the asked date is returned, not merely the last one written"
ROWS = [
    Row("T1", f"{_C1}. Retroactive fact: \"the deadline was March 1 before the change\" arrives last; April 20 stays current"),
    Row("T2", f"{_C1}. Out-of-order arrival: an older update is ingested after a newer one; the newer value stays current"),
    Row("T3", f"{_C1}. Future-dated change: \"from December you are on premium\", asked Nov 20, still the old tier"),
    Row("T4", f"{_C1}. Lapsed scoped override: $50, \"$80 for October only\", asked Nov 5 returns $50 (and a plain "
              "statement during the override still wins)"),
    Row("T5", f"{_C1}. As-of query: both \"what was true on Feb 10\" and \"what did memory believe on Feb 10\" answerable"),
    Row("T6", f"{_C1}. Future value, nothing before: \"from December you are on premium\" as the only value, asked Nov 20, "
              "no current value"),
]


@dataclass(frozen=True)
class Caps:
    valid_time: bool  # dated writes and `valid_at` reads
    recorded_at: bool
    keeps_history: bool

    def measurements(self) -> dict:
        return {"accepts_valid_time": self.valid_time, "accepts_recorded_at": self.recorded_at}


@dataclass
class Outcome:
    caps: Caps
    cases: list[Case] = field(default_factory=list)


def _capabilities(system: System) -> Caps:
    d = system.describe()
    if d["accepts_valid_time"] is None or d["accepts_recorded_at"] is None:
        raise RuntimeError(f"{system.label}: could not tell which dates the system accepts ({d['accepts_error']}); "
                           "refusing to guess")
    return Caps(bool(d["accepts_valid_time"]), bool(d["accepts_recorded_at"]), bool(d["keeps_history"]))


def _answer(system: System, topic_id: str, name: str, request: dict) -> Any:
    return current_value(field_in_response(system.query(request), topic_id, name))


def _write_story(system: System, story: Story, dated: bool, pause_after_first: bool = False
                 ) -> tuple[str | None, str | None]:
    """The story's writes in order. Returns (topic id, the moment noted after the first write). A rejected write
    raises `Rejected` to the caller."""
    topic_id, noted = None, None
    for i in range(len(story.writes)):
        response = system.ingest(ingest_request(story, i, topic_id, dated))
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


def _run_story(ctx: Ctx, story: Story) -> Outcome:
    shifted = shift_story(story, ctx.run_day)
    with ctx.fresh_system(story.id) as s:
        caps = _capabilities(s)
        out = Outcome(caps)
        path = "dated path" if caps.valid_time else "plain path"
        try:
            topic_id, _ = _write_story(s, shifted, caps.valid_time)
        except Rejected as e:
            out.cases = [Case(f"{a.label}: {story.title}", False,
                              f"[{path}] a write was {e}; the legitimate update was blocked", control=a.control)
                         for a in shifted.asks]
            return out
        for ask in shifted.asks:
            name = f"{ask.label}: {ask.when.isoformat()} -> {ask.correct!r}"
            request = query_request(ask, topic_id, send_valid=caps.valid_time)
            how = "valid_at" if "valid_at" in request else "plain read"
            try:
                got = _answer(s, topic_id, shifted.field, request)
            except Rejected as e:
                out.cases.append(Case(name, False, f"[{path}] the read was {e}", control=ask.control))
                continue
            out.cases.append(Case(name, got == ask.correct,
                                  f"[{path}] asked {ask.label} ({ask.when.isoformat()}, {how}): got {got!r}, "
                                  f"correct {ask.correct!r}", control=ask.control))
        if caps.valid_time and caps.keeps_history:
            out.cases.append(_history_case(s, shifted, topic_id))
    return out


def _verdict(row: str, cases: list[Case], caps: Caps) -> Verdict:
    v = Verdict(row=row, verdict=PASS if all(c.held for c in cases) else FAIL, cases=cases,
                measurements=caps.measurements())
    if any(c.control and not c.held for c in cases):
        v.observations.append({"name": "over-blocking",
                               "summary": "a control date failed: the system blocks reads it should answer"})
    return v


def _prefixed(prefix: str, cases: list[Case]) -> list[Case]:
    return [Case(f"{prefix}: {c.name}", c.held, c.observation, c.control) for c in cases]


def _as_of(ctx: Ctx) -> Verdict:
    """Both dates are sent to every system (ignoring them is what the probe observes). Absent when the two answers
    are identical, which also reads `absent` on a system that accepts `recorded_at` but answers it wrongly."""
    shifted = shift_story(AS_OF, ctx.run_day)
    with ctx.fresh_system(AS_OF.id) as s:
        caps = _capabilities(s)
        try:
            topic_id, noted = _write_story(s, shifted, caps.valid_time, pause_after_first=True)
        except Rejected as e:
            return _verdict("T5", [Case("as-of probe writes", False, f"a write was {e}", control=True)], caps)
        results = []
        for ask in shifted.asks:
            request = query_request(ask, topic_id, send_valid=True, send_recorded=True, recorded_at=noted)
            result = {"asked": ask.label, "control": ask.control, "request": request}
            try:
                results.append({**result, "answer": _answer(s, topic_id, shifted.field, request)})
            except Rejected as e:
                results.append({**result, "rejected": str(e), "answer": None})
        if any("rejected" in r for r in results):
            return _verdict("T5", [Case(a.label, False, r.get("rejected", "answered"), control=a.control)
                                   for a, r in zip(shifted.asks, results)], caps)
        first, second = (r["answer"] for r in results)
        if first == second:
            return Verdict.absent("T5", {
                "probe": "the same plain-read answer to a valid_at question and a recorded_at question",
                "noted_moment_after_first_write": noted, "gap_s": AS_OF_GAP_S, "asked": results},
                measurements=caps.measurements())
        cases = [Case(f"{ask.label} -> {ask.correct!r}", r["answer"] == ask.correct,
                      f"asked {ask.label}: got {r['answer']!r}, correct {ask.correct!r}", control=ask.control)
                 for ask, r in zip(shifted.asks, results)]
        if caps.valid_time and caps.keeps_history:
            cases.append(_history_case(s, shifted, topic_id))
        return _verdict("T5", cases, caps)


@check(rows=ROWS)
def time_probes(ctx: Ctx) -> list[Verdict]:
    t1, t2, t3 = (_run_story(ctx, st) for st in (RETROACTIVE, OUT_OF_ORDER, FUTURE_DATED))
    t4a, t4b = _run_story(ctx, LAPSED_OVERRIDE_1), _run_story(ctx, LAPSED_OVERRIDE_2)
    t5 = _as_of(ctx)
    t6 = _run_story(ctx, FUTURE_ONLY)
    return [_verdict("T1", t1.cases, t1.caps), _verdict("T2", t2.cases, t2.caps), _verdict("T3", t3.cases, t3.caps),
            _verdict("T4", _prefixed("story 1", t4a.cases) + _prefixed("story 2", t4b.cases), t4a.caps), t5,
            _verdict("T6", t6.cases, t6.caps)]
