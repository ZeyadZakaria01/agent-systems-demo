"""The recorded runner, evidence and scorecard, run in-process on the baseline into a temporary results directory."""

import json
from contextlib import contextmanager
from datetime import date

import pytest

from demo.baseline import Baseline
from demo.checks import Row, check, discover
from demo.run import run_recorded
from demo.server import ServerError
from demo.systems import SYSTEMS, SystemSpec
from demo.verdict import Case, Verdict


def two_row_check():
    @check(rows=[Row("X1", "claim of X1", control=True), Row("X2", "claim of X2")])
    def x(ctx):
        s = ctx.system
        s.setup_write("create_topic", label="arrange a forced id", topic_id="t0", title="T0")
        t = s.ingest({"placement": "new_topic", "title": "T", "fields": [{"name": "F", "value": "v"}]})
        s.query({"q": "T", "stages": ["temporal"], "topic_ids": [t["topic_id"]]})
        return [Verdict.from_cases("X1", [Case("holds", True)]),
                Verdict.absent("X2", probe_evidence={"probe": "asked for edges", "observed": "none"})]
    return x


def crashing_check():
    @check(row="X3", claim="claim of X3")
    def boom(ctx):
        ctx.system.ingest({"placement": "new_topic", "title": "before the crash"})
        raise RuntimeError("boom")
    return boom


def recorded(tmp_path, checks, systems=("baseline",), registry=None):
    return run_recorded(systems=list(systems), checks=checks, results_root=tmp_path,
                        command="python -m demo.run test", run_day=date(2026, 10, 20),
                        registry=registry or SYSTEMS, runtime_root=tmp_path / "runtime")


def load(path):
    return json.loads(path.read_text())


def test_each_run_writes_its_own_directory_with_a_machine_readable_results_file(tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")
    first = recorded(tmp_path, [c1])
    second = recorded(tmp_path, [c1])
    assert first.dir != second.dir and first.dir.parent == tmp_path
    results = load(first.dir / "results.json")
    (v,) = results["verdicts"]
    assert (v["row"], v["system"], v["verdict"], v["control"]) == ("C1", "baseline", "pass", True)
    assert (first.dir / v["snapshot"]).is_file()
    assert results["mode"] == "recorded" and results["command"] == "python -m demo.run test"
    assert results["complete"] is True and results["deviations"]


def test_snapshot_holds_requests_state_timestamps_and_keeps_setup_writes_apart(tmp_path):
    run = recorded(tmp_path, [two_row_check()])
    snap = load(run.dir / run.verdicts[0].snapshot)
    assert snap["system"] == "baseline"
    for key in ("db_path", "commit", "engine"):
        assert key in snap["describe"]
    assert snap["started_at"] and snap["finished_at"]
    # scored transitions carry request, response and timestamps; the setup write is not among them
    ops = [(e["op"], e["request"]["placement"] if e["op"] == "ingest" else None) for e in snap["scored_transitions"]]
    assert ops == [("ingest", "new_topic"), ("query", None)]
    assert snap["scored_transitions"][0]["response"]["topic_id"] == "T"
    assert snap["scored_transitions"][0]["started_at"] and snap["scored_transitions"][0]["finished_at"]
    assert [e["request"]["label"] for e in snap["setup_writes"]] == ["arrange a forced id"]
    assert "T" in snap["state"]["topics"] and "edges" in snap["state"]
    # both rows of one check share the check's snapshot
    assert run.verdicts[0].snapshot == run.verdicts[1].snapshot


def test_scorecard_lists_claims_and_snapshot_links_and_counts_fails_and_absences_separately(tmp_path):
    run = recorded(tmp_path, [two_row_check()])
    assert "claim of X1" in run.scorecard and "claim of X2" in run.scorecard
    assert all(v.snapshot in run.scorecard for v in run.verdicts)
    counts = load(run.dir / "results.json")["counts"]["baseline"]
    assert (counts["pass"], counts["fail"], counts["absent"]) == (1, 0, 1)


def test_a_crashing_check_is_recorded_as_an_error_with_its_snapshot_and_the_run_continues(tmp_path):
    run = recorded(tmp_path, [crashing_check(), two_row_check()])
    by_row = {v.row: v for v in run.verdicts}
    assert by_row["X3"].verdict == "error" and "boom" in by_row["X3"].error
    snap = load(run.dir / by_row["X3"].snapshot)
    assert [e["request"]["title"] for e in snap["scored_transitions"]] == ["before the crash"]
    assert by_row["X1"].verdict == "pass"


def test_an_aborted_run_keeps_the_verdicts_collected_so_far(tmp_path):
    @check(row="X4", claim="claim of X4")
    def interrupted(ctx):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        recorded(tmp_path, [two_row_check(), interrupted])
    (run_dir,) = tmp_path.iterdir()
    results = load(run_dir / "results.json")
    assert results["complete"] is False
    assert sorted(v["row"] for v in results["verdicts"]) == ["X1", "X2"]


def failing_open(check_id, run):
    @contextmanager
    def cm():
        raise ServerError("port 8765 is busy")
        yield
    return cm()


def test_a_system_that_cannot_open_gives_error_verdicts_and_the_run_goes_on(tmp_path):
    registry = {"broken": SystemSpec("broken", "broken", failing_open), **SYSTEMS}
    run = recorded(tmp_path, [two_row_check()], systems=("broken", "baseline"), registry=registry)
    by_system = {(v.system, v.row): v for v in run.verdicts}
    assert by_system[("broken", "X1")].verdict == "error" and "port 8765" in by_system[("broken", "X1")].error
    assert by_system[("baseline", "X1")].verdict == "pass"


def hooked_registry(events, fail_setup=False):
    @contextmanager
    def open_(check_id, run):
        yield Baseline()

    def setup(run):
        events.append("setup")
        if fail_setup:
            raise RuntimeError("checkout failed")

    return {"hooked": SystemSpec("hooked", "hooked", open_, setup=setup, teardown=lambda run: events.append("teardown"))}


def test_a_systems_setup_and_teardown_hooks_wrap_its_checks_and_teardown_runs_after_errors(tmp_path):
    events = []
    run = recorded(tmp_path, [crashing_check()], systems=("hooked",), registry=hooked_registry(events))
    assert events == ["setup", "teardown"]
    assert run.verdicts[0].verdict == "error"


def test_a_failing_setup_gives_error_verdicts_for_that_system_and_still_runs_teardown(tmp_path):
    events = []
    registry = {**hooked_registry(events, fail_setup=True), "baseline": SYSTEMS["baseline"]}
    run = recorded(tmp_path, [two_row_check()], systems=("hooked", "baseline"), registry=registry)
    assert events == ["setup", "teardown"]
    hooked = [v for v in run.verdicts if v.system == "hooked"]
    assert {v.row for v in hooked} == {"X1", "X2"} and all("checkout failed" in v.error for v in hooked)
    assert any(v.system == "baseline" and v.verdict == "pass" for v in run.verdicts)


def two_stories_check():
    @check(row="X5", claim="claim of X5")
    def stories(ctx):
        seen = []
        for tag in ("story-1", "story-2"):
            with ctx.fresh_system(tag) as s:
                s.ingest({"placement": "new_topic", "title": f"title of {tag}"})
                seen.append(sorted(s.read_state()["topics"]))
        # each story had its own database: story 2 does not see story 1's topic
        return Verdict.from_cases("X5", [Case("fresh each time", seen == [["title of story-1"], ["title of story-2"]])])
    return stories


def test_a_row_can_be_assembled_from_several_fresh_systems_each_with_its_own_snapshot(tmp_path):
    run = recorded(tmp_path, [two_stories_check()])
    (v,) = run.verdicts
    assert v.verdict == "pass"
    assert len(v.snapshots) == 2 and v.snapshot == v.snapshots[0]
    titles = [list(load(run.dir / p)["state"]["topics"]) for p in v.snapshots]
    assert titles == [["title of story-1"], ["title of story-2"]]


def test_opening_a_second_system_while_one_is_open_fails_clearly(tmp_path):
    @check(row="X6", claim="claim of X6")
    def nested(ctx):
        ctx.system  # the default system stays open until the check ends
        with ctx.fresh_system("again"):
            pass

    run = recorded(tmp_path, [nested])
    assert run.verdicts[0].verdict == "error" and "still open" in run.verdicts[0].error
