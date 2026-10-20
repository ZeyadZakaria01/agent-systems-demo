"""MemState over HTTP, as a `System` (see `adapter.py` for the operations and their shapes)."""

from __future__ import annotations

from typing import Any

import httpx

from demo.adapter import Rejected, System
from demo.server import ServerInfo


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

    def _read_topic(self, topic_id: str) -> dict | None:
        topic = self._get_or_none(f"/api/ui/topics/{topic_id}")
        if topic is None:
            return None
        for f in topic["fields"].values():
            # Explicit `current` per field: entry, or None for "no value". Upstream's stored topic lists history
            # newest first and its current entry is history[0] (`datamodel/fields.py:77`). A server that states
            # `current` itself (the patch must, since its history is ordered by valid time) is taken at its word.
            if "current" not in f:
                f["current"] = f["history"][0] if f.get("history") else None
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
        """What the server's own OpenAPI schema declares: dated writes (one schema with `valid_from` and
        `invalid_at`) with `valid_at` reads, and `recorded_at` reads. All schemas are searched, so a model-name variant
        (`FieldWrite-Input`) does not matter. Unreadable schema: both flags `None` and the reason is returned."""
        try:
            schemas = self._call("GET", "/openapi.json").json()["components"]["schemas"]
        except Exception as e:
            return {"accepts_valid_time": None, "accepts_recorded_at": None,
                    "accepts_error": f"could not read /openapi.json: {type(e).__name__}: {e}"}
        props = [set(sch.get("properties", {})) for sch in schemas.values()]
        return {"accepts_valid_time": any({"valid_from", "invalid_at"} <= p for p in props)
                and any("valid_at" in p for p in props),
                "accepts_recorded_at": any("recorded_at" in p for p in props), "accepts_error": None}

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
                "keeps_history": True, **self._date_capabilities(), "health_error": health_error}
