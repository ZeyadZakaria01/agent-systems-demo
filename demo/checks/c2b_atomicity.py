"""C2(b), atomic commit: one `new_topic` with valid fields and an edge to a topic that does not exist.

Outcomes (spec stories 17, 21; report §9.4):
- the system errors and the topic or its fields persisted -> partial commit: **fail**;
- the system succeeds and reports the edge applied -> a soundness issue (reported as an observation and in the case
  text); the invalid edge never made the transition fail, so the verdict is **not-scored**;
- neither outcome (a clean rejection with nothing persisted, a success without the edge reported, a system with no
  edges) -> atomicity is not testable with this input: **not-scored**.

The verdict comes from the run only. The check reads the stored state afterwards (every topic, plus edges) to see what
persisted, matching on the unique title so it never depends on the response of a failed request.
"""

import uuid

import httpx

from demo.checks import Ctx, check
from demo.client import Rejected
from demo.reads import NO_VALUE, current_value
from demo.verdict import Case, Verdict

CLAIM = ("C2 (transition soundness), by construction (§4.3): every transition respects P_t, and policies are "
         "evaluated before an atomic commit.")
TITLE = "Website Redesign"
CASE = "an ingest with valid fields and an invalid edge commits nothing (all or nothing)"


@check(row="C2(b)", claim=CLAIM)
def c2b(ctx: Ctx) -> Verdict:
    s = ctx.system
    missing_id = str(uuid.uuid4())  # no topic has this id: nothing was ever written under it
    fields = {"Deadline": "March 15", "Owner": "Alice"}
    request = {"placement": "new_topic", "title": TITLE, "topic_kind": "project",
               "fields": [{"name": n, "value": v, "provenance": "kickoff-notes"} for n, v in fields.items()],
               "edges": [{"to_topic_id": missing_id, "kind": "extension"}]}
    response, error = None, None
    try:
        response = s.ingest(request)
    except Rejected as e:
        error = f"rejected {e.status}: {e.detail}"
    except httpx.HTTPStatusError as e:  # the server answered with a 5xx: still an error outcome
        error = f"server error {e.response.status_code}"

    state = s.read_state()
    topics = [t for t in state["topics"].values() if t.get("title") == TITLE]
    persisted = {name: current_value(t["fields"].get(name)) for t in topics for name in fields}
    persisted = {n: v for n, v in persisted.items() if v is not NO_VALUE}
    stored = (f"topics titled {TITLE!r}: {len(topics)}; fields stored: {persisted or 'none'}; "
              f"missing target created as a topic: {missing_id in state['topics']}")
    evidence = {"request": request, "response": response, "error": error, "missing_topic_id": missing_id,
                "stored": stored}

    if error is not None:
        if topics or persisted:
            return Verdict.from_cases("C2(b)", [Case(CASE, held=False, observation=f"partial commit: the system "
                                                     f"errored ({error}) but {stored}")],
                                      measurements={"evidence": evidence})
        return Verdict.from_cases("C2(b)", [Case(CASE, held=None, observation=(
            f"neither outcome: the system errored ({error}) and nothing persisted ({stored}); atomicity is not "
            "scored on this input"))], measurements={"evidence": evidence})

    applied = (response or {}).get("applied") or []
    reported = f"edge:{missing_id}" in applied
    edges = state["edges"]
    edge_exists = None if edges is None else any(missing_id in (e.get("from"), e.get("to")) for e in edges)
    stored_edge = {None: "the system's edges are not readable", False: "no edge is stored",
                   True: "a dangling edge is stored"}[edge_exists]
    observations = []
    if reported:
        issue = (f"soundness issue: the response lists edge:{missing_id} as applied, but the target topic does not "
                 f"exist and {stored_edge}")
        observations.append(issue)
        why = f"{issue}; the ingest succeeded, so atomicity is not testable with this input; {stored}"
    else:
        why = (f"neither outcome: the ingest succeeded without reporting the edge applied; {stored_edge}; atomicity is "
               f"not testable with this input; {stored}")
    return Verdict.from_cases("C2(b)", [Case(CASE, held=None, observation=why)], observations=observations,
                              measurements={"evidence": evidence})
