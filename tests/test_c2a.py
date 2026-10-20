"""C2(a), the merge helpers and the merge extras, in-process. No server and no MemState mocks.

The baseline gives the pinned expectation (pass, 0 violations: it upserts, nothing is ever duplicated). MemState's
own verdicts are never pinned here. `LowerIdKeeper` below is a generic second system on the adapter, not a model of
MemState: it folds same-title topics together with whatever keeper rule the test picks, so that violation counting,
the arrangement guard, windows and timeouts run through the check as it would run on any system.
"""

import threading
import time
import uuid

from demo.adapter import Rejected, System
from demo.baseline import Baseline
from demo.checks import discover
from demo.checks.c2a_merge import measure_merges
from demo.merge import await_merge, create_duplicate_pair, current_after_merge, trigger_and_await_merge
from demo.merge_extras import active_into_archived, three_same_title
from demo.reads import NO_VALUE
from demo.verdict import ABSENT, FAIL, NOT_SCORED, PASS


def c2a():
    return next(c for c in discover() if c.id == "C2(a)")


class LowerIdKeeper(System):
    """A test double, not a model of MemState. Topics are keyed by uuid4; a background pass after each ingest folds
    same-title topics together: the one with the lower id (`keep="lower"`) or the higher one (`keep="higher"`)
    survives and keeps its own value for a field both hold (`newer_wins`: takes the dropped topic's value instead),
    and the other topic is deleted (`archive`: archived instead). `merge=False` never folds, `delay` postpones the
    pass, `supports_setup=False` refuses every setup write (no way to retitle). Archived topics take part in the pass.
    """

    def __init__(self, delay: float = 0.0, merge: bool = True, archive: bool = False, supports_setup: bool = True,
                 newer_wins: bool = False, keep: str = "lower") -> None:
        super().__init__("lower-id-keeper")
        self.topics: dict[str, dict] = {}
        self.delay, self.merge, self.archive, self.supports_setup = delay, merge, archive, supports_setup
        self.newer_wins, self.keep = newer_wins, keep
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
            live = sorted(self.topics.values(), key=lambda t: t["id"], reverse=self.keep == "higher")
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


def test_c2a_passes_on_the_baseline_with_zero_violations():
    (verdict,) = c2a().execute(Baseline())
    assert verdict.verdict == PASS
    assert len(verdict.cases) == 20 and all(c.held for c in verdict.cases)
    assert verdict.measurements["violations"] == 0


def test_the_baseline_counts_its_upserts_apart_from_merges_and_has_no_window():
    (verdict,) = c2a().execute(Baseline())
    m = verdict.measurements
    assert m["upserted"] == 20 and m["merges"] == 0  # nothing was ever duplicated, so nothing merged
    assert m["window_median_s"] is None and m["window_samples"] == 0


def test_the_baseline_runs_the_extras_and_skips_the_archived_one_it_cannot_arrange():
    (verdict,) = c2a().execute(Baseline())
    extras = next(o for o in verdict.observations if o["name"] == "merge extras")
    three = extras["three_same_title"]
    assert len(three["survivor_ids"]) == 1
    assert three["survivors"][0]["current"] == "May 31"  # last write wins
    assert extras["active_into_archived"]["skipped"] is True


def test_repetitions_use_distinct_titles_and_are_recorded_one_by_one():
    (verdict,) = c2a().execute(Baseline())
    reps = verdict.measurements["per_repetition"]
    assert len(reps) == 20
    assert len({r["title"] for r in reps}) == 20


# -- a system that merges the way the check must catch


def test_a_merge_that_keeps_the_lower_id_value_breaks_every_repetition_because_the_dropped_topic_holds_the_newer_value():
    verdict = c2a().execute(LowerIdKeeper())[0]
    m = verdict.measurements
    assert m["dropped_held_newer"] == 20  # the precondition holds in every repetition, whatever the random ids
    assert m["violations"] == 20 and m["violation_rate"] == "20/20"
    assert verdict.verdict == FAIL
    assert m["merges"] == 20 and m["upserted"] == 0
    assert m["window_samples"] == 20 and m["window_min_s"] <= m["window_median_s"] <= m["window_max_s"]


def test_a_merge_that_lets_the_newer_value_win_passes_with_no_violations():
    verdict = c2a().execute(LowerIdKeeper(newer_wins=True))[0]
    assert verdict.verdict == PASS and verdict.measurements["violation_rate"] == "0/20"


def test_a_repetition_in_which_the_newer_topic_survived_is_not_a_case():
    # keeping the higher id means the dropped topic held the OLDER value: the claim is not tested, so no verdict
    verdict = measure_merges(LowerIdKeeper(keep="higher"), timeout=0.3)  # the extras give up after 0.3 s
    m = verdict.measurements
    assert m["arrangement_not_met"] == 20 and m["dropped_held_newer"] == 0 and m["violations"] == 0
    assert all(c.held is None for c in verdict.cases)
    assert verdict.verdict == NOT_SCORED


def test_a_system_that_cannot_retitle_falls_back_to_same_title_writes():
    s = LowerIdKeeper(supports_setup=False)
    out = trigger_and_await_merge(s, "Fallback")
    assert out.merged and out.pair.title.startswith("Fallback ")


def test_the_window_includes_the_merge_delay_and_is_measured_by_the_logged_wait():
    s = LowerIdKeeper(delay=0.3)
    out = trigger_and_await_merge(s, "Window Title")
    assert out.merged and not out.waited.timed_out
    assert 0.25 <= out.window_s < 2.0
    waits = s.log.of_kind("wait")
    assert len(waits) == 1 and waits[0]["response"]["elapsed_s"] == out.window_s
    assert all(e["kind"] != "wait" for e in s.log.entries if e["op"] in ("ingest", "read_topic"))


def test_a_merge_that_never_comes_times_out_and_is_not_a_case():
    s = LowerIdKeeper(merge=False)
    pair = create_duplicate_pair(s, "No Merge")
    t0 = time.perf_counter()
    out = await_merge(s, pair, timeout=0.3)
    assert not out.merged and out.waited.timed_out and out.window_s is None
    assert time.perf_counter() - t0 < 2
    assert current_after_merge(s, out) is NO_VALUE


def test_a_system_that_never_merges_scores_absent_with_the_waits_as_evidence():
    verdict = measure_merges(LowerIdKeeper(merge=False), repetitions=2, timeout=0.2)
    assert verdict.verdict == ABSENT and verdict.probe_evidence["merges_seen"] == 0
    assert len(verdict.probe_evidence["waits_s"]) == 2
    assert all(c.held is None for c in verdict.cases)


def test_an_archived_dropped_topic_counts_as_a_merge_and_is_not_reported_deleted():
    s = LowerIdKeeper(archive=True)
    out = trigger_and_await_merge(s, "Archive On Merge")
    assert out.merged and out.dropped_state == "archived"


# -- extras


def test_three_same_title_is_arranged_as_a_three_way_tie_and_leaves_one_topic():
    out = three_same_title(LowerIdKeeper())
    assert out["arranged_as_three_way_tie"] is True and not out["timed_out"]
    assert len(out["survivor_ids"]) == 1 and len(out["deleted_ids"]) == 2


def test_active_into_archived_deletes_the_active_topic_and_keeps_the_archived_one():
    out = active_into_archived(LowerIdKeeper())
    assert out["skipped"] is False and not out["timed_out"] and out["active_topic_state"] == "deleted"
    assert out["survivor"]["archived"] is True
