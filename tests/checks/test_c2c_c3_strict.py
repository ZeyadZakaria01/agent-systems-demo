"""The stricter C3 and C2(c) checks (spec stories 22, 23, 64, 65), against in-process stand-ins.

`GemStandIn` is a versioned row with extension/association edges, one-hop revision flags and runtime policies; each
test switches one behaviour off or breaks it, and the verdict must follow. No MemState mock; the reference GEM tickets
are built against the same pass criteria (the check modules' docstrings).
"""

import pytest

from demo.checks import c3_propagation, discover
from demo.systems.adapter import Rejected, utc_now
from demo.systems.baseline import Baseline
from demo.verdict import ABSENT, FAIL, PARTIAL, PASS, Verdict

OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def run(row, system) -> Verdict:
    check = next(c for c in discover() if row in [r.id for r in c.rows])
    (verdict,) = check.execute(system)
    return verdict


@pytest.fixture(autouse=True)
def short_wait(monkeypatch):
    monkeypatch.setattr(c3_propagation, "REVISION_WAIT_S", 0.3)


class GemStandIn(Baseline):
    """Flags every topic linked to a written topic by an extension edge (either direction) with evidence; the flag
    clears when the flagged topic is written; policies added at runtime reject writes before anything is saved."""

    def __init__(
        self,
        *,
        flag_surface=True,
        flags=True,
        flag_association=False,
        flag_everything=False,
        evidence="full",
        clears=True,
        policies_enforced=True,
        reject_ordinary=False,
    ):
        super().__init__()
        self.edges, self.flagged, self.policies = [], {}, []
        self.flag_surface, self.flags, self.flag_association = flag_surface, flags, flag_association
        self.flag_everything, self.evidence, self.clears = flag_everything, evidence, clears
        self.policies_enforced, self.reject_ordinary = policies_enforced, reject_ordinary

    def _violates(self, request):
        values = {f["name"]: f["value"] for f in request.get("fields") or []}
        for p in self.policies:
            c = p["condition"]
            if (
                c["field"] in values
                and c["other_field"] in values
                and OPS[c["op"]](values[c["field"]], values[c["other_field"]])
            ):
                return p
        return None

    def _ingest(self, request):
        if self.policies_enforced and self._violates(request):
            raise Rejected(422, "policy violated")
        if (
            self.reject_ordinary
            and request.get("fields")
            and request["placement"] == "new_topic"
            and any(f["name"] == "Deadline" for f in request["fields"])
        ):
            raise Rejected(422, "rejects everything with a Deadline")
        out = super()._ingest(request)
        owner = out["topic_id"]
        for e in request.get("edges") or []:
            self.edges.append({"from": owner, "to": e["to_topic_id"], "kind": e["kind"]})
        if self.clears:
            self.flagged.pop(owner, None)
        if self.flags and request.get("fields"):
            for field in request["fields"]:
                for e in self.edges:
                    if owner not in (e["from"], e["to"]):
                        continue
                    if e["kind"] == "extension" or self.flag_association:
                        other = e["to"] if e["from"] == owner else e["from"]
                        self.flagged[other] = {
                            "source_topic_id": owner,
                            "updated_field": field["name"],
                            "timestamp": utc_now(),
                        }
            if self.flag_everything:
                for tid in self._rows:
                    if tid != owner:
                        self.flagged[tid] = {
                            "source_topic_id": owner,
                            "updated_field": request["fields"][0]["name"],
                            "timestamp": utc_now(),
                        }
        return out

    def _read_topic(self, topic_id):
        topic = super()._read_topic(topic_id)
        if topic and self.flag_surface:
            ev = self.flagged.get(topic_id)
            if ev and self.evidence == "none":
                ev = {}
            topic["revision_flag"] = {"flagged": ev is not None, "evidence": ev}
        return topic

    def _read_state(self):
        state = super()._read_state()
        for tid, t in state["topics"].items():
            if self.flag_surface:
                t["revision_flag"] = self._read_topic(tid)["revision_flag"]
        return {**state, "edges": list(self.edges)}

    def _add_policy(self, rule):
        self.policies.append(rule)
        return rule


# -- C3


def test_a_stand_in_that_flags_correctly_passes_c3_on_both_pairs():
    v = run("C3", GemStandIn())
    assert v.verdict == PASS
    assert len(v.cases) == 6 and all(c.held for c in v.cases)
    assert sum(c.control for c in v.cases) == 2
    (window,) = v.measurements["windows"]
    assert "unbounded" not in window["value"]


def test_a_stand_in_that_also_flags_association_linked_topics_does_not_pass_c3():
    v = run("C3", GemStandIn(flag_association=True))
    assert v.verdict == PARTIAL
    controls = [c for c in v.cases if c.control]
    assert [c.held for c in controls] == [False, False]


def test_a_stand_in_that_flags_every_other_topic_does_not_pass_c3():
    v = run("C3", GemStandIn(flag_everything=True))
    assert v.verdict != PASS
    assert [c.held for c in v.cases if c.control] == [False, False]


def test_a_stand_in_that_never_flags_and_never_propagates_is_absent_with_the_probe_as_evidence():
    for stand_in in (GemStandIn(flags=False), GemStandIn(flag_surface=False, flags=False)):
        v = run("C3", stand_in)
        assert v.verdict == ABSENT
        assert len(v.probe_evidence["pairs"]) == 2 and not any(p["reflected"] for p in v.probe_evidence["pairs"])
        assert v.measurements["windows"][0]["value"] == "unbounded (C3 absent)"


def test_a_system_that_changes_b_without_a_flag_fails_c3_and_its_control_is_not_scored():
    class RewritesDependents(GemStandIn):
        """Has a flag surface, never flags, and rewrites the topic linked to A by an extension edge instead."""

        def _ingest(self, request):
            out = super()._ingest(request)
            if request["placement"] == "version_field":
                for e in self.edges:
                    if e["kind"] == "extension" and out["topic_id"] in (e["from"], e["to"]):
                        other = e["to"] if e["from"] == out["topic_id"] else e["from"]
                        Baseline._ingest(
                            self,
                            {
                                "placement": "version_field",
                                "topic_id": other,
                                "fields": [{"name": "Date", "value": "April 25", "provenance": "propagated"}],
                            },
                        )
            return out

    v = run("C3", RewritesDependents(flags=False))
    assert v.verdict == FAIL, [(c.name, c.held) for c in v.cases]
    assert [c.held for c in v.cases if c.control] == [None, None]  # nothing was flagged: "not flagged" shows nothing


def test_a_flag_that_does_not_name_the_update_breaks_case_1():
    v = run("C3", GemStandIn(evidence="none"))
    assert v.verdict != PASS
    assert [c.held for c in v.cases[::3]] == [False, False]


def test_a_flag_that_never_clears_breaks_case_3():
    v = run("C3", GemStandIn(clears=False))
    assert v.verdict == PARTIAL
    assert [c.held for c in v.cases[2::3]] == [False, False]


def test_a_flag_is_raised_whichever_way_the_extension_edge_points():
    v = run("C3", GemStandIn())
    directions = [c.name.rsplit("(", 1)[1] for c in v.cases[::3]]
    assert directions == ["B->A)", "A->B)"] and all(c.held for c in v.cases[::3])


def test_the_versioned_row_reads_absent_on_both_rows():
    assert run("C3", Baseline()).verdict == ABSENT
    assert run("C2(c)", Baseline()).verdict == ABSENT


def test_no_flag_surface_reads_as_the_nothing_value_through_read_topic():
    s = Baseline()
    topic_id = s.ingest({"placement": "new_topic", "title": "X", "fields": []})["topic_id"]
    assert "revision_flag" in s.read_topic(topic_id) and s.read_topic(topic_id)["revision_flag"] is None
    assert s.read_state()["topics"][topic_id]["revision_flag"] is None
    assert s.add_policy({"name": "p"}) is None


# -- C2(c)


def test_a_policy_added_at_runtime_that_rejects_the_violating_write_passes_c2c():
    s = GemStandIn()
    v = run("C2(c)", s)
    assert v.verdict == PASS
    assert [c.held for c in v.cases] == [True, True] and v.cases[1].control
    assert s.policies and s.policies[0]["condition"] == {"field": "Deadline", "op": "<", "other_field": "Start"}
    assert "Policy Check Violating" not in s._rows and "Policy Check Ordinary" in s._rows


def test_a_stand_in_whose_runtime_policy_is_ignored_fails_c2c():
    v = run("C2(c)", GemStandIn(policies_enforced=False))
    assert v.verdict == FAIL
    assert v.cases[0].held is False and "accepted" in v.cases[0].observation


def test_a_rejected_write_that_changes_anything_else_in_the_stored_state_does_not_hold():
    class StoresAnEdgeThenRejects(GemStandIn):
        def _ingest(self, request):
            if self._violates(request):
                self.edges.append({"from": "a", "to": "b", "kind": "extension"})  # not a title or a current value
                raise Rejected(422, "policy violated (after a side effect)")
            return super()._ingest(request)

    v = run("C2(c)", StoresAnEdgeThenRejects())
    assert v.cases[0].held is False and "changed by the write" in v.cases[0].observation


def test_a_stand_in_that_rejects_the_ordinary_write_breaks_the_control():
    v = run("C2(c)", GemStandIn(reject_ordinary=True))
    assert v.verdict == PARTIAL
    assert v.cases[1].held is False and v.cases[1].control


def test_a_rejection_that_still_saves_something_does_not_hold():
    class SavesThenRejects(GemStandIn):
        def _ingest(self, request):
            if self._violates(request):
                Baseline._ingest(self, request)
                raise Rejected(422, "policy violated (too late)")
            return super()._ingest(request)

    v = run("C2(c)", SavesThenRejects())
    assert v.cases[0].held is False and v.verdict != PASS
