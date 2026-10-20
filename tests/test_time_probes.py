"""Time probes: the story shift (pure), request construction, and the rows on the baseline in-process.
No MemState mock and no MemState verdict is pinned: the dated paths are proven by the patch smoke runs (tickets 12/13)."""

from contextlib import nullcontext
from datetime import date

import pytest

from demo.baseline import Baseline
from demo.checks import discover
from demo.reads import NO_VALUE, current_value, field_in_response
from demo.session import Session
from demo.time_stories import (AS_OF, LAPSED_OVERRIDE_1, STORIES, history_intact, ingest_request, iso, query_request,
                               shift_story)
from demo.verdict import ABSENT, FAIL

RUN_DAY = date(2026, 10, 20)


def time_check():
    return next(c for c in discover() if "T1" in [r.id for r in c.rows])


@pytest.fixture(scope="module")
def baseline_run():
    """One run of the check on the baseline (it includes the as-of probe's 1 s pause): verdicts by row, and the
    tags of the fresh systems it opened."""
    session = Session(lambda tag: nullcontext(Baseline()), capture=lambda system, tag, a, b: {"tag": tag})
    out = {v.row: v for v in time_check().execute(session, run_day=RUN_DAY)}
    return out, [c["tag"] for c in session.captured]


def test_the_shift_puts_today_on_the_run_day_and_keeps_every_gap():
    shifted = shift_story(LAPSED_OVERRIDE_1, RUN_DAY)
    assert shifted.today == RUN_DAY
    assert [w.valid_from for w in shifted.writes][0] == date(2026, 8, 16)  # spec: Sep 1 -> Aug 16
    assert shifted.writes[1].valid_from == date(2026, 9, 15) and shifted.writes[1].invalid_at == date(2026, 10, 16)
    for story in STORIES:
        moved = shift_story(story, RUN_DAY)
        assert moved.today == RUN_DAY
        original = [d for w in story.writes for d in (w.valid_from, w.invalid_at) if d] + [a.when for a in story.asks if a.when]
        after = [d for w in moved.writes for d in (w.valid_from, w.invalid_at) if d] + [a.when for a in moved.asks if a.when]
        assert [(d - story.today) for d in original] == [(d - RUN_DAY) for d in after]


def test_the_shifted_today_is_the_run_day_on_any_run_day():
    assert shift_story(LAPSED_OVERRIDE_1, date(2027, 3, 1)).asks[1].when == date(2027, 3, 1)


def test_writes_carry_dates_only_for_a_system_that_accepts_them_and_asks_stay_plain_otherwise():
    story = shift_story(LAPSED_OVERRIDE_1, RUN_DAY)
    plain = ingest_request(story, 1, "t", dated=False)
    dated = ingest_request(story, 1, "t", dated=True)
    assert "valid_from" not in plain["fields"][0] and "invalid_at" not in plain["fields"][0]
    assert dated["fields"][0]["valid_from"] == iso(date(2026, 9, 15))
    assert dated["fields"][0]["invalid_at"] == iso(date(2026, 10, 16))
    assert {k: v for k, v in dated["fields"][0].items() if k not in ("valid_from", "invalid_at")} == plain["fields"][0]
    oct15, today = story.asks
    assert query_request(oct15, "t", send_valid=False) == query_request(today, "t", send_valid=True) == \
        query_request(today, "t", send_valid=False)  # one plain read for every date; "today" never carries a date
    assert query_request(oct15, "t", send_valid=True)["valid_at"] == iso(date(2026, 9, 29))


def test_the_recorded_question_uses_the_noted_moment():
    asked = shift_story(AS_OF, RUN_DAY).asks[1]
    assert query_request(asked, "t", True, True, recorded_at="2026-10-20T10:00:00+00:00")["recorded_at"] == \
        "2026-10-20T10:00:00+00:00"
    assert "recorded_at" not in query_request(asked, "t", True, False, recorded_at="2026-10-20T10:00:00+00:00")


def test_history_intact_requires_every_value_and_a_copy_for_each_expired_entry():
    story = AS_OF
    intact = {"history": [
        {"id": "3", "value": "April 20", "valid_from": "x", "operation": "interval_corrected", "replaces_entry_id": "1"},
        {"id": "2", "value": "May 1"},
        {"id": "1", "value": "April 20", "expired_at": "t"}]}
    assert history_intact(story, intact)[0] is True
    no_copy = {"history": [{"id": "2", "value": "May 1"}, {"id": "1", "value": "April 20", "expired_at": "t"}]}
    assert history_intact(story, no_copy)[0] is False
    lost = {"history": [{"id": "2", "value": "May 1"}]}
    assert "April 20" in history_intact(story, lost)[1]
    assert history_intact(story, {"history": None})[0] is False


def test_the_baseline_gets_the_table_s_upstream_expected_answer_for_every_asked_date():
    # last write wins, same plain read for every date: the "upstream expected" column of the spec's table
    for story in STORIES:
        s = Baseline()
        topic_id = None
        for i in range(len(story.writes)):
            topic_id = s.ingest(ingest_request(story, i, topic_id, dated=False))["topic_id"]
        for ask in story.asks:
            got = current_value(field_in_response(s.query(query_request(ask, topic_id, True, True, "now")), topic_id, story.field))
            assert got == ask.recency, (story.id, ask.label)


def test_the_baseline_fails_five_time_probes_with_the_wrong_date_observed_and_is_absent_on_as_of(baseline_run):
    v, _ = baseline_run
    assert sorted(v) == ["T1", "T2", "T3", "T4", "T5", "T6"]
    for row in ("T1", "T2", "T3", "T4", "T6"):
        assert v[row].verdict == FAIL, row
        assert any(c.held is False and "got" in c.observation for c in v[row].cases), row
    assert v["T1"].cases[0].observation.endswith("got 'March 1', correct 'April 20'")
    assert v["T6"].cases[0].observation.count("NO_VALUE") == 1
    assert v["T5"].verdict == ABSENT
    asked = v["T5"].probe_evidence["asked"]
    assert asked[0]["answer"] == asked[1]["answer"] == "May 1"
    assert "valid_at" in asked[0]["request"] and "recorded_at" in asked[1]["request"]  # the dates were sent and ignored


def test_the_control_date_of_each_probe_is_flagged_and_the_baseline_shows_no_over_blocking(baseline_run):
    v, _ = baseline_run
    for row in ("T1", "T2", "T3", "T4", "T5", "T6"):
        if v[row].verdict != ABSENT:
            assert sum(c.control for c in v[row].cases) >= 1, row
    # the baseline answers the plain read: only the asks upstream expects wrong fail, so no probe shows over-blocking
    assert all("over-blocking" not in v[r].observations for r in v)


def test_the_lapsed_override_row_passes_only_if_both_stories_pass(baseline_run):
    t4 = baseline_run[0]["T4"]
    names = [c.name for c in t4.cases]
    assert any(n.startswith("story 1") for n in names) and any(n.startswith("story 2") for n in names)
    story1 = [c for c in t4.cases if c.name.startswith("story 1")]
    story2 = [c for c in t4.cases if c.name.startswith("story 2")]
    # on the baseline story 1 fails (Nov 5 -> $80) and story 2 fails (Oct 5 -> $100): either failing fails the row
    assert not all(c.held for c in story1) and not all(c.held for c in story2)
    assert t4.verdict == FAIL


def test_each_story_runs_on_its_own_fresh_system_and_every_row_records_the_path_that_ran(baseline_run):
    verdicts, tags = baseline_run
    assert sorted(tags) == sorted(["retroactive", "out-of-order", "future-dated", "lapsed-override-1",
                                   "lapsed-override-2", "future-value", "as-of"])
    for v in verdicts.values():  # the baseline accepts no dates: plain path for the writes and every read
        assert v.measurements == {"accepts_valid_time": False, "accepts_recorded_at": False}
    assert all("[plain path]" in c.observation for c in verdicts["T1"].cases)
