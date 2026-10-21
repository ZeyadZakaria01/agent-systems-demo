"""C5 mechanism and natural trajectory, plus the latency table, in-process.

The baseline has no archived flag, so both rows are absent (report §9.3). A stand-in that archives
topics below a threshold once the count gate fires shows pass / partial. MemState verdicts
are never pinned; the ramp sizes and gate are monkeypatched so the tests stay small.
"""

import pytest

from demo.baseline import Baseline
from demo import ramp
from demo.adapter import System
from demo.checks import discover
from demo.latency_tables import aggregate, no_difference_notes, render_latency
from demo.ramp import no_measurable_difference
from demo.session import Session
from demo.verdict import ABSENT, FAIL, PARTIAL, PASS, Case, Verdict


def by_row(row):
    return next(c for c in discover() if c.id == row)


@pytest.fixture(autouse=True)
def tiny_ramps(monkeypatch):
    monkeypatch.setattr(ramp, "STEPS", (2, 4))
    monkeypatch.setattr(ramp, "FORGET_GATE", 3)
    monkeypatch.setattr(ramp, "REPEATS", 2)
    monkeypatch.setattr(ramp, "QUERY_SAMPLES", 3)
    monkeypatch.setattr(ramp, "ARCHIVE_WAIT_S", 0.4)


def run(factory):
    out = {}
    for row in ("C5-1", "C5-2"):
        for v in by_row(row).execute(Session.in_process(factory)):
            out[v.row] = v
    return out


def test_both_c5_rows_quote_the_clause_and_are_absent_on_the_baseline():
    assert [r.id for r in by_row("C5-1").rows] == ["C5-1"]
    assert [r.id for r in by_row("C5-2").rows] == ["C5-2"]
    out = run(Baseline)
    assert out["C5-1"].verdict == ABSENT and out["C5-2"].verdict == ABSENT
    assert out["C5-1"].probe_evidence["archived"] is None
    assert "nothing-value" in out["C5-2"].probe_evidence["probe"]


class ThresholdArchiver(System):
    """Test stand-in: archives every topic with salience below a threshold once the topic count reaches the gate.

    It models no MemState behaviour; it only gives the check an adapter that tracks an archived flag, so the
    check's own pass / partial / fail branches run. `archives=False` keeps the flag but never archives.
    """

    def __init__(self, archives=True, start_salience=1.0):
        super().__init__("threshold-archiver")
        self.archives = archives
        self.start_salience = start_salience
        self.topics: dict[str, dict] = {}

    def _ingest(self, request):
        tid = request.get("topic_id") or request.get("title") or f"t{len(self.topics)}"
        if request["placement"] == "new_topic":
            tid = request.get("title") or tid
            sal = request.get("salience", self.start_salience)
            self.topics[tid] = {"id": tid, "title": tid, "salience": sal, "archived": False,
                                "fields": {f["name"]: {"current": {"value": f.get("value")}, "history": None}
                                           for f in request.get("fields") or []}}
        self._archive_low()
        return {"topic_id": tid, "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _archive_low(self):
        if not self.archives or len(self.topics) < ramp.FORGET_GATE:
            return
        for t in self.topics.values():
            if not t["archived"] and (t["salience"] or 0) < 0.05:
                t["archived"] = True
                t["salience"] = (t["salience"] or 0) * 0.5

    def _query(self, request):
        live = [t for t in self.topics.values() if not t["archived"]]
        return {"candidates": [{"topic_id": t["id"], "fields": []} for t in live[:8]]}

    def _read_state(self):
        return {"topics": dict(self.topics), "edges": None}

    def _read_topic(self, topic_id):
        return self.topics.get(topic_id)

    def _setup_write(self, action, params):
        return None

    def _describe(self):
        return {"keeps_history": False}


def test_mechanism_passes_when_the_0_01_topic_is_archived_and_is_partial_when_only_the_gate_fires():
    out = run(ThresholdArchiver)
    assert out["C5-1"].verdict == PASS
    assert out["C5-1"].measurements["target_archived"] is True
    only_gate = run(lambda: ThresholdArchiver(archives=False))
    assert only_gate["C5-1"].verdict == PARTIAL
    held = {c.name: c.held for c in only_gate["C5-1"].cases}
    assert held["the count gate fires (n ≥ 500)"] is True
    assert held["the 0.01 topic is archived after the 500-topic trigger"] is False


def test_natural_trajectory_fails_when_the_system_archives_nothing():
    out = run(ThresholdArchiver)  # undated writes start at salience 1.0, so nothing is eligible
    assert out["C5-2"].verdict == FAIL
    assert all(r["archived"] == 0 for r in out["C5-2"].measurements["ramps"])


def test_each_ramp_takes_several_plain_query_reads():
    """B4: a ramp used to record a single query sample, so query latency had no median or range."""
    out = run(ThresholdArchiver)["C5-2"]
    assert [len(r["query_samples_ms"]) for r in out.measurements["ramps"]] == [3] * 4
    assert [r["repeat"] for r in out.measurements["ramps"]] == [1, 2, 1, 2]


def ramp_verdict(system, per_n, verdict=PASS):
    """A C5-2 verdict whose ramps carry the given (ingest median, query samples, settle) per repeat of each n."""
    ramps = [{"n": n, "repeat": i, "archived": 0, "ingest_median_ms": ing, "query_samples_ms": q, "settle_s": st}
             for n, repeats in per_n.items() for i, (ing, q, st) in enumerate(repeats, 1)]
    v = Verdict.from_cases("C5-2", [Case("x", verdict == PASS, "")], measurements={"ramps": ramps})
    v.system = system
    return v


def test_aggregate_reports_median_and_range_per_system_and_n():
    v = ramp_verdict("upstream", {2: [(10.0, [4.0, 6.0], 0.1), (14.0, [5.0, 9.0], 0.3), (12.0, [7.0], 0.2)]})
    [entry] = aggregate([v])
    assert (entry["system"], entry["n"], entry["repeats"]) == ("upstream", 2, 3)
    assert (entry["ingest"]["median"], entry["ingest"]["min"], entry["ingest"]["max"]) == (12.0, 10.0, 14.0)
    assert (entry["query"]["median"], entry["query"]["min"], entry["query"]["max"]) == (6.0, 4.0, 9.0)
    assert (entry["settle"]["median"], entry["settle"]["min"], entry["settle"]["max"]) == (0.2, 0.1, 0.3)


def test_no_difference_fires_for_overlapping_ranges_and_not_for_disjoint_ones():
    overlap = [ramp_verdict("upstream", {2: [(10.0, [4.0, 6.0], 0.1), (13.0, [4.0, 6.0], 0.1)]}),
               ramp_verdict("step1", {2: [(11.0, [5.0, 7.0], 0.1), (14.0, [5.0, 7.0], 0.1)]})]
    notes = no_difference_notes(aggregate(overlap))
    assert any("ingest" in n for n in notes) and any("query" in n for n in notes)
    disjoint = [ramp_verdict("upstream", {2: [(10.0, [4.0, 5.0], 0.1), (11.0, [4.0, 5.0], 0.1)]}),
                ramp_verdict("step1", {2: [(50.0, [40.0, 41.0], 0.1), (51.0, [40.0, 41.0], 0.1)]})]
    assert no_difference_notes(aggregate(disjoint)) == []


def test_only_adjacent_chain_steps_are_compared():
    same = {2: [(10.0, [4.0, 5.0], 0.1)]}
    steps = [ramp_verdict(s, same) for s in ("upstream", "step1", "step3")]  # step2 missing: step1 and step3 are not adjacent
    notes = no_difference_notes(aggregate(steps))
    assert any("upstream vs step1" in n for n in notes)
    assert not any("step3" in n for n in notes)
    assert not any("upstream vs step3" in n for n in notes)


def test_systems_whose_c5_2_verdict_is_absent_are_skipped():
    baseline = Verdict.absent("C5-2", {"probe": "x"}, measurements={"ramps": [
        {"n": 2, "repeat": 1, "archived": None, "ingest_median_ms": 0.001, "query_samples_ms": [1.0], "settle_s": 0.1}]})
    baseline.system = "baseline"
    upstream = ramp_verdict("upstream", {2: [(10.0, [4.0], 0.1)]})
    assert [e["system"] for e in aggregate([baseline, upstream])] == ["upstream"]
    assert render_latency([baseline]) == ""
    assert render_latency([]) == ""


def test_no_measurable_difference_is_a_median_inside_the_combined_range():
    assert no_measurable_difference([10, 12], [11, 13]) is True
    assert no_measurable_difference([10, 11], [50, 60]) is False


# -- the declared bound beside the active count, and F24

class Bounded(ThresholdArchiver):
    def __init__(self, resets_fielded=False, **kw):
        super().__init__(**kw)
        self.resets_fielded = resets_fielded

    def _ingest(self, request):
        if self.resets_fielded and request.get("fields"):
            request = {**request, "salience": 1.0}  # a field write resets the topic's salience before any pass
        return super()._ingest(request)

    def _describe(self):
        return {**super()._describe(), "declared_bound": {"topics": 500, "name": "soft limit"}}


def test_the_natural_trajectory_text_states_the_declared_bound_beside_the_active_count():
    out = run(Bounded)
    (case,) = out["C5-2"].cases
    assert "4 active topics at n=4 against declared bound 500 topics (soft limit)" in case.observation
    assert out["C5-2"].measurements["declared_bound"] == {"topics": 500, "name": "soft limit"}
    assert out["C5-2"].measurements["active_at_largest_n"] == {"n": 4, "active": 4}
    assert "declared bound 500 topics" in out["C5-1"].cases[0].observation


def test_a_system_declaring_no_bound_says_so():
    (case,) = run(ThresholdArchiver)["C5-2"].cases
    assert "the system declares no bound" in case.observation


def test_a_topic_with_fields_reset_to_full_salience_and_never_forgotten_is_recorded_as_an_observation():
    (obs,) = run(lambda: Bounded(resets_fielded=True))["C5-1"].observations
    assert obs["name"] == "topic with fields not forgotten"
    assert obs["reset"] is True and obs["forgotten"] is False and obs["stored_salience"] == 1.0
    assert "F24" in obs["summary"]


def test_a_topic_with_fields_that_is_forgotten_is_not_reported_as_reset():
    (obs,) = run(Bounded)["C5-1"].observations
    assert obs["forgotten"] is True and obs["reset"] is False


class AcceptsValidAt(ThresholdArchiver):
    def _describe(self):
        return {"keeps_history": False, "accepts": {"valid_at": True}}


def test_the_largest_ramp_of_a_system_accepting_valid_at_times_twenty_as_of_reads_apart_from_the_plain_ones():
    ramps = run(AcceptsValidAt)["C5-2"].measurements["ramps"]
    largest = max(r["n"] for r in ramps)
    assert [len(r["as_of_samples_ms"]) for r in ramps if r["n"] == largest] == [20] * len([r for r in ramps if r["n"] == largest])
    assert all(r["as_of_samples_ms"] == [] for r in ramps if r["n"] != largest)
    assert all(len(r["query_samples_ms"]) == 3 for r in ramps)  # the plain samples do not include the as-of reads


def test_a_system_without_valid_at_times_no_as_of_reads():
    ramps = run(ThresholdArchiver)["C5-2"].measurements["ramps"]
    assert all(r["as_of_samples_ms"] == [] for r in ramps)
    assert "As-of reads" not in render_latency([run(ThresholdArchiver)["C5-2"]])


def test_the_latency_output_reports_the_as_of_reads_beside_the_plain_ones():
    v = ramp_verdict("step3", {2000: [(10.0, [4.0, 6.0], 0.1)]})
    v.measurements["ramps"][0]["as_of_samples_ms"] = [5.0] * 19 + [9.0]
    [entry] = aggregate([v])
    assert entry["as_of"]["median"] == 5.0 and entry["as_of"]["max"] == 9.0
    text = render_latency([v])
    assert "As-of reads" in text and "| step3 | 2000 | 20 | 5.0 (5.0–9.0) | 5.0 (4.0–6.0) |" in text
