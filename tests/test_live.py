"""Live mode, in-process: real checks on the baseline through the live runner (`connect=`). The server-facing path
(title scoping and pacing on `LiveSystem`) is proven by the smoke run (docs/findings.md F14), not by mocks."""

import json

import pytest

from demo.checks import check, discover
from demo.live import LiveError, preflight, run_live
from demo.paths import RESULTS_ROOT
from demo.systems.baseline import Baseline
from demo.verdict import Verdict


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
    return Baseline()


def test_live_run_is_labelled_live_and_written_apart(tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")
    lines = []
    result = run_live(
        "http://live.example",
        [c1],
        tmp_path / "live",
        "python -m demo.run --mode live",
        as_system="upstream",
        log=lines.append,
        connect=baseline_connect,
    )
    (v,) = result.verdicts
    assert v.system == "live" and v.row == "C1"
    assert result.dir.parent == tmp_path / "live"
    assert (result.dir / "scorecard-live.md").read_text().startswith("**LIVE RUN")
    assert not (result.dir / "scorecard.md").exists()
    data = json.loads((result.dir / "results.json").read_text())
    assert data["mode"] == "live" and data["complete"] is True
    assert all(x["mode"] == "live" and x["system"] == "live" for x in data["verdicts"])
    assert (result.dir / v.snapshot).is_file()
    assert lines and all(x.startswith("[LIVE]") for x in lines)


def test_live_run_prints_storyline_tables_but_not_a_scorecard_row(tmp_path):
    storyline = next(c for c in discover() if c.id == "Storyline")
    result = run_live(
        "http://live.example",
        [storyline],
        tmp_path / "live",
        "cmd",
        as_system="upstream",
        log=lambda m: None,
        connect=baseline_connect,
    )
    (v,) = result.verdicts
    assert v.row == "Storyline" and v.system == "live"
    out = result.scorecard
    assert "### Storyline: search failures vs memory failures" in out
    assert "| Storyline" not in out.split("### Storyline")[0]
    data = json.loads((result.dir / "results.json").read_text())
    assert data["rows"] == []
    assert all(n == 0 for n in data["counts"]["live (http://live.example)"].values())


def test_live_run_honours_the_check_system_filter_and_records_errors(tmp_path):
    @check(row="L1", claim="only on patch", systems=("step1",))
    def only_patch(ctx):
        return Verdict.not_scored("L1")

    @check(row="L2", claim="crashes")
    def crashes(ctx):
        ctx.system.ingest({"placement": "new_topic", "title": "x"})
        raise RuntimeError("boom")

    result = run_live(
        "http://live.example", [only_patch, crashes], tmp_path, "cmd", log=lambda m: None, connect=baseline_connect
    )
    assert [(v.row, v.verdict) for v in result.verdicts] == [("L2", "error")]


def test_every_check_and_every_fresh_system_gets_its_own_scope_for_its_titles(tmp_path):
    scopes = []

    def connect(scope, pace):
        scopes.append(scope)
        return Baseline()

    @check(row="L3", claim="two stories")
    def stories(ctx):
        for tag in ("story-1", "story-2"):
            with ctx.fresh_system(tag):
                pass
        return Verdict.not_scored("L3")

    c1 = next(c for c in discover() if c.id == "C1")
    run_live("http://live.example", [c1, stories], tmp_path, "cmd", log=lambda m: None, connect=connect)
    assert len(scopes) == len(set(scopes)) == 3 and all(s.startswith(("C1 ", "L3--story-")) for s in scopes)
