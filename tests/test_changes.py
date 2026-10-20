"""The per-step change table and the patch column, from verdicts built directly and from a recorded run."""

import json
from contextlib import contextmanager
from datetime import date

from demo.baseline import Baseline
from demo.changes import case_changes_per_step, changes_per_step, render_change_table
from demo.checks import Row, discover
from demo.run import run_recorded
from demo.scorecard import COLUMNS, render_scorecard
from demo.systems import SystemSpec
from demo.verdict import ERROR, Case, Verdict

ROWS = [Row("C1", "c1", control=True), Row("C2a", "c2a"), Row("C3", "c3")]


def v(system, row, verdict):
    return Verdict(row=row, verdict=verdict, system=system)


def test_changed_cells_are_marked_against_the_previous_measured_column_and_unchanged_ones_are_not():
    verdicts = [v("upstream", "C1", "pass"), v("step1", "C1", "pass"), v("step2", "C1", "pass"),
                v("upstream", "C3", "fail"), v("step1", "C3", "fail"), v("step2", "C3", "partial"),
                v("step3", "C3", "pass")]
    table = render_change_table(ROWS, verdicts)
    lines = {line.split("|")[1].strip(): [c.strip() for c in line.split("|")[2:-1]]
             for line in table.splitlines() if line.startswith("| C")}
    assert lines["C1 (control)"] == ["pass", "pass", "pass", "—"]
    assert lines["C3"] == ["fail", "fail", "**fail → partial** (vs step 1)", "**partial → pass** (vs step 2)"]
    assert lines["C2a"] == ["—", "—", "—", "—"]
    assert "- step 1 vs upstream: no change." in table
    assert "- step 2 vs step 1: changed: C3 (fail → partial)." in table
    assert changes_per_step(ROWS, verdicts)["step3"] == [{"row": "C3", "from": "partial", "to": "pass", "vs": "step2"}]


def test_step_one_is_compared_with_upstream_verdict_for_verdict():
    table = render_change_table(ROWS, [v("upstream", "C2a", "partial"), v("step1", "C2a", "partial")])
    assert "| C2a | partial | partial | — | — |" in table
    assert "- step 1 vs upstream: no change." in table


def test_a_step_compared_when_upstream_was_not_measured_reports_nothing_to_compare_against():
    table = render_change_table(ROWS, [v("step1", "C1", "pass")])
    assert "step 1 vs" not in table and "| C1 (control) | — | pass | — | — |" in table


def test_patch_column_shows_the_last_step_measured_and_says_which():
    verdicts = [v("step1", "C1", "fail"), v("step2", "C1", "pass"), v("upstream", "C1", "pass")]
    card = render_scorecard(ROWS[:1], COLUMNS, verdicts)
    assert "bitemporal patch (step2, LadybugDB)" in card
    patch_cell = card.splitlines()[2].split("|")[4].strip()
    assert patch_cell == "pass"
    assert "no step measured" in render_scorecard(ROWS[:1], COLUMNS, [v("upstream", "C1", "pass")])


def test_a_patch_cell_from_an_earlier_step_than_the_header_names_says_which_step_it_is():
    # C1 was measured on step 1 and step 2, C3 only on step 1: step 2 heads the column, C3's cell is step 1's
    verdicts = [v("step1", "C1", "fail"), v("step2", "C1", "pass"), v("step1", "C3", "fail")]
    rows = {line.split("|")[1].strip(): line.split("|")[4].strip()
            for line in render_scorecard([ROWS[0], ROWS[2]], COLUMNS, verdicts).splitlines() if line.startswith("| C")}
    assert rows == {"C1 (control)": "pass", "C3": "fail (from step1)"}


def _baseline_spec(system_id):
    @contextmanager
    def open_fn(tag_id, run):
        yield Baseline()
    return SystemSpec(system_id, system_id, open_fn)


def test_a_recorded_run_prints_the_change_table_and_stores_it_in_results(tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")
    registry = {s: _baseline_spec(s) for s in ("upstream", "step1")}
    run = run_recorded(["upstream", "step1"], [c1], tmp_path, "cmd", run_day=date(2026, 10, 20),
                       registry=registry, runtime_root=tmp_path / "rt", log=lambda *_: None)
    assert "### Per-step change table" in run.scorecard
    assert "- step 1 vs upstream: no change." in run.scorecard
    results = json.loads((run.dir / "results.json").read_text())
    assert results["change_table"] == {"chain": ["upstream", "step1", "step2", "step3"],
                                       "measured": ["upstream", "step1"], "changes": {"step1": []},
                                       "case_changes": {"step1": []}}
    assert any("bitemporal patch (step1, LadybugDB)" == c["header"] for c in results["columns"])


def test_a_baseline_only_run_has_no_change_table(tmp_path):
    c1 = next(c for c in discover() if c.id == "C1")
    run = run_recorded(["baseline"], [c1], tmp_path, "cmd", run_day=date(2026, 10, 20),
                       registry={"baseline": _baseline_spec("baseline")}, runtime_root=tmp_path / "rt",
                       log=lambda *_: None)
    assert "change table" not in run.scorecard


def test_error_cells_are_never_marked_and_never_a_baseline():
    # step 1 failed to run: not a flip into error, and step 2 compares with upstream's real verdict
    verdicts = [v("upstream", "C3", "fail"), v("step1", "C3", ERROR), v("step2", "C3", "fail")]
    table = render_change_table(ROWS, verdicts)
    assert "| C3 | fail | error | fail | — |" in table
    assert "- step 1 not compared, error: C3." in table
    assert "- step 2 vs upstream: no change." in table
    assert changes_per_step(ROWS, verdicts) == {"step1": [], "step2": []}


def test_an_upstream_error_gives_the_next_step_nothing_to_be_marked_against():
    verdicts = [v("upstream", "C1", ERROR), v("step1", "C1", "pass"), v("step2", "C1", "fail")]
    table = render_change_table(ROWS, verdicts)
    assert "| C1 (control) | error | pass | **pass → fail** (vs step 1) | — |" in table
    assert "- step 1 nothing earlier to compare with: C1." in table
    assert "**error" not in table and "→ pass**" not in table


def test_each_marked_cell_and_the_summary_name_the_system_compared_with_per_row():
    # C1 has no step 1 verdict, so at step 2 it is compared with upstream; C3 with step 1
    verdicts = [v("upstream", "C1", "pass"), v("step2", "C1", "fail"),
                v("upstream", "C3", "fail"), v("step1", "C3", "fail"), v("step2", "C3", "pass")]
    table = render_change_table(ROWS, verdicts)
    assert "| C1 (control) | pass | — | **pass → fail** (vs upstream) | — |" in table
    assert "| C3 | fail | fail | **fail → pass** (vs step 1) | — |" in table
    assert "- step 2 vs upstream (C1): changed: C1 (pass → fail); vs step 1 (C3): changed: C3 (fail → pass)." in table
    assert changes_per_step(ROWS, verdicts)["step2"] == [{"row": "C1", "from": "pass", "to": "fail", "vs": "upstream"},
                                                         {"row": "C3", "from": "fail", "to": "pass", "vs": "step1"}]


def test_a_storyline_only_run_has_no_measured_systems_and_no_changes_for_the_steps(tmp_path):
    storyline = next(c for c in discover() if c.id == "Storyline")
    registry = {s: _baseline_spec(s) for s in ("upstream", "step1")}
    run = run_recorded(["upstream", "step1"], [storyline], tmp_path, "cmd", run_day=date(2026, 10, 20),
                       registry=registry, runtime_root=tmp_path / "rt", log=lambda *_: None)
    table = json.loads((run.dir / "results.json").read_text())["change_table"]
    assert table["measured"] == [] and table["changes"] == {}
    assert "change table" not in run.scorecard


def cv(system, row, verdict, **held):
    """A verdict with cases `{id: held}` (True held, False broken, None n/a)."""
    return Verdict(row=row, verdict=verdict, system=system,
                   cases=[Case(f"case {i}", h, id=i) for i, h in held.items()])


C4_ROWS = [Row("C4", "c4"), Row("C1", "c1", control=True)]


def test_a_row_whose_verdict_is_unchanged_but_whose_case_outcomes_changed_lists_the_cases():
    verdicts = [cv("upstream", "C4", "partial", update=True, merge=False, archive=False),
                cv("step1", "C4", "partial", update=True, merge=False, archive=False),
                cv("step2", "C4", "partial", update=True, merge=True, archive=False),
                cv("upstream", "C1", "pass", default=True), cv("step1", "C1", "pass", default=True),
                cv("step2", "C1", "pass", default=True)]
    table = render_change_table(C4_ROWS, verdicts)
    assert "| C4 | partial | partial | partial | — |" in table
    assert "- step 2 cases: C4: partial → partial · case merge: broken → fixed" in table
    assert "- step 1 cases" not in table and "C1:" not in table.split("cases")[-1]
    assert case_changes_per_step(C4_ROWS, verdicts) == {
        "step1": [], "step2": [{"row": "C4", "from": "partial", "to": "partial", "vs": "step1", "cases": [
            {"case": "merge", "name": "case merge", "from": "broken", "to": "fixed"}]}]}


def test_a_row_with_no_case_change_lists_nothing():
    verdicts = [cv("upstream", "C1", "pass", default=True), cv("step1", "C1", "pass", default=True)]
    table = render_change_table(C4_ROWS, verdicts)
    assert "cases:" not in table
    assert case_changes_per_step(C4_ROWS, verdicts) == {"step1": []}


def test_a_case_not_applicable_on_one_system_and_held_on_the_next_reads_n_a_to_held():
    verdicts = [cv("upstream", "C4", "pass", update=True, archive=None), cv("step1", "C4", "pass", update=True, archive=True)]
    table = render_change_table(C4_ROWS, verdicts)
    assert "- step 1 cases: C4: pass → pass · case archive: n/a → held" in table


def test_case_changes_follow_the_verdict_comparison_chain_skipping_errors_and_unmeasured_steps():
    verdicts = [cv("upstream", "C4", "fail", merge=False), v("step1", "C4", ERROR), cv("step2", "C4", "pass", merge=True)]
    changes = case_changes_per_step(C4_ROWS, verdicts)
    assert changes["step1"] == []
    assert changes["step2"][0]["vs"] == "upstream" and changes["step2"][0]["cases"][0]["to"] == "fixed"
    assert "- step 2 cases: C4: fail → pass · case merge: broken → fixed" in render_change_table(C4_ROWS, verdicts)


def test_random_id_counts_are_shown_but_not_compared():
    def natural(system, count):
        return Verdict(row="C2a", verdict="partial", system=system, measurements={"natural_count": count},
                       cases=[Case("existence", False, id="existence")])
    rows = [Row("C2a", "c2a")]
    verdicts = [natural("upstream", "10/20"), natural("step1", "3/20")]
    table = render_change_table(rows, verdicts)
    assert "- step 1 cases: C2a: partial → partial · random-ID count 10/20 → 3/20 (shown, not compared)" in table
    assert case_changes_per_step(rows, verdicts) == {"step1": [{"row": "C2a", "from": "partial", "to": "partial",
                                                                "vs": "upstream", "cases": [],
                                                                "counts": {"from": "10/20", "to": "3/20"}}]}


def test_generic_over_any_chain():
    chain = ("phase1", "phase2")
    verdicts = [cv("phase1", "C4", "partial", merge=False), cv("phase2", "C4", "partial", merge=True)]
    table = render_change_table(C4_ROWS, verdicts, chain)
    assert "- phase2 cases: C4: partial → partial · case merge: broken → fixed" in table
