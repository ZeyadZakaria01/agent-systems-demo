"""C1 (the control) and check discovery, run in-process against the baseline. No server, no MemState mocks."""

from demo.baseline import Baseline
from demo.checks import discover
from demo.adapter import System
from demo.verdict import FAIL, PASS


def by_row(row):
    return next(c for c in discover() if row in [r.id for r in c.rows])


def test_c1_passes_on_the_baseline_both_cases_held():
    (verdict,) = by_row("C1").execute(Baseline())
    assert verdict.verdict == PASS
    held = {c.name: c.held for c in verdict.cases}
    assert held["default read returns only April 20"] is True
    assert held["temporal read returns the full history"] is True  # the versioned row keeps its history


class NoHistory(Baseline):
    """A system that declares it keeps no history: the history case does not apply, and the reader is told why."""

    def _describe(self):
        return {**super()._describe(), "keeps_history": False}


def test_a_system_declaring_no_history_has_the_history_case_not_applicable():
    (verdict,) = by_row("C1").execute(NoHistory())
    assert verdict.verdict == PASS
    history_case = next(c for c in verdict.cases if c.name.startswith("temporal"))
    assert history_case.held is None and "keeps no history" in history_case.observation


class ClaimsHistoryButReturnsNone(Baseline):
    """A system that declares it keeps history yet returns none on a history request must fail the control."""

    @staticmethod
    def _field(entries, recorded_at=None, with_history=False):
        return Baseline._field(entries, recorded_at, with_history=False)


def test_a_system_that_claims_history_but_returns_none_fails_c1():
    (verdict,) = by_row("C1").execute(ClaimsHistoryButReturnsNone())
    held = {c.name: c.held for c in verdict.cases}
    assert held["temporal read returns the full history"] is False
    assert verdict.verdict != PASS
