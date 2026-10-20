"""C3, dependency consistency: update A, read B (linked to A by an `extension` edge) before B is written (F7, then the
stricter criteria of spec story 64).

Two pairs, each with A `Deadline = March 15` and B `Date = March 20`: B -> A (the edge is written with B) and A -> B (the
edge is added to A by `extend_topic`). Each pair also has a control topic C linked to A only by an `association` edge.
A is updated through `version_field` to `April 20`. The extension edge is stored first (a missing edge is a broken
probe, not an absence).

Pass criteria, per pair, each scored as a case (the reference GEM tickets are built against them):
1. *Extension edge.* After the update, `read_topic(B)` (a read before B is written) carries a revision flag
   (`revision_flag`, see `adapter.py`) that names that update: the evidence's `source_topic_id` is A, its
   `updated_field` is `Deadline` and it has a `timestamp`. The flag is due to the extension edge, whatever its
   direction (B -> A and A -> B are both scored).
2. *Control.* After the same update, C (association edge only) is not flagged. Not applicable (`held=None`) on a system
   with no flag surface.
3. *The flag clears.* B is written next (`version_field` on `Date`); the next read of B carries no flag. Applicable only
   when case 1 saw a flag.

Verdict: every case held -> pass; some -> partial; none -> fail (a system that changes B but never flags it fails case
1). **Absent** only when neither pair showed a flag nor any change in B (title, summary, kind, archived flag, fields and
histories; events, key set and salience do not count: our own reads bump salience) after a polled wait
(`REVISION_WAIT_S`, the same 15 s the C2(a) merge wait uses, counted from the update's response): the F17 probe, with both
pairs' observations as the evidence (ADR 0002). The dependent-topic staleness window is reported from the same run:
seconds from the update's response to B flagged or changed, or "unbounded (C3 absent)" when it never was within the wait.
"""

import json
import time
from dataclasses import asdict, dataclass
from statistics import median

from demo.checks import Ctx, check
from demo.reads import current_value, field_in_response, read_request
from demo.merge import DEFAULT_TIMEOUT_S
from demo.verdict import Case, Verdict

CLAIM = ("C3 (dependency consistency): updating a unit triggers evaluation of units linked by propagation-bearing "
         "edges. Claimed by §4's opening ('by construction'); not listed in §4.3.")
REVISION_WAIT_S = DEFAULT_TIMEOUT_S  # bounded wait for the background revision (F7 used a fixed 2 s)
EDGE_KIND = "extension"
WINDOW = "Dependent-topic staleness window"
CONTROL_EDGE_KIND = "association"
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


def _edge_linked(state: dict, src: str, dst: str, kind: str = EDGE_KIND) -> bool | None:
    if state["edges"] is None:
        return None  # the system stores no edges
    return any(e.get("from") == src and e.get("to") == dst and e.get("kind") == kind for e in state["edges"])


def _flag(topic: dict | None) -> dict | None:
    """The topic's revision flag as read: `None` when the system has no flag surface, else `{"flagged", "evidence"}`."""
    return None if topic is None else topic.get("revision_flag")


def _names_the_update(flag: dict | None, a_id: str) -> bool:
    """Flagged, and the evidence names the update: A's topic, the updated field, a timestamp."""
    evidence = (flag or {}).get("evidence") or {}
    return bool(flag and flag.get("flagged") and evidence.get("source_topic_id") == a_id
                and evidence.get("updated_field") == "Deadline" and evidence.get("timestamp"))


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
    control_id: str
    control_edge_linked: bool | None
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
    reflected: bool  # B was flagged or changed within the wait
    flag_surface: bool  # the system has a revision flag at all
    b_flag_after: dict | None
    flag_names_update: bool
    control_flag_after: dict | None
    control_flagged: bool | None  # None: no flag surface
    b_flag_after_write: dict | None
    flag_cleared: bool | None  # None: B was never flagged, so nothing to clear


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
    c_edges = [{"to_topic_id": a_id, "kind": CONTROL_EDGE_KIND}] if direction == "B->A" else []
    c_id = s.ingest({"placement": "new_topic", "title": f"Style Guide {n}", "topic_kind": "document",
                     "fields": [{"name": "Version", "value": "1", "provenance": "kickoff-notes"}],
                     "edges": c_edges})["topic_id"]
    if direction == "A->B":
        s.ingest({"placement": "extend_topic", "topic_id": a_id, "fields": [],
                  "edges": [{"to_topic_id": c_id, "kind": CONTROL_EDGE_KIND}]})
    src, dst = (b_id, a_id) if direction == "B->A" else (a_id, b_id)
    csrc, cdst = (c_id, a_id) if direction == "B->A" else (a_id, c_id)
    state = s.read_state()
    linked = _edge_linked(state, src, dst)
    control_linked = _edge_linked(state, csrc, cdst, CONTROL_EDGE_KIND)
    if linked is False or control_linked is False:
        missing = EDGE_KIND if linked is False else CONTROL_EDGE_KIND
        raise RuntimeError(f"C3 probe setup failed: no {missing} edge {direction} in the stored state")

    b_before = s.read_topic(b_id)
    before = _signature(b_before)
    update = s.ingest({"placement": "version_field", "topic_id": a_id,
                       "fields": [{"name": "Deadline", "value": "April 20", "provenance": "pm-email",
                                   "why_changed": "vendor delay"}]})
    t_update = time.perf_counter()  # the window starts when the update's response is back
    in_window = _stale_read(s, b_id)
    def reflects() -> bool:
        topic = s.read_topic(b_id)
        return bool((_flag(topic) or {}).get("flagged")) or _signature(topic) != before

    waited = s.wait_until(reflects, max(REVISION_WAIT_S - (time.perf_counter() - t_update), 0.0))
    wait_s = time.perf_counter() - t_update
    b_after = s.read_topic(b_id)
    b_flag = _flag(b_after)
    c_flag = _flag(s.read_topic(c_id))
    surface = b_flag is not None
    flagged = bool((b_flag or {}).get("flagged"))
    cleared = None
    flag_after_write = None
    if flagged:  # the next write of B: a re-check of its date
        s.ingest({"placement": "version_field", "topic_id": b_id,
                  "fields": [{"name": "Date", "value": "April 25", "provenance": "pm-email",
                              "why_changed": "re-checked after A moved"}]})
        flag_after_write = _flag(s.read_topic(b_id))
        cleared = not (flag_after_write or {}).get("flagged")
    f_before, f_after = b_before["fields"].get("Date") or {}, b_after["fields"].get("Date") or {}
    return Pair(
        direction=direction, a_id=a_id, b_id=b_id, edge_linked=linked, control_id=c_id,
        control_edge_linked=control_linked, update_applied=update["applied"],
        a_deadline_now=current_value(s.read_topic(a_id)["fields"].get("Deadline")),
        b_date_before=current_value(f_before or None), b_date_read_right_after_update=in_window,
        b_date_after_wait=current_value(f_after or None), b_date_read_after_wait=_stale_read(s, b_id),
        b_history_after=[e.get("value") for e in f_after.get("history") or []],
        b_topic_events_after=[h.get("kind") for h in b_after.get("topic_history") or []],
        b_topic_keys_after=sorted(b_after), wait_s=wait_s, reflected=not waited.timed_out,
        flag_surface=surface, b_flag_after=b_flag, flag_names_update=_names_the_update(b_flag, a_id),
        control_flag_after=c_flag, control_flagged=None if c_flag is None else bool(c_flag.get("flagged")),
        b_flag_after_write=flag_after_write, flag_cleared=cleared)


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
    cases = []
    for p in pairs:
        cases += [
            Case(f"B is flagged by A's update, the flag naming the updated field and timestamp, via the extension "
                 f"edge ({p.direction})", held=p.flag_names_update,
                 observation=f"B Date {p.b_date_before!r} before; {p.b_date_after_wait!r} after {p.wait_s:.1f} s"
                             f"{'' if p.reflected else ' (wait ran out)'}; A is {p.a_deadline_now!r}; B's flag: "
                             f"{'no flag surface' if not p.flag_surface else p.b_flag_after}; edge stored: "
                             f"{'no edges in this system' if p.edge_linked is None else p.edge_linked}"),
            Case(f"control: a topic linked to A only by an association edge is not flagged ({p.direction})",
                 held=None if p.control_flagged is None else not p.control_flagged, control=True,
                 observation=f"control flag: {'no flag surface' if p.control_flagged is None else p.control_flag_after}; "
                             f"association edge stored: "
                             f"{'no edges in this system' if p.control_edge_linked is None else p.control_edge_linked}"),
            Case(f"the flag clears when B is next written ({p.direction})", held=p.flag_cleared,
                 observation="B was never flagged, so there was nothing to clear" if p.flag_cleared is None
                 else f"B's flag after its next write: {p.b_flag_after_write}")]
    window = [{"name": WINDOW, "value": _window_value(pairs)}]
    measurements = {"windows": window, "revision_wait_s": REVISION_WAIT_S}
    if not any(p.reflected for p in pairs):
        return Verdict.absent("C3", {"probe": "F7: update A, read B before and after revision, both pairs",
                                     "pairs": [asdict(p) for p in pairs], "wait_s": REVISION_WAIT_S}, cases=cases,
                              measurements=measurements)
    return Verdict.from_cases("C3", cases, measurements=measurements,
                              observations=[{"name": "pairs", "pairs": [asdict(p) for p in pairs]}])
