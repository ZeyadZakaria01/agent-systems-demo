"""The system adapter: the single seam between checks and the memory systems they score.

Every check is written against `System`; adding a system means writing one subclass (see `baseline.py`
for the smallest) and registering it in `systems.py`. MemState over HTTP is `memstate_system.py`.

Operations
- `ingest(request)` and `query(request)` are *scored transitions*, shaped like MemState's `/v1/ingest` and
  `/v1/query`. A system rejecting a request raises `Rejected` (an observation, not an adapter failure).
- `read_state()` and `read_topic(id)` read what the system stores, shaped like MemState's UI endpoints:
  `{"topics": {id: topic}, "edges": [...]}` and one topic dict (`id, title, summary, topic_kind, salience,
  failed_salience, archived, fields{name: {field_type, ref_topic_id, history|current}}, topic_history, ...`).
  A capability the system lacks reads as `None` (salience, archived, edges, history), never as an error.
  Every field carries an explicit `current`: the entry (`{"value": ..., ...}`) or `None` for "no value". A `null`
  write that became current is `{"value": None}`, which is not "no value" (`reads.current_value` tells them apart).
  A missing topic reads as `None`: deleted. Every topic carries `revision_flag` (the adapter fills it in): `None` where
  the system has no revision-flag surface (MemState, the versioned row), otherwise `{"flagged": False}` or
  `{"flagged": True, "evidence": {"source_topic_id": the topic whose update raised it, "updated_field": the field
  updated, "timestamp": when the update was recorded}}`. A system without the surface can never be scored as
  flagging; one with it is scored on what the evidence names (C3, `checks/c3_propagation.py`). Extra keys a system returns (the patch's dates, tags) pass through.
- `setup_write(action, label=..., **params)` arranges a starting state through an editor path. It is logged
  as kind "setup" and never judged. Actions: `create_topic`, `patch_topic`, `add_edge`. A system that cannot
  do an action returns `None`.
- `probe(method, path)` looks at the API surface the system exposes (MemState: any HTTP route, 4xx included, never
  raising): `{"status", "content_type", "body"}`, or `None` when the system has no such surface (the baseline has no
  API). Logged as a read. Used where a check must look for a capability before scoring it absent (C2(c)).
- `add_policy(rule)` adds a declarative policy at runtime, logged as kind "setup" (never judged). A rule is a
  dict `{"name", "event": "write", "condition": {"field", "op", "other_field"}, "action": "reject" | "flag"}`: the
  action fires when the condition holds on the topic being written, e.g. `{"field": "Deadline", "op": "<",
  "other_field": "Start"}` says "Deadline before Start" (`op` in `<`, `<=`, `>`, `>=`, `==`, `!=`; values compare as
  ISO date strings or numbers). It returns the stored policy (a dict) once added, or `None` where the system has no
  surface for adding one (MemState, the versioned row): an explicit nothing-value, not an error. A write the
  policy rejects raises `Rejected` with nothing saved.
- `wait_until(predicate, timeout)` polls a state predicate; returns `Waited(elapsed, timed_out)`.
  Each wait is logged apart from client latency.
- `chat(request)` sends one chat request (MemState: `POST /api/llm/chat`, the body as the server defines it) and
  returns the response (`reply`, `tool_log`, `model`, `provider`, `intent`, `intent_source`). Logged as kind "chat".
  A system without an LLM chat raises `NotImplementedError` (the reference GEM has none).
- `describe()` returns system label, server URL, DB path, MemState commit and engine line (`None` where not
  applicable) and `keeps_history` (a declared capability: checks read "no history" from it, never from a
  missing key). It also returns `accepts`: one flag per date, `valid_from`, `invalid_at` (dated writes) and
  `valid_at`, `recorded_at` (reads), all False by default (`DATES`). MemState states them in its own OpenAPI schema, so
  the patch is recognised by what its server accepts, not by a name; in-process systems declare theirs. A flag is `None`
  (with `accepts_error`, the reason) if the schema could not be read. `declared_bound` is the system's own bound on
  active topics for C5, `{"topics": int, "name": str}` (MemState: `topic_count_soft_limit`, 500; the reference GEM:
  its β), or `None` for a system that declares none. `accepts_source` says whether a field write may
  carry a `source_message` (C4' probe); False by default, `None` with `accepts_error` if the schema could not be read,
  and `source_surface` lists the source-named request properties and paths the schema declares (evidence, MemState only).
- `resolve_source(entry)` returns the stored source message an entry's provenance points to (`entry` is a stored
  field's `current`, as read back), or `None` where the system stores none. Logged as a read. `ingest` carries the
  message as `source_message` on a field write, only where the system accepts one.

Everything that crosses the adapter is appended to `system.log` (`ExchangeLog`): scored transitions, setup
writes, reads and waits stay apart by `kind`, which is how snapshots keep setup writes out of scored ones.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable



DATES = ("valid_from", "invalid_at", "valid_at", "recorded_at")  # the dates `describe()["accepts"]` reports


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

    # -- chat (an LLM in front of the memory; logged as kind "chat", never scored by a check)
    def chat(self, request: dict) -> dict:
        return self.log.record("chat", "chat", request, lambda: self._chat(request))

    # -- reads of stored state (not transitions)
    def read_state(self) -> dict:
        # The state is the snapshot's payload; the log keeps the timing and the size of the read.
        holder: dict = {}

        def read() -> dict:
            holder["state"] = self._read_state()
            for topic in holder["state"]["topics"].values():
                topic.setdefault("revision_flag", None)
            edges = holder["state"]["edges"]
            return {"topics": len(holder["state"]["topics"]), "edges": None if edges is None else len(edges)}

        self.log.record("read", "read_state", None, read)
        return holder["state"]

    def read_topic(self, topic_id: str) -> dict | None:
        def read() -> dict | None:
            topic = self._read_topic(topic_id)
            if topic is not None:
                topic.setdefault("revision_flag", None)  # no surface: the nothing-value
            return topic

        return self.log.record("read", "read_topic", {"topic_id": topic_id}, read)

    def list_topic_ids(self, include_archived: bool = True) -> list[str] | None:
        """Cheap topic listing; `None` when the system has no listing separate from `read_state` (the baseline)."""
        return self.log.record("read", "list_topic_ids", {"include_archived": include_archived},
                               lambda: self._list_topic_ids(include_archived))

    def probe(self, method: str, path: str) -> dict | None:
        return self.log.record("read", "probe", {"method": method, "path": path}, lambda: self._probe(method, path))

    def resolve_source(self, entry: dict) -> Any:
        return self.log.record("read", "resolve_source", {"entry": entry}, lambda: self._resolve_source(entry))

    # -- setup writes
    def setup_write(self, action: str, *, label: str, **params: Any) -> dict | None:
        request = {"action": action, "label": label, **params}
        return self.log.record("setup", action, request, lambda: self._setup_write(action, params))

    def add_policy(self, rule: dict) -> dict | None:
        """Add a declarative policy at runtime; `None` where the system has no surface for it."""
        return self.log.record("setup", "add_policy", {"label": "add_policy", "rule": rule},
                               lambda: self._add_policy(rule))

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
        described = self._describe()
        accepts = {**{d: False for d in DATES}, **described.pop("accepts", {})}
        return {"system": self.label, "url": None, "db_path": None, "commit": None, "engine": None,
                "keeps_history": None, "accepts_error": None, "declared_bound": None, "accepts_source": False,
                "source_surface": None, **described, "accepts": accepts}

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

    def _list_topic_ids(self, include_archived: bool) -> list[str] | None:
        return None

    def _chat(self, request: dict) -> dict:
        raise NotImplementedError(f"{self.label} has no chat")

    def _probe(self, method: str, path: str) -> dict | None:
        return None  # no API surface

    def _add_policy(self, rule: dict) -> dict | None:
        return None  # no way to add a policy at runtime

    def _resolve_source(self, entry: dict) -> Any:
        return None  # no source store
