"""The verdict model, generic over rows and systems.

Scale (ADR 0002): pass = every applicable case held; partial = some held; fail = the capability is implemented
and every case broke; absent = a probe confirmed the capability missing (the probe evidence is mandatory);
not-scored = no case applied (C2(b)'s "neither outcome" rule). `ERROR` is not part of the scale: the check
crashed, and the scorecard shows it as such.

`measurements` carries numbers a row reports beside its verdict (violation rate, windows, latencies);
`observations` carries findings that are not verdicts (over-blocking, salience not durable, route log).
The runner fills `system`, `snapshot` and `snapshots`; checks never set them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PASS, PARTIAL, FAIL, ABSENT, NOT_SCORED = "pass", "partial", "fail", "absent", "not-scored"
ERROR = "error"
SCALE = (PASS, PARTIAL, FAIL, ABSENT, NOT_SCORED)


@dataclass
class Case:
    """One tested case. `held=None` means the case does not apply to this system (a nothing-value)."""

    name: str
    held: bool | None
    observation: str = ""
    control: bool = False


@dataclass
class Verdict:
    row: str
    verdict: str
    cases: list[Case] = field(default_factory=list)
    observations: list[Any] = field(default_factory=list)
    probe_evidence: Any = None
    measurements: dict = field(default_factory=dict)
    control: bool = False
    system: str | None = None
    snapshot: str | None = None  # the first of `snapshots`: the link the scorecard shows
    snapshots: list[str] = field(default_factory=list)  # one per fresh system the check opened, in order
    error: str | None = None

    @classmethod
    def from_cases(cls, row: str, cases: list[Case], **kwargs: Any) -> "Verdict":
        applicable = [c.held for c in cases if c.held is not None]
        if not applicable:
            verdict = NOT_SCORED
        elif all(applicable):
            verdict = PASS
        elif any(applicable):
            verdict = PARTIAL
        else:
            verdict = FAIL
        return cls(row=row, verdict=verdict, cases=cases, **kwargs)

    @classmethod
    def absent(cls, row: str, probe_evidence: Any, **kwargs: Any) -> "Verdict":
        if not probe_evidence:
            raise ValueError(f"{row}: an absent verdict needs the probe run that confirmed the absence")
        return cls(row=row, verdict=ABSENT, probe_evidence=probe_evidence, **kwargs)

    @classmethod
    def not_scored(cls, row: str, **kwargs: Any) -> "Verdict":
        return cls(row=row, verdict=NOT_SCORED, **kwargs)

    @classmethod
    def errored(cls, row: str, error: str, **kwargs: Any) -> "Verdict":
        return cls(row=row, verdict=ERROR, error=error, **kwargs)

    def to_dict(self) -> dict:
        return asdict(self)


def last_verdict(verdicts: list[Verdict], system_id: str, row_id: str) -> Verdict | None:
    """The last verdict recorded for (system, row), `None` if the row was not run on that system."""
    found = None
    for v in verdicts:
        if v.system == system_id and v.row == row_id:
            found = v
    return found
