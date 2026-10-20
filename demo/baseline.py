"""The baseline: a versioned row, in-process; MAFBench's concrete solution (versioned fact stores with MVCC, a
write-ahead log and conflict resolution, `2602.03128v2.md:568`) reduced to what the checks can observe.

- An append-only history per (title, field): every write appends an entry `{"value", "provenance", "why_changed",
  "recorded_at"}` and nothing is overwritten or dropped. The current value is the latest entry recorded.
- One transaction per write: the whole `/v1/ingest` request is validated first and then applied, or `Rejected` and
  nothing is saved (no topic created, no field appended). Like a NOT NULL / CHECK constraint it rejects empty (`""`)
  and `null` values and a field whose `ref_topic_id` names no stored topic.
- A second `new_topic` with an existing title appends to that topic's histories, so no merge ever occurs. The topic id
  is the title.
- It has no salience, archived flag, edges or valid-time dates: they read as `None` (nothing-values), and a probe of
  each confirms the rows can read `absent` (ADR 0002). It accepts `recorded_at` reads and answers them from its
  history; `valid_at` is ignored. A read changes nothing.
- Its semantic query embeds with MiniLM (the model MemState uses) and returns the top 8.

The baseline is strict about placement, on purpose: `extend_topic` / `version_field` on an unknown topic and a
`version_field` with other than one field are `Rejected`, as MemState's own validation does ([INFERENCE], from
reading the API code), so a check never scores the baseline on a write MemState would refuse.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from demo.adapter import Rejected, System, utc_now

TOP_K = 8
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _instant(text: str) -> datetime:
    t = datetime.fromisoformat(text)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


class Baseline(System):
    def __init__(self, label: str = "baseline") -> None:
        super().__init__(label)
        # title -> {"title", "summary", "topic_kind", "history": {field: [entry, ...] oldest first}}
        self._rows: dict[str, dict] = {}
        self._embedder = None
        self._vectors: dict[str, np.ndarray] = {}  # embedding text -> unit vector

    # -- writes: validate the whole request, then apply it (one transaction)
    def _ingest(self, request: dict) -> dict:
        placement = request["placement"]
        fields = request.get("fields") or []
        if placement == "new_topic":
            title = request.get("title") or "untitled"
            row = self._rows.get(title)
        elif placement in ("extend_topic", "version_field"):
            title = request.get("topic_id")
            row = self._rows.get(title)
            if row is None:
                raise Rejected(400, "topic not found")
            if placement == "version_field" and len(fields) != 1:
                raise Rejected(400, "version_field requires topic_id and exactly one field")
        else:
            raise Rejected(422, f"unknown placement {placement!r}")
        for f in fields:  # NOT NULL / CHECK: one bad value rejects the whole write
            if f.get("value") is None or f["value"] == "":
                raise Rejected(422, f"field {f.get('name')!r}: empty and null values are not allowed")
            ref = f.get("ref_topic_id")  # a foreign key: it must name a stored topic
            if ref is not None and ref not in self._rows:
                raise Rejected(400, f"ref_topic_id not found: {ref}")
        if row is None:
            row = self._rows[title] = {"title": title, "summary": None, "topic_kind": None, "history": {}}
            applied = [f"created_topic:{title}"]
        else:
            applied = []
        if placement == "new_topic":
            for key in ("summary", "topic_kind"):
                if request.get(key) is not None:
                    row[key] = request[key]
        versions = {}
        for f in fields:
            row["history"].setdefault(f["name"], []).append(
                {"value": f["value"], "provenance": f.get("provenance"), "why_changed": f.get("why_changed"),
                 "recorded_at": utc_now()})
            versions[f["name"]] = None
            applied.append(f"version:{f['name']}" if placement == "version_field" else f"field:{f['name']}")
        return {"topic_id": title, "applied": applied, "version_ids": versions, "similar_topic_ids": []}

    # -- reads
    @staticmethod
    def _field(entries: list[dict], recorded_at: str | None = None, with_history: bool = False) -> dict:
        """`current` is the latest entry recorded (by `recorded_at`, if asked: the latest recorded at or before it)."""
        visible = entries
        if recorded_at is not None:
            moment = _instant(recorded_at)
            visible = [e for e in entries if _instant(e["recorded_at"]) <= moment]
        return {"field_type": None, "ref_topic_id": None,
                "current": dict(visible[-1]) if visible else None,
                "history": [dict(e) for e in reversed(visible)] if with_history else None}

    def _topic(self, row: dict) -> dict:
        return {
            "id": row["title"], "title": row["title"], "summary": row["summary"], "topic_kind": row["topic_kind"],
            "salience": None, "failed_salience": None, "archived": None, "topic_history": None,
            "created_at": None, "updated_at": None,
            "fields": {name: self._field(entries, with_history=True) for name, entries in row["history"].items()},
        }

    def _read_topic(self, topic_id: str) -> dict | None:
        row = self._rows.get(topic_id)
        return self._topic(row) if row else None

    def _read_state(self) -> dict:
        return {"topics": {tid: self._topic(row) for tid, row in self._rows.items()}, "edges": None}

    def _vector(self, text: str) -> np.ndarray:
        if text not in self._vectors:
            if self._embedder is None:
                from fastembed import TextEmbedding

                self._embedder = TextEmbedding(model_name=MODEL)
            v = np.asarray(next(iter(self._embedder.embed([text if text.strip() else " "]))), dtype=np.float64)
            self._vectors[text] = v / (np.linalg.norm(v) or 1.0)
        return self._vectors[text]

    def _query(self, request: dict) -> dict:
        stages = request.get("stages") or ["semantic", "structural", "temporal"]
        topic_ids = request.get("topic_ids")
        sims: dict[str, float | None] = {}
        if "semantic" in stages:
            q = self._vector(request["q"])
            scored = sorted(((float(q @ self._vector(f"{r['title']}\n{r['summary'] or ''}")), t)
                             for t, r in self._rows.items()), reverse=True)[:TOP_K]
            sims = {t: s for s, t in scored if topic_ids is None or t in topic_ids}
        else:
            ids = topic_ids if topic_ids is not None else list(self._rows)[:TOP_K]
            sims = {t: None for t in ids if t in self._rows}
        names = request.get("field_names")
        recorded_at = request.get("recorded_at")
        candidates = []
        for tid, sim in sims.items():
            row = self._rows[tid]
            fields = []
            if "structural" in stages or "temporal" in stages:
                for name in sorted(row["history"]):
                    if names is None or name in names:
                        fields.append({"name": name, **self._field(row["history"][name], recorded_at,
                                                                   with_history=bool(request.get("explain")))})
            candidates.append({"topic_id": tid, "title": row["title"], "summary": row["summary"],
                               "topic_kind": row["topic_kind"], "salience": None, "failed_salience": None,
                               "neighbors": None, "fields": fields, "similarity": sim})
        return {"query": request["q"], "candidates": candidates, "summary_text": ""}

    # -- setup, description
    def _setup_write(self, action: str, params: dict) -> dict | None:
        return None  # no ids, salience, archived flag or edges to arrange

    def _describe(self) -> dict:
        return {"engine": "in-process versioned row", "keeps_history": True, "embedder": MODEL, "top_k": TOP_K,
                "accepts": {"valid_from": False, "invalid_at": False, "valid_at": False, "recorded_at": True}}
