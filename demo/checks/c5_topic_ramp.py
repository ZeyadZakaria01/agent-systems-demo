"""C5 (bounded active state): the forgetting mechanism and the natural trajectory, driven by `demo/ramp.py`.

Two rows, one check each (so each row links its own snapshots and databases), matching C6:

- `C5-1` mechanism: a field-less topic ingested at salience 0.01, the store ramped past the 500-topic gate, then
  whether that topic is archived. Pass = the topic is archived. Partial = the count gate fired (n ≥ 500) but the
  topic was not archived. Absent = the system has no archived flag.
- `C5-2` natural trajectory: at each ramp size, on a fresh database, identical undated writes and a plain read,
  no salience setup. Counts archived topics; fail if the system tracks archived and none were; absent if it does
  not. The same runs fill the latency table (ingest / query client latency, Reasoner wait, archived count).

MemState verdicts come only from a recorded run. Tests pin the baseline (both absent) and fakes on the adapter.
"""

from __future__ import annotations

from demo.checks import Ctx, Row, check
from demo.client import System
from demo.ramp import (ARCHIVE_WAIT_S, FORGET_GATE, REPEATS, STEPS, archive_stats, filler, ingest_undated,
                       median_ms, plain_read, scored_latencies)
from demo.verdict import Case, Verdict

CLAUSE = ("C5 (Bounded active state). For every interaction count n, the active memory satisfies "
          "|D_t^active| ≤ β(n) for a policy-defined bound β; archived content remains recoverable.")
ROWS = [
    Row("C5-1", CLAUSE + " Mechanism: a field-less topic at salience 0.01 is archived once the 500-topic trigger fires."),
    Row("C5-2", CLAUSE + " Natural trajectory: archived topics counted at each ramp step with no setup."),
]
MECH_SALIENCE = 0.01


def _probe_no_archive(system: System, stats: dict) -> dict:
    sample = system.read_topic(next(iter(system.read_state()["topics"]))) if stats["total"] else None
    return {"probe": "archived flag is a nothing-value (the system does not archive)",
            "archived": None if sample is None else sample.get("archived"),
            "total": stats["total"]}


def _mechanism(ctx: Ctx) -> Verdict:
    with ctx.fresh_system("c5-mech") as s:
        target_id = s.ingest({"placement": "new_topic", "title": "Low Salience Canary",
                              "summary": "Field-less; ingested at 0.01 so the forgetting pass can take it",
                              "salience": MECH_SALIENCE})["topic_id"]
        topics = 1
        for i in range(FORGET_GATE - topics):
            filler(s, i)
        s.ingest({"placement": "new_topic", "title": "Filler trigger",
                  "summary": "Ingested after the topic count reached the gate; its response schedules the pass"})
        topics = FORGET_GATE + 1
        waited = s.wait_until(lambda: (s.read_topic(target_id) or {}).get("archived") is True, ARCHIVE_WAIT_S)
        target = s.read_topic(target_id) or {}
        stats = archive_stats(s)
        if stats["archived"] is None:
            return Verdict.absent("C5-1", _probe_no_archive(s, stats),
                                  cases=[Case("the 0.01 topic is archived after the 500-topic trigger", None,
                                              "the system has no archived flag")])
        archived = target.get("archived") is True
        gate = stats["total"] >= FORGET_GATE
        cases = [
            Case("the count gate fires (n ≥ 500)", gate,
                 f"topics after the ramp={stats['total']}, gate={FORGET_GATE}"),
            Case("the 0.01 topic is archived after the 500-topic trigger", archived,
                 f"archived={target.get('archived')!r}, salience={target.get('salience')!r}, "
                 f"waited {waited.elapsed:.3f}s (timeout={waited.timed_out})"),
        ]
        return Verdict.from_cases("C5-1", cases, measurements={
            "topics": stats["total"], "archived_total": stats["archived"], "target_archived": archived,
            "waited_s": waited.elapsed, "gate": FORGET_GATE, "start_salience": MECH_SALIENCE,
        })


def _reasoner_wait(system: System):
    """Poll until the archived count repeats, so the background pass is not still running."""
    seen: dict = {"value": object(), "same": 0}

    def pred() -> bool:
        cur = archive_stats(system)["archived"]
        if cur == seen["value"]:
            seen["same"] += 1
            return seen["same"] >= 2
        seen["value"], seen["same"] = cur, 1
        return False

    return system.wait_until(pred, 5.0, interval=0.1)


def _one_ramp(system: System, n: int, repeat: int) -> dict:
    for i in range(n):
        ingest_undated(system, i)
    waited = _reasoner_wait(system)
    _ = plain_read(system)
    stats = archive_stats(system)
    ingest = scored_latencies(system, "ingest")
    query = scored_latencies(system, "query")
    return {
        "n": n, "repeat": repeat, "total": stats["total"], "archived": stats["archived"],
        "ingest_median_ms": median_ms(ingest), "ingest_samples": len(ingest),
        "query_ms": query[-1] if query else None, "reasoner_wait_s": waited.elapsed,
        "reasoner_timed_out": waited.timed_out,
    }


def _natural(ctx: Ctx) -> Verdict:
    ramps: list[dict] = []
    for n in STEPS:
        for repeat in range(1, REPEATS + 1):
            with ctx.fresh_system(f"ramp-{n}-r{repeat}") as s:
                ramps.append(_one_ramp(s, n, repeat))
    archived_values = [r["archived"] for r in ramps]
    if all(a is None for a in archived_values):
        return Verdict.absent("C5-2", {"probe": "archived flag is a nothing-value at every ramp step",
                                       "steps": list(STEPS), "repeats": REPEATS},
                              cases=[Case("archived topics counted at each ramp step", None,
                                          "the system has no archived flag")],
                              measurements={"ramps": ramps, "steps": list(STEPS), "repeats": REPEATS})
    any_archived = any((a or 0) > 0 for a in archived_values)
    counts = ", ".join(f"n={r['n']} r{r['repeat']}: {r['archived']}" for r in ramps)
    return Verdict.from_cases(
        "C5-2",
        [Case("archived topics counted at each ramp step", any_archived,
              f"archived at each (n, repeat): {counts}" + ("" if any_archived else "; none archived"))],
        measurements={"ramps": ramps, "steps": list(STEPS), "repeats": REPEATS},
    )


@check(row="C5-1", claim=ROWS[0].claim)
def c5_mechanism(ctx: Ctx) -> Verdict:
    return _mechanism(ctx)


@check(row="C5-2", claim=ROWS[1].claim)
def c5_natural(ctx: Ctx) -> Verdict:
    return _natural(ctx)
