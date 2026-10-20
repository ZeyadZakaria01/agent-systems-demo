"""The per-step change table: upstream, step 1, step 2, step 3 verdicts per row, changed cells marked.

Each measured cell is compared, verdict for verdict, with the nearest earlier cell of the same row in the chain that
holds a real verdict (step 1 with upstream, step 2 with step 1, step 3 with step 2). A changed cell reads
`**<before> → <after>** (vs <system>)`, naming the system it was compared with; an unchanged one just the verdict;
an unmeasured one `—`. `error` is not a verdict on the scale (a crashed check, a failed setup): an `error` cell is
shown as `error`, never marked, and never the baseline of a later cell, so a step that failed to run neither
fabricates nor hides changes. Rows whose verdict comes from a random-ID test carry their counts in
`Verdict.measurements["random_id_counts"] = {"<label>": [count, of]}` (C2(a): stale value current 10 of 20): the
table shows them beside the verdict and never compares them, so chance variation between two runs of the same engine
is not read as an engine effect (spec story 13; F9, F11). Generic over rows and verdicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from demo.checks import Row
from demo.verdict import ERROR, Verdict, last_verdict

CHAIN = ("upstream", "step1", "step2", "step3")
HEADERS = {"upstream": "upstream", "step1": "step 1", "step2": "step 2", "step3": "step 3"}
RANDOM_ID_KEY = "random_id_counts"


@dataclass
class ChangeCell:
    system: str
    verdict: str
    compared_with: str | None = None  # the system whose verdict this one was compared with; None if there was none
    changed_from: str | None = None  # that system's verdict when it differs from this one
    random_id_counts: dict[str, list[int]] = field(default_factory=dict)  # shown, never compared


def change_cells(row_id: str, verdicts: list[Verdict], chain: tuple[str, ...] = CHAIN) -> dict[str, ChangeCell | None]:
    cells: dict[str, ChangeCell | None] = {}
    previous: tuple[str, str] | None = None  # (system, verdict) of the nearest earlier real verdict
    for system_id in chain:
        v = last_verdict(verdicts, system_id, row_id)
        if v is None:
            cells[system_id] = None
            continue
        counts = {k: list(n) for k, n in (v.measurements.get(RANDOM_ID_KEY) or {}).items()}
        cell = ChangeCell(system_id, v.verdict, random_id_counts=counts)
        if v.verdict != ERROR:
            if previous is not None:
                cell.compared_with = previous[0]
                cell.changed_from = previous[1] if previous[1] != v.verdict else None
            previous = (system_id, v.verdict)
        cells[system_id] = cell
    return cells


def measured(verdicts: list[Verdict], chain: tuple[str, ...] = CHAIN) -> list[str]:
    return [s for s in chain if any(v.system == s for v in verdicts)]


def changes_per_step(rows: list[Row], verdicts: list[Verdict],
                     chain: tuple[str, ...] = CHAIN) -> dict[str, list[dict]]:
    """For each measured system after the first of the chain: the rows whose verdict changed, with before/after and
    the system compared with."""
    out: dict[str, list[dict]] = {}
    for system_id in measured(verdicts, chain)[1:]:
        cells = ((r, change_cells(r.id, verdicts, chain)[system_id]) for r in rows)
        out[system_id] = [{"row": r.id, "from": c.changed_from, "to": c.verdict, "vs": c.compared_with}
                          for r, c in cells if c and c.changed_from]
    return out


def _counts(cell: ChangeCell) -> str:
    return "".join(f" ({label} {n}/{of})" for label, (n, of) in cell.random_id_counts.items())


def _text(cell: ChangeCell | None) -> str:
    if cell is None:
        return "—"
    if cell.changed_from:
        verdict = f"**{cell.changed_from} → {cell.verdict}** (vs {HEADERS.get(cell.compared_with, cell.compared_with)})"
    else:
        verdict = cell.verdict
    return verdict + _counts(cell)


def _summary(system_id: str, rows: list[Row], verdicts: list[Verdict], chain: tuple[str, ...]) -> str:
    """One line for a measured step: per system it was compared with (rows can differ), what changed; rows with an
    `error` cell are named as not compared."""
    name = lambda s: HEADERS.get(s, s)  # noqa: E731
    by_baseline: dict[str, list[tuple[str, ChangeCell]]] = {}
    errored, no_baseline = [], []
    for r in rows:
        cell = change_cells(r.id, verdicts, chain)[system_id]
        if cell is None:
            continue
        if cell.verdict == ERROR:
            errored.append(r.id)
        elif cell.compared_with is None:
            no_baseline.append(r.id)
        else:
            by_baseline.setdefault(cell.compared_with, []).append((r.id, cell))
    parts = []
    for baseline in sorted(by_baseline, key=chain.index):
        cells = by_baseline[baseline]
        changed = [f"{row} ({c.changed_from} → {c.verdict})" for row, c in cells if c.changed_from]
        rows_note = f" ({', '.join(row for row, _ in cells)})" if len(by_baseline) > 1 else ""
        parts.append(f"vs {name(baseline)}{rows_note}: " + ("changed: " + ", ".join(changed) if changed else "no change"))
    if errored:
        parts.append(f"not compared, error: {', '.join(errored)}")
    if no_baseline:
        parts.append(f"nothing earlier to compare with: {', '.join(no_baseline)}")
    return f"- {name(system_id)} " + ("; ".join(parts) or "has no cells") + "."


def render_change_table(rows: list[Row], verdicts: list[Verdict], chain: tuple[str, ...] = CHAIN) -> str:
    """Markdown: one row per scorecard row, one column per system of the chain, then one line per measured step
    after the first stating, per system compared with, what changed."""
    lines = ["| Row | " + " | ".join(HEADERS.get(s, s) for s in chain) + " |", "|---|" + "---|" * len(chain)]
    for r in rows:
        cells = change_cells(r.id, verdicts, chain)
        label = f"{r.id} (control)" if r.control else r.id
        lines.append(f"| {label} | " + " | ".join(_text(cells[s]) for s in chain) + " |")
    lines.append("")
    lines += [_summary(s, rows, verdicts, chain) for s in measured(verdicts, chain)[1:]]
    lines.append("- Changed cells are bold (`before → after`, naming the system compared with: the nearest earlier real "
                 "verdict of the row, never an `error`); counts from random-ID tests are shown, not compared.")
    return "\n".join(lines)
