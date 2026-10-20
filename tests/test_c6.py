"""C6 clause 1 and clause 2, run in-process. The baseline tracks no salience, so both clauses fail with it unchanged;
`BumpingStore` (a Baseline subclass that reinforces and forgets) shows the passing path, the observations and the
check's own failure branches."""

from demo.baseline import Baseline
from demo.checks import discover
from demo.checks import c6_retrieval_adaptation as c6mod
from demo.verdict import FAIL, PARTIAL, PASS


def by_row(row):
    return next(c for c in discover() if [r.id for r in c.rows] == [row])


def run(system, row):
    (verdict,) = by_row(row).execute(system)
    return verdict


def observation(verdict, name):
    return next(o for o in verdict.observations if o["name"] == name)


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


class BumpingStore(Baseline):
    """A generic salience-tracking store, a second adapter implementation for exercising the check's branches. It
    models no MemState behaviour: it only has to be consistent with the check's own constants. Salience starts at the
    request's value (default 1.0), each returned topic gains `BUMP`, a field write sets it to 1.0 (unless
    `field_write_resets=False`), and an ingest that finds >= FORGET_GATE topics archives every topic below the
    threshold (`forgets=False` leaves the pass out). It overrides Baseline's private `_ingest`, `_query` and `_topic`,
    so it is coupled to those internals."""

    def __init__(self, forgets=True, field_write_resets=True):
        super().__init__()
        self.forgets = forgets
        self.field_write_resets = field_write_resets
        self.salience, self.archived = {}, {}

    def _ingest(self, request):
        response = super()._ingest(request)
        topic_id = response["topic_id"]
        if request["placement"] == "new_topic":
            self.salience[topic_id] = request.get("salience", 1.0)
            self.archived[topic_id] = False
        if request.get("fields") and self.field_write_resets:
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


def test_a_bumping_store_passes_clause_1_and_every_unrelated_candidate_rose():
    verdict = run(BumpingStore(), "C6-1")
    assert verdict.verdict == PASS
    over = observation(verdict, "over-reinforcement")
    assert over["unrelated_topics_that_rose"] == over["unrelated_topics"] == 3  # the top k is returned whatever the similarity
    target = over["per_topic"][over["target_topic_id"]]
    assert target["returned_in_retrievals"] == c6mod.RETRIEVALS_CLAUSE_1
    assert target["rise"] >= target["expected_min_rise"] - c6mod.EPS


def test_clause_1_fails_when_the_system_raises_less_than_the_retrievals_returned():
    class Weak(BumpingStore):
        def _query(self, request):
            response = Baseline._query(self, request)
            for c in response["candidates"]:
                self.salience[c["topic_id"]] += c6mod.BUMP / 10
            return response

    assert run(Weak(), "C6-1").verdict == FAIL


def test_a_bumping_store_passes_clause_2_after_the_forgetting_pass_ran():
    system = BumpingStore()
    verdict = run(system, "C6-2")
    assert verdict.verdict == PASS
    assert [c.held for c in verdict.cases] == [True, True]
    gate = observation(verdict, "forgetting pass")
    assert gate["ran"] is True and gate["control"]["archived"] is True and gate["target"]["archived"] is False
    assert gate["topics_after"] > c6mod.FORGET_GATE
    trajectory = observation(verdict, "salience trajectory")
    assert trajectory["start"] == c6mod.START_SALIENCE
    assert trajectory["after_each_retrieval"][-1] >= c6mod.FORGET_THRESHOLD
    assert gate["control"]["salience"] == c6mod.CONTROL_SALIENCE  # never returned, so never bumped
    assert observation(verdict, "salience durability")["reset"] is True


def test_clause_2_is_partial_when_the_control_shows_no_forgetting_pass_ran(monkeypatch):
    monkeypatch.setattr(c6mod, "ARCHIVE_WAIT_S", 0.2)
    verdict = run(BumpingStore(forgets=False), "C6-2")
    assert verdict.verdict == PARTIAL  # reinforcement held, forgetting not demonstrated
    assert [c.held for c in verdict.cases] == [True, False]
    assert observation(verdict, "forgetting pass")["control"]["archived"] is False


def test_clause_1_fails_when_only_unrelated_topics_were_returned():
    class MissesTarget(BumpingStore):
        def _query(self, request):
            response = Baseline._query(self, request)
            response["candidates"] = [c for c in response["candidates"] if c["topic_id"] != c6mod.TARGET[0]]
            for c in response["candidates"]:
                self.salience[c["topic_id"]] += c6mod.BUMP
            return response

    verdict = run(MissesTarget(), "C6-1")
    assert verdict.verdict == FAIL
    assert observation(verdict, "over-reinforcement")["per_topic"]["Marathon Training"]["returned_in_retrievals"] == 0


def test_durability_compares_with_the_salience_after_the_forgetting_pass():
    class DecaysInThePass(BumpingStore):
        """The forgetting pass lowers every salience by 0.01 once; a field write then leaves salience alone."""

        decayed = False

        def _ingest(self, request):
            response = super()._ingest(request)
            if not self.decayed and len(self._rows) >= c6mod.FORGET_GATE:
                self.decayed = True
                for t in self.salience:
                    self.salience[t] -= 0.01
            return response

    verdict = run(DecaysInThePass(field_write_resets=False), "C6-2")
    durability = observation(verdict, "salience durability")
    assert durability["after_field_write"] == durability["before_field_write"]
    assert durability["reset"] is False
