"""Helpers for reading `/v1/query` responses and stored topics the same way on every system."""

from __future__ import annotations

from typing import Any


def read_request(topic_id: str, explain: bool = False, q: str = "read") -> dict:
    """The deterministic read of one topic: temporal stage only, no similarity involved (spec "Reads used by checks")."""
    return {"q": q, "stages": ["temporal"], "topic_ids": [topic_id], "explain": explain}


def field_in_response(response: dict, topic_id: str, name: str) -> dict | None:
    for cand in response["candidates"]:
        if cand["topic_id"] == topic_id:
            return next((f for f in cand["fields"] if f["name"] == name), None)
    return None


class _NoValue:
    """Marker for "the field has no current value", distinct from a `null` that was written and became current."""

    def __repr__(self) -> str:
        return "NO_VALUE"

    def __bool__(self) -> bool:
        return False


NO_VALUE = _NoValue()


def current_value(field: dict | None) -> Any:
    """Current value of a field, or `NO_VALUE`.

    Every field the suite reads states `current` itself: query responses, and stored topics once the adapter has
    normalised them (`MemStateSystem._read_topic`; upstream's `history[0]` rule lives only there). `None` means no
    current value (even if history exists, e.g. a future-dated entry); an entry's `value` may itself be `None`
    (a `null` write).
    """
    if field is None:
        return NO_VALUE
    entry = field["current"]
    return NO_VALUE if entry is None else entry.get("value")


def history_values(field: dict | None) -> list | None:
    """Values newest first, or `None` when the system keeps no history (a nothing-value)."""
    if not field or field.get("history") is None:
        return None
    return [e.get("value") for e in field["history"]]
