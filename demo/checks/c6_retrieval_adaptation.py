"""C6 (retrieval-induced adaptation), two rows, one check each (so each row links its own snapshot and database).

The clause, copied from `docs/papers/2605.26252v1.md:218` (Definition 4):

    C6 (Retrieval-induced adaptation). Every retrieval that accesses u_i induces a transition in which the salience
    of u_i is updated. Repeated retrieval strictly reduces u_i's eligibility for attenuation.

- `C6-1` (clause 1): each retrieval raises the salience of the topics it returns, by at least `BUMP` per retrieval that
  returned them. Beside the verdict, as an observation (never graded): whether unrelated candidates rise too
  (over-reinforcement; upstream returns the top k whatever the similarity, `docs/findings.md` F8).
- `C6-2` (clause 2): a field-less topic ingested at salience 0.03 is read by id until its salience reaches
  `FORGET_THRESHOLD` (0.05; a topic is eligible for forgetting while its salience is strictly below it). Then the
  forgetting pass is made to run: field-less filler topics bring the topic count to `FORGET_GATE` (whether upstream
  counts archived topics too is [INFERENCE], code reading; the F15 run only shows the control archived), one more
  ingest follows, and the stored `archived` flag and salience are read. A control topic ingested at salience 0.01 and
  never read must be archived by that pass; if it is not, the pass cannot be shown to have run, so the "left
  eligibility" case does not hold: the row is `partial` (reinforcement held, forgetting not demonstrated), never a
  pass. Observation (never graded): a field write after the pass - does the salience the topic has then survive it
  (durability)?

Salience is read with `read_topic` (upstream `GET /api/ui/topics/{id}`), which never bumps. The only retrievals the
suite issues are the ones the checks count; each adds the system's `BUMP` to every topic it returns, so the expected
minimum rise of a topic is `BUMP` times the retrievals that returned it. A system that does not track salience reads
`None`: the clauses fail, with salience unchanged.
"""

from __future__ import annotations

from demo.checks import Ctx, check
from demo.adapter import System, Waited
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
    return Verdict.from_cases("C6-1", [case], observations=observations)


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
    title, summary = PERMIT
    target_id = s.ingest({"placement": "new_topic", "title": title, "summary": summary,
                          "salience": START_SALIENCE})["topic_id"]
    control_id = s.ingest({"placement": "new_topic", "title": CONTROL[0], "summary": CONTROL[1],
                           "salience": CONTROL_SALIENCE})["topic_id"]
    start = salience(s, target_id)
    trajectory = [start]
    hits = 0
    # Read by id, so only the target is returned (the control must stay unread).
    while len(trajectory) <= MAX_RETRIEVALS and _eligible(trajectory[-1]) is not False and trajectory[-1] is not None:
        response = s.query(read_request(target_id, q=title))
        hits += any(c["topic_id"] == target_id for c in response["candidates"])
        trajectory.append(salience(s, target_id))
    reached = trajectory[-1]
    expected_min = None if start is None else start + BUMP * hits
    lifted = (reached is not None and expected_min is not None and _eligible(reached) is False
              and reached >= expected_min - EPS)
    cases = [Case(f"repeated retrieval lifts the topic from {START_SALIENCE} to at least {FORGET_THRESHOLD}",
                  held=lifted,
                  observation=f"salience {' -> '.join(_fmt(x) for x in trajectory)}; {hits} retrieval(s) returned the "
                              f"topic, expected at least {_fmt(expected_min)}")]
    gate: dict = {"ran": False}
    if not lifted:
        cases.append(Case("the topic left forgetting eligibility", held=False,
                          observation=f"salience {_fmt(reached)} never reached {FORGET_THRESHOLD}, so the topic is "
                                      "still (or not demonstrably not) eligible; the forgetting pass was not run"))
    else:
        topics, waited = _force_forgetting_pass(s, 2, control_id)
        control, target = _stored(s, control_id), _stored(s, target_id)
        pass_ran = control.get("archived") is True
        gate = {"ran": True, "topics_after": topics, "waited_s": waited.elapsed,
                "control": {"id": control_id, "start": CONTROL_SALIENCE, "salience": control.get("salience"),
                            "archived": control.get("archived")},
                "target": {"id": target_id, "salience": target.get("salience"), "archived": target.get("archived")}}
        left = target.get("archived") is False and _eligible(target.get("salience")) is False
        cases.append(Case(
            "the topic left forgetting eligibility", held=pass_ran and left,
            observation=(f"after the pass ({topics} topics) the target has salience {_fmt(target.get('salience'))}, "
                         f"archived={target.get('archived')!r}; the never-read control at {CONTROL_SALIENCE} "
                         f"archived={control.get('archived')!r}")
                        + ("" if pass_ran else " - the control was not archived within "
                           f"{ARCHIVE_WAIT_S:.0f}s, so the pass cannot be shown to have run; forgetting not "
                           "demonstrated")))

    observations = [{"name": "salience trajectory", "target_topic_id": target_id, "start": start,
                     "after_each_retrieval": trajectory[1:], "threshold": FORGET_THRESHOLD},
                    {"name": "forgetting pass", **gate}, _durability(s, target_id)]
    return Verdict.from_cases("C6-2", cases, observations=observations)
