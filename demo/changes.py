"""The per-step change table: upstream, then each patch step, one verdict per row, changed cells marked.

Each measured cell is compared, verdict for verdict, with the nearest earlier cell of the same row in the chain that
holds a real verdict (step 1 with upstream, step 2 with step 1, and so on). A changed cell reads
`**<before> → <after>** (vs <system>)`, naming the system it was compared with; an unchanged one just the verdict;
an unmeasured one `—`. `error` is not a verdict on the scale (a crashed check, a failed setup): an `error` cell is
shown as `error`, never marked, and never the baseline of a later cell, so a step that failed to run neither
fabricates nor hides changes. Beside the verdicts, each step lists per row the cases whose outcome changed against the
same baseline (cases matched by `Case.id`; a case missing on one side reads `n/a`): a row can keep its verdict
(`partial → partial`) while a case flips. A count a row measures on random ids (`measurements["natural_count"]`,
C2(a)'s natural arrangement) is shown beside the case lines when it differs, never compared. The chain and the step names come from the system registry (`demo/systems.py`); the
functions are otherwise generic over rows and verdicts.
"""

from __future__ import annotations

from dataclasses import dataclass

from demo.checks import Row
from demo.reference_gem import PHASES, reference_gem_id
from demo.systems import STEP_IDS, SYSTEMS
from demo.verdict import ABSENT, ERROR, FAIL, NOT_SCORED, PARTIAL, PASS, Case, Verdict, last_verdict, measured

CHAIN = ("upstream", *STEP_IDS)
REFERENCE_CHAIN = tuple(map(reference_gem_id, PHASES))  # the reference GEM's phases: its own chain
CHAINS = (CHAIN, REFERENCE_CHAIN)
HEADERS = {"upstream": "upstream", **{i: f"step {SYSTEMS[i].step}" for i in STEP_IDS},
           **{reference_gem_id(p): f"phase {p}" for p in PHASES}}


@dataclass
class ChangeCell:
    system: str
    verdict: str
    compared_with: str | None = None  # the system whose verdict this one was compared with; None if there was none
    changed_from: str | None = None  # that system's verdict when it differs from this one


def change_cells(row_id: str, verdicts: list[Verdict], chain: tuple[str, ...] = CHAIN) -> dict[str, ChangeCell | None]:
    cells: dict[str, ChangeCell | None] = {}
    previous: tuple[str, str] | None = None  # (system, verdict) of the nearest earlier real verdict
    for system_id in chain:
        v = last_verdict(verdicts, system_id, row_id)
        if v is None:
            cells[system_id] = None
            continue
        cell = ChangeCell(system_id, v.verdict)
        if v.verdict != ERROR:
            if previous is not None:
                cell.compared_with = previous[0]
                cell.changed_from = previous[1] if previous[1] != v.verdict else None
            previous = (system_id, v.verdict)
        cells[system_id] = cell
    return cells


def _all_cells(rows: list[Row], verdicts: list[Verdict], chain: tuple[str, ...]) -> dict[str, dict[str, ChangeCell | None]]:
    """`{row id: change_cells}`, each row's chain walked once."""
    return {r.id: change_cells(r.id, verdicts, chain) for r in rows}


def changes_per_step(rows: list[Row], verdicts: list[Verdict],
                     chain: tuple[str, ...] = CHAIN) -> dict[str, list[dict]]:
    """For each measured system after the first of the chain: the rows whose verdict changed, with before/after and
    the system compared with."""
    cells = _all_cells(rows, verdicts, chain)
    return {system_id: [{"row": r.id, "from": c.changed_from, "to": c.verdict, "vs": c.compared_with}
                        for r in rows if (c := cells[r.id][system_id]) and c.changed_from]
            for system_id in measured(verdicts, chain)[1:]}


def _text(cell: ChangeCell | None) -> str:
    if cell is None:
        return "—"
    if cell.changed_from:
        return f"**{cell.changed_from} → {cell.verdict}** (vs {HEADERS.get(cell.compared_with, cell.compared_with)})"
    return cell.verdict


def _summary(system_id: str, rows: list[Row], cells: dict[str, dict[str, ChangeCell | None]],
             chain: tuple[str, ...]) -> str:
    """One line for a measured step: per system it was compared with (rows can differ), what changed; rows with an
    `error` cell are named as not compared."""
    name = lambda s: HEADERS.get(s, s)  # noqa: E731
    by_baseline: dict[str, list[tuple[str, ChangeCell]]] = {}
    errored, no_baseline = [], []
    for r in rows:
        cell = cells[r.id][system_id]
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
        compared = by_baseline[baseline]
        changed = [f"{row} ({c.changed_from} → {c.verdict})" for row, c in compared if c.changed_from]
        rows_note = f" ({', '.join(row for row, _ in compared)})" if len(by_baseline) > 1 else ""
        parts.append(f"vs {name(baseline)}{rows_note}: " + ("changed: " + ", ".join(changed) if changed else "no change"))
    if errored:
        parts.append(f"not compared, error: {', '.join(errored)}")
    if no_baseline:
        parts.append(f"nothing earlier to compare with: {', '.join(no_baseline)}")
    return f"- {name(system_id)} " + ("; ".join(parts) or "has no cells") + "."


def render_change_table(rows: list[Row], verdicts: list[Verdict], chain: tuple[str, ...] = CHAIN) -> str:
    """Markdown: one row per scorecard row, one column per system of the chain, then one line per measured step
    after the first stating, per system compared with, what changed."""
    cells = _all_cells(rows, verdicts, chain)
    lines = ["| Row | " + " | ".join(HEADERS.get(s, s) for s in chain) + " |", "|---|" + "---|" * len(chain)]
    for r in rows:
        label = f"{r.id} (control)" if r.control else r.id
        lines.append(f"| {label} | " + " | ".join(_text(cells[r.id][s]) for s in chain) + " |")
    lines.append("")
    lines += [_summary(s, rows, cells, chain) for s in measured(verdicts, chain)[1:]]
    lines += _case_lines(rows, verdicts, chain)
    lines.append("- Changed cells are bold (`before → after`, naming the system compared with: the nearest earlier real "
                 "verdict of the row, never an `error`).")
    return "\n".join(lines)


def _outcome(case: Case | None) -> str:
    return "n/a" if case is None or case.held is None else "held" if case.held else "broken"


RANDOM_ID_COUNT = "natural_count"  # the measurement key of a count taken on random ids: shown, not compared


def case_changes_per_step(rows: list[Row], verdicts: list[Verdict],
                          chain: tuple[str, ...] = CHAIN) -> dict[str, list[dict]]:
    """For each measured system after the first of the chain: the rows with a case-level change against the system the
    row's verdict was compared with. An entry: the row, its verdict before and after, `vs`, `cases` (id, name, before,
    after; a broken case that now holds reads `fixed`) and `counts` when the row's random-id count differs. Rows without a case change are not listed."""
    cells = _all_cells(rows, verdicts, chain)
    out: dict[str, list[dict]] = {}
    for system_id in measured(verdicts, chain)[1:]:
        entries = []
        for r in rows:
            cell = cells[r.id][system_id]
            if cell is None or cell.compared_with is None or cell.verdict == ERROR:
                continue
            before = last_verdict(verdicts, cell.compared_with, r.id)
            after = last_verdict(verdicts, system_id, r.id)
            old = {c.id: c for c in before.cases}
            new = {c.id: c for c in after.cases}
            changed = []
            for case_id in [*new, *(i for i in old if i not in new)]:
                a, b = _outcome(old.get(case_id)), _outcome(new.get(case_id))
                if a != b:
                    changed.append({"case": case_id, "name": (new.get(case_id) or old[case_id]).name,
                                    "from": a, "to": "fixed" if (a, b) == ("broken", "held") else b})
            entry = {"row": r.id, "from": before.verdict, "to": after.verdict, "vs": cell.compared_with,
                     "cases": changed}
            counts = [v.measurements.get(RANDOM_ID_COUNT) for v in (before, after)]
            if counts[0] != counts[1]:
                entry["counts"] = {"from": counts[0] or "n/a", "to": counts[1] or "n/a"}
            if changed or "counts" in entry:
                entries.append(entry)
        out[system_id] = entries
    return out


def _case_lines(rows: list[Row], verdicts: list[Verdict], chain: tuple[str, ...]) -> list[str]:
    lines = []
    for system_id, entries in case_changes_per_step(rows, verdicts, chain).items():
        for e in entries:
            parts = [f"{e['row']}: {e['from']} → {e['to']}"]
            parts += [f"{c['name']}: {c['from']} → {c['to']}" for c in e["cases"]]
            if "counts" in e:
                parts.append(f"random-ID count {e['counts']['from']} → {e['counts']['to']} (shown, not compared)")
            lines.append(f"- {HEADERS.get(system_id, system_id)} cases: " + " · ".join(parts)
                         + f" (vs {HEADERS.get(e['vs'], e['vs'])})")
    return lines


def render_change_tables(rows: list[Row], verdicts: list[Verdict]) -> str:
    """The change table of every chain that has a measured system (upstream → step 1 → step 2 → step 3; phase 1 →
    phase 2), each under its own heading; "" when no chain was measured."""
    parts = [f"### Per-step change table: {' → '.join(HEADERS[s] for s in chain)}\n\n"
             + render_change_table(rows, verdicts, chain)
             for chain in CHAINS if measured(verdicts, chain)]
    return "\n\n".join(parts)


def change_table_payload(rows: list[Row], verdicts: list[Verdict], chain: tuple[str, ...]) -> dict:
    """The machine-readable form of one chain's change table, for `results.json`."""
    return {"chain": list(chain), "measured": measured(verdicts, chain), "changes": changes_per_step(rows, verdicts, chain),
            "case_changes": case_changes_per_step(rows, verdicts, chain)}


_RANK = {PASS: 3, PARTIAL: 2, FAIL: 1, ABSENT: 0, NOT_SCORED: 0}  # a drop in rank is "worse"; ERROR has no rank


def regression_summary(rows: list[Row], verdicts: list[Verdict], before: str = "step1", after: str = "step3") -> str:
    """One line on whether `after` is worse than `before` on any row. "No regressions on the rows the suite checks" is
    said only when both were measured, every row measured on both has no lower verdict, no case that held at `before`
    broke at `after` (the change table lists those), no row measured at `before` is missing at `after` and no verdict
    is an `error`. Otherwise the line names what blocks the claim."""
    name = HEADERS.get
    if not measured(verdicts, (before,)) or not measured(verdicts, (after,)):
        return (f"**Regressions not assessed:** {name(before, before)} and {name(after, after)} were not both measured, "
                "so the suite makes no claim about regressions.")
    worse, broke, unknown, missing, compared = [], [], [], [], 0
    for r in rows:
        a, b = last_verdict(verdicts, before, r.id), last_verdict(verdicts, after, r.id)
        if a is None:
            continue
        if b is None:
            missing.append(r.id)
        elif ERROR in (a.verdict, b.verdict):
            unknown.append(r.id)
        else:
            compared += 1
            if _RANK[b.verdict] < _RANK[a.verdict]:
                worse.append(f"{r.id} ({a.verdict} → {b.verdict})")
            old = {c.id: c for c in a.cases}
            broken = [c.name for c in b.cases if c.held is False and (o := old.get(c.id)) is not None and o.held]
            if broken:
                broke.append(f"{r.id} ({'; '.join(broken)})")
    blockers = []
    if worse:
        blockers.append(f"worse at {name(after, after)}: {', '.join(worse)}")
    if broke:
        blockers.append(f"a case that held at {name(before, before)} broke: {', '.join(broke)}")
    if unknown:
        blockers.append(f"an error verdict, not compared: {', '.join(unknown)}")
    if missing:
        blockers.append(f"not measured at {name(after, after)}: {', '.join(missing)}")
    if blockers:
        return f"**Regressions not ruled out:** " + "; ".join(blockers) + "."
    return (f"**No regressions on the rows the suite checks:** none of the {compared} rows measured at "
            f"{name(before, before)} and {name(after, after)} is worse at {name(after, after)} (verdict and case level).")
