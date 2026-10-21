"""C4 (provenance preservation): a field history survives an update, a merge and real forgetting, empty and
null writes must not replace the current value, and a 501-write case decides the 500-entry cap.

Cases (spec "Stricter check pass criteria"): (1) update survives, the control: an ordinary March 15 -> April 20 keeps
both entries. (2) Merge keeps history; n/a where the system has no merge (a second same-title write appends to the same
topic). (2b) The dated merge, for a system that accepts `valid_from`: topic A holds "April 20 since Jan 5"; the
duplicate B, written later, holds "March 15 since Dec 1" (B has the higher id, so it is the one dropped); after the
merge, today reads April 20 and both values are in the history, each with its provenance. A system that interleaves
the two histories by valid time holds; one that drops B's value breaks. The tag on B's entry (`merged_from_topic_id`)
is read and reported, not scored: it is the patch's own key. N/a where no date is accepted or no two-topic merge
happened. (3) Real forgetting keeps history: a topic with fields, ingested at salience 0.01, must reach forgetting through
the system's own operations (the count gate is driven past `ramp.FORGET_GATE` with field-less fillers, a field-less
control at 0.01 shows the pass ran), and its history and provenance are intact after. The case is n/a where the system
has no archived flag, where the pass is not shown to run, and where the pass ran (the control is archived) and the topic
with fields was not forgotten: that is confirmed by the run (upstream, F24: any field write resets the topic's salience
to the field average, 1.0). No editor archive write is ever used. (4) `version_field` with `""` and separately with
`null` does not replace April 20 (empty and null writes are the trap: implied by C2/C4, not part of C4's definition;
report §9.4). (5) The cap: one `new_topic` and 500 `version_field` writes (501) to one field, then is the first value
still readable, in the history or in the field's `archived_history` (overflow the cap moved out of the active history;
the reference GEM archives it, upstream drops it, F21)? The verdict rests on the cases that could run.

`archived_history` is the one key the adapter contract adds for the cap case: on a stored field, the entries archived
as overflow, newest first, each shaped like a history entry. A system that deletes overflow has no such key.
"""

from __future__ import annotations

from datetime import date

from demo import ramp
from demo.adapter import Rejected, System
from demo.checks import Ctx, check
from demo.merge import (
    DEADLINE,
    FIELD,
    NEWER,
    NEWER_PROVENANCE,
    OLDER,
    OLDER_PROVENANCE,
    PairSpec,
    trigger_and_await_merge,
)
from demo.reads import current_value
from demo.time_stories import YEAR, iso
from demo.verdict import Case, Verdict

CLAIM = "C4 (provenance preservation): revision and forgetting preserve the provenance chain of reachable units."
CAP_WRITES = 501  # 1 new_topic + 500 version_field
CAP_FIRST = "v000"
LOW_SALIENCE = 0.01
DATED_MERGE = PairSpec(  # "older" is written first (to the topic that survives), "newer" second (to the dropped one)
    older_value=NEWER,
    older_provenance=NEWER_PROVENANCE,
    older_valid_from=iso(date(YEAR, 1, 5)),
    newer_value=OLDER,
    newer_provenance=OLDER_PROVENANCE,
    newer_valid_from=iso(date(YEAR - 1, 12, 1)),
)


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
    topic_id = system.ingest(
        {
            "placement": "new_topic",
            "title": title,
            "topic_kind": "project",
            "fields": [{"name": FIELD, "value": OLDER, "provenance": OLDER_PROVENANCE}],
        }
    )["topic_id"]
    system.ingest(
        {
            "placement": "version_field",
            "topic_id": topic_id,
            "fields": [{"name": FIELD, "value": NEWER, "provenance": NEWER_PROVENANCE, "why_changed": "vendor delay"}],
        }
    )
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
    return Case(
        "history survives a value update",
        held,
        f"current={current!r}, history={_fmt(history)!r}",
        control=True,
        id="update",
    ), lost


def _merge_case(s: System) -> Case:
    name = "history survives a merge"
    outcome = trigger_and_await_merge(s, "Vendor Contract", DEADLINE)
    if not outcome.merged:
        return Case(name, None, f"no merge seen within {outcome.waited.elapsed:.1f}s (timeout)", id="merge")
    history = history_entries(s, outcome.survivor_id)
    if outcome.pair.upserted:
        return Case(
            name,
            None,
            "arrangement not met: the second write went to the same topic, so no duplicate was "
            f"created and no merge occurs; not a case; history={_fmt(history, provenance=False)!r}",
            id="merge",
        )
    return Case(
        name,
        _holds_both(history),
        f"survivor {outcome.survivor_id} ({outcome.dropped_state} dropped); history={_fmt(history)!r}",
        id="merge",
    )


def _dated_merge_case(s: System) -> tuple[Case, dict]:
    name = f"a dated merge keeps both values, today reads {NEWER}"
    if not s.dates_accepted("valid_from")["valid_from"]:
        return Case(name, None, "the system accepts no valid_from, so no dated write is possible", id="merge-dated"), {}
    outcome = trigger_and_await_merge(s, "Vendor Contract (dated)", DATED_MERGE)
    if not outcome.merged:
        return Case(name, None, f"no merge seen within {outcome.waited.elapsed:.1f}s (timeout)", id="merge-dated"), {}
    if outcome.pair.upserted or outcome.dropped_held_newer is not True:
        return Case(
            name,
            None,
            "arrangement not met: the topic written later was not the one dropped (or no duplicate was created)",
            id="merge-dated",
        ), {}
    history = history_entries(s, outcome.survivor_id) or []
    current = _current(s, outcome.survivor_id)
    both = _has(history, NEWER, NEWER_PROVENANCE) and _has(history, OLDER, OLDER_PROVENANCE)
    tag = next((e.get("merged_from_topic_id") for e in history if e.get("value") == OLDER), None)
    case = Case(
        name,
        current == NEWER and both,
        f"survivor {outcome.survivor_id} ({outcome.dropped_state} dropped {outcome.dropped_id}); "
        f"current={current!r}, history={_fmt(history)!r}, the {OLDER!r} entry's merged_from_topic_id={tag!r}",
        id="merge-dated",
    )
    return case, {
        "survivor_id": outcome.survivor_id,
        "dropped_id": outcome.dropped_id,
        "current": current,
        "merged_from_topic_id": tag,
        "tagged_with_dropped_id": tag == outcome.dropped_id,
    }


def _forgetting_case(s: System) -> tuple[Case, dict]:
    """Real forgetting: the field-bearing topic reaches forgetting only through the system's own operations."""
    name = "history survives real forgetting"
    if ramp.archive_stats(s)["archived"] is None:
        return Case(name, None, "the system has no archived flag, so no topic is forgotten", id="forgetting"), {
            "ran": False
        }
    target_id = s.ingest(
        {
            "placement": "new_topic",
            "title": "Old Vendor (forgetting)",
            "topic_kind": "project",
            "salience": LOW_SALIENCE,
            "fields": [{"name": FIELD, "value": OLDER, "provenance": OLDER_PROVENANCE}],
        }
    )["topic_id"]
    s.ingest(
        {
            "placement": "version_field",
            "topic_id": target_id,
            "fields": [{"name": FIELD, "value": NEWER, "provenance": NEWER_PROVENANCE, "why_changed": "vendor delay"}],
        }
    )
    control_id = s.ingest(
        {
            "placement": "new_topic",
            "title": "Library Card (forgetting control)",
            "summary": "Field-less and never read; shows the forgetting pass ran",
            "salience": LOW_SALIENCE,
        }
    )["topic_id"]

    def archived(topic_id: str) -> bool:
        return (s.read_topic(topic_id) or {}).get("archived") is True

    if not archived(control_id):
        for i in range(max(0, ramp.FORGET_GATE - ramp.archive_stats(s)["total"])):
            ramp.filler(s, i)
        s.ingest(
            {
                "placement": "new_topic",
                "title": "Filler trigger",
                "summary": "Ingested after the topic count reached the gate; its response schedules the pass",
            }
        )
        s.wait_until(lambda: archived(control_id), ramp.ARCHIVE_WAIT_S)
    topic = s.read_topic(target_id) or {}
    evidence = {
        "ran": archived(control_id),
        "target_salience": topic.get("salience"),
        "target_archived": topic.get("archived"),
        "topics": ramp.archive_stats(s)["total"],
    }
    if not evidence["ran"]:
        return Case(
            name,
            None,
            f"forgetting was not shown to run: the never-read control at {LOW_SALIENCE} was not "
            f"archived after {evidence['topics']} topics",
            id="forgetting",
        ), evidence
    if topic.get("archived") is not True:
        return Case(
            name,
            None,
            f"the pass ran (the control is archived) but a topic with fields ingested at "
            f"{LOW_SALIENCE} was not forgotten: salience {topic.get('salience')!r}, "
            f"archived={topic.get('archived')!r}; it cannot be forgotten through the system's own "
            "operations",
            id="forgetting",
        ), evidence
    history = history_entries(s, target_id)
    return Case(name, _holds_both(history), f"forgotten; history={_fmt(history)!r}", id="forgetting"), evidence


def _empty_write(system: System, topic_id: str, value: object) -> tuple[object, str]:
    """Send `version_field` with `value`; return (current afterwards, observation)."""
    try:
        system.ingest(
            {
                "placement": "version_field",
                "topic_id": topic_id,
                "fields": [{"name": FIELD, "value": value, "provenance": "empty-write"}],
            }
        )
        how = "accepted"
    except Rejected as e:
        how = f"rejected ({e.status})"
    current = _current(system, topic_id)
    return current, f"{how}; current={current!r}"


def _empty_cases(s: System) -> tuple[list[Case], object, object]:
    """`""` and `null` written over April 20: the cases, and what became current for each."""
    empty, empty_obs = _empty_write(s, _write_deadline(s, "Website Redesign (empty write)"), "")
    null, null_obs = _empty_write(s, _write_deadline(s, "Website Redesign (null write)"), None)
    return (
        [
            Case(f'version_field with "" does not replace {NEWER}', empty == NEWER, empty_obs, id="empty-string"),
            Case(f"version_field with null does not replace {NEWER}", null == NEWER, null_obs, id="null"),
        ],
        empty,
        null,
    )


def _cap_case(s: System) -> tuple[Case, dict]:
    """One `new_topic` and `CAP_WRITES - 1` `version_field` writes to one field; is the first value still there?"""
    topic_id = s.ingest(
        {
            "placement": "new_topic",
            "title": "Website Redesign (history cap)",
            "topic_kind": "project",
            "fields": [{"name": FIELD, "value": CAP_FIRST, "provenance": "cap-0"}],
        }
    )["topic_id"]
    for i in range(1, CAP_WRITES):
        s.ingest(
            {
                "placement": "version_field",
                "topic_id": topic_id,
                "fields": [{"name": FIELD, "value": f"v{i:03d}", "provenance": f"cap-{i}"}],
            }
        )
    values = _fmt(history_entries(s, topic_id), provenance=False)
    in_history = bool(values) and CAP_FIRST in values
    length = None if values is None else len(values)
    overflow = _fmt((_field(s.read_topic(topic_id)) or {}).get("archived_history"), provenance=False)
    in_overflow = bool(overflow) and CAP_FIRST in overflow
    present = in_history or in_overflow
    where = "in the history" if in_history else "in the archived overflow" if in_overflow else "nowhere"
    case = Case(
        f"the first value is still readable after {CAP_WRITES} writes (1 new_topic + {CAP_WRITES - 1} "
        "version_field), in the history or as archived overflow",
        present,
        f"length={length}, archived overflow={0 if overflow is None else len(overflow)}, "
        f"first {CAP_FIRST!r} readable {where}",
        id="cap",
    )
    return case, {
        "writes": CAP_WRITES,
        "first": CAP_FIRST,
        "first_present": present,
        "first_in_history": in_history,
        "first_in_archived_overflow": in_overflow,
        "length": length,
        "newest": values[0] if values else None,
    }


@check(row="C4", claim=CLAIM)
def c4(ctx: Ctx) -> Verdict:
    s = ctx.system
    update, lost = _update_case(s)
    merge = _merge_case(s)
    dated_merge, dated_merge_run = _dated_merge_case(s)
    forgetting, forgetting_run = _forgetting_case(s)
    empty_cases, empty_current, null_current = _empty_cases(s)
    cap, history_cap = _cap_case(s)
    cases = [update, merge, dated_merge, forgetting, *empty_cases, cap]
    observations = [
        {
            "name": "lost earlier value",
            "lost": lost,
            "summary": (
                f"the earlier value {OLDER} is missing after the update"
                if lost
                else f"the earlier value {OLDER} is still in the history after the update"
            ),
        },
        {
            "name": "empty value becoming current",
            "empty_current": empty_current == "",
            "null_current": null_current is None,
            "summary": f"empty write current={empty_current!r}; null write current={null_current!r}",
        },
    ]
    measurements = {
        "history_cap": history_cap,
        "forgetting": forgetting_run,
        "dated_merge": dated_merge_run,
        "keeps_history": s.describe()["keeps_history"],
    }
    return Verdict.from_cases("C4", cases, observations=observations, measurements=measurements)
