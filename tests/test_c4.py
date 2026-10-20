"""C4 (provenance preservation): history survival, empty/null writes, the 500-entry cap.

The baseline is last-write-wins with no history, so C4 fails with the observations a scorecard reader relies on (lost
earlier value, empty value becoming current). `AppendOnlyStore` shows the passing path and that a system accepting
empty writes breaks those cases. MemState verdicts are never pinned.
"""

import uuid

from demo.adapter import Rejected, System
from demo.baseline import Baseline
from demo.checks import discover
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


def test_c4_marks_only_the_update_path_as_a_control():
    controls = [c.name for c in run(Baseline()).cases if c.control]
    assert controls == ["history survives a value update"]


def test_c4_fails_on_the_baseline_with_the_lost_earlier_value_and_empty_current():
    v = run(Baseline())
    assert v.verdict == FAIL
    assert by_name(v, "history survives a value update").held is False
    assert by_name(v, "history survives a merge").held is False
    assert by_name(v, "history survives archiving").held is None  # no archived flag
    assert by_name(v, 'version_field with "" does not replace April 20').held is False
    assert by_name(v, "version_field with null does not replace April 20").held is False
    assert observation(v, "lost earlier value")["lost"] is True
    empty = observation(v, "empty value becoming current")
    assert empty["empty_current"] is True and empty["null_current"] is True


class AppendOnlyStore(System):
    """A test double, not a model of MemState: it keeps every write of a field as history (newest first), folds
    same-title topics by concatenating their histories, and rejects empty and null values unless `accept_empty`."""

    def __init__(self, accept_empty=False):
        super().__init__("append-only-store")
        self.topics = {}
        self.accept_empty = accept_empty

    def _topic(self, t):
        fields = {n: {"current": h[0], "history": list(h)} for n, h in t["fields"].items()}
        return {**t, "fields": fields}

    def _ingest(self, request):
        if request["placement"] == "new_topic":
            tid = str(uuid.uuid4())
            self.topics[tid] = {"id": tid, "title": request["title"], "archived": False, "fields": {}}
        else:
            tid = request["topic_id"]
            if tid not in self.topics:
                raise Rejected(400, "topic not found")
        for f in request.get("fields") or []:
            if f.get("value") in ("", None) and not self.accept_empty:
                raise Rejected(422, "empty value")
            entry = {"value": f.get("value"), "provenance": f.get("provenance")}
            self.topics[tid]["fields"].setdefault(f["name"], []).insert(0, entry)
        self._merge_pass()
        return {"topic_id": tid, "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _merge_pass(self):
        by_title = {}
        for t in self.topics.values():
            by_title.setdefault(t["title"], []).append(t)
        for group in by_title.values():
            keep, *dropped = sorted(group, key=lambda t: t["id"])
            for drop in dropped:
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
        if action != "patch_topic":
            return None
        self.topics[params["topic_id"]].update({k: v for k, v in params.items() if k in ("archived", "title")})
        return {"topic_id": params["topic_id"]}

    def _describe(self):
        return {"keeps_history": True}


def test_a_system_that_keeps_history_and_rejects_empty_writes_passes_c4():
    v = run(AppendOnlyStore())
    assert v.verdict == PASS
    assert observation(v, "lost earlier value")["lost"] is False
    empty = observation(v, "empty value becoming current")
    assert empty["empty_current"] is False and empty["null_current"] is False


def test_accepting_an_empty_write_that_becomes_current_breaks_the_empty_cases():
    v = run(AppendOnlyStore(accept_empty=True))
    assert by_name(v, 'version_field with "" does not replace April 20').held is False
    assert by_name(v, "version_field with null does not replace April 20").held is False
    assert observation(v, "empty value becoming current")["empty_current"] is True
    assert v.verdict != PASS
