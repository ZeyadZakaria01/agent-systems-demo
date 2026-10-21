"""The reference GEM run through every check, in-process, shared by the reference GEM and mutation tests.

The unmutated runs are computed once per test session (`unmutated`), not once per module. Three kinds of
wait in a run say nothing about an in-process system, so every run here shortens them (the verdicts do not depend on
them): the merge wait of C2(a)'s active-into-archived extra, which times out by design on the reference GEM
(`merge.DEFAULT_TIMEOUT_S`, 15 s), the waits for a forgetting pass (`ARCHIVE_WAIT_S`, 20 s, which a mutant that never
forgets sits through in several checks), and the pause between the as-of probe's two writes
(`time_probes.AS_OF_GAP_S`, 1 s, which only has to exceed the clock's resolution). `small_ramps` also shrinks the C5 ramp, the way `tests/test_c5.py` does for its fakes: the
mutation tests need the natural trajectory to archive something, not the 2,000-topic figures, which the reference GEM
tests pin on the full ramp.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from functools import cache, partial

import pytest

from demo import merge, ramp
from demo.adapter import System
from demo.checks import c6_retrieval_adaptation, discover, time_probes
from demo.reference_gem import ReferenceGem
from demo.session import Session
from demo.verdict import Verdict

RUN_DAY = date(2026, 10, 20)
SMALL_STEPS = (100, 500)  # past the decay horizon (400 interactions), so the natural trajectory archives something


@contextmanager
def _fast(small_ramps: bool) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(merge, "DEFAULT_TIMEOUT_S", 0.3)
        mp.setattr(time_probes, "AS_OF_GAP_S", 0.05)
        mp.setattr(
            ramp, "ARCHIVE_WAIT_S", 0.3
        )  # waits for a forgetting pass; in-process it has happened or it never will
        mp.setattr(c6_retrieval_adaptation, "ARCHIVE_WAIT_S", 0.3)
        if small_ramps:
            mp.setattr(ramp, "STEPS", SMALL_STEPS)
            mp.setattr(ramp, "REPEATS", 1)
        yield


def run_checks(factory: Callable[[], System], small_ramps: bool = False) -> dict[str, Verdict]:
    """Every check but the storyline (it has its own tests) on fresh instances of `factory`: verdicts by row."""
    out: dict[str, Verdict] = {}
    with _fast(small_ramps):
        for check in discover():
            if check.id == "Storyline":
                continue
            for v in check.execute(Session.in_process(factory), run_day=RUN_DAY):
                out[v.row] = v
    return out


@cache
def unmutated(phase: int, small_ramps: bool = False) -> dict[str, Verdict]:
    return run_checks(partial(ReferenceGem, phase=phase), small_ramps)
