"""C5 mechanism and natural trajectory, plus the latency table, in-process.

The baseline has no archived flag, so both rows are absent (report §9.3). A stand-in that archives
topics below the forget threshold once the count gate fires shows pass / partial. MemState verdicts
are never pinned; the ramp sizes and gate are monkeypatched so the tests stay small.
"""

import pytest

from demo.baseline import Baseline
from demo.checks import discover
from demo.client import System
from demo.latency_tables import render_latency
from demo.ramp import no_measurable_difference
from demo.session import Session
from demo.verdict import ABSENT, FAIL, PARTIAL, PASS, Verdict


def by_row(row):
    return next(c for c in discover() if c.id == row)


@pytest.fixture(autouse=True)
def tiny_ramps(monkeypatch):
    import demo.checks.c5_topic_ramp as c5mod
    import demo.ramp as ramp

    monkeypatch.setattr(ramp, "STEPS", (2, 4))
    monkeypatch.setattr(ramp, "FORGET_GATE", 3)
    monkeypatch.setattr(ramp, "REPEATS", 1)
    monkeypatch.setattr(ramp, "ARCHIVE_WAIT_S", 0.4)
    monkeypatch.setattr(c5mod, "STEPS", (2, 4))
    monkeypatch.setattr(c5mod, "FORGET_GATE", 3)
    monkeypatch.setattr(c5mod, "REPEATS", 1)
    monkeypatch.setattr(c5mod, "ARCHIVE_WAIT_S", 0.4)


def run(factory):
    out = {}
    for row in ("C5-1", "C5-2"):
        for v in by_row(row).execute(Session.in_process(factory)):
            out[v.row] = v
    return out


def test_both_c5_rows_quote_the_clause_and_are_absent_on_the_baseline():
    assert [r.id for r in by_row("C5-1").rows] == ["C5-1"]
    assert [r.id for r in by_row("C5-2").rows] == ["C5-2"]
    assert all("Bounded active state" in by_row(row).rows[0].claim for row in ("C5-1", "C5-2"))
    out = run(Baseline)
    assert out["C5-1"].verdict == ABSENT and out["C5-2"].verdict == ABSENT
    assert out["C5-1"].probe_evidence["archived"] is None
    assert "nothing-value" in out["C5-2"].probe_evidence["probe"]


class Forgetter(System):
    """Archives every topic with salience < 0.05 once the topic count reaches the gate.

    `forgets=False` still counts topics and exposes `archived=False`, so the gate can fire without a victim.
    """

    def __init__(self, forgets=True, start_salience=1.0):
        super().__init__("forgetter")
        self.forgets = forgets
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
        self._forget()
        return {"topic_id": tid, "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _forget(self):
        import demo.ramp as ramp
        if not self.forgets or len(self.topics) < ramp.FORGET_GATE:
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
    out = run(Forgetter)
    assert out["C5-1"].verdict == PASS
    assert out["C5-1"].measurements["target_archived"] is True
    only_gate = run(lambda: Forgetter(forgets=False))
    assert only_gate["C5-1"].verdict == PARTIAL
    held = {c.name: c.held for c in only_gate["C5-1"].cases}
    assert held["the count gate fires (n ≥ 500)"] is True
    assert held["the 0.01 topic is archived after the 500-topic trigger"] is False


def test_natural_trajectory_fails_when_the_system_archives_nothing():
    out = run(Forgetter)  # undated writes start at salience 1.0, so nothing is eligible
    assert out["C5-2"].verdict == FAIL
    assert all(r["archived"] == 0 for r in out["C5-2"].measurements["ramps"])


def test_the_latency_table_renders_from_c5_2_and_stays_quiet_without_it():
    v = Verdict.from_cases("C5-2", [], measurements={"ramps": [
        {"n": 2, "repeat": 1, "ingest_median_ms": 10.0, "query_ms": 4.0, "reasoner_wait_s": 0.1, "archived": 0},
    ]})
    v.system = "upstream"
    text = render_latency([v])
    assert "### Latency ramps" in text and "ingest median" in text and "10.0" in text
    assert render_latency([]) == ""


def test_no_measurable_difference_is_a_median_inside_the_combined_range():
    assert no_measurable_difference([10, 12], [11, 13]) is True
    assert no_measurable_difference([10, 11], [50, 60]) is False
