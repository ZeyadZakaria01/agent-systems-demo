#!/usr/bin/env python3
"""Replay the W1 writes of recorded two-weeks takes through a patched copy's tool runner, with no model and no server.

Each take's `memory_append_field` calls are replayed with the model's original arguments (from the recording's tool
log), the take's reference time and its user message, on a throwaway store; the script prints what was stored in the
recording beside what the given source would store now. It checks resolver changes on real model output before any
live take is spent.

    PYTHONPATH=MemState-patched/src .venv/bin/python scripts/replay_two_weeks_writes.py runs/chat-series/qwen3.5-4b-think/two-weeks
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from memstate.llm.tool_runner import MemoryToolRunner
from memstate.schema import init_graph
from memstate.store.graph_store import GraphStore
from memstate.store.kuzu_adapter import KuzuGraph, clear_kuzu_graph_cache


def replay(turn: dict) -> list[tuple[str, str]]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    clear_kuzu_graph_cache()
    graph = KuzuGraph(path)
    init_graph(graph)
    store = GraphStore(graph)
    tid = str(uuid.uuid4())
    store.create_topic(tid, title="Me", summary=None, salience=1.0, archived=False, embedding=None)
    runner = MemoryToolRunner(
        store, reference_time=datetime.fromisoformat(turn["reference_time"]), user_message=turn["text"]
    )
    stored = []
    for call in turn.get("tool_log") or []:
        if call["tool"] != "memory_append_field" or not call.get("args", {}).get("field_name"):
            continue
        args = {**call["args"], "topic_id": tid}
        if runner.execute("memory_append_field", args).get("ok"):
            entry = store.get_field_with_history(tid, args["field_name"]).history[0]
            stored.append((str(entry.value), str(entry.valid_from)[:10]))
    return stored


def main() -> int:
    for path in sorted(Path(sys.argv[1]).glob("two-weeks-*.json")):
        w1 = json.loads(path.read_text())["turns"][0]
        before = [(str(e["value"]), str(e.get("valid_from"))[:10]) for e in w1.get("written") or []]
        print(f"{path.name[10:25]}  recorded: {before or 'nothing'}")
        print(f"{'':17}now:      {replay(w1) or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
