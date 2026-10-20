"""Identical undated writes and plain reads for C5 and the latency ramps.

One generator drives both (spec stories 26, 41, 43). Sizes 100 / 250 / 500 / 1,000 / 2,000, each on its own
fresh database. `--ramp-repeats` (default 1 while building, 3 for the run of record) lives here so the check
and the runner share it. Tests monkeypatch `STEPS` and `FORGET_GATE`.
"""

from __future__ import annotations

import statistics

from demo.client import System

STEPS = (100, 250, 500, 1000, 2000)
FORGET_GATE = 500  # Policies.topic_count_soft_limit; the forgetting pass runs once the topic count (archived included) reaches it
FORGET_THRESHOLD = 0.05
REPEATS = 1
ARCHIVE_WAIT_S = 20.0


def ingest_undated(system: System, i: int) -> dict:
    """One undated `new_topic` write. Titles are distinct so the Reasoner has nothing to merge."""
    return system.ingest({
        "placement": "new_topic",
        "title": f"Ramp Topic {i:04d}",
        "summary": "Identical undated write for the C5 and latency ramps.",
        "topic_kind": "note",
        "fields": [{"name": "Index", "value": str(i), "provenance": "ramp"}],
    })


def plain_read(system: System) -> dict:
    return system.query({"q": "Ramp Topic", "stages": ["semantic"], "top_k": 8})


def filler(system: System, i: int) -> dict:
    """Field-less topic used to grow the store to the forgetting gate without bumping anyone."""
    return system.ingest({"placement": "new_topic", "title": f"Filler {i:04d}",
                          "summary": f"Field-less filler topic number {i}"})


def archive_stats(system: System) -> dict:
    """`{total, archived}`. `archived` is `None` when the system has no archived flag (the baseline)."""
    if hasattr(system, "list_topic_ids"):
        all_ids = system.list_topic_ids(include_archived=True)
        live = system.list_topic_ids(include_archived=False)
        return {"total": len(all_ids), "archived": len(all_ids) - len(live)}
    topics = system.read_state()["topics"]
    flags = [t.get("archived") for t in topics.values()]
    if not topics or all(f is None for f in flags):
        return {"total": len(topics), "archived": None}
    return {"total": len(topics), "archived": sum(f is True for f in flags)}


def scored_latencies(system: System, op: str) -> list[float]:
    return [e["latency_ms"] for e in system.log.of_kind("scored") if e["op"] == op and e.get("latency_ms") is not None]


def median_ms(samples: list[float]) -> float | None:
    return None if not samples else round(statistics.median(samples), 3)


def range_ms(samples: list[float]) -> tuple[float, float] | None:
    return None if not samples else (round(min(samples), 3), round(max(samples), 3))


def no_measurable_difference(a: list[float], b: list[float]) -> bool:
    """The difference of medians is not measurable when it is no larger than the larger sample range."""
    if not a or not b:
        return False
    spread = max(max(a) - min(a), max(b) - min(b))
    return abs(statistics.median(a) - statistics.median(b)) <= spread
