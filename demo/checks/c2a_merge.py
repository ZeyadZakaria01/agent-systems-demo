"""C2(a) (superseded value): how often the Reasoner's merge makes a superseded value current.

Twenty repetitions in one fresh database, random topic ids, distinct titles. Each repetition makes the topic to be
dropped hold the newer value: two topics are written through `/v1` under distinct titles, the lower id gets `Deadline:
March 15` and the higher id `Deadline: April 20` (MemState keeps the lower id, F9), both are given one title by a
labelled setup `PATCH title` (values are never written by an editor endpoint), and a `/v1 extend_topic` with no fields
triggers the merge (`demo/merge.py`). A system that cannot retitle falls back to two same-title `new_topic` writes
(the baseline upserts them). A case holds when the newer value is current after the merge; the violation (a measure
beside the verdict, never compared between engines) is the superseded value March 15 being current; no value or a
null is a broken case but not a violation. All held = pass, some = partial, none = fail.

The merge is awaited by polling (`demo/merge.py`); the window per repetition is the wait logged by the adapter.
A repetition whose merge is not seen within the timeout is not a case (`held=None`); if that is every repetition the
row is `absent` with those waits as the probe evidence. Beside the verdict: the window median and range, the
observation "topic deleted on merge", and the extras of `demo/merge_extras.py`.
"""

from __future__ import annotations

import statistics

from demo.checks import Ctx, check
from demo.merge import DEFAULT_TIMEOUT_S, current_after_merge, trigger_and_await_merge
from demo.merge_extras import active_into_archived, three_same_title
from demo.reads import NO_VALUE
from demo.verdict import Case, Verdict

CLAIM = ("C2 (transition soundness): every transition respects the policy, and no revision produces a state in "
         "which a superseded value is returned as current.")
REPETITIONS = 20
OLDER, NEWER = "March 15", "April 20"


@check(row="C2(a)", claim=CLAIM)
def c2a(ctx: Ctx) -> Verdict:
    s = ctx.system
    cases: list[Case] = []
    reps: list[dict] = []
    for i in range(1, REPETITIONS + 1):
        outcome = trigger_and_await_merge(s, "Vendor Contract", OLDER, NEWER)
        current = current_after_merge(s, outcome)
        pair = outcome.pair
        rep = {"repetition": i, "title": pair.title, "older_id": pair.older_id, "newer_id": pair.newer_id,
               "merged": outcome.merged, "upserted": pair.upserted, "survivor_id": outcome.survivor_id,
               "dropped_id": outcome.dropped_id, "dropped_state": outcome.dropped_state,
               "window_s": outcome.window_s, "waited_s": None if outcome.waited is None else outcome.waited.elapsed,
               "survivor_held": None if outcome.survivor_id is None else
               "newer" if outcome.survivor_id == pair.newer_id else "older",
               "current": "NO_VALUE" if current is NO_VALUE else current,
               "violation": outcome.merged and current == OLDER,
               "dropped_held_newer": None if outcome.dropped_id is None else outcome.dropped_id == pair.newer_id}
        reps.append(rep)
        if not outcome.merged:
            cases.append(Case(f"repetition {i}: the newer value is current after the merge", None,
                              f"no merge seen within {outcome.waited.elapsed:.1f}s (timeout)"))
            continue
        how = ("same topic (upsert, no duplicate)" if pair.upserted else
               f"survivor held the {rep['survivor_held']} value, dropped topic {outcome.dropped_state}")
        cases.append(Case(f"repetition {i}: the newer value is current after the merge", current == NEWER,
                          f"{how}; current={rep['current']!r}"))

    merged = [r for r in reps if r["merged"]]
    violations = sum(r["violation"] for r in merged)
    windows = [r["window_s"] for r in reps if r["window_s"] is not None]
    timeouts = sum(not r["merged"] for r in reps)
    measurements = {
        "repetitions": REPETITIONS, "merged": len(merged), "merge_timeouts": timeouts,
        "random_id_counts": {"stale value current": [violations, len(merged)]},
        "dropped_held_newer": sum(r["dropped_held_newer"] is True for r in merged),
        "violations": violations, "violation_rate": f"{violations}/{len(merged)}",
        "window_median_s": round(statistics.median(windows), 3) if windows else None,
        "window_min_s": min(windows) if windows else None, "window_max_s": max(windows) if windows else None,
        "window_samples": len(windows),
        "window_note": ("from the duplicate-creating ingest's response to the poll that sees the merge; "
                        "no duplicate is ever created on this system (upsert)" if merged and not windows else
                        "from the duplicate-creating ingest's response to the poll that sees the merge"),
        "per_repetition": reps,
    }
    measurements["windows"] = [{"name": "Merge revision window", "value": (
        f"median {measurements['window_median_s']} s, range {measurements['window_min_s']}-{measurements['window_max_s']} s "
        f"over {len(windows)} repetitions" if windows else
        f"no merge seen within {DEFAULT_TIMEOUT_S:g} s in {timeouts}/{REPETITIONS} repetitions" if timeouts else
        "not applicable: no duplicate is ever created (upsert)")}]
    dropped = [r for r in merged if r["dropped_state"] is not None]
    observations: list = []
    if dropped:
        deleted = sum(r["dropped_state"] == "deleted" for r in dropped)
        observations.append({"name": "topic deleted on merge",
                             "summary": f"topic deleted on merge: dropped topic reads as missing in {deleted}/{len(dropped)} "
                                        f"merges (the rest archived: {len(dropped) - deleted})"})
    else:
        observations.append({"name": "topic deleted on merge",
                             "summary": "topic deleted on merge: not applicable, the system created no duplicate to merge"})
    observations.append({"name": "merge extras", "three_same_title": (three := three_same_title(s)),
                         "active_into_archived": (arch := active_into_archived(s)),
                         "summary": f"three same-title: {three['summary']} | archived duplicate: {arch['summary']}"})

    if not merged:
        return Verdict.absent("C2(a)", {"probe": f"{REPETITIONS} duplicate pairs written, each awaited by polling until "
                                                 "one of the pair was deleted or archived",
                                        "merges_seen": 0, "waits_s": [r["waited_s"] for r in reps]},
                              cases=cases, measurements=measurements, observations=observations)
    return Verdict.from_cases("C2(a)", cases, measurements=measurements, observations=observations)
