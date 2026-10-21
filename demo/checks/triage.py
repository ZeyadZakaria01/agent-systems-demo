"""Storyline triage and reinforcement precision (spec stories 38-40; `demo/storyline.py`, `demo/triage.py`).

The storyline's events are sent as `/v1` placements on a fresh database, then its questions are read with the
default stages and `top_k` 8 (the baseline: top 8 too). This is a measurement, not a scorecard row: the row is not
on the scorecard (`on_scorecard=False`), its numbers go to `demo/storyline_tables.py` (triage counts per system, and
reinforcement precision beside C6 clause 1, which carries no verdict). The verdict only summarises the questions: one
case per question, held when the read answered it.
"""

from demo.checks import Ctx, Row, check
from demo.storyline import ROW, WEBSITE_REDESIGN
from demo.triage import CORRECT, run_storyline
from demo.verdict import Case, Verdict

CLAIM = (
    "Storyline questions: each wrong answer is a search failure (labelled topic not returned) or a memory "
    "failure (returned, stored value wrong); reinforcement precision = Precision@k, no verdict."
)


@check(rows=[Row(ROW, CLAIM, on_scorecard=False)])
def storyline(ctx: Ctx) -> Verdict:
    run = run_storyline(ctx.system, WEBSITE_REDESIGN)
    cases = [
        Case(
            f"{o.question} [{o.ability}] {o.text}",
            held=o.outcome == CORRECT,
            observation=f"{o.outcome}: ground truth {o.truth!r}, "
            + (
                f"labelled topic ranked {o.rank} of {len(o.returned_ids)}, stored {o.stored!r}"
                if o.returned
                else f"labelled topic not among the {len(o.returned_ids)} returned"
            ),
        )
        for o in run.outcomes
    ]
    observations = [
        {
            "name": "write path",
            "event": e.event,
            "observation": e.observation,
            "summary": f"write path: {e.event} left a different state than expected ({e.observation})",
        }
        for e in run.events
        if not e.matched
    ]
    return Verdict.from_cases(ROW, cases, observations=observations, measurements=run.to_measurements())
