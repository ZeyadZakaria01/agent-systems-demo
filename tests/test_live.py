"""Live mode, in-process. Title scoping and pacing are tested on `LiveSystem` with the HTTP call stubbed at the
adapter's transport methods; results, labelling and separation run real checks on the baseline through the same
runner (`connect=`). The server-facing path is covered by the smoke run (docs/findings.md)."""

import json

import pytest

from demo.checks import discover
from demo.live import LiveError, LiveSystem, make_pace, preflight, run_live, suffixed
from demo.paths import RESULTS_ROOT


def test_titles_are_scoped_per_check_and_empty_titles_stay_empty():
    assert suffixed("Website Redesign", "C1") == "Website Redesign [live C1]"
    assert suffixed("Website Redesign", "C1--story-1") != suffixed("Website Redesign", "C1")
    assert suffixed("", "C1") == ""


def test_live_system_scopes_titles_of_new_topics_and_setup_writes_only(monkeypatch):
    sent = []
    s = LiveSystem("live", "http://x", "C9", pace=lambda what: sent.append(what))
    monkeypatch.setattr("demo.client.MemStateSystem._ingest", lambda self, r: sent.append(("ingest", r)) or {})
    monkeypatch.setattr("demo.client.MemStateSystem._setup_write", lambda self, a, p: sent.append((a, p)) or {})
    s.ingest({"placement": "new_topic", "title": "T"})
    s.ingest({"placement": "extend_topic", "topic_id": "i", "title": "kept"})
    s.setup_write("create_topic", label="x", title="U", topic_id="t")
    s.setup_write("add_edge", label="x", from_id="a", to_topic_id="b", kind="k")
    posted = [x for x in sent if isinstance(x, tuple)]
    assert posted[0][1]["title"] == "T [live C9]"
    assert posted[1][1]["title"] == "kept"
    assert posted[2][1]["title"] == "U [live C9]" and posted[2][1]["topic_id"] == "t"
    assert "title" not in posted[3][1]
    assert len([x for x in sent if isinstance(x, str)]) == 4  # every write paced


def test_pace_sleeps_for_delay_and_waits_for_enter_in_step_mode():
    slept, prompts, lines = [], [], []
    make_pace(1.5, False, lines.append, sleep=slept.append)("a step")
    make_pace(1.5, True, lines.append, wait=prompts.append, sleep=slept.append)("b step")
    make_pace(0, False, lines.append, sleep=slept.append)("c step")
    assert slept == [1.5] and len(prompts) == 1 and lines == ["  a step", "  b step", "  c step"]


def test_live_refuses_to_start_without_a_server_and_does_not_start_one(tmp_path):
    with pytest.raises(LiveError, match="never starts one"):
        preflight("http://127.0.0.1:9")  # nothing listens on the discard port
    with pytest.raises(LiveError):
        run_live("http://127.0.0.1:9", discover(), tmp_path, "cmd")
    assert list(tmp_path.iterdir()) == []


def test_live_refuses_a_results_root_inside_the_recorded_results():
    with pytest.raises(LiveError, match="recorded results"):
        run_live("http://127.0.0.1:9", [], RESULTS_ROOT / "x", "cmd")


def baseline_connect(scope, pace):
    from demo.baseline import Baseline
    return Baseline()


def test_live_run_is_labelled_live_and_written_apart(tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")
    lines = []
    result = run_live("http://live.example", [c1], tmp_path / "live", "python -m demo.run --mode live", as_system="upstream",
                      log=lines.append, connect=baseline_connect)
    (v,) = result.verdicts
    assert v.system == "live" and v.row == "C1"
    assert result.dir.parent == tmp_path / "live"
    assert (result.dir / "scorecard-live.md").read_text().startswith("**LIVE RUN")
    assert not (result.dir / "scorecard.md").exists()
    data = json.loads((result.dir / "results.json").read_text())
    assert data["mode"] == "live" and data["complete"] is True
    assert all(x["mode"] == "live" and x["system"] == "live" for x in data["verdicts"])
    assert (result.dir / v.snapshot).is_file() and "snapshots/live/" in v.snapshot
    assert lines and all(x.startswith("[LIVE]") for x in lines)


def test_live_run_prints_storyline_tables_but_not_a_scorecard_row(tmp_path):
    storyline = next(c for c in discover() if c.id == "Storyline")
    result = run_live("http://live.example", [storyline], tmp_path / "live", "cmd", as_system="upstream",
                      log=lambda m: None, connect=baseline_connect)
    (v,) = result.verdicts
    assert v.row == "Storyline" and v.system == "live"
    out = result.scorecard
    assert "### Storyline: search failures vs memory failures" in out
    assert "| Storyline" not in out.split("### Storyline")[0]
    data = json.loads((result.dir / "results.json").read_text())
    assert data["rows"] == []
    assert all(n == 0 for n in data["counts"]["live (http://live.example)"].values())


def test_live_run_honours_the_check_system_filter_and_records_errors(tmp_path):
    from demo.checks import check
    from demo.verdict import Verdict

    @check(row="L1", claim="only on patch", systems=("step1",))
    def only_patch(ctx):
        return Verdict.not_scored("L1")

    @check(row="L2", claim="crashes")
    def crashes(ctx):
        ctx.system.ingest({"placement": "new_topic", "title": "x"})
        raise RuntimeError("boom")

    result = run_live("http://live.example", [only_patch, crashes], tmp_path, "cmd", log=lambda m: None,
                      connect=baseline_connect)
    assert [(v.row, v.verdict) for v in result.verdicts] == [("L2", "error")]


def test_run_live_passes_its_pace_to_every_system_a_check_opens(tmp_path):
    from demo.baseline import Baseline

    class PacedBaseline(Baseline):
        def __init__(self, pace):
            super().__init__()
            self.pace = pace

        def _ingest(self, request):
            response = super()._ingest(request)
            self.pace("ingest")
            return response

    slept = []
    c1 = next(c for c in discover() if c.id == "C1")
    run_live("http://live.example", [c1], tmp_path, "cmd", delay=2, log=lambda m: None, sleep=slept.append,
             connect=lambda scope, pace: PacedBaseline(pace))
    assert slept == [2, 2]  # C1 ingests twice


def test_pause_stays_out_of_the_recorded_latency(monkeypatch):
    import time
    s = LiveSystem("live", "http://x", "C9", pace=lambda what: time.sleep(0.3))
    monkeypatch.setattr("demo.client.MemStateSystem._ingest", lambda self, r: {})
    s.ingest({"placement": "new_topic", "title": "T"})
    (entry,) = s.log.entries
    assert entry["latency_ms"] < 100


@pytest.mark.parametrize("argv, message", [
    (["--mode", "live"], "--url"),
    (["--mode", "live", "--url", "http://x", "--systems", "upstream"], "--systems"),
    (["--mode", "live", "--url", "http://x", "--as", "baseline"], "--as"),
    (["--mode", "live", "--url", "http://x", "--as", "nope"], "--as"),
])
def test_live_argument_errors_exit_before_touching_a_server(argv, message, capsys):
    from demo.run import main
    with pytest.raises(SystemExit) as e:
        main(argv)
    assert e.value.code == 2 and message in capsys.readouterr().err
