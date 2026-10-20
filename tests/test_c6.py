"""C6 clause 1 and clause 2, run in-process. The baseline tracks no salience, so both clauses fail with it unchanged;
a conforming stand-in (a Baseline subclass that reinforces and forgets) shows the passing path and the observations."""

from demo.baseline import Baseline
from demo.checks import discover
from demo.checks import c6_retrieval_adaptation as c6mod
from demo.verdict import FAIL, NOT_SCORED, PASS


def by_row(row):
    return next(c for c in discover() if [r.id for r in c.rows] == [row])


def run(system, row):
    (verdict,) = by_row(row).execute(system)
    return verdict


def observation(verdict, name):
    return next(o for o in verdict.observations if o["name"] == name)


def test_each_clause_is_its_own_row_that_quotes_the_clause_wording():
    (r1,) = by_row("C6-1").rows
    (r2,) = by_row("C6-2").rows
    assert "Every retrieval that accesses u_i induces a transition in which the salience of u_i is updated" in r1.claim
    assert "Repeated retrieval strictly reduces u_i's eligibility for attenuation" in r2.claim


def test_clause_1_fails_on_the_baseline_with_salience_unchanged():
    verdict = run(Baseline(), "C6-1")
    assert verdict.verdict == FAIL
    assert [c.held for c in verdict.cases] == [False]
    over = observation(verdict, "over-reinforcement")
    assert all(t["start"] is None and t["end"] is None and t["rise"] is None for t in over["per_topic"].values())
    assert over["unrelated_topics_that_rose"] == 0


def test_clause_2_fails_on_the_baseline_with_salience_unchanged():
    verdict = run(Baseline(), "C6-2")
    assert verdict.verdict == FAIL
    assert [c.held for c in verdict.cases] == [False, False]
    assert observation(verdict, "salience trajectory")["after_each_retrieval"] == []
    assert observation(verdict, "forgetting pass")["ran"] is False
    durability = observation(verdict, "salience durability")
    assert durability["reset"] is None and durability["after_field_write"] is None


class Conforming(Baseline):
    """A stand-in that satisfies both clauses: salience starts at the request's value (default 1.0), each returned
    topic gains `BUMP`, a field write sets it to 1.0, and an ingest that finds >= FORGET_GATE topics archives every
    topic below the threshold (`forgets=False` leaves the pass out)."""

    def __init__(self, forgets=True):
        super().__init__()
        self.forgets = forgets
        self.salience, self.archived = {}, {}

    def _ingest(self, request):
        response = super()._ingest(request)
        topic_id = response["topic_id"]
        if request["placement"] == "new_topic":
            self.salience[topic_id] = request.get("salience", 1.0)
            self.archived[topic_id] = False
        if request.get("fields"):
            self.salience[topic_id] = 1.0
        if self.forgets and len(self._rows) >= c6mod.FORGET_GATE:
            for t, s in self.salience.items():
                if s < c6mod.FORGET_THRESHOLD:
                    self.archived[t] = True
        return response

    def _query(self, request):
        response = super()._query(request)
        for c in response["candidates"]:
            self.salience[c["topic_id"]] += c6mod.BUMP
        return response

    def _topic(self, row):
        topic = super()._topic(row)
        topic["salience"] = self.salience[row["title"]]
        topic["archived"] = self.archived[row["title"]]
        return topic


def test_a_conforming_system_passes_clause_1_and_every_unrelated_candidate_rose():
    verdict = run(Conforming(), "C6-1")
    assert verdict.verdict == PASS
    over = observation(verdict, "over-reinforcement")
    assert over["unrelated_topics_that_rose"] == over["unrelated_topics"] == 3  # the top k is returned whatever the similarity
    target = over["per_topic"][over["target_topic_id"]]
    assert target["returned_in_retrievals"] == c6mod.RETRIEVALS_CLAUSE_1
    assert target["rise"] >= target["expected_min_rise"] - c6mod.EPS


def test_clause_1_fails_when_the_system_raises_less_than_the_retrievals_returned():
    class Weak(Conforming):
        def _query(self, request):
            response = Baseline._query(self, request)
            for c in response["candidates"]:
                self.salience[c["topic_id"]] += c6mod.BUMP / 10
            return response

    assert run(Weak(), "C6-1").verdict == FAIL


def test_a_conforming_system_passes_clause_2_after_the_forgetting_pass_ran():
    system = Conforming()
    verdict = run(system, "C6-2")
    assert verdict.verdict == PASS
    assert [c.held for c in verdict.cases] == [True, True]
    gate = observation(verdict, "forgetting pass")
    assert gate["ran"] is True and gate["control"]["archived"] is True and gate["target"]["archived"] is False
    assert gate["topics_after"] > c6mod.FORGET_GATE
    trajectory = observation(verdict, "salience trajectory")
    assert trajectory["start"] == c6mod.START_SALIENCE
    assert trajectory["after_each_retrieval"][-1] >= c6mod.FORGET_THRESHOLD
    # only the target was ever returned: the control was never read
    assert observation(verdict, "salience durability")["reset"] is True


def test_clause_2_is_not_scored_when_the_control_shows_no_forgetting_pass_ran(monkeypatch):
    monkeypatch.setattr(c6mod, "ARCHIVE_WAIT_S", 0.2)
    verdict = run(Conforming(forgets=False), "C6-2")
    assert verdict.verdict == NOT_SCORED
    assert [c.held for c in verdict.cases] == [True, None]
    assert observation(verdict, "forgetting pass")["control"]["archived"] is False
