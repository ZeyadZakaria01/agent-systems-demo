"""Scorecard rendering, generic over rows and over system columns.

A `Column` is a header plus the system ids that feed it; a cell shows the verdict of the last of those systems that
has one for the row (so the patch column follows step 1 → 3 and shows the last step measured; its header says which:
`{last}` in a header is replaced by that system's id, `no step measured` if none ran). A cell whose verdict comes from
an earlier system of the column than the header names (a check restricted by `systems=`) says so: `<verdict> (from
<system>)`. Cells read `<verdict> [snapshot](<run-relative path>)...` (one link per fresh system the check opened;
`(n case(s) n/a)` after the verdict when n cases did not apply to the system); `—` means the row was not run on that
system. Fails and absences are counted
separately (ADR 0002: a missing capability is open research, not a defect).
"""

from __future__ import annotations

from dataclasses import dataclass

from demo.checks import Row
from demo.deviations import DEVIATIONS, Deviation
from demo.systems import STEP_IDS
from demo.verdict import ABSENT, ERROR, FAIL, NOT_SCORED, PARTIAL, PASS, Verdict, last_verdict, measured

COUNT_ORDER = (PASS, PARTIAL, FAIL, ABSENT, NOT_SCORED, ERROR)


@dataclass(frozen=True)
class Column:
    header: str
    systems: tuple[str, ...]

    def last(self, verdicts: list[Verdict]) -> str | None:
        """The last of this column's systems that has a verdict."""
        found = measured(verdicts, self.systems)
        return found[-1] if found else None

    def title(self, verdicts: list[Verdict]) -> str:
        """The header with `{last}` resolved to the last of this column's systems that has a verdict."""
        if "{last}" not in self.header:
            return self.header
        return self.header.replace("{last}", self.last(verdicts) or "no step measured")


COLUMNS = (
    Column("upstream (Kuzu)", ("upstream",)),
    Column("bitemporal patch ({last}, LadybugDB)", STEP_IDS),
    Column("baseline", ("baseline",)),
)


def cell_verdict(column: Column, row_id: str, verdicts: list[Verdict]) -> Verdict | None:
    found = None
    for system_id in column.systems:
        found = last_verdict(verdicts, system_id, row_id) or found
    return found


def esc(text: object) -> str:
    """A table cell: pipes escaped, newlines flattened."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _cell(v: Verdict | None, header_system: str | None = None) -> str:
    """`header_system`: the system the column's header names; a verdict from another system is labelled with it."""
    if v is None:
        return "—"
    n_a = sum(c.held is None for c in v.cases)  # cases that did not apply: the verdict rests on the others
    text = f"{v.verdict} ({n_a} case{'s' * (n_a != 1)} n/a)" if n_a and v.verdict in (PASS, PARTIAL, FAIL) else v.verdict
    if header_system is not None and v.system != header_system:
        text += f" (from {v.system})"
    links = [f"[snapshot]({p})" if len(v.snapshots) == 1 else f"[snapshot {i}]({p})" for i, p in enumerate(v.snapshots, 1)]
    return " ".join([text, *links])


def counts(column: Column, rows: list[Row], verdicts: list[Verdict]) -> dict[str, int]:
    tally = {k: 0 for k in COUNT_ORDER}
    for r in rows:
        v = cell_verdict(column, r.id, verdicts)
        if v is not None:
            tally[v.verdict] += 1
    return tally


def render_scorecard(rows: list[Row], columns: tuple[Column, ...], verdicts: list[Verdict]) -> str:
    lines = ["| Row | [P1]'s claim | " + " | ".join(esc(c.title(verdicts)) for c in columns) + " |",
             "|---|---|" + "---|" * len(columns)]
    for r in rows:
        label = f"{r.id} (control)" if r.control else r.id
        cells = " | ".join(esc(_cell(cell_verdict(c, r.id, verdicts), c.last(verdicts) if len(c.systems) > 1 else None))
                           for c in columns)
        lines.append(f"| {esc(label)} | {esc(r.claim)} | {cells} |")
    tallies = [" · ".join(f"{k} {n}" for k, n in counts(c, rows, verdicts).items()) for c in columns]
    lines.append("| **Counts** | | " + " | ".join(tallies) + " |")
    return "\n".join(lines)


SCOPE_NOTE = ("Verdicts measure the published proof of concept against the paper's conditions; fail and absent mark "
              "gaps its authors state (its README: \"Proof-of-Concept, NOT Full Implementation\"), not defects.")


def render_deviations(deviations: tuple[Deviation, ...] = DEVIATIONS) -> str:
    lines = ["| Item | As shipped | Used here | Why |", "|---|---|---|---|"]
    lines += [f"| {esc(d.item)} | {esc(d.as_shipped)} | {esc(d.used_here)} | {esc(d.why)} |" for d in deviations]
    return "\n".join(lines)
