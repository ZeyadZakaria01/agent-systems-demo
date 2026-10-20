"""C2(a) (superseded value): how often the Reasoner's merge makes a superseded value current.

Twenty repetitions in one fresh database, random topic ids, distinct titles. Each repetition makes the topic to be
dropped hold the newer value: two topics are written through `/v1` under distinct titles, the lower id gets `Deadline:
March 15` and the higher id `Deadline: April 20` (MemState keeps the lower id, F9), both are given one title by a
labelled setup write (`PATCH title`; values are never written by an editor endpoint), and a `/v1 extend_topic` with no
fields triggers the merge (`demo/merge.py`). A system that cannot retitle falls back to two same-title `new_topic`
writes (the baseline upserts them). A case holds when the newer value is current after the merge; the violation (a
measure beside the verdict, never compared between engines) is the superseded value March 15 being current; no value
or a null is a broken case but not a violation. All held = pass, some = partial, none = fail.

The arrangement is enforced: a repetition in which the dropped topic did not hold the newer value is not a case
(`held=None`, counted under `arrangement_not_met`), because it would not test the claim. The merge is awaited by
polling (`demo/merge.py`); the window per repetition is the wait logged by the adapter. A repetition whose merge is
not seen within the timeout is not a case either; if no repetition saw a merge the row is `absent` with those waits as
the probe evidence. Beside the verdict: the window median and range, the observation "topic deleted on merge", and
the extras of `demo/merge_extras.py`. `measure_merges` takes the repetition count and the merge timeout so a test can
shorten them through the same path the check runs.
"""

from __future__ import annotations

import statistics

from demo.adapter import System
from demo.checks import Ctx, check
from demo.merge import (DEADLINE, DEFAULT_TIMEOUT_S, NEWER, OLDER, DroppedState, MergeOutcome, current_after_merge,
                        trigger_and_await_merge)
from demo.merge_extras import active_into_archived, three_same_title
from demo.reads import NO_VALUE
from demo.verdict import Case, Verdict

CLAIM = ("C2 (transition soundness): every transition respects the policy, and no revision produces a state in "
         "which a superseded value is returned as current.")
REPETITIONS = 20


def _scored(outcome: MergeOutcome) -> bool:
    """A repetition is a case when a merge was seen and the dropped topic held the newer value (or nothing was
    dropped: an upsert)."""
    return outcome.merged and outcome.dropped_held_newer is not False


def _repetition(i: int, outcome: MergeOutcome, current: object) -> dict:
    pair = outcome.pair
    return {"repetition": i, "title": pair.title, "older_id": pair.older_id, "newer_id": pair.newer_id,
            "merged": outcome.merged, "upserted": pair.upserted, "survivor_id": outcome.survivor_id,
            "dropped_id": outcome.dropped_id, "dropped_state": outcome.dropped_state,
            "window_s": outcome.window_s, "waited_s": None if outcome.waited is None else outcome.waited.elapsed,
            "survivor_held": outcome.survivor_held, "current": "NO_VALUE" if current is NO_VALUE else current,
            "scored": _scored(outcome), "violation": _scored(outcome) and current == OLDER,
            "dropped_held_newer": outcome.dropped_held_newer}


def _case(i: int, outcome: MergeOutcome, current: object) -> Case:
    name = f"repetition {i}: the newer value is current after the merge"
    if not outcome.merged:
        return Case(name, None, f"no merge seen within {outcome.waited.elapsed:.1f}s (timeout)")
    if not _scored(outcome):
        return Case(name, None, f"arrangement not met: the survivor held the {outcome.survivor_held} value, so the "
                                "dropped topic did not hold the newer one; not a case")
    how = ("same topic (upsert, no duplicate)" if outcome.pair.upserted else
           f"survivor held the {outcome.survivor_held} value, dropped topic {outcome.dropped_state}")
    shown = "NO_VALUE" if current is NO_VALUE else current
    return Case(name, current == NEWER, f"{how}; current={shown!r}")


def _windows(reps: list[dict], seen: list[dict], repetitions: int, timeout: float) -> tuple[dict, dict]:
    """The window measurements and the `windows` entry the scorecard renders."""
    samples = [r["window_s"] for r in reps if r["window_s"] is not None]
    timeouts = sum(not r["merged"] for r in reps)
    median = round(statistics.median(samples), 3) if samples else None
    low, high = (min(samples), max(samples)) if samples else (None, None)
    base = "from the duplicate-creating ingest's response to the poll that sees the merge"
    measures = {"merge_timeouts": timeouts, "window_median_s": median, "window_min_s": low, "window_max_s": high,
                "window_samples": len(samples),
                "window_note": f"{base}; no duplicate is ever created on this system (upsert)"
                if seen and not samples else base}
    value = (f"median {median} s, range {low}-{high} s over {len(samples)} repetitions" if samples else
             f"no merge seen within {timeout:g} s in {timeouts}/{repetitions} repetitions" if timeouts else
             "not applicable: no duplicate is ever created (upsert)")
    return measures, {"name": "Merge revision window", "value": value}


def _observations(system: System, seen: list[dict], timeout: float) -> list[dict]:
    dropped = [r for r in seen if r["dropped_state"] is not None]
    if dropped:
        deleted = sum(r["dropped_state"] == DroppedState.DELETED for r in dropped)
        summary = (f"topic deleted on merge: dropped topic reads as missing in {deleted}/{len(dropped)} "
                   f"merges (the rest archived: {len(dropped) - deleted})")
    else:
        summary = "topic deleted on merge: not applicable, the system created no duplicate to merge"
    three, archived = three_same_title(system, timeout), active_into_archived(system, timeout)
    return [{"name": "topic deleted on merge", "summary": summary},
            {"name": "merge extras", "three_same_title": three, "active_into_archived": archived,
             "summary": f"three same-title: {three['summary']} | archived duplicate: {archived['summary']}"}]


def measure_merges(system: System, repetitions: int = REPETITIONS, timeout: float = DEFAULT_TIMEOUT_S) -> Verdict:
    cases: list[Case] = []
    reps: list[dict] = []
    for i in range(1, repetitions + 1):
        outcome = trigger_and_await_merge(system, "Vendor Contract", DEADLINE, timeout)
        current = current_after_merge(system, outcome)
        reps.append(_repetition(i, outcome, current))
        cases.append(_case(i, outcome, current))

    seen = [r for r in reps if r["merged"]]
    scored = [r for r in reps if r["scored"]]
    violations = sum(r["violation"] for r in scored)
    window_measures, window = _windows(reps, seen, repetitions, timeout)
    measurements = {
        "repetitions": repetitions, "merges": sum(not r["upserted"] for r in seen),
        "upserted": sum(r["upserted"] for r in seen), "arrangement_not_met": len(seen) - len(scored),
        "dropped_held_newer": sum(r["dropped_held_newer"] is True for r in seen),
        "violations": violations, "violation_rate": f"{violations}/{len(scored)}",
        **window_measures, "windows": [window], "per_repetition": reps,
    }
    observations = _observations(system, seen, timeout)
    if not seen:
        return Verdict.absent("C2(a)", {"probe": f"{repetitions} duplicate pairs written, each awaited by polling until "
                                                 "one of the pair was deleted or archived",
                                        "merges_seen": 0, "waits_s": [r["waited_s"] for r in reps]},
                              cases=cases, measurements=measurements, observations=observations)
    return Verdict.from_cases("C2(a)", cases, measurements=measurements, observations=observations)


@check(row="C2(a)", claim=CLAIM)
def c2a(ctx: Ctx) -> Verdict:
    return measure_merges(ctx.system)
