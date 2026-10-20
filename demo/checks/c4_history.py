"""C4 (provenance preservation): a field history survives an update, a merge and archiving, empty and
null writes must not replace the current value, and a 501-write case decides the 500-entry cap.

The update path is the control (an ordinary March 15 → April 20 that should keep both entries). Empty and
null writes are the trap (implied by C2/C4, not part of C4's definition; report §9.4). The cap case writes one value
with `new_topic` and 500 more with `version_field` (501 writes) and records whether the first value is still in the
history: the run decides whether the oldest entry is dropped.

The baseline has no history: C4 fails, with the observations a scorecard reader relies on (lost earlier
value, empty value becoming current). MemState outcomes come only from a recorded run.
"""

from __future__ import annotations

from demo.adapter import Rejected, System
from demo.checks import Ctx, check
from demo.merge import DEADLINE, FIELD, NEWER, NEWER_PROVENANCE, OLDER, OLDER_PROVENANCE, trigger_and_await_merge
from demo.reads import current_value
from demo.verdict import Case, Verdict

CLAIM = ("C4 (provenance preservation): revision and forgetting preserve the provenance chain of "
         "reachable units.")
CAP_WRITES = 501  # 1 new_topic + 500 version_field
CAP_FIRST = "v000"


def _field(topic: dict | None, name: str = FIELD) -> dict | None:
    if topic is None:
        return None
    return (topic.get("fields") or {}).get(name)


def history_entries(system: System, topic_id: str, field: str = FIELD) -> list | None:
    """Stored history (newest first), or `None` when the system keeps no history."""
    field_rec = _field(system.read_topic(topic_id), field)
    if not field_rec or field_rec.get("history") is None:
        return None
    return field_rec["history"]


def _has(history: list, value: object, provenance: str) -> bool:
    return any(e.get("value") == value and e.get("provenance") == provenance for e in history)


def _holds_both(history: list | None) -> bool:
    """Both the older and the newer entry, each with its provenance."""
    return history is not None and _has(history, OLDER, OLDER_PROVENANCE) and _has(history, NEWER, NEWER_PROVENANCE)


def _fmt(history: list | None, provenance: bool = True) -> list | None:
    """The history as `(value, provenance)` pairs, or just the values; `None` when there is none."""
    if history is None:
        return None
    return [(e.get("value"), e.get("provenance")) if provenance else e.get("value") for e in history]


def _write_deadline(system: System, title: str) -> str:
    topic_id = system.ingest({
        "placement": "new_topic", "title": title, "topic_kind": "project",
        "fields": [{"name": FIELD, "value": OLDER, "provenance": OLDER_PROVENANCE}],
    })["topic_id"]
    system.ingest({
        "placement": "version_field", "topic_id": topic_id,
        "fields": [{"name": FIELD, "value": NEWER, "provenance": NEWER_PROVENANCE, "why_changed": "vendor delay"}],
    })
    return topic_id


def _current(system: System, topic_id: str) -> object:
    return current_value(_field(system.read_topic(topic_id)))


def _update_case(s: System) -> tuple[Case, bool]:
    """The control: history survives an ordinary update. Also returns whether the earlier value got lost."""
    topic_id = _write_deadline(s, "Website Redesign")
    history = history_entries(s, topic_id)
    current = _current(s, topic_id)
    held = current == NEWER and _holds_both(history)
    lost = history is None or not any(e.get("value") == OLDER for e in history)
    return Case("history survives a value update", held, f"current={current!r}, history={_fmt(history)!r}",
                control=True), lost


def _merge_case(s: System) -> Case:
    name = "history survives a merge"
    outcome = trigger_and_await_merge(s, "Vendor Contract", DEADLINE)
    if not outcome.merged:
        return Case(name, None, f"no merge seen within {outcome.waited.elapsed:.1f}s (timeout)")
    history = history_entries(s, outcome.survivor_id)
    if outcome.pair.upserted:
        return Case(name, _holds_both(history), f"upsert (no duplicate); history={_fmt(history, provenance=False)!r}")
    return Case(name, _holds_both(history), f"survivor {outcome.survivor_id} ({outcome.dropped_state} dropped); "
                                            f"history={_fmt(history)!r}")


def _archive_case(s: System) -> Case:
    name = "history survives archiving"
    topic_id = _write_deadline(s, "Website Redesign (archive)")
    archived = s.setup_write("patch_topic", label="archive after the history is written (values untouched)",
                             topic_id=topic_id, archived=True)
    if archived is None:
        return Case(name, None, "the system has no archived flag (setup write returned nothing)")
    history = history_entries(s, topic_id)
    topic = s.read_topic(topic_id)
    flag = None if topic is None else topic.get("archived")
    return Case(name, flag is True and _holds_both(history),
                f"archived={flag!r}, history={_fmt(history, provenance=False)!r}")


def _empty_write(system: System, topic_id: str, value: object) -> tuple[object, str]:
    """Send `version_field` with `value`; return (current afterwards, observation)."""
    try:
        system.ingest({"placement": "version_field", "topic_id": topic_id,
                       "fields": [{"name": FIELD, "value": value, "provenance": "empty-write"}]})
        how = "accepted"
    except Rejected as e:
        how = f"rejected ({e.status})"
    current = _current(system, topic_id)
    return current, f"{how}; current={current!r}"


def _empty_cases(s: System) -> tuple[list[Case], object, object]:
    """`""` and `null` written over April 20: the cases, and what became current for each."""
    empty, empty_obs = _empty_write(s, _write_deadline(s, "Website Redesign (empty write)"), "")
    null, null_obs = _empty_write(s, _write_deadline(s, "Website Redesign (null write)"), None)
    return ([Case(f'version_field with "" does not replace {NEWER}', empty == NEWER, empty_obs),
             Case(f"version_field with null does not replace {NEWER}", null == NEWER, null_obs)], empty, null)


def _cap_case(s: System) -> tuple[Case, dict]:
    """One `new_topic` and `CAP_WRITES - 1` `version_field` writes to one field; is the first value still there?"""
    topic_id = s.ingest({
        "placement": "new_topic", "title": "Website Redesign (history cap)", "topic_kind": "project",
        "fields": [{"name": FIELD, "value": CAP_FIRST, "provenance": "cap-0"}],
    })["topic_id"]
    for i in range(1, CAP_WRITES):
        s.ingest({"placement": "version_field", "topic_id": topic_id,
                  "fields": [{"name": FIELD, "value": f"v{i:03d}", "provenance": f"cap-{i}"}]})
    values = _fmt(history_entries(s, topic_id), provenance=False)
    present = bool(values) and CAP_FIRST in values
    length = None if values is None else len(values)
    case = Case(f"the first value is still in the history after {CAP_WRITES} writes (1 new_topic + {CAP_WRITES - 1} "
                "version_field)", present, f"length={length}, first {CAP_FIRST!r} present={present}")
    return case, {"writes": CAP_WRITES, "first": CAP_FIRST, "first_present": present, "length": length,
                  "newest": values[0] if values else None}


@check(row="C4", claim=CLAIM)
def c4(ctx: Ctx) -> Verdict:
    s = ctx.system
    update, lost = _update_case(s)
    merge = _merge_case(s)
    archive = _archive_case(s)
    empty_cases, empty_current, null_current = _empty_cases(s)
    cap, history_cap = _cap_case(s)
    cases = [update, merge, archive, *empty_cases, cap]
    observations = [
        {"name": "lost earlier value", "lost": lost,
         "summary": (f"the earlier value {OLDER} is missing after the update"
                     if lost else f"the earlier value {OLDER} is still in the history after the update")},
        {"name": "empty value becoming current",
         "empty_current": empty_current == "", "null_current": null_current is None,
         "summary": f'empty write current={empty_current!r}; null write current={null_current!r}'},
    ]
    measurements = {"history_cap": history_cap, "keeps_history": s.describe()["keeps_history"]}
    return Verdict.from_cases("C4", cases, observations=observations, measurements=measurements)
