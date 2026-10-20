"""Time probes: the story shift (pure), request construction, and the rows on the baseline in-process.
No MemState mock and no MemState verdict is pinned: the dated paths are proven by the patch smoke runs (tickets 12/13)."""

from contextlib import nullcontext
from datetime import date

import pytest

from demo.baseline import Baseline
from demo.checks import discover
from demo.reads import NO_VALUE, current_value, field_in_response
from demo.session import Session
from demo.time_stories import (AS_OF, LAPSED_OVERRIDE_1, STORIES, history_intact, ingest_request, query_request,
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


def test_history_intact_requires_every_value_and_a_copy_for_each_expired_entry():
    story = AS_OF
    intact = {"history": [
        {"id": "3", "value": "April 20", "valid_from": "x", "operation": "interval_corrected", "replaces_entry_id": "1",
         "expired_at": None},
        {"id": "2", "value": "May 1", "expired_at": None},
        {"id": "1", "value": "April 20", "expired_at": "t"}]}
    assert history_intact(story, intact)[0] is True
    no_copy = {"history": [{"id": "2", "value": "May 1", "expired_at": None},
                           {"id": "1", "value": "April 20", "expired_at": "t"}]}
    assert history_intact(story, no_copy)[0] is False
    lost = {"history": [{"id": "2", "value": "May 1", "expired_at": None}]}
    assert "April 20" in history_intact(story, lost)[1]
    assert history_intact(story, {"history": None})[0] is False


def test_history_intact_fails_on_entries_that_are_not_patch_shaped():
    unshaped = {"history": [{"id": "2", "value": "May 1"}, {"id": "1", "value": "April 20"}]}
    intact, why = history_intact(AS_OF, unshaped)
    assert intact is False and "expired_at" in why


class HistoryStore(Baseline):
    """A generic adapter implementation that keeps a per-field history, for exercising the history-intact case. It
    models no MemState behaviour. Its query response carries only id and value per entry (like a bare read), while
    `read_topic` returns the full stored entries. `defect` picks what the stored history gets wrong: None (nothing),
    `no_copy` (an expired entry has no linked copy), `lost` (a superseded value is dropped) or `unshaped` (entries have
    no `expired_at` key)."""

    def __init__(self, defect=None):
        super().__init__()
        self.defect = defect
        self.history: dict[tuple[str, str], list[dict]] = {}
        self.counter = 0

    def _next_id(self):
        self.counter += 1
        return str(self.counter)

    def _ingest(self, request):
        response = super()._ingest(request)
        for f in request.get("fields") or []:
            entries = self.history.setdefault((response["topic_id"], f["name"]), [])
            entry = {"id": self._next_id(), "value": f["value"]}
            if self.defect != "unshaped":
                entry["expired_at"] = None
            if entries and self.defect == "lost":
                entries.pop(0)
            elif entries:
                if self.defect != "unshaped":
                    entries[0]["expired_at"] = "t"
                if self.defect not in ("no_copy", "unshaped"):
                    copy = {"id": self._next_id(), "value": entries[0]["value"], "replaces_entry_id": entries[0]["id"],
                            "expired_at": None}
                    entries.insert(0, copy)
            entries.insert(0, entry)
        return response

    def _query(self, request):
        response = super()._query(request)
        for c in response["candidates"]:
            for f in c["fields"]:
                f["history"] = [{"id": e["id"], "value": e["value"]} for e in self.history[(c["topic_id"], f["name"])]]
        return response

    def _topic(self, row):
        topic = super()._topic(row)
        for name, f in topic["fields"].items():
            f["history"] = [dict(e) for e in self.history[(row["title"], name)]]
        return topic

    def _describe(self):
        return {"keeps_history": True, "accepts_valid_time": True, "accepts_recorded_at": True}


def history_case(defect):
    session = Session(lambda tag: nullcontext(HistoryStore(defect)))
    t1 = next(v for v in time_check().execute(session, run_day=RUN_DAY) if v.row == "T1")
    return next(c for c in t1.cases if c.name.startswith("history intact"))


def test_the_history_case_reads_the_stored_entries_and_holds_when_they_are_intact():
    assert history_case(None).held is True


@pytest.mark.parametrize("defect", ["no_copy", "lost", "unshaped"])
def test_the_history_case_fails_on_a_stored_defect_the_query_response_does_not_show(defect):
    assert history_case(defect).held is False


def test_the_baseline_gets_the_table_s_upstream_expected_answer_for_every_asked_date():
    # last write wins, same plain read for every date: the "upstream expected" column of the spec's table
    for story in STORIES:
        s = Baseline()
        topic_id = None
        for i in range(len(story.writes)):
            topic_id = s.ingest(ingest_request(story, i, topic_id, dated=False))["topic_id"]
        for ask in story.asks:
            request = query_request(ask, topic_id, send_valid=True, send_recorded=True, recorded_at="now")
            got = current_value(field_in_response(s.query(request), topic_id, story.field))
            assert got == ask.recency, (story.id, ask.label)


def test_the_baseline_fails_five_time_probes_with_the_wrong_date_observed_and_is_absent_on_as_of(baseline_run):
    v, _ = baseline_run
    assert sorted(v) == ["T1", "T2", "T3", "T4", "T5", "T6"]
    for row in ("T1", "T2", "T3", "T4", "T6"):
        assert v[row].verdict == FAIL, row
        assert any(c.held is False for c in v[row].cases), row
    assert [c.held for c in v["T1"].cases] == [False, True]  # today is wrong, the control date is right
    assert v["T5"].verdict == ABSENT
    asked = v["T5"].probe_evidence["asked"]
    assert asked[0]["answer"] == asked[1]["answer"] == "May 1"
    assert "valid_at" in asked[0]["request"] and "recorded_at" in asked[1]["request"]  # the dates were sent and ignored


def test_the_control_date_of_each_probe_is_flagged_and_the_baseline_shows_no_over_blocking(baseline_run):
    v, _ = baseline_run
    for row in ("T1", "T2", "T3", "T4", "T6"):
        assert sum(c.control for c in v[row].cases) >= 1, row
    assert [r["control"] for r in v["T5"].probe_evidence["asked"]] == [True, False]
    # the baseline answers the plain read: only the asks upstream expects wrong fail, so no probe shows over-blocking
    assert all(o.get("name") != "over-blocking" for r in v for o in v[r].observations)


def test_the_lapsed_override_row_passes_only_if_both_stories_pass(baseline_run):
    t4 = baseline_run[0]["T4"]
    names = [c.name for c in t4.cases]
    assert any(n.startswith("story 1") for n in names) and any(n.startswith("story 2") for n in names)
    story1 = [c for c in t4.cases if c.name.startswith("story 1")]
    story2 = [c for c in t4.cases if c.name.startswith("story 2")]
    # on the baseline story 1 fails (Nov 5 -> $80) and story 2 fails (Oct 5 -> $100): either failing fails the row
    assert not all(c.held for c in story1) and not all(c.held for c in story2)
    assert t4.verdict == FAIL


def test_each_story_runs_on_its_own_fresh_system(baseline_run):
    _, tags = baseline_run
    assert sorted(tags) == sorted(["retroactive", "out-of-order", "future-dated", "lapsed-override-1",
                                   "lapsed-override-2", "future-value", "as-of"])
