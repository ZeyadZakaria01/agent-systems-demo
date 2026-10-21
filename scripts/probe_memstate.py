"""Probe a running MemState server over HTTP and print the observations as JSON.

Scored transitions go through /v1/ingest and /v1/query; state is read through
GET /api/ui/topics and /api/ui/graph. Run each probe against a server started on a
fresh absolute DB (scripts/run_memstate.sh /abs/path/memstate.kuzu).

Usage: probe_memstate.py {c3,salience,merge,ramp,partial-commit,field-salience} [--base URL] [--out FILE] [options]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

import httpx

BG_WAIT_S = 2.0  # background Reasoner runs after each /v1 response; nothing in the API reports completion


class Client:
    def __init__(self, base: str) -> None:
        self.http = httpx.Client(base_url=base, timeout=120)

    def ingest(self, body: dict) -> tuple[dict, float]:
        t0 = time.perf_counter()
        r = self.http.post("/v1/ingest", json=body)
        dt = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        return r.json(), dt

    def query(self, body: dict) -> tuple[dict, float]:
        t0 = time.perf_counter()
        r = self.http.post("/v1/query", json=body)
        dt = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        return r.json(), dt

    def topic(self, tid: str) -> dict | None:
        r = self.http.get(f"/api/ui/topics/{tid}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def topic_ids(self, include_archived: bool) -> list[str]:
        r = self.http.get("/api/ui/topics", params={"include_archived": include_archived})
        r.raise_for_status()
        return r.json()["topic_ids"]

    def graph(self) -> dict:
        r = self.http.get("/api/ui/graph")
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        r = self.http.get("/health/graph")
        r.raise_for_status()
        return r.json()


def field(value: str, name: str, provenance: str = "probe", why: str | None = None) -> dict:
    return {"name": name, "value": value, "provenance": provenance, "why_changed": why}


def current(topic: dict | None, name: str):
    if not topic or name not in topic["fields"] or not topic["fields"][name]["history"]:
        return None
    return topic["fields"][name]["history"][0]["value"]


def values(topic: dict | None, name: str) -> list:
    if not topic or name not in topic["fields"]:
        return []
    return [e["value"] for e in topic["fields"][name]["history"]]


def probe_c3(c: Client, args) -> dict:
    """B depends on A through an `extension` edge; update A; read B before and after revision."""
    pairs = []
    for direction in ("B->A", "A->B"):
        tag = uuid.uuid4().hex[:6]
        a, _ = c.ingest(
            {
                "placement": "new_topic",
                "title": f"Website Redesign {tag}",
                "fields": [field("March 15", "Deadline", "kickoff-notes")],
            }
        )
        b_edges = [{"to_topic_id": a["topic_id"], "kind": "extension"}] if direction == "B->A" else []
        b, _ = c.ingest(
            {
                "placement": "new_topic",
                "title": f"Launch Milestone {tag}",
                "fields": [field("March 20", "Date", "kickoff-notes")],
                "edges": b_edges,
            }
        )
        if direction == "A->B":
            c.ingest(
                {
                    "placement": "extend_topic",
                    "topic_id": a["topic_id"],
                    "edges": [{"to_topic_id": b["topic_id"], "kind": "extension"}],
                }
            )
        time.sleep(BG_WAIT_S)
        a_id, b_id = a["topic_id"], b["topic_id"]
        b_before = c.topic(b_id)
        upd, _ = c.ingest(
            {
                "placement": "version_field",
                "topic_id": a_id,
                "fields": [field("April 20", "Deadline", "pm-email", "vendor delay")],
            }
        )
        read_now, _ = c.query(
            {"q": "launch milestone date", "stages": ["structural", "temporal"], "topic_ids": [b_id], "explain": True}
        )
        time.sleep(BG_WAIT_S)
        b_after = c.topic(b_id)
        read_after, _ = c.query(
            {"q": "launch milestone date", "stages": ["structural", "temporal"], "topic_ids": [b_id], "explain": True}
        )
        g = c.graph()
        edge_rows = [e for e in g.get("edges", []) if {a_id, b_id} <= {str(v) for v in e.values()}]
        pairs.append(
            {
                "direction": direction,
                "A": a_id,
                "B": b_id,
                "update_applied": upd["applied"],
                "A_deadline_now": current(c.topic(a_id), "Deadline"),
                "B_date_before": current(b_before, "Date"),
                "B_date_read_right_after_update": read_now["candidates"][0]["fields"][0]["current"]["value"]
                if read_now["candidates"]
                else None,
                "B_date_after_wait": current(b_after, "Date"),
                "B_history_after": values(b_after, "Date"),
                "B_topic_history_kinds_after": [h.get("kind") for h in b_after["topic_history"]],
                "B_row_keys": sorted(b_after.keys()),
                "B_neighbors_in_query": read_after["candidates"][0]["neighbors"] if read_after["candidates"] else None,
                "graph_edges_between_A_B": edge_rows,
            }
        )
    return {"probe": "c3", "pairs": pairs}


def probe_salience(c: Client, args) -> dict:
    """Which returned candidates get the query bump."""
    topics = {
        "Sourdough": ("Hydration", "75% with a 12-hour cold proof"),
        "Kubernetes upgrade": ("Target version", "1.31 on the staging cluster first"),
        "Marathon Training": ("Long run", "32 km on Sunday at easy pace"),
        "Tax return": ("Due", "file by April 30"),
        "Garden": ("Tomatoes", "plant after the last frost"),
    }
    ids = {}
    for title, (fname, val) in topics.items():
        r, _ = c.ingest({"placement": "new_topic", "title": title, "fields": [field(val, fname)]})
        ids[r["topic_id"]] = title
    time.sleep(BG_WAIT_S)
    before = {tid: c.topic(tid)["salience"] for tid in ids}
    q, _ = c.query({"q": "how far is my weekend running session", "stages": ["semantic"], "top_k": 8})
    time.sleep(BG_WAIT_S)
    after = {tid: c.topic(tid)["salience"] for tid in ids}
    return {
        "probe": "salience",
        "query": q["query"],
        "returned": [
            {
                "title": ids.get(x["topic_id"]),
                "similarity": x["similarity"],
                "salience_before": before[x["topic_id"]],
                "salience_after": after[x["topic_id"]],
            }
            for x in q["candidates"]
        ],
        "not_returned": [ids[t] for t in ids if t not in {x["topic_id"] for x in q["candidates"]}],
    }


def probe_merge(c: Client, args) -> dict:
    """Two same-title topics; the second (to be merged) holds the newer value."""
    runs = []
    for _ in range(args.repeats):
        title = f"Vendor Contract {uuid.uuid4().hex[:8]}"
        t1, _ = c.ingest(
            {"placement": "new_topic", "title": title, "fields": [field("March 15", "Deadline", "kickoff-notes")]}
        )
        time.sleep(BG_WAIT_S)
        t2, _ = c.ingest(
            {
                "placement": "new_topic",
                "title": title,
                "fields": [field("April 20", "Deadline", "pm-email", "vendor delay")],
            }
        )
        time.sleep(BG_WAIT_S)
        s1, s2 = c.topic(t1["topic_id"]), c.topic(t2["topic_id"])
        survivor = s1 or s2
        runs.append(
            {
                "older_id": t1["topic_id"],
                "newer_id": t2["topic_id"],
                "older_survives": s1 is not None,
                "newer_survives": s2 is not None,
                "survivor_current": current(survivor, "Deadline"),
                "survivor_history": values(survivor, "Deadline"),
            }
        )
    violations = sum(r["survivor_current"] != "April 20" for r in runs)
    history_loss = sum(set(r["survivor_history"]) != {"March 15", "April 20"} for r in runs)
    both_survive = sum(r["older_survives"] and r["newer_survives"] for r in runs)
    return {
        "probe": "merge",
        "repeats": args.repeats,
        "stale_current": violations,
        "history_lost": history_loss,
        "unmerged": both_survive,
        "runs": runs,
    }


WORDS = [
    "amber",
    "basil",
    "cedar",
    "delta",
    "ember",
    "fjord",
    "granite",
    "harbor",
    "indigo",
    "juniper",
    "kestrel",
    "lumen",
    "maple",
    "nectar",
    "onyx",
    "prairie",
    "quartz",
    "raven",
    "sierra",
    "tundra",
    "umber",
    "violet",
    "willow",
    "xenon",
    "yarrow",
    "zephyr",
]


def ramp_title(i: int) -> str:
    return f"{WORDS[i % 26].title()} {WORDS[(i // 26) % 26].title()} project {i}"


def probe_ramp(c: Client, args) -> dict:
    """Grow the store through /v1/ingest; per step, query latency, ingest latency, archived count."""
    steps = [int(s) for s in args.steps.split(",")]
    out, n, ingest_ms = [], 0, []
    queries = [f"status of the {WORDS[k].lower()} project" for k in range(args.queries)]
    for step in steps:
        while n < step:
            _, dt = c.ingest(
                {
                    "placement": "new_topic",
                    "title": ramp_title(n),
                    "fields": [field(f"phase {n % 7}", "Status"), field(f"Q{n % 4 + 1}", "Due")],
                }
            )
            ingest_ms.append(dt)
            n += 1
        time.sleep(BG_WAIT_S)
        q_ms = []
        for q in queries:
            _, dt = c.query({"q": q, "stages": ["semantic"], "top_k": 8})
            q_ms.append(dt)
        time.sleep(BG_WAIT_S)
        active = c.topic_ids(False)
        total = c.topic_ids(True)
        window = ingest_ms[-min(len(ingest_ms), 50) :]
        out.append(
            {
                "topics": n,
                "active": len(active),
                "archived": len(total) - len(active),
                "query_ms_median": round(statistics.median(q_ms), 1),
                "query_ms_p95": round(sorted(q_ms)[int(0.95 * (len(q_ms) - 1))], 1),
                "ingest_ms_median_last50": round(statistics.median(window), 1),
            }
        )
        print(json.dumps(out[-1]), file=sys.stderr, flush=True)
    sal = [c.topic(t)["salience"] for t in c.topic_ids(True)[:200]]
    return {"probe": "ramp", "steps": out, "salience_min_first200": min(sal), "salience_max_first200": max(sal)}


def probe_partial_commit(c: Client, args) -> dict:
    """One new_topic whose second field refs a topic that does not exist: is anything stored after the error?"""
    missing = str(uuid.uuid4())
    title = f"Website Redesign {uuid.uuid4().hex[:6]}"
    r = c.http.post(
        "/v1/ingest",
        json={
            "placement": "new_topic",
            "title": title,
            "topic_kind": "project",
            "fields": [
                field("March 15", "Deadline", "kickoff-notes"),
                {**field("Alice", "Owner", "kickoff-notes"), "ref_topic_id": missing},
            ],
        },
    )
    stored = [t for t in (c.topic(tid) for tid in c.topic_ids(True)) if t and t["title"] == title]
    return {
        "probe": "partial-commit",
        "missing_ref_topic_id": missing,
        "status": r.status_code,
        "body": r.text[:300],
        "topics_stored": len(stored),
        "fields_stored": {n: current(t, n) for t in stored for n in t["fields"]},
    }


def probe_field_salience(c: Client, args) -> dict:
    """A new_topic asks for salience 0.01 and carries one field: what salience is stored?"""
    r, _ = c.ingest(
        {
            "placement": "new_topic",
            "title": f"Old Vendor {uuid.uuid4().hex[:6]}",
            "salience": 0.01,
            "fields": [field("Bob", "Contact", "email")],
        }
    )
    t = c.topic(r["topic_id"])
    return {
        "probe": "field-salience",
        "requested_salience": 0.01,
        "applied": r["applied"],
        "stored_salience": t["salience"],
        "archived": t["archived"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("probe", choices=["c3", "salience", "merge", "ramp", "partial-commit", "field-salience"])
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--out")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--steps", default="100,250,500,1000,2000")
    ap.add_argument("--queries", type=int, default=20)
    args = ap.parse_args()
    c = Client(args.base)
    res = {"health": c.health(), **globals()[f"probe_{args.probe.replace('-', '_')}"](c, args)}
    text = json.dumps(res, indent=2, default=str)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
