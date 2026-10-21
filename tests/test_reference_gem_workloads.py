"""Reference GEM workloads (ticket 30): both phases registered, the windows counted in interactions, the storyline."""

from datetime import date
from functools import partial

import pytest

from demo import merge, ramp
from demo.checks import discover
from demo.checks.c2a_merge import measure_merges
from demo.latency_tables import render_latency
from demo.merge import DEADLINE, create_duplicate_pair
from demo.baseline import Baseline
from demo.reference_gem import PHASES, ReferenceGem, reference_gem_id
from demo.run import run_recorded
from demo.session import Session
from demo.storyline import WEBSITE_REDESIGN
from demo.systems import SYSTEMS
from demo.triage import CORRECT, run_storyline
from demo.verdict import Verdict
from demo.windows import interactions, render_windows

IDS = tuple(map(reference_gem_id, PHASES))
RUN_DAY = date(2026, 10, 21)


def by_row(row):
    return next(c for c in discover() if row in {r.id for r in c.rows})


def window(verdict, name):
    return next(w["value"] for w in verdict.measurements["windows"] if w["name"] == name)


@pytest.mark.parametrize("phase", (1, 2))
def test_registered_in_process_and_declares_its_milliseconds_not_comparable(phase):
    spec = SYSTEMS[IDS[phase - 1]]
    assert spec.label == f"reference GEM (phase {phase})" and spec.step is None
    assert Baseline().describe()["latency_comparable"] is True
    order = list(SYSTEMS)
    assert order.index("step3") < order.index(IDS[0]) < order.index(IDS[1]) < order.index("baseline")
    system = spec.open("C1", None).__enter__()
    assert isinstance(system, ReferenceGem) and system.phase == phase and system.label == spec.label
    assert system.describe()["latency_comparable"] is False
    assert IDS == ("reference-gem-p1", "reference-gem-p2")


@pytest.mark.parametrize("phase", (1, 2))
def test_merge_window_is_zero_interactions_with_revision_after_every_ingest(phase):
    v = measure_merges(ReferenceGem(phase=phase), repetitions=20, timeout=0.3)  # the extras' merge wait times out by design
    assert v.measurements["window_samples_interactions"] == [0] * 20
    assert v.measurements["window_median_interactions"] == 0
    assert (v.measurements["window_min_interactions"], v.measurements["window_max_interactions"]) == (0, 0)
    assert window(v, "Merge revision window") == "median 0 interactions, range 0-0 over 20 repetitions"


def test_pre_merge_window_is_exposed_when_revision_is_held_back():
    gem = ReferenceGem(revise_after_ingest=False)
    pair = create_duplicate_pair(gem, "Vendor Contract", DEADLINE)
    assert gem.read_topic(pair.older_id) and gem.read_topic(pair.newer_id)  # both copies visible
    before = gem.interactions
    gem.revise()
    assert gem.interactions == before  # revising is no interaction: the window counts the ingests and queries between
    assert [gem.read_topic(t) is None for t in (pair.older_id, pair.newer_id)].count(True) == 1  # the lower id survives


@pytest.mark.parametrize("phase", (1, 2))
def test_dependent_topic_window_is_zero_interactions(phase):
    [v] = by_row("C3").execute(Session.in_process(partial(ReferenceGem, phase=phase)), run_day=RUN_DAY)
    assert v.verdict == "pass"
    assert window(v, "Dependent-topic staleness window") == "median 0 interactions (B->A 0, A->B 0)"


def test_windows_table_cites_the_interaction_unit():
    [v] = by_row("C3").execute(Session.in_process(ReferenceGem), run_day=RUN_DAY)
    v.system = IDS[0]
    assert "0 interactions" in render_windows([v])


def test_interactions_helper_is_none_where_the_system_does_not_count():
    from demo.baseline import Baseline
    assert interactions(Baseline()) is None
    gem = ReferenceGem()
    gem.ingest({"placement": "new_topic", "title": "T"})
    assert interactions(gem) == 1


@pytest.mark.parametrize("phase", (1, 2))
def test_storyline_counts(phase):
    run = run_storyline(ReferenceGem(phase=phase), WEBSITE_REDESIGN)
    assert run.top_k == 8
    assert run.triage == {"questions": 15, "correct": 15, "search_failures": 0, "memory_failures": 0}
    assert run.reinforcement.precision == pytest.approx(1 / 8)


def test_c5_states_beta_beside_the_active_count_at_2000(monkeypatch):
    monkeypatch.setattr(ramp, "REPEATS", 1)
    v = by_row("C5-2").execute(Session.in_process(ReferenceGem), run_day=RUN_DAY)[0]
    text = v.cases[0].observation
    assert "declared bound 500 topics (β)" in text and "active topics at n=2000" in text
    active = v.measurements["active_at_largest_n"]["active"]
    assert 300 <= active <= 500


def test_c5_runs_each_size_once_and_records_no_milliseconds_on_the_reference_gem(monkeypatch):
    monkeypatch.setattr(ramp, "STEPS", (20, 40))
    monkeypatch.setattr(ramp, "REPEATS", 3)
    v = by_row("C5-2").execute(Session.in_process(ReferenceGem), run_day=RUN_DAY)[0]
    ramps = v.measurements["ramps"]
    assert [(r["n"], r["repeat"]) for r in ramps] == [(20, 1), (40, 1)]  # not 3 repeats
    assert v.measurements["repeats"] == 1
    assert all(set(r) == {"n", "repeat", "total", "archived"} for r in ramps)  # counts only: no timing of any kind
    assert "active topics at n=40" in v.cases[0].observation


def test_runner_runs_reference_gem_both_phases_and_shows_no_latency(tmp_path, monkeypatch):
    monkeypatch.setattr(merge, "DEFAULT_TIMEOUT_S", 0.3)  # C2(a)'s active-into-archived extra times out by design
    checks = [c for c in discover() if c.id in {"C2(a)", "C3", "Storyline"}]
    run = run_recorded(list(IDS), checks, tmp_path, "python -m demo.run test", run_day=RUN_DAY,
                       runtime_root=tmp_path / "runtime")
    assert {(v.system, v.row) for v in run.verdicts} >= {(i, "C3") for i in IDS}
    assert not any(v.verdict == "error" for v in run.verdicts), [v.error for v in run.verdicts if v.error]
    assert "Latency ramps" not in run.scorecard
    assert "interactions" in run.scorecard


def test_latency_table_leaves_out_a_system_whose_ramps_carry_no_timing():
    timed = [{"n": 2, "repeat": 1, "total": 2, "archived": 0, "ingest_median_ms": 0.1, "ingest_samples": 2,
              "query_samples_ms": [0.2], "settle_s": 0.1, "settle_timed_out": False}]
    untimed = [{"n": 2, "repeat": 1, "total": 2, "archived": 0}]
    out = []
    for system, ramps in (("upstream", timed), (IDS[0], untimed)):
        v = Verdict.from_cases("C5-2", [], measurements={"ramps": ramps})
        v.system = system
        out.append(v)
    table = render_latency(out)
    assert "upstream" in table and IDS[0] not in table
