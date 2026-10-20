"""The Website Redesign storyline: its shape, the triage check on the baseline, the printed tables, the review draft."""

import json
from contextlib import contextmanager
from datetime import date

import pytest

from demo.baseline import Baseline
from demo.checks import discover
from demo.run import run_recorded
from demo.storyline import (ABILITIES, KNOWLEDGE_UPDATE, WEBSITE_REDESIGN, Edge, Event, Question, Storyline, Write)
from demo.storyline_draft import DRAFT_PATH
from demo.storyline_tables import PRECISION_NOTE, render_storyline
from demo.systems import SystemSpec


def triage_check():
    return next(c for c in discover() if c.id == "Storyline")


def test_the_storyline_has_20_to_30_events_and_10_to_15_labelled_questions():
    story = WEBSITE_REDESIGN
    assert 20 <= len(story.events) <= 30
    assert 10 <= len(story.questions) <= 15
    assert all(e.placement in ("new_topic", "extend_topic", "version_field") for e in story.events)
    assert all(q.ability in ABILITIES and q.truth and q.topic in story.titles for q in story.questions)
    # the paper's example: Alice, a vendor delay, a deadline that changes, dependent topics
    last = story.expected_after(story.events[-1].id)
    assert last["redesign"].fields["Deadline"] == "April 20"
    assert ("redesign", "extension") in last["alice"].edges and ("redesign", "extension") in last["milestones"].edges


def test_a_ground_truth_that_is_not_the_stored_end_state_is_rejected():
    event = Event("E1", "t", "said", "new_topic", "a", title="A", writes=(Write("F", "x", "p"),))
    with pytest.raises(ValueError, match="ground truth"):
        Storyline((event,), (Question("Q1", "q", KNOWLEDGE_UPDATE, "a", "F", "y"),))


def test_a_storyline_cannot_reuse_a_title_or_write_a_topic_before_it_exists():
    def new(n, key, title):
        return Event(f"E{n}", "t", "s", "new_topic", key, title=title)
    with pytest.raises(ValueError, match="already used"):
        Storyline((new(1, "a", "Same"), new(2, "b", "Same")), ())
    with pytest.raises(ValueError, match="before it is created"):
        Storyline((Event("E1", "t", "s", "extend_topic", "a", writes=(Write("F", "x", "p"),)),), ())
    with pytest.raises(ValueError, match="does not exist yet"):
        Storyline((Event("E1", "t", "s", "new_topic", "a", title="A", edges=(Edge("zzz", "extension"),)),), ())


def test_the_storyline_runs_on_the_baseline_and_every_question_is_triaged():
    (verdict,) = triage_check().execute(Baseline())
    m = verdict.measurements["storyline"]
    t = m["triage"]
    assert t["questions"] == len(WEBSITE_REDESIGN.questions)
    assert t["correct"] + t["search_failures"] + t["memory_failures"] == t["questions"]
    assert m["top_k"] == 10  # the baseline's own query
    assert m["events"]["mismatches"] == []  # last write wins: every event leaves the expected current values
    assert m["reinforcement"] is None  # no salience on the baseline
    assert {c.held for c in verdict.cases} <= {True, False}
    assert len(verdict.cases) == len(WEBSITE_REDESIGN.questions)


def _inproc(system_id):
    @contextmanager
    def open_fn(tag_id, run):
        yield Baseline()
    return SystemSpec(system_id, system_id, open_fn)


def test_the_run_output_prints_triage_counts_and_reinforcement_precision_but_no_scorecard_row(tmp_path):
    registry = {s: _inproc(s) for s in ("upstream", "baseline")}
    result = run_recorded(systems=["upstream", "baseline"], checks=[triage_check()], results_root=tmp_path,
                          command="python -m demo.run test", run_day=date(2026, 10, 20), registry=registry,
                          runtime_root=tmp_path / "runtime")
    out = result.scorecard
    assert "### Storyline: search failures vs memory failures" in out
    assert "Search failures" in out and "Memory failures" in out
    assert "### Reinforcement precision (beside C6 clause 1; no verdict)" in out
    assert "n/a" in out  # in-process baseline has no salience, so reinforcement precision is not applicable
    assert "Precision@k" in out and PRECISION_NOTE in out
    assert "| Storyline" not in out.split("### Storyline")[0]  # not a scorecard row
    assert "change table" not in out  # Storyline is off the scorecard, so no empty per-step table
    results = json.loads((result.dir / "results.json").read_text())
    assert results["change_table"]["measured"] == []
    assert render_storyline([]) == ""


def test_the_committed_review_draft_names_every_event_and_question():
    text = DRAFT_PATH.read_text()
    for event in WEBSITE_REDESIGN.events:
        assert event.id in text, event.id
    for question in WEBSITE_REDESIGN.questions:
        assert question.id in text, question.id
    assert "Complete" in text and "Website Redesign Phase 2" in text
