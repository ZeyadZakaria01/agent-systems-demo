"""C2(c), declarative policies: does the system expose a surface for declarative policies `<event, condition, action>`?

The check looks before it scores (ADR 0002, spec story 17). Through the adapter's `probe` it reads the API schema
(`/openapi.json`: routes, request/response schemas, numeric parameters), the interactive docs, the routes where a policy
or config surface would sit if it existed, and the config-like routes the server really has (`/api/ui/system-context`,
`/api/ui/datamodel`). It also searches the schema for the names of MemState's numeric governance knobs
(`Policies` in `core/models.py`, [INFERENCE] from code: constructed with defaults, never read from a request).

Verdict: no route, schema or property names policies (or rules, constraints, invariants, triggers), no candidate route
answers, and no schema carries event + condition + action together -> **absent**, with the probe attached. A surface
found is not scored here: the check raises, so the run shows an error until a person extends the probe to exercise it.
A system with no API at all (the baseline) answers every probe with nothing, which is the evidence.
"""

import re

from demo.checks import Ctx, check
from demo.verdict import Verdict

CLAIM = ("C2 (transition soundness), by construction (§4.3): every transition respects P_t, the declarative "
         "policies ⟨event, condition, action⟩.")

POLICY_TERMS = re.compile(r"polic|rule|constraint|invariant|trigger", re.IGNORECASE)
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


def _status(probe: dict | None) -> int | None:
    return None if probe is None else probe["status"]


def _types(prop: dict) -> set[str]:
    kinds = {prop["type"]} if "type" in prop else set()
    for alt in prop.get("anyOf", []) + prop.get("oneOf", []):
        kinds |= _types(alt)
    return kinds


def _read_schema(openapi: dict) -> dict:
    schemas = openapi.get("components", {}).get("schemas", {})
    props = {name: sorted(spec.get("properties", {})) for name, spec in schemas.items()}
    numeric = sorted(f"{name}.{p}: {'/'.join(sorted(_types(spec) & {'integer', 'number'}))}"
                     for name, s in schemas.items() for p, spec in s.get("properties", {}).items()
                     if _types(spec) & {"integer", "number"})
    paths = {path: sorted(ops) for path, ops in openapi.get("paths", {}).items()}
    names = [*paths, *schemas, *(p for ps in props.values() for p in ps)]
    return {"paths": paths, "schema_properties": props, "numeric_properties": numeric,
            "policy_term_hits": sorted({n for n in names if POLICY_TERMS.search(n)}),
            "triple_schemas": sorted(n for n, ps in props.items() if all(t in ps for t in TRIPLE))}


@check(row="C2(c)", claim=CLAIM)
def c2c(ctx: Ctx) -> Verdict:
    s = ctx.system
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
        surface += [f"named in the API schema: {n}" for n in schema["policy_term_hits"]]
        surface += [f"schema with event, condition and action: {n}" for n in schema["triple_schemas"]]
    surface += [f"route answers: {p} ({guessed[p]})" for p in answering]
    if schema is None:
        finding = (f"no readable API schema (openapi probe: {'nothing' if openapi_probe is None else openapi_probe['status']}); "
                   f"guessed policy/config routes answering: {answering or 'none'}")
    else:
        reachable = [p for p, r in config_like.items() if r is not None and r["status"] == 200]
        finding = (f"no policy-like route, schema or property in {len(schema['paths'])} routes; "
                   f"{len(schema['numeric_properties'])} numeric parameters in the schema; "
                   f"policy knob names in the schema: {knobs_in_schema or 'none'}; "
                   f"config-like routes that answer: {reachable or 'none'}; "
                   f"{len(guessed) - len(answering)} of {len(guessed)} guessed policy/config routes absent")
    evidence = {
        "api_schema": None if schema is None else {"status": openapi_probe["status"], **schema},
        "docs_status": docs, "guessed_route_status": guessed, "config_like_routes": config_like,
        "policy_knob_names_in_schema": knobs_in_schema, "describe": s.describe(),
        "searched_terms": POLICY_TERMS.pattern, "searched_triple": TRIPLE, "finding": finding,
    }
    if surface:
        raise RuntimeError("C2(c): a policy-like surface was found, which this probe does not score; extend the "
                           f"check to exercise it. Found: {surface}")
    return Verdict.absent("C2(c)", evidence)
