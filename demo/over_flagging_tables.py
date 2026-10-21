"""The over-flagging table, shown beside the C3 row with no verdict. Reads `Verdict.measurements["over_flagging"]`
written by `demo/checks/over_flagging.py`; `render_over_flagging` returns "" when no such run is in the verdicts."""

from __future__ import annotations

from demo.checks.over_flagging import ROW
from demo.scorecard import esc
from demo.verdict import ERROR, Verdict

NOTE = ("Measurement, not a verdict, beside the C3 row (report §5.5, \"how many hops\"). One chain A ← B ← C ← D over "
        "extension edges; A's field is updated; B and C need revision, D does not depend on the updated field (the "
        "anti-trap). *Missed* = needed and not flagged; *not needed* = flagged and not needed. No MemState system is "
        "measured: none propagates (F17).")


def _names(keys: list[str]) -> str:
    return ", ".join(keys) or "none"


def render_over_flagging(verdicts: list[Verdict]) -> str:
    lines = ["### Over-flagging (one chain, beside C3)", "", NOTE, "",
             "| System | Propagation | Flags raised | Flags needed | Flags missed | Flags not needed |",
             "|---|---|---|---|---|---|"]
    rows = 0
    for v in verdicts:
        data = None if v.row != ROW or v.verdict == ERROR else v.measurements.get("over_flagging")
        for run in (data or {}).get("runs", []):
            rows += 1
            lines.append(f"| {esc(v.system)} | {esc(run['mode'])} | {run['flags_raised']} ({_names(run['raised'])}) | "
                         f"{run['flags_needed']} ({_names(run['needed'])}) | {run['flags_missed']} "
                         f"({_names(run['missed'])}) | {run['flags_not_needed']} ({_names(run['not_needed'])}) |")
    return "\n".join(lines) if rows else ""
