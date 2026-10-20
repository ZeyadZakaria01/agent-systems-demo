"""Scorecard rendering, generic over rows and over system columns.

A `Column` is a header plus the system ids that feed it; a cell shows the verdict of the last of those systems that
has one for the row (so the patch column follows step 1 → 3 and shows the last step measured; its header says which:
`{last}` in a header is replaced by that system's id, `no step measured` if none ran). Cells read
`<verdict> [<snapshot path>]...` (one link per fresh system the check opened); `—` means the row was not run on that system. Fails and absences are counted
separately (ADR 0002: a missing capability is open research, not a defect).
"""

from __future__ import annotations

from dataclasses import dataclass

from demo.checks import Row
from demo.deviations import DEVIATIONS, Deviation
from demo.verdict import ABSENT, ERROR, FAIL, NOT_SCORED, PARTIAL, PASS, Verdict, last_verdict

COUNT_ORDER = (PASS, PARTIAL, FAIL, ABSENT, NOT_SCORED, ERROR)


@dataclass(frozen=True)
class Column:
    header: str
    systems: tuple[str, ...]

    def title(self, verdicts: list[Verdict]) -> str:
        """The header with `{last}` resolved to the last of this column's systems that has a verdict."""
        if "{last}" not in self.header:
            return self.header
        measured = [s for s in self.systems if any(v.system == s for v in verdicts)]
        return self.header.replace("{last}", measured[-1] if measured else "no step measured")


COLUMNS = (
    Column("upstream (Kuzu)", ("upstream",)),
    Column("bitemporal patch ({last}, LadybugDB)", ("step1", "step2", "step3")),
    Column("baseline", ("baseline",)),
)


def cell_verdict(column: Column, row_id: str, verdicts: list[Verdict]) -> Verdict | None:
    found = None
    for system_id in column.systems:
        found = last_verdict(verdicts, system_id, row_id) or found
    return found


def _esc(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _cell(v: Verdict | None) -> str:
    if v is None:
        return "—"
    return " ".join([v.verdict, *(f"[{p}]" for p in v.snapshots)])


def counts(column: Column, rows: list[Row], verdicts: list[Verdict]) -> dict[str, int]:
    tally = {k: 0 for k in COUNT_ORDER}
    for r in rows:
        v = cell_verdict(column, r.id, verdicts)
        if v is not None:
            tally[v.verdict] += 1
    return tally


def render_scorecard(rows: list[Row], columns: tuple[Column, ...], verdicts: list[Verdict]) -> str:
    lines = ["| Row | [P1]'s claim | " + " | ".join(_esc(c.title(verdicts)) for c in columns) + " |",
             "|---|---|" + "---|" * len(columns)]
    for r in rows:
        label = f"{r.id} (control)" if r.control else r.id
        cells = " | ".join(_esc(_cell(cell_verdict(c, r.id, verdicts))) for c in columns)
        lines.append(f"| {_esc(label)} | {_esc(r.claim)} | {cells} |")
    tallies = [" · ".join(f"{k} {n}" for k, n in counts(c, rows, verdicts).items()) for c in columns]
    lines.append("| **Counts** | | " + " | ".join(tallies) + " |")
    return "\n".join(lines)


def render_deviations(deviations: tuple[Deviation, ...] = DEVIATIONS) -> str:
    lines = ["| Item | As shipped | Used here | Why |", "|---|---|---|---|"]
    lines += [f"| {_esc(d.item)} | {_esc(d.as_shipped)} | {_esc(d.used_here)} | {_esc(d.why)} |" for d in deviations]
    return "\n".join(lines)
