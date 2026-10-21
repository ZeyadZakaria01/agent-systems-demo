"""C2(b), atomic commit: one `new_topic` with a valid first field and a second field whose `ref_topic_id` points to a
topic that does not exist (F23; `graph_store.py:450-452` validates it mid-write).

Outcomes (spec stories 17, 21; report §9.4):
- the system errors and the topic or the first field persisted -> partial commit: **fail** (upstream, F23);
- the system refuses and nothing is stored -> the transition held all-or-nothing: **pass**;
- the system accepts the missing reference -> atomicity is not testable with this input: **not-scored**.

The verdict comes from the run only. The check reads the stored state afterwards (every topic) to see what persisted.
A failed request has no response to name the topic, so the topic is found by the title the system stores it under: the
check's title, with the scope suffix a live server adds (`describe()["title_scope"]`, as the storyline does) when there
is one. A topic the response names is found by its id.

The earlier input, an edge to a missing topic, is a separate ingest after the verdict is settled and never a verdict:
when the system reports the edge applied (`applied` lists `edge:<id>`) the check records the observation "edge reported
applied but not stored" (upstream, F17) with what the stored edges show.
"""

import uuid

import httpx

from demo.checks import Ctx, check
from demo.systems.adapter import Rejected
from demo.systems.reads import NO_VALUE, current_value
from demo.verdict import Case, Verdict

CLAIM = (
    "C2 (transition soundness), by construction (§4.3): every transition respects P_t, and policies are "
    "evaluated before an atomic commit."
)
TITLE = "Website Redesign"
EDGE_TITLE = "Website Redesign (edge)"
CASE = "a refused ingest with a valid field and a field referencing a missing topic commits nothing (all or nothing)"


def _verdict(held: bool | None, observation: str, evidence: dict, observations: list[dict]) -> Verdict:
    return Verdict.from_cases(
        "C2(b)",
        [Case(CASE, held=held, observation=observation)],
        observations=observations,
        measurements={"evidence": evidence},
    )


def _edge_observation(s) -> list[dict]:
    """The separate ingest with an edge to a missing topic: an observation only when the edge is reported applied."""
    missing_id = str(uuid.uuid4())
    try:
        response = s.ingest(
            {
                "placement": "new_topic",
                "title": EDGE_TITLE,
                "topic_kind": "project",
                "edges": [{"to_topic_id": missing_id, "kind": "extension"}],
            }
        )
    except (Rejected, httpx.HTTPStatusError):
        return []
    if f"edge:{missing_id}" not in ((response or {}).get("applied") or []):
        return []
    edges = s.read_state()["edges"]
    stored = {
        None: "the system's edges are not readable",
        False: "no edge is stored",
        True: "a dangling edge is stored",
    }[None if edges is None else any(missing_id in (e.get("from"), e.get("to")) for e in edges)]
    summary = (
        f"edge reported applied but not stored: the response lists edge:{missing_id} as applied, the target "
        f"topic does not exist and {stored}"
    )
    return [
        {
            "name": "edge reported applied but not stored",
            "summary": summary,
            "missing_topic_id": missing_id,
            "response": response,
        }
    ]


@check(row="C2(b)", claim=CLAIM)
def c2b(ctx: Ctx) -> Verdict:
    s = ctx.system
    missing_id = str(uuid.uuid4())  # no topic has this id: nothing was ever written under it
    request = {
        "placement": "new_topic",
        "title": TITLE,
        "topic_kind": "project",
        "fields": [
            {"name": "Deadline", "value": "March 15", "provenance": "kickoff-notes"},
            {"name": "Owner", "value": "Alice", "provenance": "kickoff-notes", "ref_topic_id": missing_id},
        ],
    }
    response, error = None, None
    try:
        response = s.ingest(request)
    except Rejected as e:
        error = f"rejected {e.status}: {e.detail}"
    except httpx.HTTPStatusError as e:  # the server answered with a 5xx: still an error outcome
        error = f"server error {e.response.status_code}"

    scope = s.describe().get("title_scope")
    stored_title = f"{TITLE} [live {scope}]" if scope else TITLE
    named_id = (response or {}).get("topic_id")
    state = s.read_state()
    topics = [
        t
        for t in state["topics"].values()
        if t.get("title") == stored_title or (named_id is not None and t.get("id") == named_id)
    ]
    persisted = {name: current_value(t["fields"].get(name)) for t in topics for name in ("Deadline", "Owner")}
    persisted = {n: v for n, v in persisted.items() if v is not NO_VALUE}
    stored = (
        f"topics titled {stored_title!r}: {len(topics)}; fields stored: {persisted or 'none'}; "
        f"missing target created as a topic: {missing_id in state['topics']}"
    )
    evidence = {
        "request": request,
        "response": response,
        "error": error,
        "missing_topic_id": missing_id,
        "stored": stored,
    }
    observations = _edge_observation(s)

    if error is None:
        return _verdict(
            None,
            f"the system accepted the missing reference, so atomicity is not testable with this input; {stored}",
            evidence,
            observations,
        )
    if topics or persisted:
        return _verdict(False, f"partial commit: the system errored ({error}) but {stored}", evidence, observations)
    return _verdict(True, f"the system refused ({error}) and nothing persisted ({stored})", evidence, observations)
