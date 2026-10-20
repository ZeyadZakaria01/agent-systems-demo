"""Time probes: the story shift (pure), request construction, and the rows on the baseline (versioned row) in-process.

The baseline accepts `recorded_at` only, so "Expected verdicts" reads it `absent` on all six probes (each needs
`valid_from`); its `recorded_at` half is answered from its history and shows only in the evidence.
No MemState mock and no MemState verdict is pinned: the dated paths are proven by the patch smoke runs (tickets 12/13)."""

from contextlib import nullcontext
from datetime import date, datetime

import pytest

from demo.adapter import utc_now
from demo.baseline import Baseline
from demo.checks import discover
from demo.checks.time_probes import NEEDS
from demo.reads import NO_VALUE, current_value, field_in_response
from demo.session import Session
from demo.time_stories import (AS_OF, LAPSED_OVERRIDE_1, LAPSED_OVERRIDE_2, STORIES, history_intact, ingest_request, query_request,
                               shift_story)
from demo.adapter import DATES, utc_now
from demo.memstate_system import request_date_fields, with_current
from demo.verdict import ABSENT, FAIL, PASS

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
        return {"keeps_history": True, "accepts": {d: True for d in DATES}}


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
    # the latest recorded value is current, the same plain read for every date: the "upstream expected" column
    for story in STORIES:
        s = Baseline()
        topic_id = None
        for i in range(len(story.writes)):
            topic_id = s.ingest(ingest_request(story, i, topic_id, ))["topic_id"]
        for ask in story.asks:
            request = query_request(ask, topic_id, send_valid=True)
            got = current_value(field_in_response(s.query(request), topic_id, story.field))
            assert got == ask.recency, (story.id, ask.label)


def test_the_baseline_accepts_recorded_at_only_so_every_probe_is_absent_with_the_schema_and_the_answers_as_evidence(baseline_run):
    v, _ = baseline_run
    assert sorted(v) == ["T1", "T2", "T3", "T4", "T5", "T6"]
    for row, verdict in v.items():
        assert verdict.verdict == ABSENT, row
        assert verdict.measurements["accepts_dates"] in ("no", "partly"), row
        assert verdict.probe_evidence["accepts"] == {**{d: False for d in DATES}, "recorded_at": True}, row
        assert verdict.probe_evidence["missing"] == [d for d in NEEDS[row] if d != "recorded_at"], row
        assert verdict.cases == [], row  # never called wrong
    t1 = v["T1"].probe_evidence["stories"]["retroactive"]
    assert t1["write_dates"] == [] and [a["answer"] for a in t1["asked"]] == ["March 1", "March 1"]
    asked = v["T5"].probe_evidence["stories"]["as-of"]["asked"]
    assert (asked[0]["answer"], asked[1]["answer"]) == ("May 1", "April 20")  # `valid_at` ignored, `recorded_at` answered
    assert "valid_at" in asked[0]["request"] and "recorded_at" in asked[1]["request"]
    assert "valid_at" not in v["T1"].probe_evidence["stories"]["retroactive"]["asked"][1]["request"]  # plain read


def test_the_lapsed_override_evidence_holds_both_stories(baseline_run):
    assert sorted(baseline_run[0]["T4"].probe_evidence["stories"]) == ["lapsed-override-1", "lapsed-override-2"]
def test_a_recorded_at_read_on_the_baseline_answers_the_believed_on_question_from_its_history():
    s = Baseline()
    story = shift_story(AS_OF, RUN_DAY)
    topic_id = s.ingest(ingest_request(story, 0, None))["topic_id"]
    between = utc_now()
    s.ingest(ingest_request(story, 1, topic_id))
    plain = current_value(field_in_response(s.query({"q": "x", "stages": ["temporal"], "topic_ids": [topic_id]}),
                                            topic_id, story.field))
    as_of = current_value(field_in_response(s.query({"q": "x", "stages": ["temporal"], "topic_ids": [topic_id],
                                                     "recorded_at": between}), topic_id, story.field))
    assert (plain, as_of) == ("May 1", "April 20")




def test_each_story_runs_on_its_own_fresh_system(baseline_run):
    _, tags = baseline_run
    assert sorted(tags) == sorted(["retroactive", "out-of-order", "future-dated", "lapsed-override-1",
                                   "lapsed-override-2", "future-value", "as-of"])


def test_story_2_also_asks_oct_15_where_a_plain_statement_ends_the_override():
    asks = {a.label: a for a in LAPSED_OVERRIDE_2.asks}
    assert asks["Oct 15"].correct == "$100" and asks["Oct 15"].recency == "$100"
    assert [a.label for a in LAPSED_OVERRIDE_2.asks] == ["today", "Oct 15", "Oct 5"]


class Dated(Baseline):
    """An in-process stand-in that takes the dates in `accepts` and reads them like a bitemporal store: the current
    value on a date is the entry with the latest `valid_from` not after it and not ended before it. `wrong` answers a
    constant whatever the dates; `ignore_recorded` accepts `recorded_at` and then does nothing with it."""

    def __init__(self, accepts, wrong=False, ignore_recorded=False):
        super().__init__()
        self.accepts, self.wrong, self.ignore_recorded = set(accepts), wrong, ignore_recorded
        self.entries: dict[tuple[str, str], list[dict]] = {}
        self.writes: list[dict] = []

    def _ingest(self, request):
        response = super()._ingest(request)
        for f in request.get("fields") or []:
            self.writes.append(f)
            self.entries.setdefault((response["topic_id"], f["name"]), []).append(
                {"value": f["value"], "recorded": utc_now(), "from": f.get("valid_from"), "to": f.get("invalid_at")})
        return response

    def _current(self, entries, valid_at, recorded_at):
        if self.wrong:
            return {"value": "?"}
        day = valid_at or RUN_DAY.isoformat()
        known = [e for e in entries if recorded_at is None or self.ignore_recorded or e["recorded"] <= recorded_at]
        live = [e for e in known if (e["from"] or "") [:10] <= day[:10] and (e["to"] is None or day[:10] < e["to"][:10])]
        live.sort(key=lambda e: (e["from"] or "")[:10])  # stable: the later arrival wins a tie
        return {"value": live[-1]["value"]} if live else None

    def _query(self, request):
        response = super()._query(request)
        valid_at = request.get("valid_at") if "valid_at" in self.accepts else None
        recorded_at = request.get("recorded_at") if "recorded_at" in self.accepts else None
        for c in response["candidates"]:
            for f in c["fields"]:
                f["current"] = self._current(self.entries[(c["topic_id"], f["name"])], valid_at, recorded_at)
        return response

    def _describe(self):
        return {"keeps_history": False, "accepts": {d: d in self.accepts for d in DATES}}


def run_stand_in(**kwargs):
    made = []

    def open_system(tag):
        made.append(Dated(**kwargs))
        return nullcontext(made[-1])

    verdicts = {v.row: v for v in time_check().execute(Session(open_system), run_day=RUN_DAY)}
    return verdicts, made


def test_a_start_date_only_system_gets_dates_for_t1_t2_t3_t6_and_is_absent_on_t4_and_t5():
    v, made = run_stand_in(accepts={"valid_from", "valid_at"})
    for row in ("T1", "T2", "T3", "T6"):
        assert v[row].verdict == PASS, row
        assert v[row].measurements["accepts_dates"] == "yes"
    for row in ("T4", "T5"):
        assert v[row].verdict == ABSENT and v[row].measurements["accepts_dates"] == "partly", row
    assert v["T4"].probe_evidence["missing"] == ["invalid_at"]
    assert v["T5"].probe_evidence["missing"] == ["recorded_at"]
    assert all("valid_from" in w for m in made for w in m.writes)  # start dates sent on every probe ...
    assert not any("invalid_at" in w for m in made for w in m.writes)  # ... end dates never, the system takes none


def test_a_system_that_takes_every_date_and_answers_right_passes_all_six_probes():
    v, _ = run_stand_in(accepts=set(DATES))
    assert {r: x.verdict for r, x in v.items()} == {r: PASS for r in ("T1", "T2", "T3", "T4", "T5", "T6")}
    assert all(x.measurements["accepts_dates"] == "yes" for x in v.values())


def test_an_end_date_capable_system_with_a_wrong_answer_reads_fail_and_over_blocking_when_a_control_date_is_wrong():
    v, _ = run_stand_in(accepts=set(DATES), wrong=True)
    for row in ("T1", "T2", "T3", "T4", "T5", "T6"):
        assert v[row].verdict == FAIL, row
    assert any(o["name"] == "over-blocking" for o in v["T1"].observations)  # the control date is wrong too


def test_a_recorded_at_system_with_identical_answers_on_t5_reads_fail_not_absent():
    v, _ = run_stand_in(accepts=set(DATES), ignore_recorded=True)
    assert v["T5"].verdict == FAIL
    assert any(o["name"] == "identical answers" for o in v["T5"].observations)
    assert [c.held for c in v["T5"].cases] == [True, False]
    assert all(v[r].verdict == PASS for r in ("T1", "T2", "T3", "T4", "T6"))


def test_a_stand_in_with_no_dates_reads_absent_on_all_six():
    v, made = run_stand_in(accepts=set())
    assert {r: x.verdict for r, x in v.items()} == {r: ABSENT for r in ("T1", "T2", "T3", "T4", "T5", "T6")}
    assert not any(set(w) & {"valid_from", "invalid_at"} for m in made for w in m.writes)


def test_a_missing_current_is_refused_where_a_date_is_accepted_and_falls_back_to_the_newest_entry_where_none_is():
    field = {"history": [{"value": "new"}, {"value": "old"}]}
    assert with_current(dict(field), dates_accepted=False)["current"] == {"value": "new"}
    assert with_current({"history": []}, dates_accepted=False)["current"] is None
    with pytest.raises(RuntimeError, match="refusing the newest-entry fallback"):
        with_current(dict(field), dates_accepted=True)
    stated = {"history": [{"value": "x"}], "current": None}
    assert with_current(stated, dates_accepted=True)["current"] is None  # a stated `current` is taken at its word


def _openapi(*, write_fields=(), query_fields=(), entry_fields=("valid_from",)):
    prop = lambda names: {n: {"type": "string"} for n in names}
    return {"paths": {"/v1/ingest": {"post": {"requestBody": {"content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/IngestRequest"}}}}}},
                      "/v1/query": {"post": {"requestBody": {"content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/QueryRequest"}}}}}},
                      "/v1/topic": {"get": {}}},
            "components": {"schemas": {
                "IngestRequest": {"properties": {"fields": {"type": "array", "items": {"$ref": "#/components/schemas/FieldWrite-Input"}}}},
                "FieldWrite-Input": {"properties": {"value": {}, **prop(write_fields)}},
                "QueryRequest": {"properties": {"q": {}, **prop(query_fields)}},
                "HistoryEntry": {"properties": {"value": {}, **prop(entry_fields)}}}}}


def test_the_dates_a_server_accepts_are_read_per_date_from_the_models_its_requests_use():
    assert request_date_fields(_openapi()) == set()  # a response model returning valid_from is not a write model
    assert request_date_fields(_openapi(write_fields=["valid_from"], query_fields=["valid_at"])) == {"valid_from", "valid_at"}
    assert request_date_fields(_openapi(write_fields=["valid_from", "invalid_at"],
                                        query_fields=["valid_at", "recorded_at"])) == set(DATES)
    assert request_date_fields(_openapi(query_fields=["recorded_at"])) == {"recorded_at"}
