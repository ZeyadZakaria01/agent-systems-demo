"""C2(d), the superseded read on the lapsed-override story, in-process. No MemState verdict is pinned."""

from contextlib import nullcontext
from datetime import date

from demo.checks import discover
from demo.systems.adapter import Rejected
from demo.systems.baseline import Baseline
from demo.systems.session import Session
from demo.verdict import FAIL, PARTIAL, PASS

RUN_DAY = date(2026, 10, 20)


def run(factory):
    check = next(c for c in discover() if c.id == "C2(d)")
    session = Session(lambda tag: nullcontext(factory()), capture=lambda system, tag, a, b: {"tag": tag})
    (verdict,) = check.execute(session, run_day=RUN_DAY)
    return verdict


class FirstWrittenIsCurrent(Baseline):
    """A system whose current value is the first one written, whatever later statements said."""

    def _field(self, entries, recorded_at=None, with_history=False):
        return super()._field(entries[:1], recorded_at, with_history)


def test_the_versioned_row_passes_on_both_stories_with_its_own_undated_writes():
    v = run(Baseline)
    assert v.verdict == PASS
    assert [c.held for c in v.cases] == [True, True]
    assert [s["write_dates"] for s in v.measurements["stories"]] == [[], []]  # it accepts no valid-time date
    assert [s["current"] for s in v.measurements["stories"]] == ["$80", "$100"]  # story 1: ended, not superseded
    assert v.observations == []


def test_a_lapsed_override_returning_the_base_value_is_never_a_violation():
    v = run(FirstWrittenIsCurrent)  # story 1 reads $50 (the base): fine; story 2 reads $50 although $100 ended it
    assert v.verdict == PARTIAL
    assert [c.held for c in v.cases] == [True, False]
    assert [o["name"] for o in v.observations] == ["C2 violation"]
    assert v.observations[0]["story"] == "lapsed-override-2" and v.observations[0]["current"] == "$50"


def test_an_override_returned_after_the_plain_statement_ended_it_is_a_violation():
    class Override(Baseline):
        def _field(self, entries, recorded_at=None, with_history=False):
            return super()._field([e for e in entries if e["value"] != "$100"], recorded_at, with_history)

    v = run(Override)
    assert [c.held for c in v.cases] == [True, False]
    assert v.observations[0]["current"] == "$80"


def test_a_value_that_is_neither_accepted_nor_ended_breaks_the_case_without_a_violation():
    class Other(Baseline):
        def _field(self, entries, recorded_at=None, with_history=False):
            return super()._field([{**e, "value": "$7"} for e in entries], recorded_at, with_history)

    v = run(Other)
    assert v.verdict == FAIL and v.observations == []


def test_a_rejected_write_leaves_the_case_not_applicable():
    class Blocks(Baseline):
        def _ingest(self, request):
            raise Rejected(400, "no")

    v = run(Blocks)
    assert [c.held for c in v.cases] == [None, None]
