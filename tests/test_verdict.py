"""The verdict scale (ADR 0002): pass = every case held, partial = some, fail = none, absent needs a probe."""

import pytest

from demo.verdict import ABSENT, FAIL, NOT_SCORED, PARTIAL, PASS, Case, Verdict


def cases(*held):
    return [Case(name=f"case {i}", held=h, observation="") for i, h in enumerate(held)]


@pytest.mark.parametrize("held,expected", [
    ((True, True), PASS),
    ((True, False), PARTIAL),
    ((False, False), FAIL),
    ((True, None), PASS),      # a case that does not apply to the system (nothing-value) does not count
    ((False, None), FAIL),
])
def test_scale_from_cases(held, expected):
    v = Verdict.from_cases("C0", cases(*held))
    assert v.verdict == expected


def test_a_verdict_with_no_applicable_case_is_not_scored():
    assert Verdict.from_cases("C0", cases(None)).verdict == NOT_SCORED


def test_absent_is_only_asserted_with_probe_evidence():
    with pytest.raises(ValueError):
        Verdict.absent("C0", probe_evidence=None)
    v = Verdict.absent("C0", probe_evidence={"request": "...", "observed": "no such capability"})
    assert v.verdict == ABSENT and v.probe_evidence["observed"]


def test_verdict_is_machine_readable_with_cases_observations_and_control_flag():
    v = Verdict.from_cases("C0", cases(True), observations=["over-reinforcement"], control=True)
    d = v.to_dict()
    assert d["row"] == "C0" and d["verdict"] == PASS and d["control"] is True
    assert d["cases"][0]["held"] is True and d["observations"] == ["over-reinforcement"]
    assert d["snapshot"] is None and d["probe_evidence"] is None
