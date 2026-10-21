"""MemState over HTTP, as a `System` (see `adapter.py` for the operations and their shapes)."""

from __future__ import annotations

from typing import Any

import httpx

from demo.adapter import DATES, Rejected, System
from demo.server import ServerInfo

# [INFERENCE: code reading] `Policies.topic_count_soft_limit`: the forgetting pass runs once the topic count reaches it.
DECLARED_BOUND = {"topics": 500, "name": "topic_count_soft_limit"}
CHAT_TIMEOUT_S = 600.0


def with_current(field: dict, dates_accepted: bool) -> dict:
    """The field with an explicit `current`: the entry, or `None` for "no value". A server that states `current` itself
    (the patch must, since its history is ordered by valid time) is taken at its word. Upstream's stored topic lists
    history newest first and its current entry is `history[0]` (`datamodel/fields.py:77`); that fallback is right only
    where no date is accepted, so a system that accepts any date and omits `current` raises instead of giving a silent
    wrong answer."""
    if "current" not in field:
        if dates_accepted:
            raise RuntimeError("the system accepts dates but returned a field without `current`; refusing the "
                               "newest-entry fallback, which would read the wrong entry")
        field["current"] = field["history"][0] if field.get("history") else None
    return field


def request_properties(document: dict) -> set[str]:
    """Every property name of a model reachable from a request body of the OpenAPI document, through `$ref`, `anyOf`,
    `items` and nested properties. Models are found by use, not by name, so a name variant (`FieldWrite-Input`) does
    not matter; a response model that merely returns a property (upstream's history entry returns `valid_from`) is not
    a request model and does not count."""
    schemas = document["components"]["schemas"]
    pending = [body.get("content", {}).get("application/json", {}).get("schema", {})
               for path in document.get("paths", {}).values() for op in path.values() if isinstance(op, dict)
               for body in [op.get("requestBody", {})]]
    seen: set[str] = set()
    found: set[str] = set()
    while pending:
        node = pending.pop()
        if not isinstance(node, dict):
            continue
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            if name not in seen and name in schemas:
                seen.add(name)
                pending.append(schemas[name])
            continue
        props = node.get("properties", {})
        found |= set(props)
        pending += list(props.values())
        pending += [node.get("items"), node.get("additionalProperties")]
        pending += node.get("anyOf", []) + node.get("allOf", []) + node.get("oneOf", [])
    return found


def request_date_fields(document: dict) -> set[str]:
    """The dates a server accepts, read from its OpenAPI document: those among `DATES` that are request properties
    (a write model for `valid_from` / `invalid_at`, a query model for `valid_at` / `recorded_at`)."""
    return set(DATES) & request_properties(document)


SOURCE_FIELD = "source_message"  # the field-write property a source message travels in (C4' probe)


def source_surface(document: dict) -> dict:
    """The C4' probe's look at the API: every request property and every path whose name says "source", sorted."""
    return {"request_properties": sorted(p for p in request_properties(document) if "source" in p.lower()),
            "paths": sorted(p for p in document.get("paths", {}) if "source" in p.lower())}


class MemStateSystem(System):
    """MemState over HTTP: `/v1/ingest`, `/v1/query` and the UI read/editor endpoints.

    Upstream and the patched copy differ only in which server runs; every key the server returns is kept.
    `server` is what the launcher knows (`ServerInfo`); it is `None` for a server the suite did not start.
    """

    def __init__(self, label: str, base_url: str, server: ServerInfo | None = None, timeout: float = 120) -> None:
        super().__init__(label)
        self.base_url = base_url
        self.server = server or ServerInfo()
        self.http = httpx.Client(base_url=base_url, timeout=timeout)
        self._dates: dict | None = None  # the schema's verdict, read once and only if it was readable

    def close(self) -> None:
        self.http.close()

    def _call(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        r = self.http.request(method, path, **kwargs)
        if 400 <= r.status_code < 500:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise Rejected(r.status_code, detail)
        if r.status_code >= 500:  # MemState puts the upstream (LLM) error in `detail`; keep it in the message
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise httpx.HTTPStatusError(f"{r.status_code} from {method} {path}: {str(detail)[:500]}",
                                        request=r.request, response=r)
        r.raise_for_status()
        return r

    def _get_or_none(self, path: str, **kwargs: Any) -> dict | None:
        try:
            return self._call("GET", path, **kwargs).json()
        except Rejected as e:
            if e.status == 404:
                return None
            raise

    def _ingest(self, request: dict) -> dict:
        return self._call("POST", "/v1/ingest", json=request).json()

    def _query(self, request: dict) -> dict:
        return self._call("POST", "/v1/query", json=request).json()

    def _chat(self, request: dict) -> dict:
        # a local 2B model with tool rounds can take minutes on the laptop: the client waits longer than for /v1
        return self._call("POST", "/api/llm/chat", json=request, timeout=CHAT_TIMEOUT_S).json()

    def _read_topic(self, topic_id: str) -> dict | None:
        topic = self._get_or_none(f"/api/ui/topics/{topic_id}")
        if topic is None:
            return None
        dates_accepted = None
        for f in topic["fields"].values():
            if "current" not in f and dates_accepted is None:
                caps = self._date_capabilities()
                if any(v is None for v in caps["accepts"].values()):  # no schema: the fallback would be a guess
                    raise RuntimeError(f"the system returned a field without `current` and which dates it accepts is "
                                       f"unknown ({caps['accepts_error']}); refusing the newest-entry fallback, "
                                       "which would read the wrong entry if it accepts dates")
                dates_accepted = any(caps["accepts"].values())
            with_current(f, bool(dates_accepted))
        return topic

    def _list_topic_ids(self, include_archived: bool) -> list[str]:
        return self._call("GET", "/api/ui/topics", params={"include_archived": include_archived}).json()["topic_ids"]

    def _read_state(self) -> dict:
        ids = self._call("GET", "/api/ui/topics", params={"include_archived": True}).json()["topic_ids"]
        topics = {}
        for tid in ids:
            topic = self._read_topic(tid)
            if topic is not None:
                topics[tid] = topic
        return {"topics": topics, "edges": self._call("GET", "/api/ui/graph").json()["edges"]}

    def _setup_write(self, action: str, params: dict) -> dict | None:
        params = dict(params)
        if action == "create_topic":
            return self._call("POST", "/api/ui/topics", json=params).json()
        if action == "patch_topic":
            topic_id = params.pop("topic_id")
            return self._call("PATCH", f"/api/ui/topics/{topic_id}", json=params).json()
        if action == "add_edge":
            from_id = params.pop("from_id")
            return self._call("POST", f"/api/ui/topics/{from_id}/relationships", json=params).json()
        raise ValueError(f"unknown setup action {action!r}")

    def _date_capabilities(self) -> dict:
        """What the server's own OpenAPI schema declares, one flag per date (`request_date_fields`). Unreadable
        schema: every flag `None` and the reason is returned."""
        if self._dates is not None:
            return self._dates
        try:
            document = self._call("GET", "/openapi.json").json()
            properties = request_properties(document)
            surface = source_surface(document)
        except Exception as e:
            return {"accepts": {d: None for d in DATES}, "accepts_source": None, "source_surface": None,
                    "accepts_error": f"could not read /openapi.json: {type(e).__name__}: {e}"}
        self._dates = {"accepts": {d: d in properties for d in DATES}, "accepts_source": SOURCE_FIELD in properties,
                       "source_surface": surface, "accepts_error": None}
        return self._dates

    def _probe(self, method: str, path: str) -> dict | None:
        r = self.http.request(method, path)  # no redirects followed, no raise on 4xx/5xx: the status is the finding
        content_type = r.headers.get("content-type", "")
        try:
            body = r.json() if "json" in content_type else r.text[:2000]
        except ValueError:
            body = r.text[:2000]
        return {"status": r.status_code, "content_type": content_type, "body": body}

    def _describe(self) -> dict:
        try:
            db_path, health_error = self._call("GET", "/health/graph").json().get("path"), None
        except Exception as e:  # a dead server must not take the evidence down with it
            db_path, health_error = self.server.db_path, f"{type(e).__name__}: {e}"
        return {"url": self.base_url, "db_path": db_path, "commit": self.server.commit,
                "engine": self.server.engine_line, "source_dir": self.server.source_dir,
                "keeps_history": True, "declared_bound": DECLARED_BOUND, **self._date_capabilities(), "health_error": health_error}
