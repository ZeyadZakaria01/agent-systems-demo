"""The baseline: a last-write-wins row keyed by (title, field).

It accepts the `/v1/ingest` shape and writes whatever arrives (`""` and `null` included); a second `new_topic`
with an existing title upserts. It keeps no history, salience, archived flag, edges or dates, so those read as
`None` (nothing-values). Its semantic query embeds with MiniLM (the same model MemState uses) and returns the top
10 (survey setting); a read changes nothing. The topic id is the title.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from demo.client import Rejected, System

TOP_K = 10
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Baseline(System):
    def __init__(self, label: str = "baseline") -> None:
        super().__init__(label)
        self._rows: dict[str, dict] = {}  # title -> {"title", "summary", "topic_kind", "fields": {name: value}}
        self._embedder = None
        self._vectors: dict[str, np.ndarray] = {}  # embedding text -> unit vector

    # -- writes
    def _ingest(self, request: dict) -> dict:
        placement = request["placement"]
        if placement == "new_topic":
            title = request.get("title") or "untitled"
            row = self._rows.setdefault(title, {"title": title, "summary": None, "topic_kind": None, "fields": {}})
            if request.get("summary") is not None:
                row["summary"] = request["summary"]
            if request.get("topic_kind") is not None:
                row["topic_kind"] = request["topic_kind"]
            applied = [f"created_topic:{title}"]
        elif placement in ("extend_topic", "version_field"):
            title = request.get("topic_id")
            row = self._rows.get(title)
            if row is None:
                raise Rejected(400, "topic not found")
            fields = request.get("fields") or []
            if placement == "version_field" and len(fields) != 1:
                raise Rejected(400, "version_field requires topic_id and exactly one field")
            applied = []
        else:
            raise Rejected(422, f"unknown placement {placement!r}")
        versions = {}
        for f in request.get("fields") or []:
            row["fields"][f["name"]] = f.get("value", "")
            versions[f["name"]] = None
            applied.append(f"version:{f['name']}" if placement == "version_field" else f"field:{f['name']}")
        return {"topic_id": title, "applied": applied, "version_ids": versions, "similar_topic_ids": []}

    # -- reads
    @staticmethod
    def _field(value: Any) -> dict:
        return {"field_type": None, "ref_topic_id": None, "current": {"value": value}, "history": None}

    def _topic(self, row: dict) -> dict:
        return {
            "id": row["title"], "title": row["title"], "summary": row["summary"], "topic_kind": row["topic_kind"],
            "salience": None, "failed_salience": None, "archived": None, "topic_history": None,
            "created_at": None, "updated_at": None,
            "fields": {name: self._field(value) for name, value in row["fields"].items()},
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
        candidates = []
        for tid, sim in sims.items():
            row = self._rows[tid]
            fields = []
            if "structural" in stages or "temporal" in stages:
                for name in sorted(row["fields"]):
                    if names is None or name in names:
                        fields.append({"name": name, **self._field(row["fields"][name])})
            candidates.append({"topic_id": tid, "title": row["title"], "summary": row["summary"],
                               "topic_kind": row["topic_kind"], "salience": None, "failed_salience": None,
                               "neighbors": None, "fields": fields, "similarity": sim})
        return {"query": request["q"], "candidates": candidates, "summary_text": ""}

    # -- setup, description
    def _setup_write(self, action: str, params: dict) -> dict | None:
        return None  # no ids, salience, archived flag or edges to arrange

    def _describe(self) -> dict:
        return {"engine": "in-process dict", "keeps_history": False, "embedder": MODEL, "top_k": TOP_K}
