"""C1 (the control) and check discovery, run in-process against the baseline. No server, no MemState mocks."""

from demo.baseline import Baseline
from demo.checks import discover
from demo.adapter import System
from demo.verdict import FAIL, PASS


def by_row(row):
    return next(c for c in discover() if row in [r.id for r in c.rows])


def test_c1_passes_on_the_baseline_on_the_one_case_that_applies():
    (verdict,) = by_row("C1").execute(Baseline())
    assert verdict.verdict == PASS
    held = {c.name: c.held for c in verdict.cases}
    assert held["default read returns only April 20"] is True
    # the baseline declares that it keeps no history: the history case does not apply, and the reader is told why
    assert held["temporal read returns the full history"] is None
    history_case = next(c for c in verdict.cases if c.name.startswith("temporal"))
    assert "keeps no history" in history_case.observation


class NoHistoryButClaimsIt(Baseline):
    """A system that declares it keeps history yet returns none on a history request must fail the control."""

    def _describe(self):
        return {**super()._describe(), "keeps_history": True}


def test_a_system_that_claims_history_but_returns_none_fails_c1():
    (verdict,) = by_row("C1").execute(NoHistoryButClaimsIt())
    held = {c.name: c.held for c in verdict.cases}
    assert held["temporal read returns the full history"] is False
    assert verdict.verdict != PASS
