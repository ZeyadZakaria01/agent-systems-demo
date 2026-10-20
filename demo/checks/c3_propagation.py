"""C3, dependency consistency: update A, read B (linked by an `extension` edge) before and after revision (F7).

Two pairs, each with A `Deadline = March 15` and B `Date = March 20`: B -> A (the edge is written with B) and A -> B (the
edge is added to A by `extend_topic`). A is updated through `version_field` to `April 20`; B is read from the stored state
before, through `/v1/query` right after the update (the window), and from the stored state after `wait_until` saw B
change or the wait ran out (`REVISION_WAIT_S`). B "reflects" the update when its title, summary, kind, archived flag or
fields (current values and histories) changed; events, key set and salience do not count (our own reads bump
salience, and an unrelated event would not be propagation). The check cannot judge a repair, only that B changed. The edge is checked in the stored state first: a missing edge is a broken probe, not an absence.

Verdict: every pair reflected -> pass; some -> partial; none -> **absent**, with both pairs' observations as the probe
evidence (ADR 0002). The dependent-topic staleness window is reported from the same run: seconds from the update to B
reflecting it, or "unbounded (C3 absent)" when it never did within the wait.
"""

import json
from dataclasses import asdict, dataclass
from statistics import median

from demo.checks import Ctx, check
from demo.reads import current_value, field_in_response, read_request
from demo.verdict import Case, Verdict

CLAIM = ("C3 (dependency consistency): updating a unit triggers evaluation of units linked by propagation-bearing "
         "edges. Claimed by §4's opening ('by construction'); not listed in §4.3.")
REVISION_WAIT_S = 5.0  # bounded wait for the background revision (F7 used a fixed 2 s)
EDGE_KIND = "extension"
WINDOW = "Dependent-topic staleness window"
DIRECTIONS = ("B->A", "A->B")


def _signature(topic: dict | None) -> str | None:
    """What B stores that a propagated update would change: title, summary, kind, archived flag, fields and their
    histories. Not salience or topic events (our own reads bump them)."""
    if topic is None:
        return None
    fields = {name: {"current": repr(current_value(f)),
                     "history": [[e.get("value"), e.get("provenance"), e.get("operation")]
                                 for e in f.get("history") or []]}
              for name, f in sorted(topic["fields"].items())}
    return json.dumps({"title": topic.get("title"), "summary": topic.get("summary"),
                       "topic_kind": topic.get("topic_kind"), "archived": topic.get("archived"),
                       "fields": fields}, sort_keys=True, default=repr)


def _edge_linked(state: dict, src: str, dst: str) -> bool | None:
    if state["edges"] is None:
        return None  # the system stores no edges
    return any(e.get("from") == src and e.get("to") == dst and e.get("kind") == EDGE_KIND for e in state["edges"])


def _stale_read(s, b_id: str):
    response = s.query(read_request(b_id, explain=True, q="launch milestone date"))
    f = field_in_response(response, b_id, "Date")
    return None if f is None else current_value(f)


@dataclass
class Pair:
    """One probed pair: what A and B held, and whether B changed within the wait."""

    direction: str
    a_id: str
    b_id: str
    edge_linked: bool | None  # None: the system stores no edges
    update_applied: list
    a_deadline_now: object
    b_date_before: object
    b_date_read_right_after_update: object
    b_date_after_wait: object
    b_date_read_after_wait: object
    b_history_after: list
    b_topic_events_after: list
    b_topic_keys_after: list
    wait_s: float
    reflected: bool


def _probe_pair(s, direction: str, n: int) -> Pair:
    a_id = s.ingest({"placement": "new_topic", "title": f"Website Redesign {n}", "topic_kind": "project",
                     "fields": [{"name": "Deadline", "value": "March 15", "provenance": "kickoff-notes"}]})["topic_id"]
    b_edges = [{"to_topic_id": a_id, "kind": EDGE_KIND}] if direction == "B->A" else []
    b_id = s.ingest({"placement": "new_topic", "title": f"Launch Milestone {n}", "topic_kind": "milestone",
                     "fields": [{"name": "Date", "value": "March 20", "provenance": "kickoff-notes"}],
                     "edges": b_edges})["topic_id"]
    if direction == "A->B":
        s.ingest({"placement": "extend_topic", "topic_id": a_id, "fields": [],
                  "edges": [{"to_topic_id": b_id, "kind": EDGE_KIND}]})
    src, dst = (b_id, a_id) if direction == "B->A" else (a_id, b_id)
    linked = _edge_linked(s.read_state(), src, dst)
    if linked is False:
        raise RuntimeError(f"C3 probe setup failed: no {EDGE_KIND} edge {direction} in the stored state")

    b_before = s.read_topic(b_id)
    before = _signature(b_before)
    update = s.ingest({"placement": "version_field", "topic_id": a_id,
                       "fields": [{"name": "Deadline", "value": "April 20", "provenance": "pm-email",
                                   "why_changed": "vendor delay"}]})
    in_window = _stale_read(s, b_id)
    waited = s.wait_until(lambda: _signature(s.read_topic(b_id)) != before, REVISION_WAIT_S)
    b_after = s.read_topic(b_id)
    f_before, f_after = b_before["fields"].get("Date") or {}, b_after["fields"].get("Date") or {}
    return Pair(
        direction=direction, a_id=a_id, b_id=b_id, edge_linked=linked, update_applied=update["applied"],
        a_deadline_now=current_value(s.read_topic(a_id)["fields"].get("Deadline")),
        b_date_before=current_value(f_before or None), b_date_read_right_after_update=in_window,
        b_date_after_wait=current_value(f_after or None), b_date_read_after_wait=_stale_read(s, b_id),
        b_history_after=[e.get("value") for e in f_after.get("history") or []],
        b_topic_events_after=[h.get("kind") for h in b_after.get("topic_history") or []],
        b_topic_keys_after=sorted(b_after), wait_s=waited.elapsed, reflected=not waited.timed_out)


def _window_value(pairs: list[Pair]) -> str:
    seen = {p.direction: p.wait_s for p in pairs if p.reflected}
    if not seen:
        return "unbounded (C3 absent)"
    times = ", ".join(f"{d} {t:.1f} s" for d, t in seen.items())
    if len(seen) == len(pairs):
        return f"median {median(seen.values()):.1f} s ({times})"
    never = ", ".join(p.direction for p in pairs if not p.reflected)
    return f"unbounded for {never} (C3 partial); {times}"


@check(row="C3", claim=CLAIM)
def c3(ctx: Ctx) -> Verdict:
    s = ctx.system
    pairs = [_probe_pair(s, direction, n) for n, direction in enumerate(DIRECTIONS, start=1)]
    cases = [Case(f"B's fields, summary or history change after A is updated ({p.direction})", held=p.reflected,
                  observation=f"B Date {p.b_date_before!r} before; {p.b_date_read_right_after_update!r} read "
                              f"right after the update; {p.b_date_after_wait!r} after {p.wait_s:.1f} s"
                              f"{'' if p.reflected else ' (wait ran out)'}; A is {p.a_deadline_now!r}; edge stored: "
                              f"{'no edges in this system' if p.edge_linked is None else p.edge_linked}")
             for p in pairs]
    window = [{"name": WINDOW, "value": _window_value(pairs), "source_row": "C3"}]
    measurements = {"windows": window, "revision_wait_s": REVISION_WAIT_S}
    if not any(p.reflected for p in pairs):
        return Verdict.absent("C3", {"probe": "F7: update A, read B before and after revision, both pairs",
                                     "pairs": [asdict(p) for p in pairs], "wait_s": REVISION_WAIT_S}, cases=cases,
                              measurements=measurements)
    return Verdict.from_cases("C3", cases, measurements=measurements,
                              observations=[{"pairs": [asdict(p) for p in pairs]}])
