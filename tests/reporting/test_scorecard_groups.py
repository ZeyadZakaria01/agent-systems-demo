"""The scorecard layout (ticket 31), rendered from stand-in results: no check runs, no server."""

from demo.checks import Row, discover
from demo.reporting.changes import REFERENCE_CHAIN, regression_summary, render_change_tables
from demo.reporting.latency import render_latency
from demo.reporting.scorecard import (
    COLUMNS,
    claimed_by_p1,
    render_deviations,
    render_limits,
    render_merge_existence,
    render_probes,
    render_scorecard,
)
from demo.verdict import ERROR, Case, Verdict

SYSTEMS = ("upstream", "step1", "step2", "step3", "reference-gem-p1", "reference-gem-p2", "baseline")
ALL_ROWS = [r for c in discover() for r in c.rows if r.on_scorecard]
MAIN_ROWS = [r for r in ALL_ROWS if not r.probe]
PROBE_ROWS = [r for r in ALL_ROWS if r.probe]
MAIN_IDS = ["C1", "C2(a)", "C2(b)", "C2(c)", "C2(d)", "C3", "C4", "C5-1", "C5-2", "C6-1", "C6-2"]
TIME_PROBES = ["T1", "T2", "T3", "T4", "T5", "T6"]


def v(system, row, verdict="pass", cases=(), **kw):
    return Verdict(
        row=row, verdict=verdict, system=system, cases=list(cases), snapshots=[f"snapshots/{system}-{row}.json"], **kw
    )


def everything(verdict="pass"):
    return [
        v(s, r.id, verdict, measurements={"accepts_dates": "yes"} if r.id.startswith("T") else {})
        for s in SYSTEMS
        for r in ALL_ROWS
    ]


def lines_of(text):
    return text.splitlines()


def test_the_main_table_has_the_eleven_rows_and_the_probes_are_not_among_them():
    assert [r.id for r in MAIN_ROWS] == MAIN_IDS
    assert sorted(r.id for r in PROBE_ROWS) == sorted([*TIME_PROBES, "C4′"])
    card = render_scorecard(MAIN_ROWS, COLUMNS, everything())
    first_cells = [line.split("|")[1].strip() for line in lines_of(card)[2:-1]]
    assert [c.split(" ")[0] for c in first_cells] == MAIN_IDS


def test_one_table_in_three_groups_with_the_claim_column_before_the_systems():
    header = lines_of(render_scorecard(MAIN_ROWS, COLUMNS, everything()))[0]
    cells = [c.strip() for c in header.split("|")[1:-1]]
    assert cells[:2] == ["Row", "Claimed by [P1]?"]
    assert [c.split(":")[0] for c in cells[2:]] == ["MemState"] * 4 + ["Reference"] * 2 + ["Baseline"]
    assert [c.split(": ")[1] for c in cells[2:]][1:] == [
        "step 1",
        "step 2",
        "step 3",
        "phase 1",
        "phase 2",
        "versioned row",
    ]


def test_every_row_has_a_claim_cell_and_the_probes_are_not_claimed():
    for r in MAIN_ROWS:
        assert claimed_by_p1(r).startswith("yes"), r.id
    assert "not in §4.3" in claimed_by_p1(next(r for r in MAIN_ROWS if r.id == "C3"))
    for r in MAIN_ROWS:
        if r.id.startswith(("C5", "C6")):
            assert "transitions" in claimed_by_p1(r)
        if r.id in ("C1", "C2(a)", "C2(b)", "C2(c)", "C2(d)", "C4"):
            assert "by construction" in claimed_by_p1(r)
    assert all(claimed_by_p1(r).startswith("no") for r in PROBE_ROWS)
    rows = lines_of(render_scorecard(MAIN_ROWS, COLUMNS, everything()))[2:-1]
    assert all(line.split("|")[2].strip() for line in rows)


def test_a_cell_is_a_verdict_with_its_snapshot_link_and_its_n_a_cases():
    cases = [Case("a", True), Case("b", None)]
    verdicts = [v("step2", "C1", "pass", cases)]
    row = next(line for line in lines_of(render_scorecard(MAIN_ROWS, COLUMNS, verdicts)) if line.startswith("| C1"))
    assert "pass (1 case n/a) [snapshot](snapshots/step2-C1.json)" in row


def test_c5_states_the_declared_bound_beside_the_active_count():
    natural = v(
        "reference-gem-p2",
        "C5-2",
        "pass",
        measurements={
            "declared_bound": {"topics": 500, "name": "β"},
            "active_at_largest_n": {"n": 2000, "active": 400},
        },
    )
    mech = v(
        "upstream",
        "C5-1",
        "partial",
        measurements={"declared_bound": {"topics": 500, "name": "soft limit"}, "topics": 501, "archived_total": 0},
    )
    card = render_scorecard(MAIN_ROWS, COLUMNS, [natural, mech])
    assert "400 active topics at n=2000, declared bound 500 topics" in card
    assert "501 active topics, declared bound 500 topics" in card


def test_the_probes_section_has_two_cells_per_time_probe_and_the_c4_prime_probe():
    verdicts = []
    for s in SYSTEMS:
        for t in TIME_PROBES:
            verdicts.append(
                v(
                    s,
                    t,
                    "absent" if s == "upstream" else "pass",
                    measurements={"accepts_dates": "no" if s == "upstream" else "yes"},
                )
            )
        verdicts.append(v(s, "C4′", "absent" if s == "baseline" else "pass"))
    text = render_probes(ALL_ROWS, COLUMNS, verdicts)
    assert text.startswith("### Probes of the proposed C1′ and C4′, outside [P1]'s claims")
    table = [line for line in lines_of(text) if line.startswith("| T") or line.startswith("| C4")]
    assert len(table) == 6 * 2 + 1
    assert table[0].split("|")[1].strip() == "T1 accepts dates"
    assert table[1].split("|")[1].strip() == "T1 answers correctly given dates"
    assert table[0].split("|")[2].strip() == "no" and table[1].split("|")[2].strip().startswith("absent")
    assert table[-1].split("|")[1].strip().startswith("C4′")


def test_case_level_controls_are_shown_with_the_c4_update_path_and_each_probes_control_date():
    held, broke = Case("control date Dec 20", True, control=True), Case("control date Dec 20", False, control=True)
    update = Case("update survives", True, control=True, id="update")
    verdicts = [
        v("step2", "T1", "pass", [held, Case("asked Mar 1", True)], measurements={"accepts_dates": "yes"}),
        v("upstream", "T1", "fail", [broke], measurements={"accepts_dates": "yes"}),
        v("step2", "C4", "pass", [update, Case("cap", True)]),
    ]
    text = render_probes(ALL_ROWS, COLUMNS, verdicts)
    assert "### Case-level controls" in text
    lines = [line for line in lines_of(text) if line.startswith("| T1: ") or line.startswith("| C4: ")]
    assert any("control date Dec 20" in line and "held" in line and "broke" in line for line in lines)
    assert any("update survives" in line and "held" in line for line in lines)
    assert not any("asked Mar 1" in line for line in lines_of(text))


def test_the_merge_is_printed_as_existence_with_the_natural_random_id_count_beside_it():
    c2a = v(
        "upstream",
        "C2(a)",
        "fail",
        [
            Case(
                "the merge does not make the superseded value current in the arranged case (existence)",
                False,
                "20 of 20 arranged repetitions made March 15 current",
            )
        ],
        measurements={"natural_count": "10/20"},
    )
    text = render_merge_existence(
        MAIN_ROWS,
        COLUMNS,
        [c2a, v("step3", "C2(a)", "pass", [Case("x", True, "0 of 20")], measurements={"natural_count": None})],
    )
    assert "existence" in text
    upstream = next(line for line in lines_of(text) if line.startswith("| MemState: upstream"))
    assert "fail" in upstream and "10/20" in upstream and "random" in text
    step3 = next(line for line in lines_of(text) if line.startswith("| MemState: step 3"))
    assert "n/a" in step3


def test_mem_states_limits_are_stated_with_their_numbers():
    text = render_limits()
    assert "500 entries" in text and "two entries" in text
    assert "500-topic" in text and "2,000" in text


def test_the_deviations_table_lists_the_reference_gem_parameters_seeds_and_the_versioned_row_settings():
    table = render_deviations()
    for needle in (
        "one-hop flagging over extension edges in either direction",
        "single archive threshold",
        "revision (merge) after every ingest, as MemState's Reasoner does",
        "no LLM",
        "restricted",
        "0.06",
        "0.03",
        "0.01",
        "Baseline (versioned row) settings",
        "top 8",
    ):
        assert needle in table or needle.replace("restricted", "limited") in table, needle


def test_the_change_table_has_two_chains():
    verdicts = [
        v("upstream", "C1", "fail"),
        v("step1", "C1", "fail"),
        v("step2", "C1", "pass"),
        v("step3", "C1", "pass"),
        v("reference-gem-p1", "T1", "absent"),
        v("reference-gem-p2", "T1", "pass"),
    ]
    rows = [Row("C1", "c1"), Row("T1", "t1", probe=True)]
    text = render_change_tables(rows, verdicts)
    assert "upstream → step 1 → step 2 → step 3" in text
    assert "phase 1 → phase 2" in text
    assert REFERENCE_CHAIN == ("reference-gem-p1", "reference-gem-p2")
    assert "**absent → pass** (vs phase 1)" in text
    assert "- phase 2 vs phase 1: changed: T1 (absent → pass)." in text


def test_the_summary_claims_no_regressions_only_when_no_row_is_worse_at_step_3_than_at_step_1():
    rows = [Row("C1", "c1"), Row("C3", "c3")]
    fine = [v("step1", "C1", "partial"), v("step3", "C1", "pass"), v("step1", "C3", "fail"), v("step3", "C3", "fail")]
    assert "no regressions on the rows the suite checks" in regression_summary(rows, fine).lower()
    worse = [*fine[:2], v("step1", "C3", "pass"), v("step3", "C3", "partial")]
    said = regression_summary(rows, worse)
    assert "no regressions" not in said.lower() and "C3 (pass → partial)" in said
    flipped = [v("step1", "C1", "partial", [Case("k", True)]), v("step3", "C1", "partial", [Case("k", False)])]
    assert "no regressions" not in regression_summary(rows[:1], flipped).lower()
    assert (
        "no regressions"
        not in regression_summary(rows[:1], [v("step1", "C1", "pass"), v("step3", "C1", ERROR)]).lower()
    )
    assert "no regressions" not in regression_summary(rows[:1], [v("step1", "C1", "pass")]).lower()


def ramp_verdict(system, repeats, ms=100.0):
    ramps = [
        {
            "n": n,
            "repeat": r,
            "ingest_median_ms": ms,
            "query_samples_ms": [ms, ms],
            "settle_s": 0.1,
            "archived": 0,
            "total": n,
        }
        for n in (100, 250)
        for r in range(1, repeats + 1)
    ]
    return v(system, "C5-2", "fail", measurements={"ramps": ramps})


def test_a_ramp_table_from_fewer_than_three_repeats_is_provisional_and_never_says_no_measurable_difference():
    text = render_latency([ramp_verdict("upstream", 1), ramp_verdict("step1", 1)])
    assert "provisional" in text.lower() and "no measurable difference" not in text
    two = render_latency([ramp_verdict("upstream", 2), ramp_verdict("step1", 2)])
    assert "provisional" in two.lower() and "no measurable difference" not in two


def test_with_three_repeats_the_rule_applies_as_before():
    text = render_latency([ramp_verdict("upstream", 3), ramp_verdict("step1", 3)])
    assert "provisional" not in text.lower()
    assert "upstream vs step1 at n=100, ingest: no measurable difference" in text


def test_a_recorded_run_prints_the_probes_section_and_the_limits_and_records_the_claim_column(tmp_path):
    import json
    from datetime import date

    from demo.run import run_recorded
    from demo.systems.registry import SYSTEMS

    checks = [c for c in discover() if c.id in ("C1", "C4′")]
    run = run_recorded(
        ["baseline"],
        checks,
        tmp_path,
        "cmd",
        run_day=date(2026, 10, 20),
        registry=SYSTEMS,
        runtime_root=tmp_path / "rt",
        log=lambda *_: None,
    )
    card = (run.dir / "scorecard.md").read_text()
    assert "### Probes of the proposed C1′ and C4′, outside [P1]'s claims" in card
    assert "### MemState's limits, with their numbers" in card
    assert "no regressions" not in card.lower()  # no MemState step measured: nothing is claimed
    rows = {r["id"]: r for r in json.loads((run.dir / "results.json").read_text())["rows"]}
    assert rows["C1"]["claimed_by_p1"].startswith("yes") and rows["C4′"]["claimed_by_p1"].startswith("no")
    assert rows["C4′"]["probe"] is True
