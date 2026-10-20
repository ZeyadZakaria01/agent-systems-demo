"""Storyline triage and reinforcement precision, in-process on the baseline (the versioned row). Seam: the system adapter.

MemState verdicts are never pinned here; they come from recorded runs. The systems below that report salience or
edges are generic System subclasses of the baseline, not mocks of MemState.
"""

from demo.baseline import Baseline
from demo.storyline import KNOWLEDGE_UPDATE, Edge, Event, Question, Storyline, Write
from demo.triage import CORRECT, MEMORY_FAILURE, SEARCH_FAILURE, QuestionOutcome, _reinforcement, run_storyline


def topic(n: int, key: str, title: str, summary: str, name: str, value: str) -> Event:
    return Event(f"E{n:02d}", "t", f"said {key}", "new_topic", key, title=title, summary=summary,
                 writes=(Write(name, value, "test"),))


def crowded_storyline() -> Storyline:
    """Twelve topics that look like the question and one that does not: the labelled one falls outside the top 8."""
    distractors = tuple(topic(i, f"d{i}", f"Budget review meeting agenda item {i}",
                              "Agenda for the quarterly budget review meeting", "Owner", f"person {i}")
                        for i in range(1, 13))
    garden = topic(13, "garden", "Garden irrigation valves", "Watering schedule for the back garden", "Valve", "north")
    return Storyline(
        events=(*distractors, garden),
        questions=(Question("Q1", "What is on the budget review meeting agenda?", KNOWLEDGE_UPDATE, "garden", "Valve",
                            "north"),))


def test_a_baseline_wrong_answer_is_a_search_failure_when_the_labelled_topic_falls_outside_the_top_8():
    run = run_storyline(Baseline(), crowded_storyline())
    (outcome,) = run.outcomes
    assert outcome.outcome == SEARCH_FAILURE
    assert outcome.returned is False and len(outcome.returned_ids) == 8  # the versioned row's top-8 query
    assert run.triage == {"questions": 1, "correct": 0, "search_failures": 1, "memory_failures": 0}


def test_a_returned_labelled_topic_with_the_ground_truth_current_is_correct():
    story = crowded_storyline()
    only_garden = Storyline(events=(story.events[-1],), questions=story.questions)
    run = run_storyline(Baseline(), only_garden)
    assert [o.outcome for o in run.outcomes] == [CORRECT]
    assert run.outcomes[0].stored == "north"


class LosesUpdates(Baseline):
    """A system that returns the right topic but never applies a `version_field`: stale value current."""

    def _ingest(self, request):
        if request["placement"] == "version_field":
            return {"topic_id": request["topic_id"], "applied": [], "version_ids": {}, "similar_topic_ids": []}
        return super()._ingest(request)


def test_a_returned_labelled_topic_with_the_wrong_stored_value_is_a_memory_failure():
    events = (
        topic(1, "redesign", "Website Redesign", "Project to redesign the company website", "Deadline", "March 15"),
        Event("E02", "t", "moved", "version_field", "redesign", writes=(Write("Deadline", "April 20", "test"),)),
    )
    story = Storyline(events=events, questions=(
        Question("Q1", "What is the deadline of the Website Redesign?", KNOWLEDGE_UPDATE, "redesign", "Deadline",
                 "April 20"),))
    run = run_storyline(LosesUpdates(), story)
    (outcome,) = run.outcomes
    assert (outcome.outcome, outcome.returned, outcome.stored) == (MEMORY_FAILURE, True, "March 15")
    assert run.triage["memory_failures"] == 1
    # the write path is reported apart: the stored state after E02 is not what the event should have left
    assert [e.matched for e in run.events] == [True, False]


class BumpsReturnedTopics(Baseline):
    """A generic System subclass: the baseline plus a salience that every returned topic gains 0.1 on. It models no
    MemState behaviour; it only gives the triage code a system that reports salience."""

    def __init__(self):
        super().__init__("baseline with salience")
        self.salience: dict[str, float] = {}

    def _read_topic(self, topic_id):
        topic = super()._read_topic(topic_id)
        if topic is not None:
            topic["salience"] = self.salience.get(topic_id, 1.0)
        return topic

    def _query(self, request):
        response = super()._query(request)
        for cand in response["candidates"]:
            self.salience[cand["topic_id"]] = self.salience.get(cand["topic_id"], 1.0) + 0.1
        return response


def three_topics_two_questions() -> Storyline:
    events = (
        topic(1, "a", "Website Redesign", "Project to redesign the company website", "Deadline", "April 20"),
        topic(2, "b", "Weekly Sync Meeting", "Recurring weekly team meeting", "Time", "11:30"),
        topic(3, "c", "Lunch Preferences", "What the team eats for lunch", "Cuisine", "Thai"),
    )
    return Storyline(events=events, questions=(
        Question("Q1", "What is the deadline of the Website Redesign?", KNOWLEDGE_UPDATE, "a", "Deadline", "April 20"),
        Question("Q2", "What time is the weekly sync meeting?", KNOWLEDGE_UPDATE, "b", "Time", "11:30")))


def test_reinforcement_precision_is_labelled_increments_over_all_increments_and_equals_precision_at_k():
    run = run_storyline(BumpsReturnedTopics(), three_topics_two_questions())
    r = run.reinforcement
    # each question returns all three topics (+0.1 each); only the labelled one of each question counts: 0.2 / 0.6
    assert (r.labelled_increments, r.all_increments) == (0.2, 0.6)
    assert abs(r.precision - 1 / 3) < 1e-9
    assert (r.questions_bumped, r.questions) == (2, 2)
    assert r.matches_precision_at_k is True and abs(r.precision_at_k - 1 / 3) < 1e-9


def test_a_labelled_topic_that_is_not_returned_is_not_bumped_so_precision_is_zero():
    run = run_storyline(BumpsReturnedTopics(), crowded_storyline())
    r = run.reinforcement
    assert (r.labelled_increments, r.questions_bumped) == (0.0, 0)
    assert abs(r.all_increments - 0.8) < 1e-9 and r.precision == 0.0  # eight returned topics, +0.1 each


def test_reinforcement_precision_is_not_applicable_on_the_baseline():
    run = run_storyline(Baseline(), three_topics_two_questions())
    assert run.reinforcement is None
    assert all(o.increments_labelled is None for o in run.outcomes)


def outcome(question, labelled, every, returned):
    return QuestionOutcome(question, "knowledge update", "q", "t", "a", "id-a", CORRECT, returned, 1 if returned else None,
                           ["id-a", "id-b"], "t", labelled, every)


def test_reinforcement_precision_is_the_summed_labelled_over_the_summed_all_increments():
    r = _reinforcement([outcome("Q1", 0.1, 0.2, True), outcome("Q2", 0.0, 0.2, False)])
    assert (r.labelled_increments, r.all_increments, r.questions_bumped, r.questions) == (0.1, 0.4, 1, 2)
    assert abs(r.precision - 0.25) < 1e-9
    assert abs(r.precision_at_k - 0.25) < 1e-9 and r.matches_precision_at_k is True  # 1 labelled of 4 returned
    assert _reinforcement([outcome("Q1", None, None, True)]) is None  # no salience: not applicable
    assert _reinforcement([outcome("Q1", 0.0, 0.0, False)]).precision is None  # nothing was bumped


def linked_storyline() -> Storyline:
    a = topic(1, "a", "Website Redesign", "Project to redesign the company website", "Deadline", "April 20")
    b = Event("E02", "t", "said b", "new_topic", "b", title="Redesign Milestones",
              summary="Dated milestones that depend on the deadline", writes=(Write("Launch", "April 20", "test"),),
              edges=(Edge("a", "extension"),))
    return Storyline(events=(a, b), questions=())


class ListsEdges(Baseline):
    """A generic System subclass: the baseline plus an edge list in `read_state`, in the adapter's edge shape;
    `keep=False` drops them. It models no MemState behaviour."""

    def __init__(self, keep: bool):
        super().__init__("baseline with edges")
        self.keep, self.edges = keep, []

    def _ingest(self, request):
        response = super()._ingest(request)
        for e in request.get("edges") or []:
            self.edges.append({"from": response["topic_id"], "to": e["to_topic_id"], "kind": e["kind"],
                               "edge_type": "related"})
        return response

    def _read_state(self):
        return {**super()._read_state(), "edges": list(self.edges) if self.keep else []}


def test_edges_are_compared_where_the_system_reports_them_and_a_missing_edge_is_a_write_path_finding():
    kept = run_storyline(ListsEdges(keep=True), linked_storyline())
    assert [(e.edges_declared, e.edges_compared, e.matched) for e in kept.events] == [(False, False, True),
                                                                                    (True, True, True)]
    lost = run_storyline(ListsEdges(keep=False), linked_storyline())
    assert lost.events[1].matched is False and "edges" in lost.events[1].observation


def test_edges_are_not_applicable_on_the_baseline_and_do_not_count_as_a_mismatch():
    run = run_storyline(Baseline(), linked_storyline())
    assert [(e.edges_declared, e.edges_compared, e.matched) for e in run.events] == [(False, False, True),
                                                                                   (True, False, True)]
    assert run.to_measurements()["storyline"]["events"]["edges_compared"] == 0


def test_a_stored_title_that_differs_from_the_storyline_is_a_write_path_finding():
    class Renames(Baseline):
        def _read_topic(self, topic_id):
            topic = super()._read_topic(topic_id)
            topic["title"] = "Something else"
            return topic

    run = run_storyline(Renames(), linked_storyline())
    assert not any(e.matched for e in run.events) and "title" in run.events[0].observation
