"""The merge extras (spec story 28): observations run beside C2(a) so that MemState's "not what is permanently
erased" promise is cited only after a run. Each function takes a system on a database where its titles are unused,
returns a plain dict (JSON-ready; `summary` is the one-line reading) and never judges: these are observations, not
verdicts.

- `three_same_title`: three topics share one title, each holding a different value.
- `active_into_archived`: an active topic is merged into an archived duplicate. The archived duplicate gets a
  forced low id through a labelled setup write (the merge keeps the lower id, `docs/findings.md` F9) so that it is
  the survivor; archiving it is a labelled setup write too. A system without those editor paths reports "skipped".
"""

from __future__ import annotations

import uuid

from demo.systems.adapter import System
from demo.systems.reads import NO_VALUE, current_value, history_values, read_request
from demo.workloads.merge import (
    DEFAULT_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
    FIELD,
    NEWER,
    NEWER_PROVENANCE,
    OLDER,
    DroppedState,
    new_topic,
    topic_gone_or_archived,
    unique_title,
)

LOW_ID_PREFIX = "00000000-0000-4000-8000-"  # followed by 12 random hex digits: sorts below any uuid4 (the keeper)


def _shown(value: object) -> object:
    return "NO_VALUE" if value is NO_VALUE else value


def _survivor_view(system: System, topic_id: str) -> dict:
    topic = system.read_topic(topic_id)
    field = topic["fields"].get(FIELD) if topic else None
    return {
        "id": topic_id,
        "archived": topic.get("archived") if topic else None,
        "current": _shown(current_value(field)),
        "history": history_values(field),
    }


def three_same_title(system: System, timeout: float = DEFAULT_TIMEOUT_S, interval: float = DEFAULT_INTERVAL_S) -> dict:
    title = unique_title("Vendor Contract (three)")
    values = [OLDER, NEWER, "May 31"]
    ids = [
        system.ingest(new_topic(f"{title} {i + 1}", FIELD, v, f"source-{i + 1}"))["topic_id"]
        for i, v in enumerate(values)
    ]
    retitled = all(
        system.setup_write(
            "patch_topic", label="give the three topics one title (values untouched)", topic_id=t, title=title
        )
        is not None
        for t in ids
    )
    if retitled:  # one scan sees all three at once (a three-way tie); this ingest is the trigger
        system.ingest({"placement": "extend_topic", "topic_id": min(ids), "fields": []})
    else:  # no retitling: the plain way, three same-title writes (each ingest triggers its own scan, pairwise)
        title = unique_title("Vendor Contract (three, plain)")
        ids = [system.ingest(new_topic(title, FIELD, v, f"source-{i + 1}"))["topic_id"] for i, v in enumerate(values)]
    distinct = sorted(set(ids))

    def active() -> list[str]:
        return [t for t in distinct if not topic_gone_or_archived(system, t)]

    waited = system.wait_until(lambda: len(active()) <= 1, timeout, interval)
    survivors = active()
    deleted = [t for t in distinct if system.read_topic(t) is None]
    out = {
        "name": "three topics sharing one title",
        "title": title,
        "arranged_as_three_way_tie": retitled,
        "ids_in_write_order": ids,
        "values_in_write_order": values,
        "timed_out": waited.timed_out,
        "window_s": None if waited.timed_out else waited.elapsed,
        "survivor_ids": survivors,
        "deleted_ids": deleted,
        "survivor_is_lowest_id": survivors == [min(distinct)] if len(distinct) > 1 else None,
        "survivors": [_survivor_view(system, t) for t in survivors],
    }
    one = out["survivors"][0] if len(survivors) == 1 else None
    out["summary"] = (
        f"{'three-way tie arranged by retitling' if retitled else 'three plain same-title writes (pairwise scans)'}; {len(distinct)} ids written; {len(survivors)} active after "
        f"{'timeout' if waited.timed_out else f'{waited.elapsed:.2f}s'}; deleted {len(deleted)}"
        + (
            f"; survivor {one['id']} current={one['current']!r} history={one['history']!r}"
            f" (lowest id: {out['survivor_is_lowest_id']}); values written {values!r}"
            if one
            else ""
        )
    )
    return out


def active_into_archived(
    system: System, timeout: float = DEFAULT_TIMEOUT_S, interval: float = DEFAULT_INTERVAL_S
) -> dict:
    title = unique_title("Vendor Contract (archived)")
    low_id = LOW_ID_PREFIX + uuid.uuid4().hex[:12]
    created = system.setup_write(
        "create_topic",
        label="archived duplicate with a forced low id (so it is the merge keeper)",
        topic_id=low_id,
        title=title,
        topic_kind="contract",
    )
    if created is None:
        return {
            "name": "active topic merged into an archived duplicate",
            "skipped": True,
            "summary": "skipped: the system has no editor path to force an id and archive a topic",
        }
    system.ingest(
        {
            "placement": "extend_topic",
            "topic_id": low_id,
            "fields": [{"name": FIELD, "value": OLDER, "provenance": "archived-copy"}],
        }
    )
    system.setup_write(
        "patch_topic", label="archive the duplicate before the active one is written", topic_id=low_id, archived=True
    )
    active_id = system.ingest(new_topic(title, FIELD, NEWER, NEWER_PROVENANCE))["topic_id"]
    waited = system.wait_until(
        lambda: topic_gone_or_archived(system, active_id) == DroppedState.DELETED, timeout, interval
    )
    keeper = _survivor_view(system, low_id)
    active_state = topic_gone_or_archived(system, active_id)
    in_v1 = any(c["topic_id"] == low_id for c in system.query(read_request(low_id, explain=True))["candidates"])
    out = {
        "name": "active topic merged into an archived duplicate",
        "skipped": False,
        "title": title,
        "archived_id": low_id,
        "active_id": active_id,
        "timed_out": waited.timed_out,
        "window_s": None if waited.timed_out else waited.elapsed,
        "active_topic_state": active_state or "still active",
        "survivor": keeper,
        "survivor_retrievable_through_v1": in_v1,
        "values_written": {"archived": OLDER, "active": NEWER},
    }
    out["summary"] = (
        f"active topic {out['active_topic_state']}; survivor {low_id} archived={keeper['archived']} "
        f"current={keeper['current']!r} history={keeper['history']!r}; "
        f"survivor retrievable through /v1 read: {in_v1}; written: archived {OLDER!r}, active {NEWER!r}"
        + (" [merge not seen within the timeout]" if waited.timed_out else "")
    )
    return out
