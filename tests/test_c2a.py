"""C2(a), the merge helpers and the merge extras, in-process. No server and no MemState mocks.

The baseline gives the pinned expectation (value pass, 0/20: it upserts, nothing is ever duplicated). MemState's
own verdicts are never pinned here; `DuplicateMerger` below is a different system on the adapter, built to merge the
way the check must be able to catch (lower id survives, its value wins), so that violation counting, windows and
timeouts are exercised through the adapter.
"""

import threading
import time
import uuid

from demo.baseline import Baseline
from demo.checks import discover
from demo.client import Rejected, System
from demo.merge import await_merge, create_duplicate_pair, current_after_merge, trigger_and_await_merge
from demo.merge_extras import active_into_archived, three_same_title
from demo.reads import NO_VALUE
from demo.run import _cases_text, _observation_text
from demo.verdict import ABSENT, FAIL, PASS, Case


def c2a():
    return next(c for c in discover() if c.id == "C2(a)")


class DuplicateMerger(System):
    """Topics keyed by uuid4; a background pass after each ingest merges same-title pairs: the lower id survives,
    keeps its own value for a shared field, and the dropped topic is deleted (or archived, `archive=True`)."""

    def __init__(self, delay: float = 0.0, merge: bool = True, archive: bool = False, supports_setup: bool = True,
                 newer_wins: bool = False) -> None:
        super().__init__("duplicate-merger")
        self.topics: dict[str, dict] = {}
        self.delay, self.merge, self.archive, self.supports_setup = delay, merge, archive, supports_setup
        self.newer_wins = newer_wins  # the dropped topic's value replaces the keeper's (a merge that respects C2(a))
        self.lock = threading.Lock()

    def _topic(self, tid, title, fields=None):
        return {"id": tid, "title": title, "archived": False, "salience": None, "summary": None, "topic_kind": None,
                "fields": {n: {"history": [{"value": v}], "current": {"value": v}} for n, v in (fields or {}).items()}}

    def _ingest(self, request):
        with self.lock:
            if request["placement"] == "new_topic":
                tid = str(uuid.uuid4())
                self.topics[tid] = self._topic(tid, request["title"], {f["name"]: f["value"] for f in request["fields"]})
            else:
                tid = request["topic_id"]
                if tid not in self.topics:
                    raise Rejected(400, "topic not found")
                for f in request["fields"]:
                    self.topics[tid]["fields"][f["name"]] = {"history": [{"value": f["value"]}],
                                                              "current": {"value": f["value"]}}
        if self.merge:
            threading.Timer(self.delay, self._merge_pass).start()
        return {"topic_id": tid, "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _merge_pass(self):
        with self.lock:
            live = sorted(self.topics.values(), key=lambda t: t["id"])  # archived topics are scanned too (upstream)
            for i, keep in enumerate(live):
                for drop in live[i + 1:]:
                    if drop["id"] in self.topics and keep["title"] == drop["title"] and keep["id"] in self.topics:
                        for n, f in drop["fields"].items():
                            if self.newer_wins:
                                keep["fields"][n] = f
                            else:
                                keep["fields"].setdefault(n, f)
                        if self.archive:
                            drop["archived"] = True
                        else:
                            del self.topics[drop["id"]]

    def _query(self, request):
        ids = [t for t in request["topic_ids"] if t in self.topics and not self.topics[t]["archived"]]
        return {"candidates": [{"topic_id": t, "fields": []} for t in ids]}

    def _read_state(self):
        return {"topics": dict(self.topics), "edges": None}

    def _read_topic(self, topic_id):
        return self.topics.get(topic_id)

    def _setup_write(self, action, params):
        if not self.supports_setup:
            return None
        with self.lock:
            if action == "create_topic":
                self.topics[params["topic_id"]] = self._topic(params["topic_id"], params["title"])
            elif action == "patch_topic":
                self.topics[params["topic_id"]].update({k: v for k, v in params.items() if k != "topic_id"})
        return {"topic_id": params["topic_id"]}

    def _describe(self):
        return {"keeps_history": False}


# -- baseline: the pinned expectation


def test_c2a_passes_on_the_baseline_with_zero_of_twenty_violations():
    (verdict,) = c2a().execute(Baseline())
    assert verdict.row == "C2(a)"
    assert verdict.verdict == PASS
    assert verdict.control is False
    assert len(verdict.cases) == 20 and all(c.held for c in verdict.cases)
    assert verdict.measurements["violation_rate"] == "0/20"
    assert verdict.measurements["violations"] == 0


def test_the_baseline_has_no_merge_window_and_the_report_says_why():
    (verdict,) = c2a().execute(Baseline())
    m = verdict.measurements
    assert m["window_median_s"] is None and m["window_samples"] == 0
    assert "upsert" in m["window_note"]
    deleted = next(o for o in verdict.observations if o["name"] == "topic deleted on merge")
    assert "not applicable" in deleted["summary"]


def test_the_baseline_runs_the_extras_and_skips_the_archived_one_it_cannot_arrange():
    (verdict,) = c2a().execute(Baseline())
    extras = next(o for o in verdict.observations if o["name"] == "merge extras")
    three = extras["three_same_title"]
    assert three["survivor_ids"] and len(three["survivor_ids"]) == 1
    assert three["survivors"][0]["current"] == "May 31"  # last write wins
    arch = extras["active_into_archived"]
    assert arch["skipped"] is True and "no editor path" in arch["summary"]


def test_repetitions_use_distinct_titles_and_are_recorded_one_by_one():
    (verdict,) = c2a().execute(Baseline())
    reps = verdict.measurements["per_repetition"]
    assert len(reps) == 20
    assert len({r["title"] for r in reps}) == 20


# -- a system that merges the way the check must catch


def test_a_merge_that_keeps_the_lower_id_value_breaks_every_repetition_because_the_dropped_topic_holds_the_newer_value():
    verdict = c2a().execute(DuplicateMerger())[0]
    m = verdict.measurements
    assert m["dropped_held_newer"] == 20  # the precondition holds in every repetition, whatever the random ids
    assert m["violations"] == 20 and m["violation_rate"] == "20/20"
    assert m["random_id_counts"] == {"stale value current": [20, 20]}
    assert verdict.verdict == FAIL
    assert m["window_samples"] == 20 and m["window_min_s"] <= m["window_median_s"] <= m["window_max_s"]
    assert "20/20" in next(o for o in verdict.observations if o["name"] == "topic deleted on merge")["summary"]


def test_a_merge_that_lets_the_newer_value_win_passes_with_no_violations():
    verdict = c2a().execute(DuplicateMerger(newer_wins=True))[0]
    assert verdict.verdict == PASS and verdict.measurements["violation_rate"] == "0/20"


def test_the_pair_is_arranged_with_labelled_setup_titles_and_scored_value_writes_only():
    s = DuplicateMerger()
    trigger_and_await_merge(s, "Arranged", "March 15", "April 20")
    setups = s.log.of_kind("setup")
    assert [e["op"] for e in setups] == ["patch_topic", "patch_topic"] and all(e["request"]["label"] for e in setups)
    assert all(set(e["request"]) <= {"action", "label", "topic_id", "title"} for e in setups)  # titles only


def test_a_system_that_cannot_retitle_falls_back_to_same_title_writes():
    s = DuplicateMerger(supports_setup=False)
    out = trigger_and_await_merge(s, "Fallback", "March 15", "April 20")
    assert out.merged and out.pair.title.startswith("Fallback ")


def test_the_window_includes_the_merge_delay_and_is_measured_by_the_logged_wait():
    s = DuplicateMerger(delay=0.3)
    out = trigger_and_await_merge(s, "Window Title", "March 15", "April 20")
    assert out.merged and not out.waited.timed_out
    assert 0.25 <= out.window_s < 2.0
    waits = s.log.of_kind("wait")
    assert len(waits) == 1 and waits[0]["response"]["elapsed_s"] == out.window_s
    assert all(e["kind"] != "wait" for e in s.log.entries if e["op"] in ("ingest", "read_topic"))


def test_a_merge_that_never_comes_times_out_and_is_not_a_case():
    s = DuplicateMerger(merge=False)
    pair = create_duplicate_pair(s, "No Merge", "March 15", "April 20")
    t0 = time.perf_counter()
    out = await_merge(s, pair, timeout=0.3)
    assert not out.merged and out.waited.timed_out and out.window_s is None
    assert time.perf_counter() - t0 < 2
    assert current_after_merge(s, out) is NO_VALUE


def test_a_system_that_never_merges_scores_absent_with_the_waits_as_evidence(monkeypatch):
    import demo.checks.c2a_merge as mod

    monkeypatch.setattr(mod, "REPETITIONS", 2)
    monkeypatch.setattr(mod, "trigger_and_await_merge",
                        lambda s, title, o, n, **kw: await_merge(s, create_duplicate_pair(s, title, o, n), timeout=0.2))
    monkeypatch.setattr(mod, "three_same_title", lambda s: {"summary": "n/a"})
    monkeypatch.setattr(mod, "active_into_archived", lambda s: {"summary": "n/a"})
    verdict = c2a().execute(DuplicateMerger(merge=False))[0]
    assert verdict.verdict == ABSENT and verdict.probe_evidence["merges_seen"] == 0
    assert all(c.held is None for c in verdict.cases)


def test_an_archived_dropped_topic_counts_as_a_merge_and_is_not_reported_deleted():
    s = DuplicateMerger(archive=True)
    out = trigger_and_await_merge(s, "Archive On Merge", "March 15", "April 20")
    assert out.merged and out.dropped_state == "archived"


# -- extras


def test_three_same_title_is_arranged_as_a_three_way_tie_and_leaves_one_topic():
    s = DuplicateMerger()
    out = three_same_title(s)
    assert out["arranged_as_three_way_tie"] is True and not out["timed_out"]
    assert len(out["survivor_ids"]) == 1 and len(out["deleted_ids"]) == 2
    assert len(s.log.of_kind("setup")) == 3


def test_active_into_archived_uses_labelled_setup_writes_for_the_archived_keeper():
    s = DuplicateMerger()
    out = active_into_archived(s)
    assert out["skipped"] is False and not out["timed_out"] and out["active_topic_state"] == "deleted"
    assert out["archived_id"].startswith("00000000-0000-4000-8000-") and len(out["archived_id"]) == 36
    setups = s.log.of_kind("setup")
    assert [e["op"] for e in setups] == ["create_topic", "patch_topic"] and all(e["request"]["label"] for e in setups)


def test_the_window_text_says_why_when_nothing_merged(monkeypatch):
    import demo.checks.c2a_merge as mod

    monkeypatch.setattr(mod, "REPETITIONS", 2)
    monkeypatch.setattr(mod, "trigger_and_await_merge",
                        lambda s, title, o, n, **kw: await_merge(s, create_duplicate_pair(s, title, o, n), timeout=0.2))
    monkeypatch.setattr(mod, "three_same_title", lambda s: {"summary": "n/a"})
    monkeypatch.setattr(mod, "active_into_archived", lambda s: {"summary": "n/a"})
    value = c2a().execute(DuplicateMerger(merge=False))[0].measurements["windows"][0]["value"]
    assert "no merge seen" in value and "2/2" in value
    (b,) = c2a().execute(Baseline())
    assert "no duplicate is ever created" in b.measurements["windows"][0]["value"]


# -- the shared findings rendering


def test_findings_rendering_of_many_cases_keeps_the_ones_that_did_not_hold():
    cases = [Case(f"c{i}", True, "ok") for i in range(7)] + [Case("bad", False, "why"), Case("na", None, "n/a-why")]
    text = _cases_text(cases)
    assert "9 cases: held 7, BROKE 1, n/a 1" in text and "bad: BROKE (why)" in text and "na: n/a (n/a-why)" in text
    assert "c3" not in text
    assert _cases_text(cases[:2]) == "c0: held (ok); c1: held (ok)"


def test_findings_rendering_of_observations_never_dumps_a_structure():
    assert _observation_text("plain") == "plain"
    assert _observation_text({"name": "n", "summary": "s", "big": list(range(999))}) == "s"
    assert _observation_text({"name": "n", "big": list(range(999))}) == "n"
