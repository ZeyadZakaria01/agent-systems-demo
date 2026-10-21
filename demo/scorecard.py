"""Scorecard rendering, generic over rows and over system columns.

One table in three groups (`COLUMNS`): MemState (upstream, step 1, step 2, step 3), Reference (the reference GEM,
phase 1 and 2), Baseline (the versioned row). A `Column` is one system under a group label. The first two columns are
the row and *claimed by [P1]?* (`claimed_by_p1`: §4 and §4.3, filled for every row). Cells read
`<verdict> [snapshot](<run-relative path>)...` (one link per fresh system the check opened; `(n case(s) n/a)` after
the verdict when n cases did not apply to the system; C5's cells add the declared bound beside the active count);
`—` means the row was not run on that system. Fails and absences are counted separately (ADR 0002: a missing
capability is open research, not a defect).

Probes of the proposed C1' and C4' (`Row.probe`) are outside [P1]'s claims and have their own section
(`render_probes`: two cells per time probe, the C4' probe, and the case-level controls). The merge is printed as
existence with the natural random-ID count beside it (`render_merge_existence`); MemState's limits with their numbers
(`render_limits`).
"""

from __future__ import annotations

from dataclasses import dataclass

from demo.checks import Row
from demo.deviations import DEVIATIONS, Deviation
from demo.reference_gem import PHASES, reference_gem_id
from demo.verdict import ABSENT, ERROR, FAIL, NOT_SCORED, PARTIAL, PASS, Verdict, last_verdict

COUNT_ORDER = (PASS, PARTIAL, FAIL, ABSENT, NOT_SCORED, ERROR)


@dataclass(frozen=True)
class Column:
    header: str
    system: str
    group: str = ""

    @property
    def title(self) -> str:
        return f"{self.group}: {self.header}" if self.group else self.header


COLUMNS = (
    Column("upstream (Kuzu)", "upstream", "MemState"),
    Column("step 1", "step1", "MemState"),
    Column("step 2", "step2", "MemState"),
    Column("step 3", "step3", "MemState"),
    *(Column(f"phase {p}", reference_gem_id(p), "Reference") for p in PHASES),
    Column("versioned row", "baseline", "Baseline"),
)

_BY_CONSTRUCTION = "yes: by construction (§4.3)"
_UNDER_TRANSITIONS = "yes: under transitions (§4.3)"
P1_CLAIMS = {
    "C1": _BY_CONSTRUCTION,
    "C2(a)": _BY_CONSTRUCTION,
    "C2(b)": _BY_CONSTRUCTION,
    "C2(c)": _BY_CONSTRUCTION,
    "C2(d)": _BY_CONSTRUCTION,
    "C4": _BY_CONSTRUCTION,
    "C3": 'yes: §4\'s opening, "by construction"; not in §4.3',
    "C5-1": _UNDER_TRANSITIONS,
    "C5-2": _UNDER_TRANSITIONS,
    "C6-1": _UNDER_TRANSITIONS,
    "C6-2": _UNDER_TRANSITIONS,
}
PROBE_CLAIM = "no: probe of a proposed condition"
ROW_LABELS = {
    "C2(d)": "C2(d) lapsed override",
    "C5-1": "C5-1 mechanism",
    "C5-2": "C5-2 natural trajectory",
    "C6-1": "C6-1 clause 1",
    "C6-2": "C6-2 clause 2",
}


def claimed_by_p1(row: Row) -> str:
    """The *claimed by [P1]?* cell: probes are not claimed; a row not in the table reads `—`."""
    return PROBE_CLAIM if row.probe else P1_CLAIMS.get(row.id, "—")


def row_label(row: Row) -> str:
    label = ROW_LABELS.get(row.id, row.id)
    return f"{label} (control)" if row.control else label


def esc(text: object) -> str:
    """A table cell: pipes escaped, newlines flattened."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _bound_note(v: Verdict) -> str:
    """C5's declared bound beside the active topic count; "" for a verdict that measured no active count."""
    m = v.measurements
    if "declared_bound" not in m:
        return ""
    if m.get("active_at_largest_n"):
        count = f"{m['active_at_largest_n']['active']} active topics at n={m['active_at_largest_n']['n']}"
    elif m.get("topics") is not None and m.get("archived_total") is not None:
        count = f"{m['topics'] - m['archived_total']} active topics"
    else:
        return ""
    bound = m["declared_bound"]
    return f"({count}, " + (
        f"declared bound {bound['topics']} topics ({bound['name']}))" if bound else "no declared bound)"
    )


def _cell(v: Verdict | None) -> str:
    if v is None:
        return "—"
    n_a = sum(c.held is None for c in v.cases)  # cases that did not apply: the verdict rests on the others
    text = (
        f"{v.verdict} ({n_a} case{'s' * (n_a != 1)} n/a)" if n_a and v.verdict in (PASS, PARTIAL, FAIL) else v.verdict
    )
    links = [
        f"[snapshot]({p})" if len(v.snapshots) == 1 else f"[snapshot {i}]({p})" for i, p in enumerate(v.snapshots, 1)
    ]
    return " ".join(filter(None, [text, _bound_note(v), *links]))


def cell_verdict(column: Column, row_id: str, verdicts: list[Verdict]) -> Verdict | None:
    return last_verdict(verdicts, column.system, row_id)


def counts(column: Column, rows: list[Row], verdicts: list[Verdict]) -> dict[str, int]:
    tally = dict.fromkeys(COUNT_ORDER, 0)
    for r in rows:
        v = cell_verdict(column, r.id, verdicts)
        if v is not None:
            tally[v.verdict] += 1
    return tally


def render_scorecard(rows: list[Row], columns: tuple[Column, ...], verdicts: list[Verdict]) -> str:
    """The main table: the rows that are [P1]'s claims (probes are in `render_probes`), one column per system."""
    rows = [r for r in rows if not r.probe]
    lines = [
        "| Row | Claimed by [P1]? | " + " | ".join(esc(c.title) for c in columns) + " |",
        "|---|---|" + "---|" * len(columns),
    ]
    for r in rows:
        cells = " | ".join(esc(_cell(cell_verdict(c, r.id, verdicts))) for c in columns)
        lines.append(f"| {esc(row_label(r))} | {esc(claimed_by_p1(r))} | {cells} |")
    tallies = [" · ".join(f"{k} {n}" for k, n in counts(c, rows, verdicts).items()) for c in columns]
    lines.append("| **Counts** | | " + " | ".join(tallies) + " |")
    return "\n".join(lines)


def _accepts_cell(v: Verdict | None) -> str:
    if v is None:
        return "—"
    return str(v.measurements.get("accepts_dates") or "—")


def _control_outcome(v: Verdict | None, case_id: str) -> str:
    if v is None:
        return "—"
    case = next((c for c in v.cases if c.control and c.id == case_id), None)
    return "—" if case is None else "n/a" if case.held is None else "held" if case.held else "broke"


def render_probes(rows: list[Row], columns: tuple[Column, ...], verdicts: list[Verdict]) -> str:
    """`rows`: every scorecard row (the probes are picked out; the controls come from all of them). The probes section (outside [P1]'s claims): a time probe has two cells (accepts dates; answers correctly given
    dates), the C4' probe one; then the case-level controls of every row (the C4 update path, each probe's control
    date), a control case being shown per system as held, broke or n/a."""
    probes = [r for r in rows if r.probe]
    head = "| Probe | " + " | ".join(esc(c.title) for c in columns) + " |"
    rule = "|---|" + "---|" * len(columns)
    lines = [
        "### Probes of the proposed C1′ and C4′, outside [P1]'s claims",
        "",
        "Not claimed by [P1]: each time probe reads C1 as C1′ (the value valid on a date) and has two cells, "
        "whether the system accepts the dates the probe needs and whether it answers correctly given them; "
        "C4′ is C4 plus the retained source message.",
        "",
        head,
        rule,
    ]
    found_by_row = {r.id: {c.system: cell_verdict(c, r.id, verdicts) for c in columns} for r in probes}
    timed = lambda r: any("accepts_dates" in v.measurements for v in found_by_row[r.id].values() if v)  # noqa: E731
    for r in sorted(probes, key=lambda r: not timed(r)):  # the time probes first, then the others (C4')
        found = found_by_row[r.id]
        if timed(r):
            lines.append(
                f"| {esc(r.id)} accepts dates | " + " | ".join(esc(_accepts_cell(v)) for v in found.values()) + " |"
            )
            lines.append(
                f"| {esc(r.id)} answers correctly given dates | "
                + " | ".join(esc(_cell(v)) for v in found.values())
                + " |"
            )
        else:
            lines.append(
                f"| {esc(r.id)} provenance resolves to the stored source | "
                + " | ".join(esc(_cell(v)) for v in found.values())
                + " |"
            )
    lines += ["", render_controls(rows, columns, verdicts)]
    return "\n".join(lines)


def render_controls(rows: list[Row], columns: tuple[Column, ...], verdicts: list[Verdict]) -> str:
    """Case-level controls (cases flagged `control`) of every row, per system: held, broke or n/a."""
    lines = [
        "### Case-level controls",
        "",
        "A control case is the ordinary path beside the case under test (C4's update, a probe's control date): "
        "a system that breaks it is blocking what it should allow.",
        "",
        "| Row: control case | " + " | ".join(esc(c.title) for c in columns) + " |",
        "|---|" + "---|" * len(columns),
    ]
    seen: dict[tuple[str, str], str] = {}
    for r in rows:
        for v in verdicts:
            if v.row == r.id:
                for c in v.cases:
                    if c.control:
                        seen.setdefault((r.id, c.id), c.name)
    for (row_id, case_id), name in seen.items():
        outcomes = [_control_outcome(last_verdict(verdicts, c.system, row_id), case_id) for c in columns]
        lines.append(f"| {esc(row_id)}: {esc(name)} | " + " | ".join(outcomes) + " |")
    if not seen:
        lines.append("| (no control case recorded) | " + " | ".join("—" for _ in columns) + " |")
    return "\n".join(lines)


def render_merge_existence(rows: list[Row], columns: tuple[Column, ...], verdicts: list[Verdict]) -> str:
    """C2(a)'s merge as existence: in the arranged case, does the merge make the superseded value current? The natural
    random-ID count (two same-title writes, no setup) is shown beside it and never compared between systems."""
    lines = [
        "### The merge (C2(a)) as existence",
        "",
        "Existence, not a rate: in the arranged case the dropped topic holds the newer value, so one repetition "
        "that makes the superseded value current decides it. Beside it, the natural count on random IDs "
        "(shown, not compared between systems, never part of the verdict).",
        "",
        "| System | Arranged case (existence) | Natural random-ID count |",
        "|---|---|---|",
    ]
    n = 0
    for c in columns:
        v = cell_verdict(c, "C2(a)", verdicts)
        if v is None:
            continue
        n += 1
        arranged = next((f"{k.name}: {k.observation}" for k in v.cases if k.observation), "")
        natural = v.measurements.get("natural_count") or "n/a (no merge seen)"
        lines.append(
            f"| {esc(c.title)} | {esc(_cell(v))}{esc(' — ' + arranged) if arranged else ''} | {esc(natural)} |"
        )
    return "\n".join(lines) if n else ""


LIMITS = (
    "### MemState's limits, with their numbers",
    "",
    "- **History cap.** MemState keeps the newest 500 entries per field and drops older ones (501 writes to one field "
    "leave 500 entries with the oldest gone, F21). A correction uses two entries, "
    "so a field holds at most 250 corrections before the oldest entries go [INFERENCE: arithmetic from "
    "the cap and the two-entry correction].",
    "- **Forgetting gate.** MemState's forgetting pass runs only from the 500-topic soft limit "
    "(`topic_count_soft_limit`) on, and the C5 ramp reaches 2,000 active topics with none archived (F10): the "
    "active state is four times the limit, so C5's bound is declared, not enforced.",
)


def render_limits() -> str:
    return "\n".join(LIMITS)


SCOPE_NOTE = (
    "Verdicts measure the published proof of concept against the paper's conditions; fail and absent mark "
    'gaps its authors state (its README: "Proof-of-Concept, NOT Full Implementation"), not defects.'
)


def render_deviations(deviations: tuple[Deviation, ...] = DEVIATIONS) -> str:
    lines = ["| Item | As shipped | Used here | Why |", "|---|---|---|---|"]
    lines += [f"| {esc(d.item)} | {esc(d.as_shipped)} | {esc(d.used_here)} | {esc(d.why)} |" for d in deviations]
    return "\n".join(lines)
