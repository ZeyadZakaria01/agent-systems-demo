"""C5 (bounded active state): the forgetting mechanism and the natural trajectory, driven by `demo/ramp.py`.

Two rows, one check each (so each row links its own snapshots and databases), matching C6:

- `C5-1` mechanism: a field-less topic ingested at salience 0.01, the store ramped past the 500-topic gate, then
  whether that topic is archived. Pass = the topic is archived. Partial = the count gate fired (n ≥ 500) but the
  topic was not archived. Absent = the system has no archived flag. There is no `fail` outcome: the count gate
  holds by construction once the check's own ingests are in, so a system that tracks archived either archives the
  topic (pass) or does not (partial); the gate case records the topic count, not an effect.
- `C5-2` natural trajectory: at each ramp size, on a fresh database, identical undated writes and a plain read,
  no salience setup. Counts archived topics; fail if the system tracks archived and none were; absent if it does
  not. The same runs fill the latency table (ingest / query client latency, settle time, archived count). On the
  largest ramp, a system that accepts `valid_at` also times `ramp.ASOF_SAMPLES` (20) as-of reads, reported in the
  latency output beside the plain reads.

C5 counts topics, not history entries. Each verdict states the system's declared bound (`describe()["declared_bound"]`:
upstream's 500-topic soft limit, the reference GEM's β) beside the active topic count (total minus archived). F24 is
recorded as a C5 observation in `C5-1`: a topic with fields ingested at salience 0.01 is reset to salience 1.0 and
never forgotten through `/v1` (upstream).

MemState verdicts come only from a recorded run. Tests pin the baseline (both absent) and fakes on the adapter.
"""

from __future__ import annotations

from demo.checks import Ctx, Row, check
from demo.adapter import System
from demo import ramp
from demo.ramp import archive_stats, as_of_read, filler, ingest_undated, median_ms, plain_read, scored_latencies
from demo.verdict import Case, Verdict

CLAUSE = ("C5 (Bounded active state). For every interaction count n, the active memory satisfies "
          "|D_t^active| ≤ β(n) for a policy-defined bound β; archived content remains recoverable.")
ROWS = [
    Row("C5-1", CLAUSE + " Mechanism: a field-less topic at salience 0.01 is archived once the 500-topic trigger fires."),
    Row("C5-2", CLAUSE + " Natural trajectory: archived topics counted at each ramp step with no setup."),
]
MECH_SALIENCE = 0.01


def _bound_text(bound: dict | None) -> str:
    return "the system declares no bound" if not bound else f"declared bound {bound['topics']} topics ({bound['name']})"


def _field_topic_observation(s: System) -> dict:
    """F24: a topic with fields, ingested at 0.01 after the pass ran, is it reset and never forgotten?"""
    topic_id = s.ingest({"placement": "new_topic", "title": "Low Salience With Fields", "salience": MECH_SALIENCE,
                         "summary": "Ingested at 0.01 with a field: can the system forget it?",
                         "fields": [{"name": "Contact", "value": "Bob", "provenance": "email"}]})["topic_id"]
    waited = s.wait_until(lambda: (s.read_topic(topic_id) or {}).get("archived") is True, ramp.ARCHIVE_WAIT_S / 4)
    topic = s.read_topic(topic_id) or {}
    reset = topic.get("salience") is not None and topic["salience"] > MECH_SALIENCE + 1e-9
    forgotten = topic.get("archived") is True
    return {"name": "topic with fields not forgotten", "topic_id": topic_id, "requested_salience": MECH_SALIENCE,
            "stored_salience": topic.get("salience"), "archived": topic.get("archived"), "reset": reset,
            "forgotten": forgotten, "waited_s": waited.elapsed,
            "summary": (f"a topic with a field ingested at salience {MECH_SALIENCE} reads salience "
                        f"{topic.get('salience')!r}, archived={topic.get('archived')!r}"
                        + (" (reset; never forgotten through /v1, F24)" if reset and not forgotten else ""))}


def _probe_no_archive(system: System, stats: dict) -> dict:
    sample = system.read_topic(next(iter(system.read_state()["topics"]))) if stats["total"] else None
    return {"probe": "archived flag is a nothing-value (the system does not archive)",
            "archived": None if sample is None else sample.get("archived"),
            "total": stats["total"]}


@check(row="C5-1", claim=ROWS[0].claim)
def c5_mechanism(ctx: Ctx) -> Verdict:
    with ctx.fresh_system("c5-mech") as s:
        target_id = s.ingest({"placement": "new_topic", "title": "Low Salience Canary",
                              "summary": "Field-less; ingested at 0.01 so the forgetting pass can take it",
                              "salience": MECH_SALIENCE})["topic_id"]
        for i in range(ramp.FORGET_GATE - 1):
            filler(s, i)
        s.ingest({"placement": "new_topic", "title": "Filler trigger",
                  "summary": "Ingested after the topic count reached the gate; its response schedules the pass"})
        waited = s.wait_until(lambda: (s.read_topic(target_id) or {}).get("archived") is True, ramp.ARCHIVE_WAIT_S)
        target = s.read_topic(target_id) or {}
        stats = archive_stats(s)
        if stats["archived"] is None:
            return Verdict.absent("C5-1", _probe_no_archive(s, stats),
                                  cases=[Case("the 0.01 topic is archived after the 500-topic trigger", None,
                                              "the system has no archived flag")])
        archived = target.get("archived") is True
        gate = stats["total"] >= ramp.FORGET_GATE
        bound = s.describe()["declared_bound"]
        cases = [
            Case("the count gate fires (n ≥ 500)", gate,
                 f"topics after the ramp={stats['total']}, gate={ramp.FORGET_GATE}; {_bound_text(bound)}"),
            Case("the 0.01 topic is archived after the 500-topic trigger", archived,
                 f"archived={target.get('archived')!r}, salience={target.get('salience')!r}, "
                 f"waited {waited.elapsed:.3f}s (timeout={waited.timed_out})"),
        ]
        field_topic = _field_topic_observation(s)
        return Verdict.from_cases("C5-1", cases, observations=[field_topic], measurements={
            "declared_bound": bound, "topics": stats["total"], "archived_total": stats["archived"],
            "target_archived": archived,
            "waited_s": waited.elapsed, "gate": ramp.FORGET_GATE, "start_salience": MECH_SALIENCE,
        })


def _settle(system: System):
    """Poll until the archived count repeats on two polls: a settle time with a floor of two polls (0.1 s each)."""
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
    settled = _settle(system)
    for _ in range(ramp.QUERY_SAMPLES):
        plain_read(system)
    query = scored_latencies(system, "query")
    stats = archive_stats(system)
    ingest = scored_latencies(system, "ingest")
    asof: list[float] = []  # last: reads can reshape salience, so they come after the counts the verdict rests on
    if n == max(ramp.STEPS) and system.describe()["accepts"]["valid_at"]:
        for _ in range(ramp.ASOF_SAMPLES):
            as_of_read(system)
        asof = scored_latencies(system, "query")[len(query):]
    return {
        "n": n, "repeat": repeat, "total": stats["total"], "archived": stats["archived"],
        "ingest_median_ms": median_ms(ingest), "ingest_samples": len(ingest),
        "query_samples_ms": query, "as_of_samples_ms": asof, "settle_s": settled.elapsed, "settle_timed_out": settled.timed_out,
    }


@check(row="C5-2", claim=ROWS[1].claim)
def c5_natural(ctx: Ctx) -> Verdict:
    ramps: list[dict] = []
    bound = None
    for n in ramp.STEPS:
        for repeat in range(1, ramp.REPEATS + 1):
            with ctx.fresh_system(f"ramp-{n}-r{repeat}") as s:
                ramps.append(_one_ramp(s, n, repeat))
                bound = s.describe()["declared_bound"]
    archived_values = [r["archived"] for r in ramps]
    if all(a is None for a in archived_values):
        return Verdict.absent("C5-2", {"probe": "archived flag is a nothing-value at every ramp step",
                                       "steps": list(ramp.STEPS), "repeats": ramp.REPEATS},
                              cases=[Case("archived topics counted at each ramp step", None,
                                          "the system has no archived flag")],
                              measurements={"ramps": ramps, "steps": list(ramp.STEPS), "repeats": ramp.REPEATS,
                                            "declared_bound": bound})
    any_archived = any((a or 0) > 0 for a in archived_values)
    counts = ", ".join(f"n={r['n']} r{r['repeat']}: {r['archived']}" for r in ramps)
    largest = max(ramps, key=lambda r: r["n"])
    active = largest["total"] - (largest["archived"] or 0)
    against = f"{active} active topics at n={largest['n']} against {_bound_text(bound)}"
    return Verdict.from_cases(
        "C5-2",
        [Case("archived topics counted at each ramp step", any_archived,
              f"archived at each (n, repeat): {counts}" + ("" if any_archived else "; none archived")
              + f"; {against}")],
        measurements={"ramps": ramps, "steps": list(ramp.STEPS), "repeats": ramp.REPEATS, "declared_bound": bound,
                      "active_at_largest_n": {"n": largest["n"], "active": active}},
    )

