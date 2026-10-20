"""C6 (retrieval-induced adaptation), two rows, one check each (so each row links its own snapshot and database).

The clause, copied from `docs/papers/2605.26252v1.md:218` (Definition 4):

    C6 (Retrieval-induced adaptation). Every retrieval that accesses u_i induces a transition in which the salience
    of u_i is updated. Repeated retrieval strictly reduces u_i's eligibility for attenuation.

- `C6-1` (clause 1): each retrieval raises the salience of the topics it returns, by at least `BUMP` per retrieval that
  returned them. Beside the verdict, as an observation (never graded): whether unrelated candidates rise too
  (over-reinforcement; upstream returns the top k whatever the similarity, `docs/findings.md` F8).
- `C6-2` (clause 2): a field-less topic ingested at salience 0.03 is read by id until its salience reaches
  `FORGET_THRESHOLD` (0.05; a topic is eligible for forgetting while its salience is strictly below it). Then the
  forgetting pass is made to run: field-less filler topics bring the topic count to `FORGET_GATE` (upstream counts
  archived topics too), one more ingest follows, and the stored `archived` flag and salience are read. A control topic
  ingested at salience 0.01 and never read must be archived by that pass; if it is not, the pass cannot be shown to
  have run and the row is not scored (never a pass). Observation (never graded): a field write afterwards - does the
  reinforced salience survive it (durability)?

Salience is read with `read_topic` (upstream `GET /api/ui/topics/{id}`), which never bumps. The only retrievals the
suite issues are the ones the checks count; each adds the system's `BUMP` to every topic it returns, so the expected
minimum rise of a topic is `BUMP` times the retrievals that returned it. A system that does not track salience reads
`None`: the clauses fail, with salience unchanged.
"""

from __future__ import annotations

from demo.checks import Ctx, check
from demo.client import System
from demo.reads import read_request
from demo.verdict import Case, Verdict

CLAUSE_1 = ("C6 (Retrieval-induced adaptation), clause 1: Every retrieval that accesses u_i induces a transition "
            "in which the salience of u_i is updated.")
CLAUSE_2 = ("C6 (Retrieval-induced adaptation), clause 2: Repeated retrieval strictly reduces u_i's eligibility "
            "for attenuation.")

FORGET_THRESHOLD = 0.05  # upstream Policies.forget_salience_threshold: salience strictly below it is eligible
FORGET_GATE = 500  # upstream topic_count_soft_limit: the forgetting pass runs once the topic count (archived included) reaches it
BUMP = 0.1  # upstream Policies.query_salience_bump: added to every topic a retrieval returns
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
QUESTION = "how far is my weekend long running session"


def salience(system: System, topic_id: str) -> float | None:
    topic = system.read_topic(topic_id)
    return None if topic is None else topic.get("salience")


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
        held=bool(returned_topics) and len(raised) == len(returned_topics),
        observation=f"{len(raised)} of {len(returned_topics)} returned topics rose by at least {BUMP} per retrieval "
                    f"that returned them ({RETRIEVALS_CLAUSE_1} retrievals; target {_fmt(start[target_id])} -> "
                    f"{_fmt(end[target_id])}, returned {returns[target_id]}x)"
                    + ("" if returned_topics else "; nothing was returned"))

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


@check(row="C6-2", claim=CLAUSE_2)
def c6_clause_2(ctx: Ctx) -> Verdict:
    s = ctx.system
    title, summary = "Parking Permit Renewal", "Renewal paperwork for the street parking permit"
    target_id = s.ingest({"placement": "new_topic", "title": title, "summary": summary,
                          "salience": START_SALIENCE})["topic_id"]
    control_id = s.ingest({"placement": "new_topic", "title": "Library Card Renewal",
                           "summary": "Never read; the control for the forgetting pass",
                           "salience": CONTROL_SALIENCE})["topic_id"]
    topics = 2
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
    evaluable = None
    if not lifted:
        cases.append(Case("the topic left forgetting eligibility", held=False,
                          observation=f"salience {_fmt(reached)} never reached {FORGET_THRESHOLD}, so the topic is "
                                      "still (or not demonstrably not) eligible; the forgetting pass was not run"))
    else:
        for i in range(FORGET_GATE - topics):
            s.ingest({"placement": "new_topic", "title": f"Filler {i:04d}", "summary": f"Filler topic number {i}"})
        s.ingest({"placement": "new_topic", "title": "Filler trigger",
                  "summary": "Ingested after the topic count reached the gate; its response schedules the pass"})
        topics = FORGET_GATE + 1
        waited = s.wait_until(lambda: (s.read_topic(control_id) or {}).get("archived") is True, ARCHIVE_WAIT_S)
        control = s.read_topic(control_id) or {}
        target = s.read_topic(target_id) or {}
        evaluable = control.get("archived") is True
        gate = {"ran": True, "topics_after": topics, "waited_s": waited.elapsed,
                "control": {"id": control_id, "start": CONTROL_SALIENCE, "salience": control.get("salience"),
                            "archived": control.get("archived")},
                "target": {"id": target_id, "salience": target.get("salience"), "archived": target.get("archived")}}
        left = target.get("archived") is False and _eligible(target.get("salience")) is False
        cases.append(Case(
            "the topic left forgetting eligibility", held=left if evaluable else None,
            observation=(f"after the pass ({topics} topics) the target has salience {_fmt(target.get('salience'))}, "
                         f"archived={target.get('archived')!r}; the never-read control at {CONTROL_SALIENCE} "
                         f"archived={control.get('archived')!r}")
                        + ("" if evaluable else " - the control was not archived within "
                           f"{ARCHIVE_WAIT_S:.0f}s, so the pass cannot be shown to have run; not evaluable")))

    # Durability: a field write after reinforcement. Not graded.
    durability: dict = {"name": "salience durability", "before_field_write": reached, "after_field_write": None,
                        "reset": None}
    if reached is None:
        durability["note"] = "salience is not tracked, so a field write has nothing to reset"
    else:
        s.ingest({"placement": "extend_topic", "topic_id": target_id,
                  "fields": [{"name": "Status", "value": "renewed", "provenance": "check"}]})
        after = salience(s, target_id)
        durability.update(after_field_write=after, reset=after is not None and abs(after - reached) > EPS)
        durability["note"] = ("a field write changed the topic's salience (reinforcement not durable)"
                              if durability["reset"] else "a field write left the salience as it was")
    observations = [{"name": "salience trajectory", "target_topic_id": target_id, "start": start,
                     "after_each_retrieval": trajectory[1:], "threshold": FORGET_THRESHOLD},
                    {"name": "forgetting pass", **gate}, durability]
    if evaluable is False:
        return Verdict.not_scored("C6-2", cases=cases, observations=observations)
    return Verdict.from_cases("C6-2", cases, observations=observations)
