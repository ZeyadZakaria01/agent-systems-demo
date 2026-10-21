"""Identical undated writes and plain reads for C5 and the latency ramps.

One generator drives both (spec stories 26, 41, 43). Sizes 100 / 250 / 500 / 1,000 / 2,000, each on its own
fresh database. `--ramp-repeats` (default 1 while building, 3 for the run of record) is set on this module by the
runner, and the check reads every constant through it (`ramp.REPEATS`), so a test patches each constant once.
Each ramp takes `QUERY_SAMPLES` plain reads, so the query latency has a median and a range. The largest ramp of a
system that accepts `valid_at` also takes `ASOF_SAMPLES` as-of reads, timed apart from the plain ones.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime

from demo.adapter import System

STEPS = (100, 250, 500, 1000, 2000)
FORGET_GATE = (
    500  # Policies.topic_count_soft_limit; the forgetting pass runs once the topic count (archived included) reaches it
)
FORGET_THRESHOLD = 0.05
REPEATS = 1
QUERY_SAMPLES = 5
ASOF_SAMPLES = 20  # as-of reads timed at the largest ramp size, by systems that accept `valid_at`
ARCHIVE_WAIT_S = 20.0


def ingest_undated(system: System, i: int) -> dict:
    """One undated `new_topic` write. Titles are distinct so the Reasoner has nothing to merge."""
    return system.ingest(
        {
            "placement": "new_topic",
            "title": f"Ramp Topic {i:04d}",
            "summary": "Identical undated write for the C5 and latency ramps.",
            "topic_kind": "note",
            "fields": [{"name": "Index", "value": str(i), "provenance": "ramp"}],
        }
    )


def plain_read(system: System) -> dict:
    return system.query({"q": "Ramp Topic", "stages": ["semantic"], "top_k": 8})


def as_of_read(system: System) -> dict:
    """The plain read with `valid_at` (now): what a dated history costs to read at a moment."""
    return system.query(
        {"q": "Ramp Topic", "stages": ["semantic"], "top_k": 8, "valid_at": datetime.now(UTC).isoformat()}
    )


def filler(system: System, i: int) -> dict:
    """Field-less topic used to grow the store to the forgetting gate without bumping anyone."""
    return system.ingest(
        {"placement": "new_topic", "title": f"Filler {i:04d}", "summary": f"Field-less filler topic number {i}"}
    )


def archive_stats(system: System) -> dict:
    """`{total, archived}`. `archived` is `None` when the system has no archived flag (the baseline)."""
    all_ids = system.list_topic_ids(include_archived=True)
    if all_ids is not None:
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
