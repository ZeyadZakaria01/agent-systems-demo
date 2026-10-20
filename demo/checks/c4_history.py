"""C4 (provenance preservation): a field history survives an update, a merge and archiving, empty and
null writes must not replace the current value, and a 501-update case decides the 500-entry cap.

The update path is the control (an ordinary March 15 → April 20 that should keep both entries). Empty and
null writes are the trap (implied by C2/C4, not part of C4's definition; report §9.4). The cap case records
whether the first value is still in the history after 501 updates (`TopicFields.cap_history` /
`graph_store.py` `max_history=500` drop the oldest [INFERENCE]; the run decides).

The baseline has no history: C4 fails, with the observations a scorecard reader relies on (lost earlier
value, empty value becoming current). MemState outcomes come only from a recorded run.
"""

from __future__ import annotations

from demo.checks import Ctx, check
from demo.client import Rejected, System
from demo.merge import trigger_and_await_merge
from demo.reads import current_value
from demo.verdict import Case, Verdict

CLAIM = ("C4 (provenance preservation): revision and forgetting preserve the provenance chain of "
         "reachable units.")
FIELD = "Deadline"
OLDER, NEWER = "March 15", "April 20"
OLDER_PROV, NEWER_PROV = "kickoff-notes", "pm-email"
CAP_UPDATES = 501
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


def _write_deadline(system: System, title: str) -> str:
    topic_id = system.ingest({
        "placement": "new_topic", "title": title, "topic_kind": "project",
        "fields": [{"name": FIELD, "value": OLDER, "provenance": OLDER_PROV}],
    })["topic_id"]
    system.ingest({
        "placement": "version_field", "topic_id": topic_id,
        "fields": [{"name": FIELD, "value": NEWER, "provenance": NEWER_PROV, "why_changed": "vendor delay"}],
    })
    return topic_id


def _current(system: System, topic_id: str) -> object:
    return current_value(_field(system.read_topic(topic_id)))


def _empty_write(system: System, topic_id: str, value: object) -> tuple[bool, object, str]:
    """Send `version_field` with `value`; return (rejected, current afterwards, observation)."""
    try:
        system.ingest({"placement": "version_field", "topic_id": topic_id,
                       "fields": [{"name": FIELD, "value": value, "provenance": "empty-write"}]})
        rejected = False
        how = "accepted"
    except Rejected as e:
        rejected = True
        how = f"rejected ({e.status})"
    current = _current(system, topic_id)
    return rejected, current, f"{how}; current={current!r}"


@check(row="C4", claim=CLAIM)
def c4(ctx: Ctx) -> Verdict:
    s = ctx.system

    update_id = _write_deadline(s, "Website Redesign")
    update_hist = history_entries(s, update_id)
    update_current = _current(s, update_id)
    update_held = (update_hist is not None and update_current == NEWER
                   and _has(update_hist, OLDER, OLDER_PROV) and _has(update_hist, NEWER, NEWER_PROV))
    lost = update_hist is None or not any(e.get("value") == OLDER for e in update_hist)
    cases = [Case("history survives a value update", update_held,
                  (f"current={update_current!r}, history="
                   f"{None if update_hist is None else [(e.get('value'), e.get('provenance')) for e in update_hist]!r}"),
                  control=True)]

    outcome = trigger_and_await_merge(s, "Vendor Contract", OLDER, NEWER)
    if outcome.pair.upserted:
        merge_hist = history_entries(s, outcome.pair.older_id)
        merge_held = (merge_hist is not None and _has(merge_hist, OLDER, OLDER_PROV)
                      and _has(merge_hist, NEWER, NEWER_PROV))
        cases.append(Case("history survives a merge", merge_held,
                          f"upsert (no duplicate); history="
                          f"{None if merge_hist is None else [e.get('value') for e in merge_hist]!r}"))
    elif not outcome.merged:
        cases.append(Case("history survives a merge", None,
                          f"no merge seen within {outcome.waited.elapsed:.1f}s (timeout)"))
    else:
        merge_hist = history_entries(s, outcome.survivor_id)
        merge_held = (merge_hist is not None and _has(merge_hist, OLDER, OLDER_PROV)
                      and _has(merge_hist, NEWER, NEWER_PROV))
        cases.append(Case("history survives a merge", merge_held,
                          f"survivor {outcome.survivor_id} ({outcome.dropped_state} dropped); history="
                          f"{None if merge_hist is None else [(e.get('value'), e.get('provenance')) for e in merge_hist]!r}"))

    archive_id = _write_deadline(s, "Website Redesign (archive)")
    archived = s.setup_write("patch_topic", label="archive after the history is written (values untouched)",
                             topic_id=archive_id, archived=True)
    if archived is None:
        cases.append(Case("history survives archiving", None,
                          "the system has no archived flag (setup write returned nothing)"))
    else:
        archive_hist = history_entries(s, archive_id)
        archive_topic = s.read_topic(archive_id)
        archive_held = (archive_topic is not None and archive_topic.get("archived") is True
                        and archive_hist is not None and _has(archive_hist, OLDER, OLDER_PROV)
                        and _has(archive_hist, NEWER, NEWER_PROV))
        cases.append(Case("history survives archiving", archive_held,
                          f"archived={None if archive_topic is None else archive_topic.get('archived')!r}, "
                          f"history={None if archive_hist is None else [e.get('value') for e in archive_hist]!r}"))

    empty_id = _write_deadline(s, "Website Redesign (empty write)")
    _, empty_current, empty_obs = _empty_write(s, empty_id, "")
    cases.append(Case('version_field with "" does not replace April 20', empty_current == NEWER, empty_obs))

    null_id = _write_deadline(s, "Website Redesign (null write)")
    _, null_current, null_obs = _empty_write(s, null_id, None)
    cases.append(Case("version_field with null does not replace April 20", null_current == NEWER, null_obs))

    cap_id = s.ingest({
        "placement": "new_topic", "title": "Website Redesign (history cap)", "topic_kind": "project",
        "fields": [{"name": FIELD, "value": CAP_FIRST, "provenance": "cap-0"}],
    })["topic_id"]
    for i in range(1, CAP_UPDATES):
        s.ingest({"placement": "version_field", "topic_id": cap_id,
                  "fields": [{"name": FIELD, "value": f"v{i:03d}", "provenance": f"cap-{i}"}]})
    cap_hist = history_entries(s, cap_id)
    cap_values = None if cap_hist is None else [e.get("value") for e in cap_hist]
    first_present = bool(cap_values) and CAP_FIRST in cap_values
    cases.append(Case("the first value is still in the history after 501 updates", first_present,
                      f"length={None if cap_values is None else len(cap_values)}, "
                      f"first {CAP_FIRST!r} present={first_present}"))

    observations = [
        {"name": "lost earlier value", "lost": lost,
         "summary": (f"the earlier value {OLDER} is missing after the update"
                     if lost else f"the earlier value {OLDER} is still in the history after the update")},
        {"name": "empty value becoming current",
         "empty_current": empty_current == "", "null_current": null_current is None,
         "summary": (f'empty write current={empty_current!r}; null write current={null_current!r}')},
    ]
    measurements = {
        "history_cap": {
            "updates": CAP_UPDATES, "first": CAP_FIRST, "first_present": first_present,
            "length": None if cap_values is None else len(cap_values),
            "newest": None if not cap_values else cap_values[0],
        },
        "keeps_history": s.describe()["keeps_history"],
    }
    return Verdict.from_cases("C4", cases, observations=observations, measurements=measurements)
