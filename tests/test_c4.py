"""C4 (provenance preservation): history survival, empty/null writes, the 500-entry cap.

The baseline (versioned row) keeps every write and rejects empty and null values, so C4 passes with the merge and
real-forgetting cases not applicable and the observations a scorecard reader relies on (nothing lost, nothing empty current). `AppendOnlyStore` shows the passing path and that a system accepting
empty writes breaks those cases. MemState verdicts are never pinned.
"""

import uuid

import pytest

from demo import ramp
from demo.adapter import Rejected, System
from demo.baseline import Baseline
from demo.checks import discover
from demo.verdict import PASS


@pytest.fixture(autouse=True)
def small_forgetting_drive(monkeypatch):
    monkeypatch.setattr(ramp, "FORGET_GATE", 12)
    monkeypatch.setattr(ramp, "ARCHIVE_WAIT_S", 0.2)


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


def test_c4_passes_on_the_baseline_with_the_merge_and_forgetting_cases_not_applicable():
    v = run(Baseline())
    assert v.verdict == PASS
    assert by_name(v, "history survives a value update").held is True
    assert by_name(v, "history survives a merge").held is None  # no duplicate is ever created, so no merge
    assert by_name(v, "history survives real forgetting").held is None  # no archived flag
    assert by_name(v, "history survives real forgetting").id == "forgetting"
    assert "no archived flag" in by_name(v, "history survives real forgetting").observation
    assert not [e for e in Baseline().log.entries if e["kind"] == "setup"]  # never an editor archive write
    assert by_name(v, 'version_field with "" does not replace April 20').held is True
    assert by_name(v, "version_field with null does not replace April 20").held is True
    assert observation(v, "lost earlier value")["lost"] is False


def test_the_baseline_rejects_the_empty_and_null_writes_and_the_current_value_stays():
    v = run(Baseline())
    empty = observation(v, "empty value becoming current")
    assert empty["empty_current"] is False and empty["null_current"] is False
    assert "rejected (422)" in by_name(v, 'version_field with "" does not replace April 20').observation
    assert "rejected (422)" in by_name(v, "version_field with null does not replace April 20").observation


def test_the_baseline_keeps_the_first_value_after_501_writes():
    v = run(Baseline())
    cap = v.measurements["history_cap"]
    assert cap["first_present"] is True and cap["length"] == 501


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


# -- real forgetting and the cap


class Forgetter(AppendOnlyStore):
    """AppendOnlyStore plus salience and forgetting, for the real-forgetting case: salience starts at the request's
    value (default 1.0); once `ramp.FORGET_GATE` topics exist an ingest archives every topic below 0.05; a field write
    resets salience to 1.0 unless `resets=False`."""

    def __init__(self, resets=True, forgets=True):
        super().__init__()
        self.resets, self.forgets = resets, forgets
        self.salience = {}

    def _topic(self, t):
        return {**super()._topic(t), "salience": self.salience.get(t["id"])}

    def _ingest(self, request):
        out = super()._ingest(request)
        tid = out["topic_id"]
        if request["placement"] == "new_topic":
            self.salience[tid] = request.get("salience", 1.0)
        if request.get("fields") and self.resets:
            self.salience[tid] = 1.0
        if self.forgets and len(self.topics) >= ramp.FORGET_GATE:
            for t in self.topics.values():
                if self.salience.get(t["id"], 1.0) < 0.05:
                    t["archived"] = True
        return out


FORGETTING = "history survives real forgetting"


def test_a_topic_with_fields_that_cannot_be_forgotten_makes_the_case_not_applicable_confirmed_by_the_run():
    v = run(Forgetter(resets=True))  # upstream's shape (F24): a field write resets salience to 1.0
    case = by_name(v, FORGETTING)
    assert case.held is None and "was not forgotten" in case.observation and case.id == "forgetting"
    assert v.measurements["forgetting"]["ran"] is True and v.measurements["forgetting"]["target_archived"] is False
    assert v.verdict == PASS  # the verdict rests on the cases that could run


def test_a_forgotten_topic_with_its_history_and_provenance_intact_holds():
    v = run(Forgetter(resets=False))
    case = by_name(v, FORGETTING)
    assert case.held is True and v.measurements["forgetting"]["target_archived"] is True
    assert v.verdict == PASS


def test_a_forgotten_topic_that_lost_its_history_breaks_the_case():
    class Wipes(Forgetter):
        def _topic(self, t):
            topic = super()._topic(t)
            if t["archived"]:
                topic["fields"] = {n: {"current": None, "history": []} for n in t["fields"]}
            return topic

    v = run(Wipes(resets=False))
    assert by_name(v, FORGETTING).held is False and v.verdict != PASS


def test_forgetting_not_shown_to_run_is_not_applicable():
    v = run(Forgetter(resets=False, forgets=False))
    case = by_name(v, FORGETTING)
    assert case.held is None and "forgetting was not shown to run" in case.observation
    assert case.id == "forgetting"  # the id is the same on every path, so the change table lines the systems up


class Capped(AppendOnlyStore):
    """History capped at 500 entries; the overflow is archived (`archive=True`) or dropped."""

    def __init__(self, archive):
        super().__init__()
        self.archive = archive
        self.overflow = {}

    def _topic(self, t):
        topic = super()._topic(t)
        for n, f in topic["fields"].items():
            f["history"] = f["history"][:500]
            if self.archive:
                f["archived_history"] = list(self.overflow.get((t["id"], n), []))
        return topic

    def _ingest(self, request):
        out = super()._ingest(request)
        t = self.topics[out["topic_id"]]
        for n, hist in t["fields"].items():
            while len(hist) > 500:
                self.overflow.setdefault((t["id"], n), []).insert(0, hist.pop())
        return out


def test_the_cap_case_holds_when_the_first_value_is_archived_overflow_readable_by_id():
    v = run(Capped(archive=True))
    cap = v.measurements["history_cap"]
    assert (
        cap["first_present"] is True and cap["first_in_history"] is False and cap["first_in_archived_overflow"] is True
    )
    assert cap["length"] == 500


def test_the_cap_case_breaks_when_the_overflow_is_dropped():
    v = run(Capped(archive=False))
    cap = v.measurements["history_cap"]
    assert cap["first_present"] is False and cap["length"] == 500
    assert v.verdict != PASS


# -- the dated merge

DATED_MERGE = "a dated merge keeps both values, today reads April 20"


class DatedStore(AppendOnlyStore):
    """AppendOnlyStore that accepts `valid_from`, orders each history by it and reads `current` as the entry with
    the latest `valid_from` not in the future. The merge interleaves the two histories by valid time, tagging the
    dropped topic's entries with `merged_from_topic_id`, or with `interleaves=False` keeps only the survivor's
    values for a field it already has (upstream's merge, and the patch before step 3)."""

    def __init__(self, interleaves=True):
        super().__init__()
        self.interleaves = interleaves

    def _topic(self, t):
        fields = {}
        for n, h in t["fields"].items():
            ordered = sorted(h, key=lambda e: e.get("valid_from") or "", reverse=True)
            started = [e for e in ordered if (e.get("valid_from") or "") <= "2999"]
            fields[n] = {"current": started[0] if started else None, "history": ordered}
        return {**t, "fields": fields}

    def _ingest(self, request):
        for f in request.get("fields") or []:
            f.setdefault("valid_from", None)
        out = super()._ingest(request)
        tid = out["topic_id"]
        for n, h in self.topics[tid]["fields"].items():  # the base class stored value and provenance only
            h[0].setdefault(
                "valid_from", next((f["valid_from"] for f in request.get("fields") or [] if f["name"] == n), None)
            )
        return out

    def _merge_pass(self):
        by_title = {}
        for t in self.topics.values():
            by_title.setdefault(t["title"], []).append(t)
        for group in by_title.values():
            keep, *dropped = sorted(group, key=lambda t: t["id"])
            for drop in dropped:
                for name, hist in drop["fields"].items():
                    if name in keep["fields"] and not self.interleaves:
                        continue
                    tagged = [{**e, "merged_from_topic_id": drop["id"]} for e in hist]
                    keep["fields"][name] = tagged + keep["fields"].get(name, [])
                del self.topics[drop["id"]]

    def _describe(self):
        return {"keeps_history": True, "accepts": {"valid_from": True}}


def test_a_merge_that_interleaves_by_valid_time_holds_the_dated_merge_case():
    v = run(DatedStore())
    case = by_name(v, DATED_MERGE)
    assert case.held is True and case.id == "merge-dated"
    assert v.measurements["dated_merge"]["current"] == "April 20"
    assert v.measurements["dated_merge"]["tagged_with_dropped_id"] is True
    assert v.verdict == PASS


def test_a_merge_that_drops_the_later_written_value_breaks_the_dated_merge_case():
    v = run(DatedStore(interleaves=False))
    case = by_name(v, DATED_MERGE)
    assert case.held is False and "merged_from_topic_id=None" in case.observation
    assert v.verdict != PASS


def test_the_dated_merge_case_is_not_applicable_where_no_date_is_accepted():
    for system in (Baseline(), AppendOnlyStore()):
        case = by_name(run(system), DATED_MERGE)
        assert case.held is None and "no valid_from" in case.observation
