"""The bad-merge chat run, its recording, replay and wiring into the results, in-process. No server, no Ollama.

`MergingStandIn` is a generic second system on the adapter, not a model of MemState: same-title topics are folded
together by a pass after every ingest (the lower id survives, fields only the other topic holds are copied over, a
field both hold keeps the survivor's history), and `chat` answers from a table the test supplies. It lets the scenario
(arrangement, merge, loss, turns) run through the adapter exactly as it runs on any system. MemState's own outcome is
never pinned here: it comes from the recorded run (evidence rule, ADR 0002).
"""

import copy
import itertools
import json
import subprocess
import sys
import uuid

import pytest

from demo.adapter import Rejected, System
from demo.chat_run import ScenarioError, build_bad_merge_state, lost_in_merge
from demo.storyline import WEBSITE_REDESIGN


class MergingStandIn(System):
    def __init__(self, first_ids=(), can_retitle=True, replies=None, merges=True):
        super().__init__("merging-stand-in")
        self.topics: dict[str, dict] = {}
        self.first_ids = list(first_ids)  # ids handed out first (then uuid4): lets a test pick the id order
        self.can_retitle, self.merges = can_retitle, merges
        self.replies = replies or {}
        self.chats: list[dict] = []

    def _new_id(self):
        return self.first_ids.pop(0) if self.first_ids else str(uuid.uuid4())

    def _write(self, topic, fields, placement):
        for f in fields:
            entry = {"value": f["value"], "provenance": f.get("provenance", "api"), "why_changed": f.get("why_changed"),
                     "impact_expected": f.get("impact_expected"), "valid_from": "t"}
            slot = topic["fields"].setdefault(f["name"], {"history": [], "current": None})
            slot["history"].insert(0, entry)
            slot["current"] = slot["history"][0]

    def _ingest(self, request):
        if request["placement"] == "new_topic":
            tid = self._new_id()
            self.topics[tid] = {"id": tid, "title": request["title"], "summary": request.get("summary"),
                                "topic_kind": request.get("topic_kind"), "archived": False, "salience": 1.0,
                                "fields": {}}
        else:
            tid = request["topic_id"]
            if tid not in self.topics:
                raise Rejected(400, "topic not found")
        self._write(self.topics[tid], request.get("fields") or [], request["placement"])
        if self.merges:
            self._merge_pass()
        return {"topic_id": tid, "applied": [], "version_ids": {}, "similar_topic_ids": []}

    def _merge_pass(self):
        for keep_id in sorted(self.topics):
            for drop_id in sorted(self.topics):
                keep, drop = self.topics.get(keep_id), self.topics.get(drop_id)
                if keep and drop and keep_id < drop_id and keep["title"] == drop["title"] != "":
                    for name, f in drop["fields"].items():
                        keep["fields"].setdefault(name, f)
                    del self.topics[drop_id]

    def _query(self, request):
        return {"candidates": []}

    def _read_state(self):
        return {"topics": {k: copy.deepcopy(v) for k, v in self.topics.items()}, "edges": None}

    def _read_topic(self, topic_id):
        return copy.deepcopy(self.topics.get(topic_id))

    def _setup_write(self, action, params):
        if not self.can_retitle:
            return None
        if action == "patch_topic":
            self.topics[params["topic_id"]].update({k: v for k, v in params.items() if k != "topic_id"})
            return {"topic_id": params["topic_id"]}
        return None

    def _describe(self):
        return {"keeps_history": True, "url": "stand-in", "db_path": None, "commit": None, "engine": None}

    def _chat(self, request):
        self.chats.append(request)
        question = request["messages"][-1]["content"]
        return {"reply": self.replies.get(question, "I do not know."), "tool_log": [],
                "model": "stand-in-model", "provider": request.get("provider", "ollama"), "intent": "query",
                "intent_source": "classifier", "max_tool_rounds": 6}


ID_ORDERS = [pytest.param(["id-1", "id-2"], id="first placeholder lower"),
             pytest.param(["id-2", "id-1"], id="first placeholder higher")]


def build(system=None, **kw):
    system = system or MergingStandIn(**kw)
    return system, build_bad_merge_state(system, WEBSITE_REDESIGN)


# -- the state: built through the adapter up to a bad merge


@pytest.mark.parametrize("first_ids", ID_ORDERS)
def test_the_reexplanation_survives_and_the_original_is_dropped_whatever_the_id_order(first_ids):
    system, built = build(first_ids=first_ids)
    assert built.outcome.survivor_id == built.reexplanation_id == "id-1"  # the lower id survives
    assert built.outcome.dropped_id == built.original_id == "id-2"
    assert system.read_topic(built.original_id) is None
    assert built.arranged  # the dropped topic was the original, as arranged


def test_the_whole_storyline_is_played_on_the_original_and_the_duplicate_exists_only_here():
    system, built = build()
    assert built.events == len(WEBSITE_REDESIGN.events)
    titles = sorted(t["title"] for t in system.topics.values())
    assert titles.count("Website Redesign") == 1 and "Website Redesign Phase 2" in titles
    assert built.topic_ids["redesign"] == built.original_id  # the storyline's `redesign` key is the original topic


def test_a_system_that_cannot_retitle_is_refused_not_scored():
    with pytest.raises(ScenarioError, match="retitle"):
        build(can_retitle=False)


def test_a_merge_that_never_happens_is_refused():
    with pytest.raises(ScenarioError, match="merge"):
        build_bad_merge_state(MergingStandIn(merges=False), WEBSITE_REDESIGN, merge_timeout=0.2)


# -- what the merge lost


def test_the_merge_loses_the_deadline_history_and_its_vendor_delay_provenance_and_keeps_the_other_fields():
    system, built = build()
    loss = built.loss
    assert loss["fields_lost"] == []  # every field the original held is still on the survivor
    assert sorted(loss["kept_fields"]) == ["Deadline", "Status", "Team"]
    assert loss["lost_values"] == {"Deadline": ["March 15"]}  # April 20 is still a value: the re-explanation holds it
    lost = {(e["value"], e["provenance"], e["why_changed"]) for e in loss["lost_entries"]["Deadline"]}
    assert lost == {("March 15", "kickoff-notes", None), ("April 20", "pm-email", "vendor delay")}
    assert system.read_topic(built.reexplanation_id)["fields"]["Deadline"]["current"]["value"] == "April 20"


def test_lost_in_merge_compares_by_value_provenance_and_reason():
    def topic(*entries):
        return {"fields": {"F": {"history": [{"value": v, "provenance": p, "why_changed": w} for v, p, w in entries]}}}

    before = topic(("b", "p", "why"), ("a", "p", None))
    assert lost_in_merge(before, topic(("b", "p", "why"), ("a", "p", None)))["lost_entries"] == {}
    gone = lost_in_merge(before, topic(("b", "p", "why")))
    assert [e["value"] for e in gone["lost_entries"]["F"]] == ["a"] and gone["lost_values"] == {"F": ["a"]}


# -- the turns and the recording

from demo.chat_recording import load_recording, render_recording, save_recording  # noqa: E402
from demo.chat_run import QUESTIONS, record_bad_merge  # noqa: E402

REPLIES = {"What is the deadline of the Website Redesign?": "The deadline is April 20.",
           "Who is on the website redesign team?": "Alice and Bob.",
           "What is the current status of the website redesign project?": "It is complete."}


def recorded(**kw):
    system = MergingStandIn(replies=REPLIES, **kw)
    return system, record_bad_merge(system, run_id="test-run", recorded_at="2026-10-21T10:00:00+00:00")


def test_the_run_asks_three_storyline_questions_and_one_chat_request_each():
    system, rec = recorded()
    assert QUESTIONS == ("Q02", "Q06", "Q11")
    assert [t["question"] for t in rec["turns"]] == ["Q02", "Q06", "Q11"]
    assert [c["messages"] for c in system.chats] == [[{"role": "user", "content": t["text"]}] for t in rec["turns"]]


def test_a_chat_request_is_provider_ollama_with_no_intent_override_and_no_model_override():
    system, _ = recorded()
    for request in system.chats:
        assert request == {"messages": request["messages"], "provider": "ollama"}


def test_each_turn_carries_question_truth_answer_route_latency_violation_and_an_empty_grade_slot():
    _, rec = recorded()
    q02 = rec["turns"][0]
    assert (q02["text"], q02["ground_truth"], q02["answer"]) == (
        "What is the deadline of the Website Redesign?", "April 20", "The deadline is April 20.")
    assert q02["route"] == {"intent": "query", "intent_source": "classifier", "tool_calls": []}
    assert q02["latency_ms"] >= 0 and q02["model"] == "stand-in-model" and q02["provider"] == "ollama"
    assert q02["hand_grade"] == {"grade": None, "note": None}
    assert q02["state_violation"]["present"] is True


def test_the_deadline_answer_looks_right_while_the_state_lost_the_history_and_its_provenance():
    _, rec = recorded()
    q02 = rec["turns"][0]
    assert q02["answer_contains_ground_truth"] is True  # a string match, not a grade
    v = q02["state_violation"]
    assert v["condition"] == "C4" and v["field"] == "Deadline"
    assert v["lost_values"] == ["March 15"]
    assert {(e["value"], e["why_changed"]) for e in v["lost_entries"]} == {("March 15", None), ("April 20", "vendor delay")}
    assert v["current_after"] == "April 20"


def test_a_field_only_the_original_held_survived_the_merge_so_its_turn_records_no_violation():
    _, rec = recorded()
    for turn in rec["turns"][1:]:
        assert turn["state_violation"]["present"] is False
        assert turn["state_violation"]["lost_entries"] == []
        assert turn["state_violation"]["current_after"] == turn["ground_truth"]
    assert rec["turns"][1]["ground_truth"] == "Alice (Frontend lead), Bob (Backend), Erin (QA)"


def test_a_turn_notes_whether_the_chat_changed_the_surviving_topic():
    class Writer(MergingStandIn):
        def _chat(self, request):
            survivor = next(t for t in self.topics.values() if t["title"] == "Website Redesign")
            self._write(survivor, [{"name": "Status", "value": "Chatted", "provenance": "chat"}], "extend_topic")
            return super()._chat(request)

    rec = record_bad_merge(Writer(replies=REPLIES), run_id="r", recorded_at="t")
    assert rec["turns"][0]["topic_changed_by_turn"] is True
    plain = recorded()[1]
    assert plain["turns"][0]["topic_changed_by_turn"] is False


def test_the_recording_describes_how_the_state_was_built_and_what_the_merge_lost():
    _, rec = recorded()
    state = rec["state"]
    assert rec["case"] == "bad-merge" and rec["run_id"] == "test-run"
    assert state["events_played"] == len(WEBSITE_REDESIGN.events)
    assert state["merge"]["survivor_id"] == state["reexplanation_id"]
    assert state["merge"]["dropped_state"] == "deleted" and state["merge"]["arranged"] is True
    assert state["loss"]["lost_values"] == {"Deadline": ["March 15"]}
    assert [h["value"] for h in state["before_merge"]["original"]["fields"]["Deadline"]["history"]] == ["April 20", "March 15"]
    assert [h["value"] for h in state["after_merge"]["survivor"]["fields"]["Deadline"]["history"]] == ["April 20"]
    assert state["setup_writes"] and all("label" in w for w in state["setup_writes"])


def test_a_recording_survives_save_and_load_unchanged(tmp_path):
    _, rec = recorded()
    path = save_recording(rec, tmp_path)
    assert path.parent == tmp_path and path.suffix == ".json"
    assert load_recording(path) == rec


def test_a_file_that_is_not_a_recording_is_refused(tmp_path):
    bad = tmp_path / "x.json"
    bad.write_text(json.dumps({"case": "bad-merge"}))
    with pytest.raises(ValueError, match="schema"):
        load_recording(bad)


# -- replay: rendered from the file alone


def test_replay_shows_every_turn_with_its_truth_answer_route_latency_violation_and_grade_slot():
    _, rec = recorded()
    text = render_recording(rec)
    for needle in ("Q02", "What is the deadline of the Website Redesign?", "April 20", "The deadline is April 20.",
                   "query", "classifier", "ms", "C4", "March 15", "vendor delay", "hand grade"):
        assert needle in text
    assert text.count("hand grade") == 3


def test_replay_runs_with_no_server_and_loads_neither_http_nor_the_server_launcher(tmp_path):
    _, rec = recorded()
    save_recording(rec, tmp_path)
    code = ("import sys; from demo.chat_run import main; rc = main(['replay', sys.argv[1]]); "
            "assert 'httpx' not in sys.modules and 'demo.server' not in sys.modules, sorted(m for m in sys.modules "
            "if m in ('httpx', 'demo.server')); sys.exit(rc)")
    done = subprocess.run([sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True,
                          cwd=str(__import__("demo.paths").paths.REPO_ROOT))
    assert done.returncode == 0, done.stderr
    assert "Q02" in done.stdout and "The deadline is April 20." in done.stdout


def test_replay_of_a_folder_with_no_recording_says_so(tmp_path, capsys):
    from demo.chat_run import main
    assert main(["replay", str(tmp_path)]) == 1
    assert "no recording" in capsys.readouterr().err


# -- wiring: the recording is a chat case in results.json and scorecard.md

from datetime import date  # noqa: E402

from demo.checks import discover  # noqa: E402
from demo.run import run_recorded  # noqa: E402


def run_with(recordings_dir, tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")
    return run_recorded(systems=["baseline"], checks=[c1], results_root=tmp_path / "results", command="python -m demo.run t",
                        run_day=date(2026, 10, 20), runtime_root=tmp_path / "runtime", recordings_dir=recordings_dir)


def test_the_recording_is_printed_in_the_scorecard_as_a_chat_case(tmp_path):
    _, rec = recorded()
    save_recording(rec, tmp_path / "rec")
    run = run_with(tmp_path / "rec", tmp_path)
    card = (run.dir / "scorecard.md").read_text()
    assert "### Chat cases" in card and "Q02" in card and "The deadline is April 20." in card
    assert card.index("### Chat cases") < card.index("### Deviations")  # before the deviations table
    assert run.scorecard == card.rstrip("\n")


def test_results_json_carries_the_chat_case_without_the_tool_logs(tmp_path):
    system, rec = recorded()
    rec["turns"][0]["tool_log"] = [{"tool": "memory_query", "args": {}, "result": {"big": "x" * 50}}]
    save_recording(rec, tmp_path / "rec")
    run = run_with(tmp_path / "rec", tmp_path)
    (case,) = json.loads((run.dir / "results.json").read_text())["chat_cases"]
    assert case["case"] == "bad-merge" and case["file"] == f"bad-merge-{rec['run_id']}.json"
    assert [t["question"] for t in case["turns"]] == ["Q02", "Q06", "Q11"]
    assert all("tool_log" not in t for t in case["turns"])
    assert case["turns"][0]["hand_grade"] == {"grade": None, "note": None}


def test_a_run_with_no_recordings_prints_no_chat_section_and_an_empty_list(tmp_path):
    run = run_with(tmp_path / "nothing", tmp_path)
    assert "Chat cases" not in (run.dir / "scorecard.md").read_text()
    assert json.loads((run.dir / "results.json").read_text())["chat_cases"] == []


def test_only_the_newest_recording_of_a_case_is_printed(tmp_path):
    _, old = recorded()
    old["run_id"], old["recorded_at"] = "old", "2026-10-01T00:00:00+00:00"
    old["turns"][0]["answer"] = "STALE ANSWER"
    _, new = recorded()
    save_recording(old, tmp_path / "rec")
    save_recording(new, tmp_path / "rec")
    card = (run_with(tmp_path / "rec", tmp_path).dir / "scorecard.md").read_text()
    assert "STALE ANSWER" not in card and "The deadline is April 20." in card


# -- the ground-truth word match (a hint printed beside the empty grade slot, never the grade)

from demo.chat_run import contains_every_word  # noqa: E402


@pytest.mark.parametrize("truth, answer, expected", [
    ("April 20", "The deadline is **April 20**.", True),
    ("Complete", "Is it a completed phase? I don't know.", False),  # a longer word is not the word
    ("Complete", "The project is complete.", True),
    ("Alice (Frontend lead), Bob (Backend), Erin (QA)", "- Alice (Frontend lead)\n- Bob (Backend)\n- Erin (QA)", True),
    ("Alice (Frontend lead), Bob (Backend), Erin (QA)", "Alice and Bob.", False),
    ("$46,500", "The budget is $46,500.", True),
])
def test_the_word_match_needs_every_word_of_the_ground_truth_and_no_longer_word(truth, answer, expected):
    assert contains_every_word(truth, answer) is expected
