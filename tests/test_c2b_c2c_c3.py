"""C2(b), C2(c), C3 and the dependent-topic staleness window, in-process.

The baseline gives the verdicts report §9.3 predicts (C2(b) not-scored, C2(c) absent, C3 absent). Fake systems that
subclass the baseline stand in for other outcomes (partial commit, soundness issue, propagation) to prove the
classification; nothing here pins a MemState verdict.
"""

import time

import httpx
import pytest

from demo.baseline import Baseline
from demo.checks import c3_propagation, discover
from demo.adapter import Rejected
from demo.verdict import ABSENT, FAIL, NOT_SCORED, PARTIAL, PASS, Verdict
from demo.windows import render_windows, window_entries


def by_row(row):
    return next(c for c in discover() if row in [r.id for r in c.rows])


def run(row, system) -> Verdict:
    (verdict,) = by_row(row).execute(system)
    return verdict


@pytest.fixture(autouse=True)
def short_wait(monkeypatch):
    monkeypatch.setattr(c3_propagation, "REVISION_WAIT_S", 0.3)


# -- baseline verdicts (report §9.3)

def test_baseline_c2b_is_not_scored():
    v = run("C2(b)", Baseline())
    assert v.verdict == NOT_SCORED
    assert [c.held for c in v.cases] == [None]
    assert v.observations == []  # it never reports an edge applied


def test_baseline_c2c_is_absent_after_probing_the_api_surface():
    baseline = Baseline()
    v = run("C2(c)", baseline)
    assert v.verdict == ABSENT
    probes = [e for e in baseline.log.entries if e["op"] == "probe"]
    assert probes  # it looked: every candidate route was probed through the adapter
    assert all(e["response"] is None for e in probes)  # the baseline has no API: nothing answers


def test_baseline_c3_is_absent_with_the_run_as_evidence():
    v = run("C3", Baseline())
    assert v.verdict == ABSENT
    assert v.probe_evidence  # absent carries the run
    assert [c.held for c in v.cases] == [False, False]


def test_baseline_pair_shows_a_updated_and_b_unchanged():
    v = run("C3", Baseline())
    pair = v.probe_evidence["pairs"][0]
    assert pair["a_deadline_now"] == "April 20"  # A really changed
    assert pair["b_date_before"] == pair["b_date_read_right_after_update"] == pair["b_date_after_wait"] == "March 20"
    assert pair["reflected"] is False
    assert pair["edge_linked"] is None  # the baseline stores no edges


def test_baseline_dependent_window_is_unbounded_and_cites_the_c3_run():
    v = run("C3", Baseline())
    v.system, v.snapshots = "baseline", ["snapshots/baseline/c3.json"]
    (window,) = v.measurements["windows"]
    assert window["value"] == "unbounded (C3 absent)"
    (entry,) = window_entries([v])
    assert entry["row"] == "C3" and entry["snapshots"] == ["snapshots/baseline/c3.json"]
    assert entry["window"] == window["name"]
    assert render_windows([v])  # rendered


def test_no_windows_no_table():
    assert render_windows([Verdict.not_scored("C2(b)")]) == ""


# -- C2(b) classification on other systems

class PartialCommit(Baseline):
    """Writes the topic and its fields, then fails on the edge."""

    def _ingest(self, request):
        super()._ingest(request)
        if request.get("edges"):
            raise Rejected(400, "edge target not found")


class CleanRejection(Baseline):
    def _ingest(self, request):
        if request.get("edges"):
            raise Rejected(400, "edge target not found")
        return super()._ingest(request)


class ServerErrorAfterWriting(Baseline):
    def _ingest(self, request):
        super()._ingest(request)
        if request.get("edges"):
            raise httpx.HTTPStatusError("boom", request=httpx.Request("POST", "http://x"),
                                        response=httpx.Response(500))


class EdgeReportedButMissing(Baseline):
    """Succeeds and lists the edge as applied, while the stored state has none (the C2(b) soundness issue)."""

    def _ingest(self, request):
        out = super()._ingest(request)
        out["applied"] += [f"edge:{e['to_topic_id']}" for e in request.get("edges") or []]
        return out

    def _read_state(self):
        return {**super()._read_state(), "edges": []}


def test_error_with_the_topic_and_fields_persisted_is_a_partial_commit_fail():
    assert run("C2(b)", PartialCommit()).verdict == FAIL


class PartialCommitUnderScopedTitle(Baseline):
    """Like a live server: every title the check writes is stored with a scope suffix, and `describe()` says which."""

    SCOPE = "C2(b) 120000"

    def _ingest(self, request):
        super()._ingest({**request, "title": f"{request['title']} [live {self.SCOPE}]"})
        raise Rejected(400, "edge target not found")

    def _describe(self):
        return {**super()._describe(), "title_scope": self.SCOPE}


def test_a_partial_commit_is_found_when_the_system_stores_titles_with_a_scope_suffix():
    assert run("C2(b)", PartialCommitUnderScopedTitle()).verdict == FAIL


def test_a_server_error_with_state_persisted_is_also_a_partial_commit():
    assert run("C2(b)", ServerErrorAfterWriting()).verdict == FAIL


def test_a_clean_rejection_is_neither_outcome_so_not_scored():
    v = run("C2(b)", CleanRejection())
    assert v.verdict == NOT_SCORED
    assert v.observations == []


def test_success_with_the_edge_reported_applied_is_a_soundness_observation_and_not_scored():
    v = run("C2(b)", EdgeReportedButMissing())
    assert v.verdict == NOT_SCORED
    assert [o["name"] for o in v.observations] == ["soundness issue"]


def test_the_soundness_issue_is_reported_even_when_the_system_stores_no_edges():
    class ReportsEdgeWithoutEdgeStorage(Baseline):
        def _ingest(self, request):
            out = super()._ingest(request)
            out["applied"] += [f"edge:{e['to_topic_id']}" for e in request.get("edges") or []]
            return out

    v = run("C2(b)", ReportsEdgeWithoutEdgeStorage())
    assert v.verdict == NOT_SCORED
    assert [o["name"] for o in v.observations] == ["soundness issue"]


# -- C2(c): a policy-bearing route or schema is never silently scored, a stray word in a property name is not one

class WithPolicyRoute(Baseline):
    def _probe(self, method, path):
        if path == "/v1/policies":
            return {"status": 200, "content_type": "application/json", "body": {"policies": []}}
        return None


class WithOpenapi(Baseline):
    def __init__(self, paths=(), schemas=None):
        super().__init__()
        self.body = {"paths": {p: {"get": {}} for p in paths}, "components": {"schemas": schemas or {}}}

    def _probe(self, method, path):
        if path == "/openapi.json":
            return {"status": 200, "content_type": "application/json", "body": self.body}
        return {"status": 404, "content_type": None, "body": None}


def test_a_system_with_a_policy_route_is_not_scored_absent():
    with pytest.raises(RuntimeError, match="policy-like surface"):
        run("C2(c)", WithPolicyRoute())


@pytest.mark.parametrize("paths,schemas", [(["/v1/policies"], {}), (["/api/ui/Rules"], {}),
                                           ([], {"PolicyRule": {"properties": {}}}),
                                           ([], {"ConstraintSet": {"properties": {}}})])
def test_a_route_or_schema_named_for_policies_is_not_scored_absent(paths, schemas):
    with pytest.raises(RuntimeError, match="policy-like surface"):
        run("C2(c)", WithOpenapi(paths, schemas))


def test_policy_words_only_inside_other_words_or_property_names_do_not_stop_the_row():
    schemas = {"Stats": {"properties": {"trigger_count": {"type": "integer"}}}, "Controller": {"properties": {}}}
    v = run("C2(c)", WithOpenapi(["/v1/ingest", "/api/ui/ruleset-version", "/api/ui/triggered-events"], schemas))
    assert v.verdict == ABSENT
    assert v.probe_evidence["api_schema"]["policy_term_property_hits"] == ["trigger_count"]


# -- C3 on systems that do propagate

class Propagating(Baseline):
    """Stores `extension` edges; updating a topic rewrites the Date of every topic linked to it, in the given directions."""

    def __init__(self, directions=("B->A", "A->B")):
        super().__init__()
        self.edges = []
        self.directions = directions

    def _ingest(self, request):
        out = super()._ingest(request)
        owner = out["topic_id"]
        for e in request.get("edges") or []:
            self.edges.append({"from": owner, "to": e["to_topic_id"], "kind": e["kind"]})
        if request["placement"] == "version_field":
            for e in self.edges:
                backward = e["to"] == owner and "B->A" in self.directions   # B depends on A
                forward = e["from"] == owner and "A->B" in self.directions  # edge added to A
                dependent = e["from"] if backward else e["to"] if forward else None
                if dependent:
                    self._rows[dependent]["fields"]["Date"] = "revised"
        return out

    def _read_state(self):
        return {**super()._read_state(), "edges": list(self.edges)}


def test_a_system_that_revises_both_dependents_passes_c3_and_reports_a_measured_window():
    v = run("C3", Propagating())
    assert v.verdict == PASS
    (window,) = v.measurements["windows"]
    assert "unbounded" not in window["value"] and window["value"].startswith("median")


def test_a_system_that_revises_one_direction_is_partial_and_the_window_says_which_is_unbounded():
    v = run("C3", Propagating(directions=("B->A",)))
    assert v.verdict == PARTIAL
    (window,) = v.measurements["windows"]
    assert "unbounded for A->B" in window["value"]


def test_the_probe_refuses_to_call_absent_when_the_edge_was_never_stored():
    class DropsEdges(Baseline):
        def _read_state(self):
            return {**super()._read_state(), "edges": []}

    with pytest.raises(RuntimeError, match="setup failed"):
        run("C3", DropsEdges())


def test_an_event_and_a_salience_change_on_b_without_a_change_to_its_fields_is_not_propagation():
    class EventOnly(Baseline):
        """Adds an event and bumps salience on every topic when something is updated; fields stay as written."""

        updates = 0

        def _ingest(self, request):
            self.updates += request["placement"] == "version_field"
            return super()._ingest(request)

        def _read_topic(self, topic_id):
            topic = super()._read_topic(topic_id)
            if topic:
                topic["topic_history"] = [{"kind": "created"}] + [{"kind": "revision"}] * self.updates
                topic["salience"] = 1 + self.updates
            return topic

    v = run("C3", EventOnly())
    assert v.verdict == ABSENT


def test_the_wait_is_counted_from_the_update_not_from_the_end_of_the_read_after_it(monkeypatch):
    class SlowQuery(Baseline):
        def _query(self, request):
            time.sleep(0.3)
            return super()._query(request)

    monkeypatch.setattr(c3_propagation, "REVISION_WAIT_S", 0.6)
    v = run("C3", SlowQuery())
    assert v.verdict == ABSENT
    waits = [p["wait_s"] for p in v.probe_evidence["pairs"]]
    assert all(0.6 <= w < 0.85 for w in waits)  # 0.6 s from the update, not 0.3 s read + 0.6 s wait


def test_a_revision_that_arrives_late_is_still_seen_and_the_window_includes_the_delay(monkeypatch):
    class LateReviser(Propagating):
        """B's revision only becomes visible 0.4 s after the update."""

        visible_at = 0.0

        def _ingest(self, request):
            out = super()._ingest(request)
            if request["placement"] == "version_field":
                self.visible_at = time.perf_counter() + 0.4
            return out

        def _read_topic(self, topic_id):
            topic = super()._read_topic(topic_id)
            if topic and "Date" in topic["fields"] and time.perf_counter() < self.visible_at:
                topic["fields"]["Date"] = self._field("March 20")
            return topic

    monkeypatch.setattr(c3_propagation, "REVISION_WAIT_S", 2.0)
    v = run("C3", LateReviser())
    assert v.verdict == PASS
    waits = [p["wait_s"] for p in v.observations[0]["pairs"]]
    assert all(0.4 <= w < 1.0 for w in waits)
