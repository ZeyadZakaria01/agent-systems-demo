"""Recording both chat runs as part of the run of record (ticket 19): `chat_run.record_chats` and `demo.run --chat`, with
stand-in systems on the adapter and no Ollama. The processes are faked at the edges (ports, `ss`, `kill`): what is pinned
is which process the run owns, where the snapshots land and which take is the scored case."""

import json
from contextlib import contextmanager, nullcontext
from datetime import date
from pathlib import Path

import pytest

from demo.chat import run as chat_run
from demo.chat.recording import latest_per_case, load_recording
from demo.checks import discover
from demo.evidence import new_run_dir
from demo.reporting.record import record_run
from demo.run import run_recorded
from demo.systems.registry import SYSTEMS, SystemSpec
from tests.chat.test_chat_run import REPLIES, MergingStandIn
from tests.chat.test_chat_two_weeks import FIRST_MESSAGE, SECOND_MESSAGE, JobStandIn


@pytest.fixture
def stand_ins(monkeypatch):
    """Upstream and step 3 are stand-ins; Ollama is up for the block and never really started."""
    made = {}

    def register(system_id, factory):
        def open_system(tag, run):
            made[system_id] = factory()
            return nullcontext(made[system_id])

        monkeypatch.setitem(SYSTEMS, system_id, SystemSpec(system_id, system_id, open_system))

    register("upstream", lambda: MergingStandIn(replies=REPLIES))
    register(
        "step3",
        lambda: JobStandIn(
            effects={FIRST_MESSAGE: [("start_date", "Sep 22", None)]},
            replies={FIRST_MESSAGE: "Noted.", SECOND_MESSAGE: "About four weeks."},
        ),
    )
    events = []

    @contextmanager
    def fake_ollama():
        events.append("up")
        try:
            yield True
        finally:
            events.append("stopped")

    monkeypatch.setattr(chat_run, "ollama_running", fake_ollama)
    monkeypatch.setattr(chat_run, "warm_up", lambda model: 0.5)
    monkeypatch.delenv("MEMSTATE_OLLAMA_BASE_URL", raising=False)
    return made, events


def new_run(tmp_path):
    return new_run_dir(tmp_path / "results", tmp_path / "runtime")


def test_both_cases_are_recorded_in_one_ollama_session_with_their_snapshots_in_the_run_folder(tmp_path, stand_ins):
    _, events = stand_ins
    run = new_run(tmp_path)
    result = chat_run.record_chats(run, tmp_path / "recordings", tmp_path / "results", "the command")
    assert result.errors == [] and [p.name for p in result.saved] == [
        f"bad-merge-{run.id}.json",
        f"two-weeks-{run.id}.json",
    ]
    assert events == ["up", "stopped"]  # one session for both cases
    assert (run.dir / "snapshots" / "upstream" / "chat-bad-merge.json").is_file()
    assert (run.dir / "snapshots" / "step3" / "chat-two-weeks.json").is_file()
    cases = {c["case"]: c for c in latest_per_case(tmp_path / "recordings")}
    assert set(cases) == {"bad-merge", "two-weeks"}
    for rec in cases.values():
        assert rec["run_id"] == run.id and rec["command"] == "the command"
        assert rec["environment"] == {
            "model_warmed_up_s": 0.5,
            "ollama_started_by_run": True,
            "ollama_model_setting": chat_run.DEFAULT_MODEL,
            "think": False,
        }
        assert Path(rec["snapshot"]).is_file() and run.dir.as_posix() in rec["snapshot"]  # the link resolves


def test_the_recorded_run_folder_resolves_the_chat_snapshot_links(tmp_path, stand_ins):
    record_root = tmp_path / "record"
    run = new_run(tmp_path)
    chat_run.record_chats(run, tmp_path / "recordings", record_root, "c")  # links name the folder the run ends in
    target = record_run(run.dir, record_root)
    for rec in latest_per_case(tmp_path / "recordings"):
        assert Path(rec["snapshot"]).is_file() and Path(rec["snapshot"]).is_relative_to(target)  # inside the copy
    assert (target / "snapshots" / "upstream" / "chat-bad-merge.json").is_file()
    assert (target / "snapshots" / "step3" / "chat-two-weeks.json").is_file()


def test_a_case_that_fails_is_reported_and_the_other_is_still_recorded(tmp_path, stand_ins, monkeypatch):
    monkeypatch.setitem(
        SYSTEMS,
        "upstream",
        SystemSpec(
            "upstream", "upstream", lambda tag, run: nullcontext(MergingStandIn(replies=REPLIES, can_retitle=False))
        ),
    )  # the arrangement cannot be made: the scenario refuses
    run = new_run(tmp_path)
    result = chat_run.record_chats(run, tmp_path / "recordings", tmp_path / "results", "c")
    assert len(result.errors) == 1 and result.errors[0].startswith("bad-merge: ScenarioError")
    assert [c["case"] for c in latest_per_case(tmp_path / "recordings")] == ["two-weeks"]


@pytest.mark.parametrize("flags", [("--no-router-decides",), ("--seed-profile",)])
def test_a_variant_take_is_saved_under_attempts_and_is_never_the_scored_case(tmp_path, stand_ins, flags):
    run = new_run(tmp_path)
    plain = chat_run.record_chats(new_run(tmp_path), tmp_path / "rec", tmp_path / "results", "c", ("two-weeks",))
    variant = chat_run.record_chats(run, tmp_path / "rec", tmp_path / "results", "c", ("two-weeks",), flags)
    (path,) = variant.saved
    assert path.parent == tmp_path / "rec" / "attempts"
    assert (load_recording(path)["state"]["first_intent_override"] is not None) or load_recording(path)["state"]["seed"]
    (scored,) = latest_per_case(tmp_path / "rec")
    assert scored["file"] == plain.saved[0].name


def test_a_variant_recorded_into_the_scored_folder_by_hand_is_still_skipped(tmp_path, stand_ins):
    from demo.chat.recording import save_recording

    base = chat_run.record_chats(new_run(tmp_path), tmp_path / "rec", tmp_path / "results", "c", ("two-weeks",))
    older = load_recording(base.saved[0])
    newer_variant = {
        **older,
        "run_id": "z-newer",
        "recorded_at": "2999-01-01T00:00:00+00:00",
        "state": {**older["state"], "first_intent_override": "ingest"},
    }
    save_recording(newer_variant, tmp_path / "rec")
    (scored,) = latest_per_case(tmp_path / "rec")
    assert (
        scored["run_id"] == older["run_id"]
    )  # the newest take is the scored one only among takes run as the spec states


# -- demo.run --chat: the suite and both chat cases in one run folder


def test_run_recorded_records_both_chat_cases_after_the_systems_and_prints_the_new_takes(tmp_path, stand_ins):
    c1 = next(c for c in discover() if c.id == "C1")
    old = tmp_path / "rec"
    chat = lambda run, recordings: chat_run.record_chats(run, recordings, tmp_path / "results", "cmd")  # noqa: E731
    run = run_recorded(
        ["baseline"],
        [c1],
        tmp_path / "results",
        "cmd",
        run_day=date(2026, 10, 20),
        runtime_root=tmp_path / "runtime",
        recordings_dir=old,
        record_chats=chat,
    )
    assert run.chat_errors == []
    results = json.loads((run.dir / "results.json").read_text())
    assert {c["case"] for c in results["chat_cases"]} == {"bad-merge", "two-weeks"}
    assert all(c["run_id"] == run.dir.name for c in results["chat_cases"])  # this run's takes, not older ones
    assert results["chat_errors"] == [] and results["complete"] is True
    card = (run.dir / "scorecard.md").read_text()
    assert "### Chat cases" in card and "two-weeks" not in card.split("### Chat cases")[0]
    assert (run.dir / "snapshots" / "upstream" / "chat-bad-merge.json").is_file()


def test_a_run_that_could_not_start_the_chats_keeps_its_suite_results_and_says_so(tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")

    def broken(run, recordings):
        raise chat_run.OllamaError("Ollama is half running")

    run = run_recorded(
        ["baseline"],
        [c1],
        tmp_path / "results",
        "cmd",
        run_day=date(2026, 10, 20),
        runtime_root=tmp_path / "runtime",
        recordings_dir=tmp_path / "rec",
        record_chats=broken,
    )
    assert any("half running" in e for e in run.chat_errors)
    assert json.loads((run.dir / "results.json").read_text())["complete"] is True and run.verdicts


# -- the processes the run owns


@pytest.fixture
def ports(monkeypatch):
    """The demo Ollama's port and the proxy's as a dict of open/closed; `kill` closes the port its pid listens on."""
    state = {chat_run.OLLAMA_PORT: False, chat_run.PROXY_PORT: False}
    killed = []
    monkeypatch.setattr(chat_run, "_port_open", lambda port: state[port])
    monkeypatch.setattr(chat_run, "_listener_pid", lambda port: 1000 + port if state[port] else None)

    def kill(pid, sig):
        killed.append(pid)
        state[pid - 1000] = False

    monkeypatch.setattr("os.kill", kill)
    started = []

    def run_script(cmd, **kw):
        started.append(cmd)
        state[chat_run.OLLAMA_PORT] = state[chat_run.PROXY_PORT] = True

    monkeypatch.setattr(chat_run.subprocess, "run", run_script)

    class Answer:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: Answer())
    return state, killed, started


def test_ollama_and_the_proxy_are_stopped_at_the_end_also_when_they_were_already_running(ports):
    state, killed, started = ports
    state[chat_run.OLLAMA_PORT] = state[chat_run.PROXY_PORT] = True  # a leftover or the user's own
    with chat_run.ollama_running() as started_by_run:
        assert started_by_run is False and started == []
    assert sorted(killed) == sorted([1000 + chat_run.OLLAMA_PORT, 1000 + chat_run.PROXY_PORT])
    assert not any(state.values())


def test_ollama_the_run_started_is_stopped_after_an_error_in_the_block(ports):
    state, killed, started = ports
    with pytest.raises(RuntimeError, match="boom"), chat_run.ollama_running() as started_by_run:
        assert started_by_run is True and len(started) == 1
        raise RuntimeError("boom")
    assert not any(state.values()) and len(killed) == 2


def test_a_half_running_pair_is_a_leftover_it_is_stopped_and_both_are_started_fresh(ports):
    state, killed, started = ports
    state[chat_run.PROXY_PORT] = True
    with chat_run.ollama_running() as started_by_run:
        assert started_by_run is True and len(started) == 1 and killed == [1000 + chat_run.PROXY_PORT]
    assert not any(state.values())
