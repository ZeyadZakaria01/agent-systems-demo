"""Staleness windows reported beside the scorecard.

A check reports a window by putting entries in its verdict's `measurements["windows"]`:
`{"name": "Dependent-topic staleness window", "value": "unbounded (C3 absent)", ...}`. The window cites the run
that produced it: this table adds the row it came from and that verdict's snapshot links. Both windows (the merge
revision window, ticket 04, and the dependent-topic window, ticket 05) use the same entries; the reference GEM's are
counted in interactions (`interactions`), a server's in seconds.
"""

from __future__ import annotations

from demo.adapter import System
from demo.verdict import Verdict


def interactions(system: System) -> int | None:
    """Interactions the system has counted so far (its `read_state()["interactions"]`: every ingest and query, rejected
    ones too, no stored-state read), or `None` for a system that does not count them (MemState, the baseline). A
    window is measured in interactions where this is not `None`, in seconds otherwise."""
    return system.read_state().get("interactions")


def window_entries(verdicts: list[Verdict]) -> list[dict]:
    out = []
    for v in verdicts:
        for w in v.measurements.get("windows") or []:
            out.append(
                {
                    "system": v.system,
                    "window": w["name"],
                    "value": w["value"],
                    "row": v.row,
                    "snapshots": list(v.snapshots),
                }
            )
    return out


def render_windows(verdicts: list[Verdict]) -> str:
    """Markdown table of every window reported, or "" when no verdict reports one."""
    entries = window_entries(verdicts)
    if not entries:
        return ""
    lines = ["| System | Window | Value | Run cited |", "|---|---|---|---|"]
    for e in entries:
        cited = f"{e['row']}: " + (" ".join(f"[{p}]" for p in e["snapshots"]) or "no snapshot")
        lines.append(f"| {e['system']} | {e['window']} | {e['value'].replace('|', chr(92) + '|')} | {cited} |")
    return "\n".join(lines)
