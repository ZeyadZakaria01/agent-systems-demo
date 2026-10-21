"""C6 (retrieval-induced adaptation), two rows, one check each (so each row links its own snapshot and database).

The clause, copied from `docs/papers/2605.26252v1.md:218` (Definition 4):

    C6 (Retrieval-induced adaptation). Every retrieval that accesses u_i induces a transition in which the salience
    of u_i is updated. Repeated retrieval strictly reduces u_i's eligibility for attenuation.

- `C6-1` (clause 1): each retrieval raises the salience of the topics it returns, by at least `BUMP` per retrieval that
  returned them. Beside the verdict, as an observation (never graded): whether unrelated candidates rise too
  (over-reinforcement; upstream returns the top k whatever the similarity, `docs/findings.md` F8).
  A second case: an as-of read (`valid_at`, else `recorded_at`) of a topic raises its salience by `BUMP` too; n/a where
  the system accepts neither date.
- `C6-2` (clause 2): a field-less topic ingested at salience 0.03 is read by id until its salience reaches
  `FORGET_THRESHOLD` (0.05; a topic is eligible for forgetting while its salience is strictly below it), and the check
  stops at the **first forgetting pass**: the first observation in which any topic has been archived. After each read
  it looks for one; if none came by the time the topic left eligibility, the pass is made to run: field-less filler
  topics bring the topic count to `FORGET_GATE` (whether upstream counts archived topics too is [INFERENCE], code
  reading; the F15 run only shows the control archived), one more ingest follows, and the stored `archived` flags and
  salience are read. A control topic ingested at salience 0.01 and never read must be archived by that pass and the
  read topic must not be (and must not be eligible). When the control is not archived, the pass was not shown to run
  (that is C5's failure, not C6's): the row is `not-scored` with the observation "forgetting was not shown to run",
  never `partial`. If the control is archived and the read topic was too, the clause broke. Observation (never graded):
  a field write after the pass - does the salience the topic has then survive it (durability)?

Salience is read with `read_topic` (upstream `GET /api/ui/topics/{id}`), which never bumps. The only retrievals the
suite issues are the ones the checks count; each adds the system's `BUMP` to every topic it returns, so the expected
minimum rise of a topic is `BUMP` times the retrievals that returned it. A system that does not track salience reads
`None`: the capability is missing, so both rows are `absent`, with that read as the probe evidence (ADR 0002).
"""

from __future__ import annotations

from demo.checks import Ctx, check
from demo import ramp
from demo.adapter import Rejected, System, Waited, utc_now
from demo.reads import read_request
from demo.verdict import Case, Verdict

CLAUSE_1 = ("C6 (Retrieval-induced adaptation), clause 1: Every retrieval that accesses u_i induces a transition "
            "in which the salience of u_i is updated.")
CLAUSE_2 = ("C6 (Retrieval-induced adaptation), clause 2: Repeated retrieval strictly reduces u_i's eligibility "
            "for attenuation.")

FORGET_THRESHOLD = 0.05  # [INFERENCE: code reading, `Policies.forget_salience_threshold`] salience strictly below it is eligible
FORGET_GATE = 500  # [INFERENCE: code reading, `topic_count_soft_limit`] the pass runs once the topic count reaches it
BUMP = 0.1  # [INFERENCE: code reading, `Policies.query_salience_bump`] added to every topic a retrieval returns
START_SALIENCE = 0.03
CONTROL_SALIENCE = 0.01
MAX_RETRIEVALS = 10
MAX_RETRIEVALS_TO_FIRST_PASS = 100  # seeds at or above the threshold: reads continue until the first forgetting pass
RETRIEVALS_CLAUSE_1 = 3
ARCHIVE_WAIT_S = 20.0  # the pass runs after the ingest response; the control's archived flag is polled for this long
EPS = 1e-9

TARGET = ("Marathon Training", "Weekly long run schedule and mileage plan for the spring marathon")
UNRELATED = [
    ("Sourdough Starter", "Feeding schedule and hydration ratios for the kitchen sourdough starter"),
    ("Tax Return", "Documents and deadlines for filing the annual income tax return"),
    ("Kubernetes Upgrade", "Cluster node pool upgrade plan and rollback notes"),
]
PERMIT = ("Parking Permit Renewal", "Renewal paperwork for the street parking permit")
CONTROL = ("Library Card Renewal", "Never read; the control for the forgetting pass")
QUESTION = "how far is my weekend long running session"


def _stored(system: System, topic_id: str) -> dict:
    """The stored topic (`read_topic` never bumps), `{}` if the system has none."""
    return system.read_topic(topic_id) or {}


def salience(system: System, topic_id: str) -> float | None:
    return _stored(system, topic_id).get("salience")


def _fmt(x: float | None) -> str:
    return "not tracked" if x is None else f"{x:.3f}"


def _eligible(x: float | None) -> bool | None:
    return None if x is None else x < FORGET_THRESHOLD - EPS


def _no_salience_probe(read: dict) -> dict:
    """The absence probe: topics written (with a salience where the row asks for one) all read back without one."""
    return {"probe": "salience is a nothing-value on every topic the check wrote (the system does not track it)",
            "salience_read": read}


@check(row="C6-1", claim=CLAUSE_1)
def c6_clause_1(ctx: Ctx) -> Verdict:
    s = ctx.system
    labels: dict[str, str] = {}
    for title, summary in [TARGET, *UNRELATED]:
        topic_id = s.ingest({"placement": "new_topic", "title": title, "summary": summary,
                             "topic_kind": "project"})["topic_id"]
        labels[topic_id] = "target" if title == TARGET[0] else "unrelated"
    target_id = next(t for t, kind in labels.items() if kind == "target")
    start = {tid: salience(s, tid) for tid in labels}
    if all(x is None for x in start.values()):
        return Verdict.absent("C6-1", _no_salience_probe(start))

    returned_in: list[list[str]] = []
    for _ in range(RETRIEVALS_CLAUSE_1):
        response = s.query({"q": QUESTION, "stages": ["semantic"], "top_k": 8})
        returned_in.append([c["topic_id"] for c in response["candidates"] if c["topic_id"] in labels])
    end = {tid: salience(s, tid) for tid in labels}
    returns = {t: sum(t in r for r in returned_in) for t in labels}
    expected_min_rise = {t: BUMP * n for t, n in returns.items()}

    def rise(t: str) -> float | None:
        return None if start[t] is None or end[t] is None else end[t] - start[t]

    raised = [t for t in labels if returns[t] and (rise(t) or 0) >= expected_min_rise[t] - EPS]
    returned_topics = [t for t in labels if returns[t]]
    case = Case(
        "each retrieval raises the salience of the topics it returns",
        held=returns[target_id] > 0 and len(raised) == len(returned_topics),
        observation=f"{len(raised)} of {len(returned_topics)} returned topics rose by at least {BUMP} per retrieval "
                    f"that returned them ({RETRIEVALS_CLAUSE_1} retrievals; target {_fmt(start[target_id])} -> "
                    f"{_fmt(end[target_id])}, returned {returns[target_id]}x)"
                    + ("" if returns[target_id] else "; the target topic was not returned"))

    # Over-reinforcement: unrelated topics that were returned and rose. Not graded.
    unrelated = [t for t, kind in labels.items() if kind == "unrelated"]
    observations = [{
        "name": "over-reinforcement",
        "question": QUESTION,
        "target_topic_id": target_id,
        "unrelated_topics": len(unrelated),
        "unrelated_topics_returned": sum(bool(returns[t]) for t in unrelated),
        "unrelated_topics_that_rose": sum(bool(returns[t]) and (rise(t) or 0) > EPS for t in unrelated),
        "per_topic": {t: {"label": labels[t], "start": start[t], "end": end[t], "returned_in_retrievals": returns[t],
                          "expected_min_rise": expected_min_rise[t], "rise": rise(t)} for t in labels},
        "note": f"salience read with read_topic, which adds nothing; the only retrievals are the {RETRIEVALS_CLAUSE_1} counted ones",
    }]
    as_of, as_of_evidence = _as_of_case(s)
    return Verdict.from_cases("C6-1", [case, as_of], observations=observations,
                              measurements={"as_of": as_of_evidence})


AS_OF_SALIENCE = 0.5


def _as_of_case(s: System) -> tuple[Case, dict]:
    """An as-of read raises the salience of the topic it returns by the system's bump; n/a without a date."""
    name = "an as-of read raises the salience of the topic it returns"
    accepts = s.describe()["accepts"]
    axis = "valid_at" if accepts["valid_at"] else "recorded_at" if accepts["recorded_at"] else None
    if axis is None:
        return Case(name, None, "the system accepts neither valid_at nor recorded_at"), {"axis": None}
    title, summary = "As-of Salience Probe", "Field-less topic read once with an as-of date"
    topic_id = s.ingest({"placement": "new_topic", "title": title, "summary": summary,
                         "salience": AS_OF_SALIENCE})["topic_id"]
    before = salience(s, topic_id)
    request = {**read_request(topic_id, q=title), axis: utc_now()}
    try:
        response = s.query(request)
    except Rejected as e:
        return (Case(name, False, f"the {axis} read was {e}"),
                {"axis": axis, "topic_id": topic_id, "before": before, "rejected": str(e)})
    returned = any(c["topic_id"] == topic_id for c in response["candidates"])
    after = salience(s, topic_id)
    rose = before is not None and after is not None and after - before >= BUMP - EPS
    return (Case(name, returned and rose,
                 f"{axis} read: salience {_fmt(before)} -> {_fmt(after)}, expected at least {_fmt(None if before is None else before + BUMP)}"
                 + ("" if returned else "; the topic was not returned")),
            {"axis": axis, "topic_id": topic_id, "before": before, "after": after, "returned": returned})


def _force_forgetting_pass(s: System, topics: int, control_id: str) -> tuple[int, Waited]:
    """Field-less filler topics bring the topic count to `FORGET_GATE`, one more ingest schedules the pass, and the
    control's `archived` flag is polled. Returns the topic count afterwards and the wait."""
    for i in range(FORGET_GATE - topics):
        s.ingest({"placement": "new_topic", "title": f"Filler {i:04d}", "summary": f"Filler topic number {i}"})
    s.ingest({"placement": "new_topic", "title": "Filler trigger",
              "summary": "Ingested after the topic count reached the gate; its response schedules the pass"})
    waited = s.wait_until(lambda: _stored(s, control_id).get("archived") is True, ARCHIVE_WAIT_S)
    return FORGET_GATE + 1, waited


def _durability(s: System, target_id: str) -> dict:
    """A field write on the target: does it change the salience the topic has now (after any forgetting pass)?"""
    before = salience(s, target_id)
    durability: dict = {"name": "salience durability", "before_field_write": before, "after_field_write": None,
                        "reset": None}
    if before is None:
        durability["note"] = "salience is not tracked, so a field write has nothing to reset"
        return durability
    s.ingest({"placement": "extend_topic", "topic_id": target_id,
              "fields": [{"name": "Status", "value": "renewed", "provenance": "check"}]})
    after = salience(s, target_id)
    durability.update(after_field_write=after, reset=after is not None and abs(after - before) > EPS)
    durability["note"] = ("a field write changed the topic's salience (reinforcement not durable)"
                          if durability["reset"] else "a field write left the salience as it was")
    return durability


@check(row="C6-2", claim=CLAUSE_2)
def c6_clause_2(ctx: Ctx) -> Verdict:
    s = ctx.system
    seeds = s.describe()["c6_clause_2_seeds"] or {"target": START_SALIENCE, "control": CONTROL_SALIENCE}
    start_salience, control_salience = seeds["target"], seeds["control"]
    title, summary = PERMIT
    target_id = s.ingest({"placement": "new_topic", "title": title, "summary": summary,
                          "salience": start_salience})["topic_id"]
    control_id = s.ingest({"placement": "new_topic", "title": CONTROL[0], "summary": CONTROL[1],
                           "salience": control_salience})["topic_id"]
    start = salience(s, target_id)
    if start is None and salience(s, control_id) is None:
        return Verdict.absent("C6-2", _no_salience_probe({target_id: start, control_id: None}))
    trajectory = [start]
    hits = 0
    pass_seen = False
    # Read by id, so only the target is returned (the control must stay unread). After each read, has any topic been
    # archived (the first forgetting pass)? The check stops there.
    # A seed below the threshold is read until it leaves eligibility. A system declaring seeds at or above it (its
    # forgetting check runs every interaction) is read on every interaction until the first forgetting pass.
    to_first_pass = _eligible(start) is False
    limit = MAX_RETRIEVALS_TO_FIRST_PASS if to_first_pass else MAX_RETRIEVALS
    while len(trajectory) <= limit and trajectory[-1] is not None and (to_first_pass or _eligible(trajectory[-1]) is not False):
        response = s.query(read_request(target_id, q=title))
        hits += any(c["topic_id"] == target_id for c in response["candidates"])
        trajectory.append(salience(s, target_id))
        if (ramp.archive_stats(s)["archived"] or 0) > 0:
            pass_seen = True
            break
    reached = trajectory[-1]
    expected_min = None if start is None else start + BUMP * hits
    lifted = (reached is not None and expected_min is not None and _eligible(reached) is False
              and reached >= expected_min - EPS)
    lift = (f"keeps the topic at or above {FORGET_THRESHOLD}, from {start_salience}, until the first forgetting pass"
            if to_first_pass else f"lifts the topic from {start_salience} to at least {FORGET_THRESHOLD}")
    cases = [Case(f"repeated retrieval {lift}",
                  held=lifted,
                  observation=f"salience {' -> '.join(_fmt(x) for x in trajectory)}; {hits} retrieval(s) returned the "
                              f"topic, expected at least {_fmt(expected_min)}")]
    gate: dict = {"ran": False}
    not_shown = False
    if not lifted and not pass_seen:
        cases.append(Case("the topic left forgetting eligibility", held=False,
                          observation=f"salience {_fmt(reached)} never reached {FORGET_THRESHOLD}, so the topic is "
                                      "still (or not demonstrably not) eligible; the forgetting pass was not run"))
    else:
        topics, waited = (None, None) if pass_seen else _force_forgetting_pass(s, 2, control_id)
        control, target = _stored(s, control_id), _stored(s, target_id)
        control_archived, target_archived = control.get("archived") is True, target.get("archived") is True
        gate = {"ran": True, "first_pass_in_reads": pass_seen, "topics_after": topics,
                "waited_s": None if waited is None else waited.elapsed,
                "control": {"id": control_id, "start": control_salience, "salience": control.get("salience"),
                            "archived": control.get("archived")},
                "target": {"id": target_id, "salience": target.get("salience"), "archived": target.get("archived")}}
        where = "during the reads" if pass_seen else f"after the forced pass ({topics} topics)"
        seen = (f"{where} the target has salience {_fmt(target.get('salience'))}, archived={target.get('archived')!r}; "
                f"the never-read control at {control_salience} archived={control.get('archived')!r}")
        if control_archived or target_archived:
            left = not target_archived and _eligible(target.get("salience")) is False
            cases.append(Case("the topic left forgetting eligibility", held=control_archived and left,
                              observation=seen))
        else:
            not_shown = True
            cases.append(Case("the topic left forgetting eligibility", held=None,
                              observation=seen + " - the control was not archived, so no forgetting pass was shown "
                                                 f"to run (waited {ARCHIVE_WAIT_S:.0f}s after the forced pass)"))

    observations = [{"name": "salience trajectory", "target_topic_id": target_id, "start": start,
                     "after_each_retrieval": trajectory[1:], "threshold": FORGET_THRESHOLD},
                    {"name": "forgetting pass", **gate}, _durability(s, target_id)]
    if not_shown:
        observations.append({"name": "forgetting was not shown to run",
                             "summary": "forgetting was not shown to run: the never-read control was not archived "
                                        "(C5's failure, not C6's)"})
        return Verdict.not_scored("C6-2", cases=cases, observations=observations)
    return Verdict.from_cases("C6-2", cases, observations=observations)
