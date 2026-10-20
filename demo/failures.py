"""Error verdicts shared by the recorded and live runners."""

from __future__ import annotations

import traceback

from demo.checks import Check
from demo.verdict import Verdict


def detail(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def errored(check: Check, system_id: str, text: str) -> list[Verdict]:
    out = [Verdict.errored(r.id, text, control=r.control) for r in check.rows]
    for v in out:
        v.system = system_id
    return out
