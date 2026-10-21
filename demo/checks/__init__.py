"""Checks: one module per condition (or group of rows) in this package, discovered by the runner.

To add a check, drop a module `demo/checks/<name>.py` that decorates a function:

    @check(row="C1", claim="[P1]'s wording", control=True, systems=None)
    def c1(ctx: Ctx) -> Verdict: ...

- `row` / `claim` / `control`: the scorecard row ID, [P1]'s claim text, whether the row is a control.
  A module with several rows passes `rows=[Row(id, claim, control), ...]` and returns one verdict per row.
- `systems`: ids the check runs on (see `demo/systems.py`); `None` = every system.
- The function gets a `Ctx` (`ctx.system` is the system adapter on a fresh database, `ctx.run_day` the run's date),
  uses only the adapter, and returns a `Verdict` (or a list, one per declared row). A check needing several fresh
  databases (a story each, a ramp per repeat) uses `with ctx.fresh_system(tag) as s:`, one at a time, each with its
  own snapshot (`demo/session.py`). It does not start servers, write snapshots or set `system` / `snapshots` on the
  verdict: the runner does.
- Read fields with `demo.reads.current_value` (it returns `NO_VALUE` for "no current value", `None` for a written
  `null`), and read capabilities from `system.describe()` (`keeps_history`), never from missing keys.
- Modules starting with `_` are skipped. No list needs editing: `discover()` imports every module here.
- `Row(..., probe=True)` marks a probe of a proposed condition (the time probes, C4'): it is not [P1]'s claim, so the
  scorecard prints it in its own "probes" section (still in the change tables), never in the main table.
- Rows are ordered on the scorecard by natural order of the row ID.
- `Row(..., on_scorecard=False)` marks a measurement that has its own table, not a scorecard row (the storyline). Its
  verdict still lands in `verdicts`, `results.json` and the snapshots, so anything that counts or tabulates by row
  (scorecard counts, the per-step change table, fail/absent totals, live mode) MUST iterate the rows with
  `on_scorecard` true, never the verdicts, or the measurement is counted as a result.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from demo.adapter import System
from demo.session import Session
from demo.verdict import Verdict


@dataclass(frozen=True)
class Row:
    id: str
    claim: str
    control: bool = False
    on_scorecard: bool = True  # False: a measurement with its own table (the storyline), not a scorecard row
    probe: bool = False  # True: a probe of a proposed condition (C1', C4'), outside [P1]'s claims: the probes section, not the main table


@dataclass
class Ctx:
    session: Session
    run_day: date

    @property
    def system(self) -> System:
        """The check's default system: a fresh database, opened on first use, closed when the check ends."""
        return self.session.system

    def fresh_system(self, tag: str):
        """`with ctx.fresh_system("story-1") as s:` opens another fresh system (own DB / server) with its own
        snapshot; one at a time (see `demo/session.py`)."""
        return self.session.fresh_system(tag)


@dataclass(frozen=True)
class Check:
    rows: tuple[Row, ...]
    systems: tuple[str, ...] | None
    fn: Callable[[Ctx], Verdict | list[Verdict]]

    @property
    def id(self) -> str:
        return self.rows[0].id

    def applies_to(self, system_id: str) -> bool:
        return self.systems is None or system_id in self.systems

    def execute(self, target: System | Session, run_day: date | None = None) -> list[Verdict]:
        """Run on one system (or session); returns exactly one verdict per declared row, control flag from the row."""
        session = target if isinstance(target, Session) else Session.around(target)
        out = self.fn(Ctx(session=session, run_day=run_day or date.today()))
        verdicts = out if isinstance(out, list) else [out]
        declared = {r.id: r for r in self.rows}
        if sorted(v.row for v in verdicts) != sorted(declared):
            raise ValueError(f"check {self.id}: returned rows {[v.row for v in verdicts]}, declared {list(declared)}")
        for v in verdicts:
            v.control = declared[v.row].control
        return verdicts


def check(
    *,
    row: str | None = None,
    claim: str | None = None,
    control: bool = False,
    rows: list[Row] | None = None,
    systems: tuple[str, ...] | None = None,
) -> Callable[[Callable], Check]:
    if rows is None:
        if row is None or claim is None:
            raise ValueError("check() needs row= and claim=, or rows=")
        rows = [Row(row, claim, control)]
    return lambda fn: Check(rows=tuple(rows), systems=systems, fn=fn)


def natural_key(row_id: str) -> list:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", row_id)]


def discover() -> list[Check]:
    """Every `Check` declared in a public module of this package, ordered by natural row ID."""
    found: dict[str, Check] = {}
    seen_rows: dict[str, str] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        for obj in vars(module).values():
            if isinstance(obj, Check) and obj.id not in found:
                for r in obj.rows:
                    if r.id in seen_rows:
                        raise ValueError(f"row {r.id} declared twice ({seen_rows[r.id]}, {info.name})")
                    seen_rows[r.id] = info.name
                found[obj.id] = obj
    return sorted(found.values(), key=lambda c: natural_key(c.id))
