"""C2(c), declarative policies `<event, condition, action>`: a policy added at runtime must reject a violating write.

Pass criteria (spec stories 22, 65; the reference GEM tickets are built against them). The check first asks the adapter
to `add_policy` "Deadline not before Start" (`{"name": "deadline-not-before-start", "event": "write", "condition":
{"field": "Deadline", "op": "<", "other_field": "Start"}, "action": "reject"}`, see `adapter.py`). A system that takes it
is scored on two cases, each on the stored state read back:
1. *The policy rejects.* A write that sets Deadline before Start (`new_topic`, Start 2026-03-10, Deadline 2026-03-01)
   is `Rejected` and the read-back shows nothing saved: every topic and every field reads as it did before the write.
2. *Control.* An ordinary write (Start 2026-03-10, Deadline 2026-03-20) commits and its fields read back.
A system whose policy is ignored accepts case 1's write: **fail** (violating write accepted), whatever the control
shows; one that rejects the ordinary write too breaks the control, so it is **partial**; both held is **pass**.

No way to add a policy at runtime (`add_policy` returns nothing) is looked for before it is scored absent (ADR 0002,
spec story 17, the F17 schema probe). Through the adapter's `probe` it reads the API schema
(`/openapi.json`: routes, request/response schemas, numeric parameters), the interactive docs, the routes where a policy
or config surface would sit if it existed, and the config-like routes the server really has (`/api/ui/system-context`,
`/api/ui/datamodel`). It also searches the schema for the names of MemState's numeric governance knobs
(`Policies` in `core/models.py`, [INFERENCE] from code: constructed with defaults, never read from a request).

Absent: no route or schema is named for policies (or rules, constraints, invariants, triggers) as a whole word of its
name (`/v1/policies`, `PolicyRule`); a property named so (`trigger_count` in some schema) is recorded as evidence only,
no candidate route answers, and no schema carries event + condition + action together -> **absent**,
with the probe attached. A policy-bearing route or schema is not scored here: the check raises, so the run shows an
error until a person extends the probe to exercise it. A system with no API at all (the baseline) answers every probe
with nothing, which is the evidence.
"""

import json
import re

from demo.adapter import Rejected, System
from demo.checks import Ctx, check
from demo.reads import current_value
from demo.verdict import FAIL, Case, Verdict

CLAIM = ("C2 (transition soundness), by construction (§4.3): every transition respects P_t, the declarative "
         "policies ⟨event, condition, action⟩.")

POLICY_WORDS = frozenset({"policy", "policies", "rule", "rules", "constraint", "constraints", "invariant",
                          "invariants", "trigger", "triggers"})
TRIPLE = ("event", "condition", "action")
# `Policies` in MemState's core/models.py (the numeric knobs); searched for in the schema, never assumed present
KNOB_NAMES = ("max_field_history", "max_topics_for_forget_scan", "forget_salience_threshold",
              "topic_count_soft_limit", "query_salience_bump", "embedding_dimension")
# where a policy or config surface would sit if the server had one (none is a MemState route)
GUESSED_ROUTES = ("/policies", "/rules", "/config", "/settings", "/v1/policies", "/v1/rules", "/v1/config",
                  "/api/policies", "/api/config", "/api/ui/policies", "/api/ui/rules", "/api/ui/config",
                  "/api/ui/settings", "/api/llm/policies", "/api/llm/config")
REAL_CONFIG_ROUTES = ("/api/ui/system-context", "/api/ui/datamodel")
DOCS = ("/docs", "/redoc")

POLICY = {"name": "deadline-not-before-start", "event": "write",
          "condition": {"field": "Deadline", "op": "<", "other_field": "Start"}, "action": "reject"}
START, VIOLATING_DEADLINE, ORDINARY_DEADLINE = "2026-03-10", "2026-03-01", "2026-03-20"


def _status(probe: dict | None) -> int | None:
    return None if probe is None else probe["status"]


def _types(prop: dict) -> set[str]:
    kinds = {prop["type"]} if "type" in prop else set()
    for alt in prop.get("anyOf", []) + prop.get("oneOf", []):
        kinds |= _types(alt)
    return kinds


def _policy_named(name: str) -> bool:
    """Does a whole word of the name (split at camelCase and at every non-alphanumeric) say policy?"""
    words = re.split(r"[^A-Za-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name))
    return any(w.lower() in POLICY_WORDS for w in words)


def _read_schema(openapi: dict) -> dict:
    schemas = openapi.get("components", {}).get("schemas", {})
    props = {name: sorted(spec.get("properties", {})) for name, spec in schemas.items()}
    numeric = sorted(f"{name}.{p}: {'/'.join(sorted(_types(spec) & {'integer', 'number'}))}"
                     for name, s in schemas.items() for p, spec in s.get("properties", {}).items()
                     if _types(spec) & {"integer", "number"})
    paths = {path: sorted(ops) for path, ops in openapi.get("paths", {}).items()}
    return {"paths": paths, "schema_properties": props, "numeric_properties": numeric,
            "policy_term_hits": sorted({n for n in [*paths, *schemas] if _policy_named(n)}),
            "policy_term_property_hits": sorted({p for ps in props.values() for p in ps if _policy_named(p)}),
            "triple_schemas": sorted(n for n, ps in props.items() if all(t in ps for t in TRIPLE))}


def _stored(s: System) -> str:
    """Every topic and its fields' current values, as the system stores them (salience and events left out)."""
    topics = s.read_state()["topics"]
    return json.dumps({tid: [t.get("title"), {n: repr(current_value(f)) for n, f in sorted(t["fields"].items())}]
                       for tid, t in sorted(topics.items())}, sort_keys=True)


def _write(title: str, deadline: str) -> dict:
    return {"placement": "new_topic", "title": title, "topic_kind": "project",
            "fields": [{"name": "Start", "value": START, "provenance": "kickoff-notes"},
                       {"name": "Deadline", "value": deadline, "provenance": "kickoff-notes"}]}


def _exercise(s: System, added: dict) -> Verdict:
    before = _stored(s)
    violating = _write("Policy Check Violating", VIOLATING_DEADLINE)
    try:
        s.ingest(violating)
        rejected, how = False, "accepted"
    except Rejected as e:
        rejected, how = True, f"rejected ({e.status}): {e.detail}"
    after = _stored(s)
    rejects = Case("a policy added at runtime rejects a write that sets Deadline before Start, saving nothing",
                   held=rejected and after == before,
                   observation=f"{how}; stored state "
                               f"{'identical to before the write' if after == before else 'changed by the write'}")
    ordinary = _write("Policy Check Ordinary", ORDINARY_DEADLINE)
    try:
        topic_id = s.ingest(ordinary)["topic_id"]
        fields = (s.read_topic(topic_id) or {"fields": {}})["fields"]
        read_back = {n: current_value(fields.get(n)) for n in ("Start", "Deadline")}
        held, how = read_back == {"Start": START, "Deadline": ORDINARY_DEADLINE}, f"committed; read back {read_back}"
    except Rejected as e:
        held, how = False, f"rejected ({e.status}): {e.detail}"
    control = Case("control: an ordinary write (Deadline after Start) commits", held=held, observation=how,
                   control=True)
    verdict = Verdict.from_cases("C2(c)", [rejects, control], measurements={"policy": POLICY, "added": added})
    if rejects.held is False and not rejected:
        verdict.verdict = FAIL  # the policy was ignored: the violating write was accepted, the control says nothing more
    return verdict


@check(row="C2(c)", claim=CLAIM)
def c2c(ctx: Ctx) -> Verdict:
    s = ctx.system
    added = s.add_policy(POLICY)
    if added is not None:
        return _exercise(s, added)
    openapi_probe = s.probe("GET", "/openapi.json")
    schema = None
    knobs_in_schema: list[str] = []
    if openapi_probe is not None and isinstance(openapi_probe["body"], dict):
        schema = _read_schema(openapi_probe["body"])
        text = str(openapi_probe["body"])
        knobs_in_schema = [k for k in KNOB_NAMES if k in text]
    docs = {p: _status(s.probe("GET", p)) for p in DOCS}
    guessed = {p: _status(s.probe("GET", p)) for p in GUESSED_ROUTES}
    config_like = {}
    for p in REAL_CONFIG_ROUTES:
        probe = s.probe("GET", p)
        config_like[p] = None if probe is None else {"status": probe["status"], "body": probe["body"]}

    answering = sorted(p for p, status in guessed.items() if status not in (None, 404))
    surface = []
    if schema is not None:
        surface += [f"route or schema named for policies in the API schema: {n}" for n in schema["policy_term_hits"]]
        surface += [f"schema with event, condition and action: {n}" for n in schema["triple_schemas"]]
    surface += [f"route answers: {p} ({guessed[p]})" for p in answering]
    if schema is None:
        finding = (f"no readable API schema (openapi probe: {'nothing' if openapi_probe is None else openapi_probe['status']}); "
                   f"guessed policy/config routes answering: {answering or 'none'}")
    else:
        reachable = [p for p, r in config_like.items() if r is not None and r["status"] == 200]
        finding = (f"no policy-named route or schema in {len(schema['paths'])} routes; "
                   f"{len(schema['numeric_properties'])} numeric parameters in the schema; "
                   f"policy knob names in the schema: {knobs_in_schema or 'none'}; "
                   f"config-like routes that answer: {reachable or 'none'}; "
                   f"{len(guessed) - len(answering)} of {len(guessed)} guessed policy/config routes absent")
    evidence = {
        "api_schema": None if schema is None else {"status": openapi_probe["status"], **schema},
        "add_policy": None, "policy_tried": POLICY, "docs_status": docs, "guessed_route_status": guessed, "config_like_routes": config_like,
        "policy_knob_names_in_schema": knobs_in_schema, "describe": s.describe(),
        "searched_words": sorted(POLICY_WORDS), "searched_triple": TRIPLE, "finding": finding,
    }
    if surface:
        raise RuntimeError("C2(c): a policy-like surface was found, which this probe does not score; extend the "
                           f"check to exercise it. Found: {surface}")
    return Verdict.absent("C2(c)", evidence)
