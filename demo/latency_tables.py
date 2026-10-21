"""Latency table for the C5 ramps. `render_latency` returns "" when no C5-2 run is in the verdicts.

Every ramp has one ingest median, `QUERY_SAMPLES` query reads and one settle time (the poll floor is 0.1 s; it is
not a Reasoner wait). `aggregate` folds the repeats of one (system, n) into a median and a min-max range (the as-of reads of the largest n
get their own table); a
difference of medians inside the larger range is reported as "no measurable difference" (spec story 43), for
ingest and for query, between ADJACENT chain steps only (the registry order in `demo/systems.py`). Systems whose
C5-2 verdict is `absent` (the baseline) are left out, and so is a system whose ramps carry no timing (the reference
GEM: in-process milliseconds are not comparable with an HTTP server, so its C5-2 runs once and times nothing). A table
from fewer than `MIN_REPEATS`
repeats is labelled provisional, with its own note, and never prints "no measurable difference": one repeat gives the
ingest no range.
"""

from __future__ import annotations

import statistics

from demo.ramp import no_measurable_difference
from demo.systems import SYSTEMS
from demo.verdict import ABSENT, Verdict

NOTE = ("A difference of medians no larger than the larger sample range is reported as "
        "no measurable difference (spec story 43). Ingest samples are the per-repeat medians, query samples are every "
        "plain read.")
PROVISIONAL_NOTE = ("Provisional: at least one (system, n) has fewer than {min} repeats, so the ingest range is "
                    "narrower than the machine's real variation and the table makes no claim that two systems do or "
                    "do not differ. A single run is reported as one run (spec story 43); {min} repeats of each ramp lift the label.")
MIN_REPEATS = 3
METRICS = ("ingest", "query", "settle")


def _stats(samples: list[float]) -> dict | None:
    if not samples:
        return None
    return {"median": round(statistics.median(samples), 3), "min": round(min(samples), 3),
            "max": round(max(samples), 3), "samples": list(samples)}


def aggregate(verdicts: list[Verdict]) -> list[dict]:
    """One entry per (system, n) of every C5-2 verdict that is not `absent`: `ingest` / `query` / `settle` hold
    `{median, min, max, samples}` (or None), `archived` the sorted archived counts seen, `repeats` the ramp count."""
    out = []
    for v in verdicts:
        if v.row != "C5-2" or v.verdict == ABSENT:
            continue
        by_n: dict[int, list[dict]] = {}
        for r in v.measurements.get("ramps") or []:
            if "ingest_median_ms" in r:  # an untimed ramp (the reference GEM) has no latency to tabulate
                by_n.setdefault(r["n"], []).append(r)
        for n, ramps in sorted(by_n.items()):
            out.append({
                "system": v.system, "n": n, "repeats": len(ramps),
                "ingest": _stats([r["ingest_median_ms"] for r in ramps if r.get("ingest_median_ms") is not None]),
                "query": _stats([q for r in ramps for q in r.get("query_samples_ms") or []]),
                "as_of": _stats([q for r in ramps for q in r.get("as_of_samples_ms") or []]),
                "settle": _stats([r["settle_s"] for r in ramps if r.get("settle_s") is not None]),
                "archived": sorted({r["archived"] for r in ramps if r.get("archived") is not None}),
            })
    return out


def _adjacent_pairs(systems: list[str]) -> list[tuple[str, str]]:
    """Consecutive registry ids that both have rows: upstream -> step1 -> step2 -> step3, never baseline or a gap."""
    order = [s for s in SYSTEMS if s != "baseline"]
    return [(a, b) for a, b in zip(order, order[1:]) if a in systems and b in systems]


def no_difference_notes(entries: list[dict]) -> list[str]:
    by_key = {(e["system"], e["n"]): e for e in entries}
    notes = []
    for a, b in _adjacent_pairs(sorted({e["system"] for e in entries})):
        for n in sorted({n for _, n in by_key}):
            ea, eb = by_key.get((a, n)), by_key.get((b, n))
            if ea is None or eb is None:
                continue
            for metric in ("ingest", "query"):
                sa, sb = ea[metric], eb[metric]
                if sa and sb and no_measurable_difference(sa["samples"], sb["samples"]):
                    notes.append(f"{a} vs {b} at n={n}, {metric}: no measurable difference "
                                 f"(medians {sa['median']} / {sb['median']} ms)")
    return notes


def _cell(stat: dict | None) -> str:
    return "—" if stat is None else f"{stat['median']} ({stat['min']}–{stat['max']})"


def render_latency(verdicts: list[Verdict]) -> str:
    entries = aggregate(verdicts)
    if not entries:
        return ""
    provisional = min(e["repeats"] for e in entries) < MIN_REPEATS
    lines = [
        "### Latency ramps" + (f" (provisional: {min(e['repeats'] for e in entries)} repeat(s), "
                               f"fewer than {MIN_REPEATS})" if provisional else ""),
        "",
        "Median (min–max) over the repeats of each (system, n).",
        "",
        "| System | n | repeats | ingest (ms) | query (ms) | settle time (poll floor 0.1 s) (s) | archived |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for e in entries:
        archived = "n/a" if not e["archived"] else "/".join(str(a) for a in e["archived"])
        lines.append(f"| {e['system'] or '—'} | {e['n']} | {e['repeats']} | {_cell(e['ingest'])} "
                     f"| {_cell(e['query'])} | {_cell(e['settle'])} | {archived} |")
    lines += ["", PROVISIONAL_NOTE.format(min=MIN_REPEATS) if provisional else NOTE]
    if as_of := [e for e in entries if e["as_of"]]:
        lines += ["", "As-of reads (`valid_at`) beside the plain reads at the same n; median (min–max) over every as-of read:", "",
                  "| System | n | as-of reads | as-of read (ms) | plain read (ms) |", "|---|---:|---:|---:|---:|"]
        lines += [f"| {e['system'] or '—'} | {e['n']} | {len(e['as_of']['samples'])} | {_cell(e['as_of'])} "
                  f"| {_cell(e['query'])} |" for e in as_of]
    if not provisional and (notes := no_difference_notes(entries)):
        lines += ["", *[f"- {n}" for n in notes]]
    return "\n".join(lines)


def with_latency(scorecard: str, verdicts: list[Verdict]) -> str:
    """The scorecard with the latency table appended when there is one (shared by the recorded and live runners)."""
    latency = render_latency(verdicts)
    return scorecard + "\n\n" + latency if latency else scorecard
