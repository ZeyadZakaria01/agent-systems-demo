"""C4 (provenance preservation): history survival, empty/null writes, the 500-entry cap.

The baseline is last-write-wins with no history, so C4 fails with the observations a scorecard reader
relies on (lost earlier value, empty value becoming current). A conforming stand-in on the adapter
shows the passing path. MemState verdicts are never pinned.
"""

import uuid

from demo.baseline import Baseline
from demo.checks import discover
from demo.client import Rejected, System
from demo.verdict import FAIL, PASS


def c4():
    return next(c for c in discover() if c.id == "C4")


def run(system):
    (verdict,) = c4().execute(system)
    return verdict


def observation(verdict, name):
    return next(o for o in verdict.observations if o["name"] == name)


def by_name(verdict, name):
    return next(c for c in verdict.cases if c.name == name)


def test_c4_quotes_the_paper_and_marks_only_the_update_path_as_a_control():
    check = c4()
    (row,) = check.rows
    assert "provenance chain of reachable units" in row.claim
    assert row.control is False
    v = run(Baseline())
    controls = [c for c in v.cases if c.control]
    assert [c.name for c in controls] == ["history survives a value update"]


def test_c4_fails_on_the_baseline_with_the_lost_earlier_value_and_empty_current():
    v = run(Baseline())
    assert v.verdict == FAIL
    assert by_name(v, "history survives a value update").held is False
    assert by_name(v, "history survives a merge").held is False
    assert "upsert (no duplicate)" in by_name(v, "history survives a merge").observation
    assert by_name(v, "history survives archiving").held is None  # no archived flag
    assert by_name(v, 'version_field with "" does not replace April 20').held is False
    assert by_name(v, "version_field with null does not replace April 20").held is False
    lost = observation(v, "lost earlier value")
    assert lost["lost"] is True and "March 15" in lost["summary"]
    empty = observation(v, "empty value becoming current")
    assert empty["empty_current"] is True and empty["null_current"] is True


class HistoryStore(System):
    """Append-only field histories, merge concatenates both, archive keeps the topic, empty/null rejected,
    no cap. The C4 passing path."""

    def __init__(self, cap=None, accept_empty=False):
        super().__init__("history-store")
        self.topics = {}
        self.cap = cap
        self.accept_empty = accept_empty

    def _field(self, history):
        hist = list(history)
        if self.cap is not None:
            hist = hist[:self.cap]  # newest first, drop the oldest
        return {"current": hist[0] if hist else None, "history": hist}

    def _topic(self, t):
        return {**t, "fields": {n: self._field(h) for n, h in t["fields"].items()}}

    def _ingest(self, request):
        placement = request["placement"]
        if placement == "new_topic":
            tid = str(uuid.uuid4())
            self.topics[tid] = {"id": tid, "title": request["title"], "archived": False, "fields": {}}
        else:
            tid = request["topic_id"]
            if tid not in self.topics:
                raise Rejected(400, "topic not found")
        for f in request.get("fields") or []:
            value = f.get("value", "")
            if value in ("", None) and not self.accept_empty:
                raise Rejected(422, "empty value")
            entry = {"value": value, "provenance": f.get("provenance")}
            hist = self.topics[tid]["fields"].setdefault(f["name"], [])
            hist.insert(0, entry)
        self._merge_pass()
        return {"topic_id": tid, "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _merge_pass(self):
        by_title: dict[str, list] = {}
        for t in self.topics.values():
            by_title.setdefault(t["title"], []).append(t)
        for group in by_title.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda t: t["id"])
            keep = group[0]
            for drop in group[1:]:
                for name, hist in drop["fields"].items():
                    keep["fields"][name] = hist + keep["fields"].get(name, [])
                del self.topics[drop["id"]]

    def _query(self, request):
        return {"candidates": []}

    def _read_state(self):
        return {"topics": {i: self._topic(t) for i, t in self.topics.items()}, "edges": None}

    def _read_topic(self, topic_id):
        t = self.topics.get(topic_id)
        return None if t is None else self._topic(t)

    def _setup_write(self, action, params):
        if action == "patch_topic":
            t = self.topics[params["topic_id"]]
            if "archived" in params:
                t["archived"] = params["archived"]
            if "title" in params:
                t["title"] = params["title"]
            return {"topic_id": params["topic_id"]}
        return None

    def _describe(self):
        return {"keeps_history": True}


def test_a_system_that_keeps_history_and_rejects_empty_writes_passes_c4():
    v = run(HistoryStore())
    assert v.verdict == PASS
    assert all(c.held for c in v.cases)
    assert observation(v, "lost earlier value")["lost"] is False
    assert observation(v, "empty value becoming current")["empty_current"] is False
    assert observation(v, "empty value becoming current")["null_current"] is False


def test_accepting_an_empty_write_that_becomes_current_breaks_the_empty_cases():
    v = run(HistoryStore(accept_empty=True))
    assert by_name(v, 'version_field with "" does not replace April 20').held is False
    assert by_name(v, "version_field with null does not replace April 20").held is False
    assert observation(v, "empty value becoming current")["empty_current"] is True
    assert v.verdict != PASS


def test_a_500_entry_cap_that_drops_the_oldest_breaks_the_cap_case():
    v = run(HistoryStore(cap=500))
    cap = by_name(v, "the first value is still in the history after 501 updates")
    assert cap.held is False
    assert v.measurements["history_cap"]["first_present"] is False
    assert v.measurements["history_cap"]["length"] == 500
