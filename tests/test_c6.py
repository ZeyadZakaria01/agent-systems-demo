"""C6 clause 1 and clause 2, run in-process. The baseline (versioned row) tracks no salience, so both clauses are absent, confirmed by the salience read;
`BumpingStore` (a Baseline subclass that reinforces and forgets) shows the passing path, the observations and the
check's own failure branches."""

from demo.baseline import Baseline
from demo.checks import discover
from demo.checks import c6_retrieval_adaptation as c6mod
from demo.verdict import ABSENT, FAIL, NOT_SCORED, PARTIAL, PASS


def by_row(row):
    return next(c for c in discover() if [r.id for r in c.rows] == [row])


def run(system, row):
    (verdict,) = by_row(row).execute(system)
    return verdict


def observation(verdict, name):
    return next(o for o in verdict.observations if o["name"] == name)


def test_clause_1_is_absent_on_the_baseline_because_salience_reads_none():
    verdict = run(Baseline(), "C6-1")
    assert verdict.verdict == ABSENT
    assert verdict.cases == []
    read = verdict.probe_evidence["salience_read"]
    assert len(read) == 4 and all(x is None for x in read.values())  # every topic written read back without salience


def test_clause_2_is_absent_on_the_baseline_because_salience_reads_none():
    verdict = run(Baseline(), "C6-2")
    assert verdict.verdict == ABSENT
    assert verdict.cases == []
    assert list(verdict.probe_evidence["salience_read"].values()) == [None, None]


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


def test_clause_2_is_not_scored_when_no_forgetting_pass_ran(monkeypatch):
    monkeypatch.setattr(c6mod, "ARCHIVE_WAIT_S", 0.2)
    verdict = run(BumpingStore(forgets=False), "C6-2")
    assert verdict.verdict == NOT_SCORED  # forgetting is C5's failure, not C6's: never partial
    assert [c.held for c in verdict.cases] == [True, None]
    assert observation(verdict, "forgetting pass")["control"]["archived"] is False
    assert observation(verdict, "forgetting was not shown to run")["summary"].startswith("forgetting was not shown to run")


def test_clause_2_stops_at_the_first_forgetting_pass_seen_during_the_reads():
    class ForgetsAtOnce(BumpingStore):
        """The pass runs on the first read: every topic below the threshold is archived by it (the control is)."""

        def _query(self, request):
            response = super()._query(request)
            for t, s in self.salience.items():
                if s < c6mod.FORGET_THRESHOLD:
                    self.archived[t] = True
            return response

    system = ForgetsAtOnce()
    verdict = run(system, "C6-2")
    assert verdict.verdict == PASS
    gate = observation(verdict, "forgetting pass")
    assert gate["first_pass_in_reads"] is True and gate["topics_after"] is None  # no filler was ingested
    assert gate["control"]["archived"] is True and gate["target"]["archived"] is False


def test_clause_2_fails_when_the_pass_archives_the_read_topic_too():
    class ArchivesEverything(BumpingStore):
        def _query(self, request):
            response = super()._query(request)
            for t in self.archived:
                self.archived[t] = True
            return response

    verdict = run(ArchivesEverything(), "C6-2")
    assert verdict.verdict == PARTIAL  # reinforcement lifted the topic, but the pass archived it anyway
    assert verdict.cases[-1].held is False


def test_an_as_of_read_raising_salience_is_a_clause_1_case():
    verdict = run(BumpingStore(), "C6-1")  # the baseline accepts recorded_at; BumpingStore bumps whatever it returns
    assert [c.held for c in verdict.cases] == [True, True]
    assert verdict.measurements["as_of"]["axis"] == "recorded_at"


def test_the_as_of_case_is_not_applicable_where_no_date_is_accepted():
    class NoDates(BumpingStore):
        def _describe(self):
            return {**super()._describe(), "accepts": {}}

    verdict = run(NoDates(), "C6-1")
    assert [c.held for c in verdict.cases] == [True, None]
    assert verdict.verdict == PASS  # the verdict rests on the cases that could run


def test_clause_1_fails_the_as_of_case_when_an_as_of_read_does_not_raise_salience():
    class AsOfDoesNotBump(BumpingStore):
        def _query(self, request):
            if request.get("recorded_at") or request.get("valid_at"):
                return Baseline._query(self, request)
            return super()._query(request)

    verdict = run(AsOfDoesNotBump(), "C6-1")
    assert [c.held for c in verdict.cases] == [True, False]
    assert verdict.verdict == PARTIAL


def test_clause_1_fails_when_only_unrelated_topics_were_returned():
    class MissesTarget(BumpingStore):
        def _query(self, request):
            response = Baseline._query(self, request)
            response["candidates"] = [c for c in response["candidates"] if c["topic_id"] != c6mod.TARGET[0]]
            for c in response["candidates"]:
                self.salience[c["topic_id"]] += c6mod.BUMP
            return response

    verdict = run(MissesTarget(), "C6-1")
    assert verdict.cases[0].held is False  # the plain-retrieval case; the as-of read still raises salience
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


def test_a_system_declaring_clause_2_seeds_is_seeded_with_them_not_with_the_checks_own():
    class Seeded(BumpingStore):
        def _describe(self):
            return {**super()._describe(), "c6_clause_2_seeds": {"target": 0.06, "control": 0.04}}

    verdict = run(Seeded(), "C6-2")
    assert observation(verdict, "salience trajectory")["start"] == 0.06
    assert observation(verdict, "forgetting pass")["control"]["start"] == 0.04
    assert verdict.cases[0].name.startswith("repeated retrieval keeps the topic at or above 0.05, from 0.06")
    assert verdict.verdict == PASS
