"""A model grades each chat turn beside the blind reviewer: it sees what a reviewer needs (the question, the
ground truth, and the answer or the stored entries), never the automatic match hints or the reviewer's grade, and
its grade is stored under `model_grade` with the exact model id, leaving `reviewer_grade` untouched."""

import copy
import json

import pytest

from demo.chat.model_grade import GradeError, grade_recording, grading_prompt, parse_grade
from demo.chat.recording import render_turn

REVIEW = {"grade": "incorrect", "note": "REVIEWER-SECRET", "grader": "rev-1", "graded_at": "t"}
BAD_MERGE_TURN = {
    "question": "Q02",
    "ability": "knowledge update",
    "text": "What is the deadline of the Website Redesign?",
    "ground_truth": "April 20",
    "answer": "The deadline is April 20th.",
    "answer_contains_ground_truth": False,
    "route": {"intent": "query", "intent_source": "classifier", "tool_calls": ["memory_graph_snapshot"]},
    "latency_ms": 2535.0,
    "model": "qwen3.5:2b",
    "provider": "ollama",
    "state_violation": {"field": "Deadline", "lost_entries": ["March 15 (kickoff-notes)"]},
    "topic_changed_by_turn": False,
    "reviewer_grade": REVIEW,
}
W1_TURN = {
    "question": "W1",
    "ability": "temporal reasoning",
    "text": "I started my new job two weeks ago",
    "graded_on": "the stored start date",
    "reference_time": "2026-10-07T00:00:00+00:00",
    "ground_truth": "2026-09-23 (two weeks before the reference time 2026-10-07), +- 1 day",
    "answer": "What details would you like me to store?",
    "route": {"intent": "query", "intent_source": "classifier", "tool_calls": ["memory_list_topics"]},
    "latency_ms": 3616.0,
    "model": "qwen3.5:2b",
    "provider": "ollama",
    "written": [
        {
            "title": "New Job",
            "topic_id": "t1",
            "field": "job_start_date",
            "value": "2026-09-23",
            "provenance": "llm",
            "valid_from": "2026-10-07T00:00:00+00:00",
        }
    ],
    "topics_created": [],
    "reviewer_grade": REVIEW,
    "stored_start_date": {"candidates": [], "within_tolerance": True, "tolerance_days": 1, "truth": "2026-09-23"},
}


def test_the_prompt_carries_what_the_person_grades():
    prompt = grading_prompt(BAD_MERGE_TURN)
    for part in (
        "What is the deadline of the Website Redesign?",
        "April 20",
        "The deadline is April 20th.",
        "the answer",
    ):
        assert part in prompt


def test_the_prompt_leaves_out_hints_the_reviewer_grade_and_the_state_evidence():
    prompt = grading_prompt(BAD_MERGE_TURN)
    for hidden in (
        "answer_contains_ground_truth",
        "reviewer_grade",
        "REVIEWER-SECRET",
        "incorrect",
        "kickoff-notes",
        "state_violation",
    ):
        assert hidden not in prompt


def test_a_turn_graded_on_the_stored_start_date_shows_the_stored_entries_and_the_reference_time():
    prompt = grading_prompt(W1_TURN)
    assert "the stored start date" in prompt
    assert "job_start_date" in prompt and "2026-09-23" in prompt and "2026-10-07" in prompt
    assert "within_tolerance" not in prompt


def test_parse_grade_reads_json_even_inside_a_code_fence():
    assert parse_grade('```json\n{"grade": "correct", "note": "says April 20"}\n```') == {
        "grade": "correct",
        "note": "says April 20",
    }


@pytest.mark.parametrize("reply", ['{"grade": "great", "note": "x"}', "not json", '{"note": "x"}'])
def test_parse_grade_refuses_anything_but_the_three_grades(reply):
    with pytest.raises(GradeError):
        parse_grade(reply)


def recording_file(tmp_path, turns):
    path = tmp_path / "rec.json"
    path.write_text(json.dumps({"schema": 1, "case": "bad-merge", "turns": turns}))
    return path


def stub(grade="correct"):
    seen = []

    def ask(system, prompt):
        seen.append(prompt)
        return json.dumps({"grade": grade, "note": "stub note"}), "claude-sonnet-test"

    ask.seen = seen
    return ask


def test_grading_a_recording_fills_model_grade_on_every_turn_and_leaves_the_reviewer_grade(tmp_path):
    path = recording_file(tmp_path, [copy.deepcopy(BAD_MERGE_TURN), copy.deepcopy(W1_TURN)])
    ask = stub()
    grade_recording(path, ask)
    turns = json.loads(path.read_text())["turns"]
    assert len(ask.seen) == 2
    for turn in turns:
        assert turn["reviewer_grade"] == REVIEW
        assert turn["model_grade"]["grade"] == "correct"
        assert turn["model_grade"]["note"] == "stub note"
        assert turn["model_grade"]["grader"] == "claude-sonnet-test"
        assert turn["model_grade"]["graded_at"]


def test_a_recording_already_model_graded_is_left_alone_unless_forced(tmp_path):
    path = recording_file(tmp_path, [copy.deepcopy(BAD_MERGE_TURN)])
    grade_recording(path, stub("correct"))
    with pytest.raises(GradeError):
        grade_recording(path, stub("incorrect"))
    grade_recording(path, stub("incorrect"), force=True)
    assert json.loads(path.read_text())["turns"][0]["model_grade"]["grade"] == "incorrect"


def plain_turn():
    turn = copy.deepcopy(BAD_MERGE_TURN)
    del turn["state_violation"]
    return turn


def test_replay_shows_the_model_grade_and_the_reviewer_grade():
    turn = {
        **plain_turn(),
        "model_grade": {"grade": "correct", "note": "says April 20", "grader": "claude-sonnet-5-5", "graded_at": "x"},
        "reviewer_grade": {"grade": "incorrect", "note": "wrong", "grader": "rev-1", "graded_at": "y"},
    }
    lines = render_turn(turn, None)
    assert lines[-2:] == [
        "  - model grade (claude-sonnet-5-5): correct; note: says April 20",
        "  - reviewer grade (rev-1): incorrect; note: wrong",
    ]
    assert not any("hand" in line for line in lines)


def test_replay_of_an_ungraded_turn_prints_no_model_grade_line():
    assert not any("model grade" in line for line in render_turn(plain_turn(), None))


def test_tally_counts_each_grade_per_case_and_turn(tmp_path):
    from demo.chat.model_grade import tally

    for i, grade in enumerate(["correct", "incorrect", "correct"]):
        turn = {
            **copy.deepcopy(BAD_MERGE_TURN),
            "model_grade": {"grade": grade, "note": "", "grader": "m", "graded_at": "x"},
        }
        (tmp_path / f"r{i}.json").write_text(json.dumps({"schema": 1, "case": "bad-merge", "turns": [turn]}))
    (tmp_path / "ungraded.json").write_text(
        json.dumps({"schema": 1, "case": "bad-merge", "turns": [copy.deepcopy(BAD_MERGE_TURN)]})
    )
    assert tally(tmp_path) == {("bad-merge", "Q02"): {"correct": 2, "incorrect": 1, "ungraded": 1}}
