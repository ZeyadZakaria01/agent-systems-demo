"""The run of record: upstream-test counts in the results and scorecard, and the tracked copy of a run."""

import json
import textwrap
from datetime import date

import pytest

from demo.checks import discover
from demo.record import record_run
from demo.run import run_recorded
from demo.systems import SYSTEMS, SystemSpec
from demo.upstream_tests import TestCounts, count_tests, render_upstream_tests


def fake_counts(passed, failed):
    return TestCounts(passed=passed, failed=failed, total=passed + failed, command="pytest", source_dir="/x")


def with_tests(counts):
    base = SYSTEMS["baseline"]
    return {"baseline": SystemSpec("baseline", "baseline", base.open, unit_tests=lambda: counts)}


def run(tmp_path, registry):
    c1 = next(c for c in discover() if c.id == "C1")
    return run_recorded(
        ["baseline"],
        [c1],
        tmp_path / "results",
        "cmd",
        run_day=date(2026, 10, 20),
        registry=registry,
        runtime_root=tmp_path / "runtime",
    )


def test_counts_per_system_reach_results_and_scorecard_and_a_failing_step_is_flagged(tmp_path):
    ok = run(tmp_path, with_tests(fake_counts(39, 0)))
    results = json.loads((ok.dir / "results.json").read_text())
    assert (results["upstream_tests"]["baseline"]["passed"], results["upstream_tests"]["baseline"]["total"]) == (39, 39)
    assert "| baseline | 39 | 0 | 39 | all pass |" in ok.scorecard

    bad = run(tmp_path, with_tests(fake_counts(38, 1)))
    assert json.loads((bad.dir / "results.json").read_text())["upstream_tests"]["baseline"]["flagged"] is True
    assert "| baseline | 38 | 1 | 39 | **FLAG: not all pass** |" in bad.scorecard


def test_a_test_run_that_cannot_happen_is_flagged_not_fatal(tmp_path):
    def boom():
        raise RuntimeError("no pytest")

    base = SYSTEMS["baseline"]
    result = run(tmp_path, {"baseline": SystemSpec("baseline", "baseline", base.open, unit_tests=boom)})
    assert "FLAG: not run" in result.scorecard
    assert result.verdicts[0].verdict == "pass"


def test_pytest_outcomes_are_counted_without_writing_bytecode_or_cache(tmp_path):
    src = tmp_path / "pkg"
    (src / "tests").mkdir(parents=True)
    (src / "tests" / "test_a.py").write_text(
        textwrap.dedent("""
        def test_ok(): pass
        def test_bad(): assert False
        def test_ok2(): pass
    """)
    )
    counts = count_tests(src)
    assert (counts.passed, counts.failed, counts.total) == (2, 1, 3)
    assert counts.flagged
    assert sorted(p.name for p in src.rglob("*") if p.is_file()) == ["test_a.py"]  # no .pyc, no .pytest_cache


def test_the_scorecard_section_is_empty_when_nothing_was_counted():
    assert render_upstream_tests({}, {}) == ""


def test_record_copies_scorecard_results_and_snapshots_but_not_logs(tmp_path):
    result = run(tmp_path, {"baseline": SYSTEMS["baseline"]})
    (result.dir / "logs").mkdir(exist_ok=True)
    (result.dir / "logs" / "x.log").write_text("log")
    target = record_run(result.dir, tmp_path / "record")
    assert target == tmp_path / "record" / result.dir.name
    assert (target / "scorecard.md").read_text() == (result.dir / "scorecard.md").read_text()
    assert (target / "results.json").exists() and any((target / "snapshots").rglob("*.json"))
    assert not (target / "logs").exists()
    link = next(l for l in (target / "scorecard.md").read_text().split("(") if l.startswith("snapshots/")).split(")")[0]
    assert (target / link).exists()
    with pytest.raises(FileExistsError):
        record_run(result.dir, tmp_path / "record")
