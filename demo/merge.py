"""Triggering the Reasoner's duplicate merge and waiting for it (C2(a), C4's merge case, the merge extras).

MemState merges topics with the same title in a background task after every `/v1/ingest` response; a query never
merges, and nothing reports completion. So a merge is triggered the only way the `/v1` API allows (write a second
`new_topic` with the same title) and awaited by polling state through `System.wait_until`, never by a fixed sleep.

"Merge visible" means one of the pair is gone (read as `None`: deleted) or archived. A system that never creates
a duplicate (the baseline upserts the second `new_topic` into the first row: both writes return the same topic id)
has nothing to wait for: the outcome says so (`upserted`) and carries no window.

Two ways to arrange a duplicate pair (both leave the merge to the system):
- `create_retitled_pair`: the topic to be dropped holds the newer value in every repetition, with random ids.
  MemState keeps the lower id (F9), so the lower-id topic gets the older value and the higher-id topic the newer one;
  both are then given one title by a labelled setup write (`patch_topic`, title only; values are only ever written
  through `/v1`) and a `/v1 extend_topic` with no fields triggers the scan. A system with no way to retitle returns
  `None` for the setup write; the caller falls back to `create_duplicate_pair`.
- `create_duplicate_pair`: two same-title `new_topic` writes, the second being the trigger. Which topic is dropped is
  then chance (random ids), and a system that upserts never creates a duplicate.

The window is measured from the moment the duplicate-creating ingest has returned to the first poll that sees the
merge. It is the wait's `elapsed`, logged by the adapter apart from client latency; it is not the ingest latency.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from demo.adapter import System, Waited
from demo.reads import NO_VALUE, current_value

DEFAULT_TIMEOUT_S = 15.0
DEFAULT_INTERVAL_S = 0.05
FIELD = "Deadline"
OLDER, NEWER = "March 15", "April 20"
OLDER_PROVENANCE, NEWER_PROVENANCE = "kickoff-notes", "pm-email"


class DroppedState(StrEnum):
    DELETED = "deleted"  # the dropped topic reads as missing
    ARCHIVED = "archived"


class SurvivorHeld(StrEnum):
    NEWER = "newer"
    OLDER = "older"


@dataclass(frozen=True)
class PairSpec:
    """What a duplicate pair carries: one field written twice, `older` first, `newer` second."""

    older_value: object = OLDER
    newer_value: object = NEWER
    field: str = FIELD
    older_provenance: str = OLDER_PROVENANCE
    newer_provenance: str = NEWER_PROVENANCE


DEADLINE = PairSpec()


def unique_title(stem: str) -> str:
    """A title no other write in the database uses (repetitions inside one DB must not merge with each other)."""
    return f"{stem} {uuid.uuid4().hex[:10]}"


def new_topic(title: str, field: str, value: object, provenance: str, topic_kind: str = "contract") -> dict:
    return {"placement": "new_topic", "title": title, "topic_kind": topic_kind,
            "fields": [{"name": field, "value": value, "provenance": provenance}]}


@dataclass(frozen=True)
class Pair:
    """Two same-title topics written in order: `older` first, `newer` second (the merge trigger)."""

    title: str
    field: str
    older_id: str
    newer_id: str
    older_value: object
    newer_value: object

    @property
    def upserted(self) -> bool:
        return self.older_id == self.newer_id


@dataclass(frozen=True)
class MergeOutcome:
    pair: Pair
    merged: bool  # False: neither topic disappeared or was archived within the timeout
    waited: Waited | None  # None when the system upserted (no duplicate, nothing to wait for)
    survivor_id: str | None
    dropped_id: str | None
    dropped_state: DroppedState | None

    @property
    def window_s(self) -> float | None:
        return None if self.waited is None or self.waited.timed_out else self.waited.elapsed

    @property
    def survivor_held(self) -> SurvivorHeld | None:
        """Which of the pair's values the survivor was written with; `None` without a merge of two topics."""
        if self.survivor_id is None or self.pair.upserted:
            return None
        return SurvivorHeld.NEWER if self.survivor_id == self.pair.newer_id else SurvivorHeld.OLDER

    @property
    def dropped_held_newer(self) -> bool | None:
        """Did the dropped topic hold the newer value (the arrangement C2(a) needs)? `None` when nothing was dropped."""
        return None if self.dropped_id is None else self.dropped_id == self.pair.newer_id


def create_duplicate_pair(system: System, title: str, spec: PairSpec = DEADLINE) -> Pair:
    """Write `title` twice through `/v1/ingest new_topic`; the second response ends the call (the merge trigger)."""
    older = system.ingest(new_topic(title, spec.field, spec.older_value, spec.older_provenance))["topic_id"]
    newer = system.ingest(new_topic(title, spec.field, spec.newer_value, spec.newer_provenance))["topic_id"]
    return Pair(title, spec.field, older, newer, spec.older_value, spec.newer_value)


def topic_gone_or_archived(system: System, topic_id: str) -> DroppedState | None:
    topic = system.read_topic(topic_id)
    if topic is None:
        return DroppedState.DELETED
    return DroppedState.ARCHIVED if topic.get("archived") else None


def await_merge(system: System, pair: Pair, timeout: float = DEFAULT_TIMEOUT_S,
                interval: float = DEFAULT_INTERVAL_S) -> MergeOutcome:
    """Poll until one of the pair is deleted or archived, or `timeout` seconds pass (a timeout is an outcome)."""
    if pair.upserted:
        return MergeOutcome(pair, True, None, pair.older_id, None, None)
    waited = system.wait_until(
        lambda: any(topic_gone_or_archived(system, t) for t in (pair.older_id, pair.newer_id)), timeout, interval)
    for survivor, dropped in ((pair.older_id, pair.newer_id), (pair.newer_id, pair.older_id)):
        state = topic_gone_or_archived(system, dropped)
        if state:
            return MergeOutcome(pair, True, waited, survivor, dropped, state)
    return MergeOutcome(pair, False, waited, None, None, None)


def create_retitled_pair(system: System, stem: str, spec: PairSpec = DEADLINE) -> Pair | None:
    """Arrange a duplicate pair whose higher-id (to be dropped) topic holds the newer value; `None` when the system
    cannot retitle a topic (the two topics written so far stay, under distinct titles)."""
    tag = unique_title(stem)
    ids = [system.ingest({"placement": "new_topic", "title": f"{tag} {n}", "topic_kind": "contract",
                          "fields": []})["topic_id"] for n in ("first", "second")]
    lower, higher = sorted(ids)
    system.ingest({"placement": "extend_topic", "topic_id": lower,
                   "fields": [{"name": spec.field, "value": spec.older_value, "provenance": spec.older_provenance}]})
    system.ingest({"placement": "extend_topic", "topic_id": higher,
                   "fields": [{"name": spec.field, "value": spec.newer_value, "provenance": spec.newer_provenance}]})
    for topic_id in (lower, higher):
        done = system.setup_write("patch_topic", label="give the pair one title (the editor never writes a value)",
                                  topic_id=topic_id, title=tag)
        if done is None:
            return None
    system.ingest({"placement": "extend_topic", "topic_id": lower, "fields": []})  # the merge trigger
    return Pair(tag, spec.field, lower, higher, spec.older_value, spec.newer_value)


def trigger_and_await_merge(system: System, title: str, spec: PairSpec = DEADLINE,
                            timeout: float = DEFAULT_TIMEOUT_S) -> MergeOutcome:
    """The dropped-holds-newer pair when the system can retitle, else the plain same-title pair; then the wait."""
    pair = create_retitled_pair(system, title, spec) or create_duplicate_pair(system, unique_title(title), spec)
    return await_merge(system, pair, timeout)


def current_after_merge(system: System, outcome: MergeOutcome) -> object:
    """The survivor's current value of the pair's field (`NO_VALUE` when it has none or nothing survived)."""
    if outcome.survivor_id is None:
        return NO_VALUE
    topic = system.read_topic(outcome.survivor_id)
    if topic is None:
        return NO_VALUE
    return current_value(topic["fields"].get(outcome.pair.field))
