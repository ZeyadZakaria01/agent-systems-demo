"""The system adapter: the single seam between checks and the memory systems they score.

Every check is written against `System`; adding a system means writing one subclass (see `baseline.py`
for the smallest) and registering it in `systems.py`.

Operations
- `ingest(request)` and `query(request)` are *scored transitions*, shaped like MemState's `/v1/ingest` and
  `/v1/query`. A system rejecting a request raises `Rejected` (an observation, not an adapter failure).
- `read_state()` and `read_topic(id)` read what the system stores, shaped like MemState's UI endpoints:
  `{"topics": {id: topic}, "edges": [...]}` and one topic dict (`id, title, summary, topic_kind, salience,
  failed_salience, archived, fields{name: {field_type, ref_topic_id, history|current}}, topic_history, ...`).
  A capability the system lacks reads as `None` (salience, archived, edges, history), never as an error.
  Every field carries an explicit `current`: the entry (`{"value": ..., ...}`) or `None` for "no value". A `null`
  write that became current is `{"value": None}`, which is not "no value" (`reads.current_value` tells them apart).
  A missing topic reads as `None`: deleted. Extra keys a system returns (the patch's dates, tags) pass through.
- `setup_write(action, label=..., **params)` arranges a starting state through an editor path. It is logged
  as kind "setup" and never judged. Actions: `create_topic`, `patch_topic`, `add_edge`. A system that cannot
  do an action returns `None`.
- `probe(method, path)` looks at the API surface the system exposes (MemState: any HTTP route, 4xx included, never
  raising): `{"status", "content_type", "body"}`, or `None` when the system has no such surface (the baseline has no
  API). Logged as a read. Used where a check must look for a capability before scoring it absent (C2(c)).
- `wait_until(predicate, timeout)` polls a state predicate; returns `Waited(elapsed, timed_out)`.
  Each wait is logged apart from client latency.
- `describe()` returns system label, server URL, DB path, MemState commit and engine line (`None` where not
  applicable) and `keeps_history` (a declared capability: checks read "no history" from it, never from a
  missing key) and two capability flags, False by default: `accepts_valid_time` (dated writes, `valid_from` / `invalid_at`,
  and `valid_at` reads) and `accepts_recorded_at` (`recorded_at` reads). MemState states them in its own OpenAPI
  schema, so the patch is recognised by what its server accepts, not by a name; `None` plus `accepts_error` (the
  reason) if the schema could not be read.

Everything that crosses the adapter is appended to `system.log` (`ExchangeLog`): scored transitions, setup
writes, reads and waits stay apart by `kind`, which is how snapshots keep setup writes out of scored ones.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from demo.server import ServerInfo


@dataclass(frozen=True)
class Waited:
    """Outcome of `wait_until`: the seconds spent and whether the predicate never held within the timeout."""

    elapsed: float
    timed_out: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Rejected(Exception):
    """The system refused a request (MemState: HTTP 4xx). Carries the status and the system's message."""

    def __init__(self, status: int, detail: Any) -> None:
        super().__init__(f"rejected ({status}): {detail}")
        self.status = status
        self.detail = detail


class ExchangeLog:
    """Ordered record of every adapter call. Kinds: scored, setup, read, wait."""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def record(self, kind: str, op: str, request: Any, run: Callable[[], Any]) -> Any:
        entry: dict = {"seq": len(self.entries), "kind": kind, "op": op, "request": request,
                       "started_at": utc_now(), "response": None, "rejected": None, "error": None}
        self.entries.append(entry)
        t0 = time.perf_counter()
        try:
            response = run()
        except Rejected as e:
            entry["rejected"] = {"status": e.status, "detail": e.detail}
            raise
        except Exception as e:  # 5xx, transport errors, bugs: keep the reason on the entry
            entry["error"] = f"{type(e).__name__}: {e}"
            raise
        finally:
            entry["latency_ms"] = round((time.perf_counter() - t0) * 1000, 3)
            entry["finished_at"] = utc_now()
        entry["response"] = response
        return response

    def of_kind(self, kind: str) -> list[dict]:
        return [e for e in self.entries if e["kind"] == kind]


class System(ABC):
    """A memory system under test. Subclasses implement the `_` methods; the public ones log."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.log = ExchangeLog()

    # -- scored transitions
    def ingest(self, request: dict) -> dict:
        return self.log.record("scored", "ingest", request, lambda: self._ingest(request))

    def query(self, request: dict) -> dict:
        return self.log.record("scored", "query", request, lambda: self._query(request))

    # -- reads of stored state (not transitions)
    def read_state(self) -> dict:
        # The state is the snapshot's payload; the log keeps the timing and the size of the read.
        holder: dict = {}

        def read() -> dict:
            holder["state"] = self._read_state()
            edges = holder["state"]["edges"]
            return {"topics": len(holder["state"]["topics"]), "edges": None if edges is None else len(edges)}

        self.log.record("read", "read_state", None, read)
        return holder["state"]

    def read_topic(self, topic_id: str) -> dict | None:
        return self.log.record("read", "read_topic", {"topic_id": topic_id}, lambda: self._read_topic(topic_id))

    def probe(self, method: str, path: str) -> dict | None:
        return self.log.record("read", "probe", {"method": method, "path": path}, lambda: self._probe(method, path))

    # -- setup writes
    def setup_write(self, action: str, *, label: str, **params: Any) -> dict | None:
        request = {"action": action, "label": label, **params}
        return self.log.record("setup", action, request, lambda: self._setup_write(action, params))

    # -- waiting
    def wait_until(self, predicate: Callable[[], bool], timeout: float, interval: float = 0.1) -> Waited:
        """Poll `predicate` until it holds or `timeout` seconds pass; a timeout is an outcome, not an error."""
        t0 = time.perf_counter()

        def poll() -> dict:
            while True:
                if predicate():
                    timed_out = False
                    break
                if time.perf_counter() - t0 >= timeout:
                    timed_out = True
                    break
                time.sleep(interval)
            return {"elapsed_s": round(time.perf_counter() - t0, 3), "timed_out": timed_out}

        result = self.log.record("wait", "wait_until", {"timeout_s": timeout, "interval_s": interval}, poll)
        return Waited(elapsed=result["elapsed_s"], timed_out=result["timed_out"])

    def describe(self) -> dict:
        return {"system": self.label, "url": None, "db_path": None, "commit": None, "engine": None,
                "keeps_history": None, "accepts_valid_time": False, "accepts_recorded_at": False,
                "accepts_error": None, **self._describe()}

    @abstractmethod
    def _ingest(self, request: dict) -> dict: ...

    @abstractmethod
    def _query(self, request: dict) -> dict: ...

    @abstractmethod
    def _read_state(self) -> dict: ...

    @abstractmethod
    def _read_topic(self, topic_id: str) -> dict | None: ...

    @abstractmethod
    def _setup_write(self, action: str, params: dict) -> dict | None: ...

    @abstractmethod
    def _describe(self) -> dict: ...

    def _probe(self, method: str, path: str) -> dict | None:
        return None  # no API surface


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

    def list_topic_ids(self, include_archived: bool = True) -> list[str]:
        """Cheap topic listing (C5 / latency ramps); not a scored transition."""
        return self.log.record(
            "read", "list_topic_ids", {"include_archived": include_archived},
            lambda: self._call("GET", "/api/ui/topics",
                               params={"include_archived": include_archived}).json()["topic_ids"])

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

