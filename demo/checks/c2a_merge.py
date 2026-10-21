"""C2(a) (superseded value), reported as existence: in the arranged case, does the merge make the superseded value
current?

Arranged case, twenty repetitions in one fresh database, random topic ids, distinct titles. Each repetition makes the
topic to be dropped hold the newer value: two topics are written through `/v1` under distinct titles, the lower id gets
`Deadline: March 15` and the higher id `Deadline: April 20` (MemState keeps the lower id, F9), both are given one title
by a labelled setup write (`PATCH title`; values are never written by an editor endpoint), and a `/v1 extend_topic`
with no fields triggers the merge (`demo/merge.py`). A system that cannot retitle falls back to two same-title
`new_topic` writes; a system that appends the second write to the first topic (the versioned row) creates no
duplicate, so no merge occurs and the repetition is not a case. The row has one case: the merge never makes the
superseded value current (nor loses the value) in any arranged repetition that was a case. It holds (pass) when no
repetition broke it, breaks (fail) when one did, and is not-scored when no repetition was a case. The per-repetition
results, and the violation count (March 15 current), are measurements beside the verdict.

Beside the existence result: the natural count. The same twenty repetitions without the arrangement: two same-title
`new_topic` writes on random ids, no setup write, and the count of merges whose survivor holds March 15 (upstream:
10/20, F9). It is reported as `natural_count`, never compared between systems, and never part of the verdict. It runs
only when the arranged repetitions saw a merge of two topics.

The arrangement is enforced: a repetition in which the dropped topic did not hold the newer value is not a case
(counted under `arrangement_not_met`), because it would not test the claim. The merge is awaited by polling
(`demo/merge.py`); the window per repetition is the wait logged by the adapter. A repetition whose merge is not seen
within the timeout is not a case either; if no repetition saw a merge the row is `absent` with those waits as the
probe evidence. Beside the verdict: the window median and range, the observation "topic deleted on merge", and the
extras of `demo/merge_extras.py`. `measure_merges` takes the repetition count and the merge timeout so a test can
shorten them through the same path the check runs.
"""

from __future__ import annotations

import statistics

from demo import merge
from demo.adapter import System
from demo.checks import Ctx, check
from demo.merge import (
    DEADLINE,
    DEFAULT_TIMEOUT_S,
    NEWER,
    OLDER,
    DroppedState,
    MergeOutcome,
    await_merge,
    create_duplicate_pair,
    current_after_merge,
    trigger_and_await_merge,
    unique_title,
)
from demo.merge_extras import active_into_archived, three_same_title
from demo.reads import NO_VALUE
from demo.verdict import Case, Verdict

CLAIM = (
    "C2 (transition soundness): every transition respects the policy, and no revision produces a state in "
    "which a superseded value is returned as current."
)
REPETITIONS = 20


def _scored(outcome: MergeOutcome) -> bool:
    """A repetition is a case when a merge of two topics was seen and the dropped topic held the newer value. A
    same-topic write (the second `new_topic` appended to the first) merges nothing: the arrangement cannot be met."""
    return outcome.merged and not outcome.pair.upserted and outcome.dropped_held_newer is not False


def _repetition(i: int, outcome: MergeOutcome, current: object) -> dict:
    pair = outcome.pair
    return {
        "repetition": i,
        "title": pair.title,
        "older_id": pair.older_id,
        "newer_id": pair.newer_id,
        "merged": outcome.merged,
        "upserted": pair.upserted,
        "survivor_id": outcome.survivor_id,
        "dropped_id": outcome.dropped_id,
        "dropped_state": outcome.dropped_state,
        "window_s": outcome.window_s,
        "window_interactions": outcome.window_interactions,
        "waited_s": None if outcome.waited is None else outcome.waited.elapsed,
        "survivor_held": outcome.survivor_held,
        "current": "NO_VALUE" if current is NO_VALUE else current,
        "scored": _scored(outcome),
        "violation": _scored(outcome) and current == OLDER,
        "dropped_held_newer": outcome.dropped_held_newer,
    }


def _windows(reps: list[dict], seen: list[dict], repetitions: int, timeout: float) -> tuple[dict, dict]:
    """The window measurements and the `windows` entry the scorecard renders."""
    counted = [r["window_interactions"] for r in reps if r["merged"] and r["window_interactions"] is not None]
    if counted:  # a system that counts interactions (the reference GEM): the window is in interactions
        median = statistics.median(counted)
        median = int(median) if median == int(median) else median
        low, high = min(counted), max(counted)
        base = (
            "interactions from the duplicate-creating ingest's response to the first read that sees the merge "
            "(polling reads are not interactions)"
        )
        measures = {
            "merge_timeouts": sum(not r["merged"] for r in reps),
            "window_unit": "interactions",
            "window_median_interactions": median,
            "window_min_interactions": low,
            "window_max_interactions": high,
            "window_samples_interactions": counted,
            "window_samples": len(counted),
            "window_note": base,
        }
        value = f"median {median} interactions, range {low}-{high} over {len(counted)} repetitions"
        return measures, {"name": "Merge revision window", "value": value}
    samples = [r["window_s"] for r in reps if r["window_s"] is not None]
    timeouts = sum(not r["merged"] for r in reps)
    median = round(statistics.median(samples), 3) if samples else None
    low, high = (min(samples), max(samples)) if samples else (None, None)
    base = "from the duplicate-creating ingest's response to the poll that sees the merge"
    measures = {
        "merge_timeouts": timeouts,
        "window_unit": "seconds",
        "window_median_s": median,
        "window_min_s": low,
        "window_max_s": high,
        "window_samples": len(samples),
        "window_note": f"{base}; no duplicate is ever created on this system (same-topic write)"
        if seen and not samples
        else base,
    }
    value = (
        f"median {median} s, range {low}-{high} s over {len(samples)} repetitions"
        if samples
        else f"no merge seen within {timeout:g} s in {timeouts}/{repetitions} repetitions"
        if timeouts
        else "not applicable: no duplicate is ever created (same-topic write)"
    )
    return measures, {"name": "Merge revision window", "value": value}


def _observations(system: System, seen: list[dict], timeout: float) -> list[dict]:
    dropped = [r for r in seen if r["dropped_state"] is not None]
    if dropped:
        deleted = sum(r["dropped_state"] == DroppedState.DELETED for r in dropped)
        summary = (
            f"topic deleted on merge: dropped topic reads as missing in {deleted}/{len(dropped)} "
            f"merges (the rest archived: {len(dropped) - deleted})"
        )
    else:
        summary = "topic deleted on merge: not applicable, the system created no duplicate to merge"
    three, archived = three_same_title(system, timeout), active_into_archived(system, timeout)
    return [
        {"name": "topic deleted on merge", "summary": summary},
        {
            "name": "merge extras",
            "three_same_title": three,
            "active_into_archived": archived,
            "summary": f"three same-title: {three['summary']} | archived duplicate: {archived['summary']}",
        },
    ]


def _natural_count(system: System, repetitions: int, timeout: float) -> dict:
    """The natural arrangement, no setup write: two same-title `new_topic` writes on random ids, `repetitions` times."""
    stale = merged = 0
    for _ in range(repetitions):
        outcome = await_merge(
            system, create_duplicate_pair(system, unique_title("Vendor Contract (natural)"), DEADLINE), timeout
        )
        if outcome.merged and not outcome.pair.upserted:
            merged += 1
            stale += current_after_merge(system, outcome) == OLDER
    return {
        "repetitions": repetitions,
        "merged": merged,
        "stale_current": stale,
        "count": f"{stale}/{repetitions}",
        "note": "random ids, no setup write; the superseded value March 15 current after the merge; "
        "shown beside the existence result and not compared between systems",
    }


def measure_merges(system: System, repetitions: int = REPETITIONS, timeout: float = DEFAULT_TIMEOUT_S) -> Verdict:
    reps: list[dict] = []
    for i in range(1, repetitions + 1):
        outcome = trigger_and_await_merge(system, "Vendor Contract", DEADLINE, timeout)
        reps.append(_repetition(i, outcome, current_after_merge(system, outcome)))

    seen = [r for r in reps if r["merged"]]
    scored = [r for r in reps if r["scored"]]
    violations = sum(r["violation"] for r in scored)
    broken = [r for r in scored if r["current"] != NEWER]
    window_measures, window = _windows(reps, seen, repetitions, timeout)
    natural = (
        _natural_count(system, repetitions, timeout) if any(r["merged"] and not r["upserted"] for r in reps) else None
    )
    measurements = {
        "repetitions": repetitions,
        "merges": sum(not r["upserted"] for r in seen),
        "upserted": sum(r["upserted"] for r in seen),
        "arrangement_not_met": len(seen) - len(scored),
        "dropped_held_newer": sum(r["dropped_held_newer"] is True for r in seen),
        "violations": violations,
        "violation_rate": f"{violations}/{len(scored)}",
        "natural": natural,
        "natural_count": None if natural is None else natural["count"],
        **window_measures,
        "windows": [window],
        "per_repetition": reps,
    }
    observations = _observations(system, seen, timeout)
    if natural is not None:
        observations.append(
            {
                "name": "natural merge count",
                "summary": f"natural arrangement (random ids, no setup write): the superseded value current in "
                f"{natural['count']} repetitions ({natural['merged']} merged); not compared between systems",
            }
        )
    name = "the merge does not make the superseded value current in the arranged case (existence)"
    if scored:
        case = Case(
            name,
            not broken,
            f"{violations} of {len(scored)} arranged repetitions made {OLDER} current; "
            f"{len(broken) - violations} had no value or another value; "
            f"{len(reps) - len(scored)} were not cases (no merge seen or arrangement not met)",
        )
    else:
        case = Case(
            name,
            None,
            f"no arranged repetition was a case: {len(seen)} merges seen, "
            f"{len(seen) - len(scored)} with the arrangement not met, "
            f"{len(reps) - len(seen)} timeouts",
        )
    if not seen:
        return Verdict.absent(
            "C2(a)",
            {
                "probe": f"{repetitions} duplicate pairs written, each awaited by polling until "
                "one of the pair was deleted or archived",
                "merges_seen": 0,
                "waits_s": [r["waited_s"] for r in reps],
            },
            cases=[case],
            measurements=measurements,
            observations=observations,
        )
    return Verdict.from_cases("C2(a)", [case], measurements=measurements, observations=observations)


@check(row="C2(a)", claim=CLAIM)
def c2a(ctx: Ctx) -> Verdict:
    return measure_merges(ctx.system, timeout=merge.DEFAULT_TIMEOUT_S)  # read at call time: a test shortens it once
