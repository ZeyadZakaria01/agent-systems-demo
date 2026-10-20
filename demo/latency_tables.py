"""Latency table for the C5 ramps. `render_latency` returns "" when no C5-2 run is in the verdicts."""

from __future__ import annotations

import statistics

from demo.ramp import no_measurable_difference
from demo.verdict import Verdict

NOTE = ("A difference of medians no larger than the larger sample range is reported as "
        "no measurable difference (spec story 43).")


def _rows(verdicts: list[Verdict]) -> list[dict]:
    out = []
    for v in verdicts:
        if v.row != "C5-2":
            continue
        for r in v.measurements.get("ramps") or []:
            out.append({"system": v.system, **r})
    return out


def render_latency(verdicts: list[Verdict]) -> str:
    rows = _rows(verdicts)
    if not rows:
        return ""
    lines = [
        "### Latency ramps",
        "",
        "| System | n | repeat | ingest median (ms) | query (ms) | Reasoner wait (s) | archived |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        arch = "n/a" if r.get("archived") is None else r["archived"]
        lines.append(
            f"| {r.get('system') or '—'} | {r['n']} | {r['repeat']} | {r.get('ingest_median_ms') if r.get('ingest_median_ms') is not None else '—'} "
            f"| {r.get('query_ms') if r.get('query_ms') is not None else '—'} | {r.get('reasoner_wait_s') if r.get('reasoner_wait_s') is not None else '—'} "
            f"| {arch} |"
        )
    by_sys_n: dict[tuple, list[float]] = {}
    for r in rows:
        if r.get("ingest_median_ms") is None:
            continue
        by_sys_n.setdefault((r.get("system"), r["n"]), []).append(r["ingest_median_ms"])
    systems = sorted({s for s, _ in by_sys_n})
    notes = []
    if len(systems) >= 2:
        for n in sorted({n for _, n in by_sys_n}):
            samples = {s: by_sys_n.get((s, n), []) for s in systems}
            pairs = [(systems[i], systems[j]) for i in range(len(systems)) for j in range(i + 1, len(systems))]
            for a, b in pairs:
                if samples[a] and samples[b] and no_measurable_difference(samples[a], samples[b]):
                    notes.append(f"{a} vs {b} at n={n}: no measurable difference "
                                 f"(medians {statistics.median(samples[a]):.1f} / {statistics.median(samples[b]):.1f} ms)")
    lines += ["", NOTE]
    if notes:
        lines += ["", *[f"- {n}" for n in notes]]
    return "\n".join(lines)
