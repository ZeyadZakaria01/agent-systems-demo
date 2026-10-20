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

    A field that states `current` (adapter output, query responses) is taken at its word: `None` there means no
    current value (even if history exists, e.g. a future-dated entry), an entry's `value` may itself be `None` (a
    `null` write). Only a raw stored-topic field without a `current` key falls back to its newest-first
    `history[0]`, which is upstream's definition of current (`datamodel/fields.py:77`).
    """
    if field is None:
        return NO_VALUE
    if "current" in field:
        entry = field["current"]
        return NO_VALUE if entry is None else entry.get("value")
    history = field.get("history")
    return history[0].get("value") if history else NO_VALUE


def history_values(field: dict | None) -> list | None:
    """Values newest first, or `None` when the system keeps no history (a nothing-value)."""
    if not field or field.get("history") is None:
        return None
    return [e.get("value") for e in field["history"]]
