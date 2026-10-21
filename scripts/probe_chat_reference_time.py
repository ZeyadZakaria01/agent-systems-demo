"""Probe the chat `reference_time` on a running patched (step 2c) server and print the observations as JSON.

Run it against a server started on a fresh absolute DB (`scripts/run_memstate.sh --patched /abs/path/memstate.lbug`),
and with Ollama up (`scripts/run_ollama.sh --bg`) unless `--no-llm`. Without an LLM it checks only the parts the
request alone decides: the schema declares `reference_time`, and a value that is not a date is a 400.

With an LLM it sends one ingest chat with `reference_time` 2026-10-06 ("I started my new job two weeks ago") on a topic
that already holds a dated `job` field, then reports what the model stored: each entry's `valid_from` and
`provenance`. A 2B model may not call the tool or may not work out the date; the probe records what happened and
asserts nothing about it (the graded two-weeks run is ticket 18).

Usage: probe_chat_reference_time.py [--base URL] [--out FILE] [--no-llm] [--reference-time ISO]
"""

from __future__ import annotations

import argparse
import json
import time

import httpx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--out")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--reference-time", default="2026-10-06")
    a = ap.parse_args()
    http = httpx.Client(base_url=a.base, timeout=900)
    out: dict = {}

    schema = http.get("/openapi.json").json()["components"]["schemas"]["ChatBody"]["properties"]
    out["schema_declares_reference_time"] = "reference_time" in schema

    bad = http.post("/api/llm/chat", json={"messages": [{"role": "user", "content": "hi"}],
                                           "reference_time": "last tuesday", "intent_override": "query"})
    out["bad_reference_time"] = {"status": bad.status_code, "detail": bad.json().get("detail")}

    if not a.no_llm:
        tid = http.post("/v1/ingest", json={
            "placement": "new_topic", "title": "Alex",
            "fields": [{"name": "job", "value": "analyst at Acme", "valid_from": "2025-01-01"}],
        }).json()["topic_id"]
        t0 = time.perf_counter()
        r = http.post("/api/llm/chat", json={
            "messages": [{"role": "user", "content": "I started my new job two weeks ago: I am a manager at Initech. "
                          f"Call memory_append_field now on the job field of the topic Alex (topic_id {tid}); "
                          "pass valid_from only if you know the start date."}],
            "provider": "ollama", "intent_override": "ingest", "study_ingest": False,
            "reference_time": a.reference_time,
        })
        out["chat"] = {"status": r.status_code, "seconds": round(time.perf_counter() - t0, 1),
                       "reply": (r.json().get("reply") if r.status_code == 200 else r.text)}
        if r.status_code == 200:
            out["chat"]["tool_log"] = [{"tool": e.get("tool"), "args": e.get("args"), "ok": (e.get("result") or {}).get("ok")} for e in r.json().get("tool_log", [])]
        job = http.get(f"/api/ui/topics/{tid}").json()["fields"].get("job", {"history": []})
        out["stored_job_history"] = [
            {k: e.get(k) for k in ("value", "valid_from", "provenance", "created_at", "expired_at")}
            for e in job["history"]]
    text = json.dumps(out, indent=2)
    print(text)
    if a.out:
        open(a.out, "w").write(text + "\n")


if __name__ == "__main__":
    main()
