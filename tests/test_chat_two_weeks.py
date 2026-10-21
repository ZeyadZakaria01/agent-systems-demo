"""The "two weeks ago" chat run, its recording and replay, in-process. No server, no Ollama.

`JobStandIn` is a generic second system on the adapter, not a model of MemState: `chat` records the request and
applies the effect (a topic written, or none) and the reply the test supplies for that message. The run's own logic
(the date plan, the two separate requests, what each turn wrote, the start-date reading, the recording and its
replay) runs through the adapter exactly as it runs on MemState. What MemState and the 2B model do is never pinned
here: it comes from the recorded run (evidence rule, ADR 0002).
"""

import copy
import itertools
import json
import subprocess
import sys
from datetime import date

import pytest

from demo.adapter import System
from demo.chat_recording import load_recording, render_recording, save_recording
from demo.chat_two_weeks import (CASE, FIRST_MESSAGE, SECOND_MESSAGE, dates_in_text, plan, record_two_weeks,
                                 states_four_weeks)

RUN_DAY = date(2026, 10, 20)


class JobStandIn(System):
    def __init__(self, effects=None, replies=None):
        super().__init__("job-stand-in")
        self.effects = effects or {}  # message -> list of (field, value, valid_from) written by that chat turn
        self.replies = replies or {}
        self.topics: dict[str, dict] = {}
        self.chats: list[dict] = []
        self.ingests: list[dict] = []
        self.ids = itertools.count(1)

    def _chat(self, request):
        self.chats.append(request)
        message = request["messages"][-1]["content"]
        for name, value, valid_from in self.effects.get(message, []):
            topic = self.topics.setdefault("t1", {"id": "t1", "title": "Me", "archived": False, "fields": {}})
            entry = {"value": value, "valid_from": valid_from, "provenance": f"chat (reference_time {request['reference_time']})",
                     "created_at": f"wall-{next(self.ids)}", "why_changed": None}
            slot = topic["fields"].setdefault(name, {"history": [], "current": None})
            slot["history"].insert(0, entry)
            slot["current"] = slot["history"][0]
        return {"reply": self.replies.get(message, "OK."),
                "tool_log": [{"tool": "memory_append_field"}] if message in self.effects else [],
                "model": "stand-in-model", "provider": request.get("provider"), "intent": "ingest" if message in self.effects else "query",
                "intent_source": "classifier", "max_tool_rounds": 6}

    def _read_state(self):
        return {"topics": copy.deepcopy(self.topics), "edges": None}

    def _read_topic(self, topic_id):
        return copy.deepcopy(self.topics.get(topic_id))

    def _ingest(self, request):  # only the optional seed goes through /v1
        self.ingests.append(request)
        entries = [{"value": f["value"], "valid_from": f.get("valid_from"), "provenance": f.get("provenance", "api"),
                    "created_at": f"wall-seed-{next(self.ids)}", "why_changed": None} for f in request["fields"]]
        fields = {f["name"]: {"history": [e], "current": e} for f, e in zip(request["fields"], entries)}
        self.topics["seed-1"] = {"id": "seed-1", "title": request["title"], "archived": False, "fields": fields}
        return {"topic_id": "seed-1", "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _query(self, request):
        raise AssertionError("the two-weeks run must not query")

    def _setup_write(self, action, params):
        raise AssertionError("the two-weeks run must not make a setup write")

    def _describe(self):
        return {"system": "stand-in step 3", "keeps_history": True, "url": "stand-in", "db_path": "/db", "commit": "5c5c9e6" + "0" * 33,
                "engine": "stand-in-engine"}


def recorded(run_day=RUN_DAY, effects=None, replies=None):
    system = JobStandIn(effects=effects if effects is not None else {FIRST_MESSAGE: [("start_date", "Sep 22", None)]},
                        replies=replies if replies is not None else {FIRST_MESSAGE: "Noted.", SECOND_MESSAGE: "About four weeks."})
    return system, record_two_weeks(system, run_id="test-run", recorded_at="2026-10-21T10:00:00+00:00", run_day=run_day)


# -- the dates: the story is told around Oct 20 and shifted so its last day is the run day


def test_on_oct_20_the_story_dates_are_unshifted():
    p = plan(date(2026, 10, 20))
    assert (p.first_day, p.second_day, p.start_date) == (date(2026, 10, 6), date(2026, 10, 20), date(2026, 9, 22))


def test_the_story_shifts_with_the_run_day_and_keeps_its_gaps():
    p = plan(date(2026, 10, 21))
    assert (p.first_day, p.second_day, p.start_date) == (date(2026, 10, 7), date(2026, 10, 21), date(2026, 9, 23))
    assert (p.second_day - p.first_day).days == 14 and (p.first_day - p.start_date).days == 14
    assert p.shift_days == 1


# -- the two requests


def test_the_run_sends_two_separate_requests_one_message_each_with_the_shifted_reference_times():
    system, _ = recorded()
    assert [c["messages"] for c in system.chats] == [[{"role": "user", "content": "I started my new job two weeks ago"}],
                                                      [{"role": "user", "content": "how long have I been there?"}]]
    assert [c["reference_time"] for c in system.chats] == ["2026-10-06T00:00:00+00:00", "2026-10-20T00:00:00+00:00"]


def test_the_requests_follow_the_run_day():
    system, _ = recorded(run_day=date(2026, 10, 21))
    assert [c["reference_time"] for c in system.chats] == ["2026-10-07T00:00:00+00:00", "2026-10-21T00:00:00+00:00"]


def test_a_request_is_provider_ollama_with_no_model_and_no_intent_override_so_the_router_decides_both_routes():
    system, rec = recorded()
    for request in system.chats:
        assert set(request) == {"messages", "provider", "reference_time"} and request["provider"] == "ollama"
    assert rec["state"]["first_intent_override"] is None and "no `intent_override`" in rec["llm"]["left_unset"]
    assert "Both routes are the router's" in render_recording(rec)


def test_the_variant_that_forces_the_first_route_says_so_in_the_request_the_recording_and_the_replay():
    system = JobStandIn()
    rec = record_two_weeks(system, run_id="r", recorded_at="t", run_day=RUN_DAY, first_intent_override="ingest")
    first, second = system.chats
    assert first == {"messages": first["messages"], "provider": "ollama", "reference_time": first["reference_time"],
                     "intent_override": "ingest"}
    assert "intent_override" not in second
    assert rec["state"]["first_intent_override"] == "ingest"
    assert any("`intent_override: ingest` on W1 only" in s for s in rec["llm"]["left_unset"])
    assert "no `intent_override`" not in rec["llm"]["left_unset"] and "intent_override: ingest" in render_recording(rec)


# -- the turns


def test_two_turns_each_with_an_empty_hand_grade_slot_and_the_ground_truth():
    _, rec = recorded()
    first, second = rec["turns"]
    assert (first["question"], second["question"]) == ("W1", "W2")
    assert first["ground_truth"].startswith("2026-09-22") and second["ground_truth"] == "four weeks"
    assert first["hand_grade"] == second["hand_grade"] == {"grade": None, "note": None}
    assert (first["graded_on"], second["graded_on"]) == ("the stored start date", "the answer")
    assert first["reference_time"] == "2026-10-06T00:00:00+00:00"
    for turn in rec["turns"]:
        assert turn["route"]["intent"] and turn["latency_ms"] >= 0 and turn["model"] == "stand-in-model"


def test_the_first_turn_records_what_it_wrote_and_the_start_date_read_from_it():
    _, rec = recorded()
    first = rec["turns"][0]
    assert [(w["field"], w["value"]) for w in first["written"]] == [("start_date", "Sep 22")]
    start = first["stored_start_date"]
    assert start["truth"] == "2026-09-22" and start["tolerance_days"] == 1
    assert [(c["source"], c["date"]) for c in start["candidates"]] == [("value", "2026-09-22")]
    assert start["within_tolerance"] is True


def test_a_start_date_one_day_off_is_within_tolerance_and_two_days_off_is_not():
    _, near = recorded(effects={FIRST_MESSAGE: [("start", "September 23, 2026", None)]})
    _, far = recorded(effects={FIRST_MESSAGE: [("start", "Sep 24", None)]})
    assert near["turns"][0]["stored_start_date"]["within_tolerance"] is True
    assert far["turns"][0]["stored_start_date"]["within_tolerance"] is False


def test_a_start_date_miscomputed_from_the_wrong_day_is_not_within_tolerance():
    _, rec = recorded(effects={FIRST_MESSAGE: [("job", "manager at Initech since 2026-10-04", None)]})
    start = rec["turns"][0]["stored_start_date"]
    assert [(c["source"], c["date"]) for c in start["candidates"]] == [("value", "2026-10-04")]
    assert start["within_tolerance"] is False


def test_the_stored_valid_from_is_a_candidate_too_and_the_reference_time_is_not_the_start_date():
    _, by_default = recorded(effects={FIRST_MESSAGE: [("job", "manager", "2026-10-06T00:00:00+00:00")]})
    _, by_model = recorded(effects={FIRST_MESSAGE: [("job", "manager", "2026-09-22T00:00:00+00:00")]})
    default = by_default["turns"][0]["stored_start_date"]
    assert [(c["source"], c["date"]) for c in default["candidates"]] == [("valid_from", "2026-10-06")]
    assert default["within_tolerance"] is False
    assert by_model["turns"][0]["stored_start_date"]["within_tolerance"] is True


def test_a_turn_that_wrote_nothing_has_no_candidate_and_says_so():
    _, rec = recorded(effects={})
    first = rec["turns"][0]
    assert first["written"] == [] and first["stored_start_date"]["candidates"] == []
    assert first["stored_start_date"]["within_tolerance"] is False


def test_the_second_turn_records_what_it_wrote_and_whether_the_answer_says_four_weeks():
    _, rec = recorded()
    second = rec["turns"][1]
    assert second["written"] == [] and second["answer"] == "About four weeks."
    assert second["answer_contains_ground_truth"] is True
    _, wrong = recorded(replies={FIRST_MESSAGE: "Noted.", SECOND_MESSAGE: "You have been there for two weeks."})
    assert wrong["turns"][1]["answer_contains_ground_truth"] is False


@pytest.mark.parametrize("answer, expected", [
    ("About four weeks.", True), ("4 weeks", True), ("Four weeks, to be exact", True), ("28 days.", True),
    ("two weeks", False), ("I don't know.", False), ("You started on September 22.", False),
])
def test_the_four_weeks_hint(answer, expected):
    assert states_four_weeks(answer) is expected


@pytest.mark.parametrize("text, found", [
    ("started on 2026-09-22", ["2026-09-22"]),
    ("Sep 22", ["2026-09-22"]),
    ("Started Sept 22nd, 2025.", ["2025-09-22"]),
    ("22 September 2026", ["2026-09-22"]),
    ("from September 22 to October 6", ["2026-09-22", "2026-10-06"]),
    ("manager at Initech", []),
    ("May 32", []),
])
def test_dates_in_text_reads_iso_and_month_name_dates_with_the_default_year(text, found):
    assert [d.isoformat() for d in dates_in_text(text, 2026)] == found


# -- the recording


def test_the_recording_describes_the_system_the_llm_and_how_the_dates_were_chosen():
    _, rec = recorded(run_day=date(2026, 10, 21))
    assert rec["case"] == CASE == "two-weeks" and rec["schema"] == 1
    assert rec["system"]["label"] == "stand-in step 3" and rec["system"]["commit"].startswith("5c5c9e6")
    assert rec["llm"]["provider"] == "ollama" and rec["llm"]["model"] == "stand-in-model"
    dates = rec["state"]["dates"]
    assert (dates["run_day"], dates["first_reference_time"], dates["start_date"], dates["shift_days"]) == (
        "2026-10-21", "2026-10-07", "2026-09-23", 1)
    assert rec["state"]["seeded_topics"] == 0 and rec["state"]["seed"] is None


# -- the optional profile seed: one topic through /v1 so the model has a place to write


def test_without_the_seed_nothing_is_ingested():
    system, _ = recorded()
    assert system.ingests == []


def test_the_seed_is_one_dated_profile_topic_written_through_ingest_before_the_first_chat():
    system = JobStandIn(effects={FIRST_MESSAGE: [("job", "manager at Initech", None)]})
    rec = record_two_weeks(system, run_id="r", recorded_at="t", run_day=RUN_DAY, seed=True)
    (request,) = system.ingests
    assert request["placement"] == "new_topic" and request["title"] == "Me"
    assert [(f["name"], f["value"], f["valid_from"]) for f in request["fields"]] == [
        ("job", "analyst at Acme", "2025-01-01T00:00:00+00:00")]
    assert rec["state"]["seeded_topics"] == 1 and rec["state"]["seed"]["request"] == request
    assert "seed-1" in rec["state"]["seed"]["topic_id"]
    assert [w["value"] for w in rec["turns"][0]["written"]] == ["manager at Initech"]  # the seed is not the turn's
    assert "seeded through `/v1`" in render_recording(rec) and "analyst at Acme" in render_recording(rec)


def test_a_recording_survives_save_and_load_unchanged(tmp_path):
    _, rec = recorded()
    path = save_recording(rec, tmp_path)
    assert path.name == "two-weeks-test-run.json" and load_recording(path) == rec


# -- replay: rendered from the file alone


def test_replay_shows_both_turns_the_reference_times_the_stored_entry_the_truth_and_two_empty_grade_slots():
    _, rec = recorded()
    text = render_recording(rec)
    for needle in ("I started my new job two weeks ago", "how long have I been there?", "2026-10-06", "2026-10-20",
                   "2026-09-22", "four weeks", "About four weeks.", "start_date", "Sep 22", "stored start date",
                   "within 1 day"):
        assert needle in text
    assert text.count("hand grade") == 2 and "graded on: the stored start date" in text and "graded on: the answer" in text


def test_replay_runs_with_no_server_and_loads_neither_http_nor_the_server_launcher(tmp_path):
    _, rec = recorded()
    save_recording(rec, tmp_path)
    code = ("import sys; from demo.chat_run import main; rc = main(['replay', sys.argv[1]]); "
            "assert 'httpx' not in sys.modules and 'demo.server' not in sys.modules, sorted(m for m in sys.modules "
            "if m in ('httpx', 'demo.server')); sys.exit(rc)")
    done = subprocess.run([sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True,
                          cwd=str(__import__("demo.paths").paths.REPO_ROOT))
    assert done.returncode == 0, done.stderr
    assert "how long have I been there?" in done.stdout and "About four weeks." in done.stdout


def test_the_scorecard_prints_the_two_weeks_case_beside_the_bad_merge(tmp_path):
    from demo.checks import discover
    from demo.run import run_recorded
    _, rec = recorded()
    save_recording(rec, tmp_path / "rec")
    c1 = next(c for c in discover() if c.id == "C1")
    run = run_recorded(systems=["baseline"], checks=[c1], results_root=tmp_path / "results", command="python -m demo.run t",
                       run_day=RUN_DAY, runtime_root=tmp_path / "runtime", recordings_dir=tmp_path / "rec")
    card = (run.dir / "scorecard.md").read_text()
    assert "### Chat cases" in card and "how long have I been there?" in card and "About four weeks." in card
    (case,) = json.loads((run.dir / "results.json").read_text())["chat_cases"]
    assert case["case"] == "two-weeks" and all("tool_log" not in t for t in case["turns"])
