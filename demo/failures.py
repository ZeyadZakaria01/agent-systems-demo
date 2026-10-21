"""What the recorded and live runners share: error verdicts and the run-one-check skeleton."""

from __future__ import annotations

import traceback
from datetime import date

from demo.checks import Check
from demo.evidence import RunDir, capture, write_snapshots
from demo.session import OpenSystem, Session
from demo.verdict import Verdict


def detail(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def errored(check: Check, system_id: str, text: str) -> list[Verdict]:
    out = [Verdict.errored(r.id, text, control=r.control) for r in check.rows]
    for v in out:
        v.system = system_id
    return out


def run_check(
    run: RunDir,
    check: Check,
    system_id: str,
    open_system: OpenSystem,
    run_day: date | None = None,
    observations: tuple[dict, ...] = (),
) -> list[Verdict]:
    """One check on the systems `open_system` yields: a crash becomes `error` verdicts, the open system is closed
    (and its evidence captured) in every case, snapshots are written, the verdicts are labelled `system_id`."""
    session = Session(open_system, lambda system, tag, t0, t1: capture(system_id, check.id, system, tag, t0, t1))
    notes: list[dict] = []
    try:
        try:
            verdicts = check.execute(session, run_day)
        except Exception as e:  # a crashing check, a server that never started or died: recorded, the run goes on
            verdicts = errored(check, system_id, detail(e))
    finally:  # also on Ctrl-C: the open system must be cleaned up
        try:
            session.close()
        except Exception as e:  # e.g. the server would not stop; its port stays busy and the next open will say so
            notes.append(
                {"name": "cleanup failed", "summary": f"cleanup after the check failed: {type(e).__name__}: {e}"}
            )
    for v in verdicts:
        v.system = system_id
        v.observations.extend([*observations, *notes])
    write_snapshots(run, session.captured, verdicts)
    return verdicts
