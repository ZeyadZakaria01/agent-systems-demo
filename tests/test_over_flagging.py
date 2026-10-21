"""The over-flagging measurement (ticket 28): one chain A <- B <- C <- D, D the anti-trap, run on the reference GEM with
one-hop propagation and with the transitive walk. Counts only, no verdict; no MemState system is measured (F17)."""

import json
from datetime import date

import pytest

from demo.checks import discover
from demo.over_flagging import SCENARIO_PATH, load_scenario, measure
from demo.over_flagging_tables import render_over_flagging
from demo.reference_gem import ReferenceGem
from demo.session import Session
from demo.verdict import NOT_SCORED


def check():
    return next(c for c in discover() if c.id == "Over-flagging")


def test_the_scenario_file_labels_the_dependents_that_need_revision():
    scenario = load_scenario()
    assert list(scenario["topics"]) == ["A", "B", "C", "D"]
    assert [k for k, t in scenario["topics"].items() if t.get("depends_on")] == ["B", "C", "D"]
    assert scenario["needs_revision"] == {"B": True, "C": True, "D": False}
    assert scenario["update"]["topic"] == "A"
    assert json.loads(SCENARIO_PATH.read_text()) == scenario


def test_one_hop_raises_b_only_and_misses_c():
    c = measure(ReferenceGem(), "one hop")
    assert (c.raised, c.needed, c.missed, c.not_needed) == (["B"], ["B", "C"], ["C"], [])


def test_the_transitive_walk_raises_b_c_and_d_and_d_is_not_needed():
    c = measure(ReferenceGem(propagation="transitive"), "transitive walk")
    assert (c.raised, c.needed, c.missed, c.not_needed) == (["B", "C", "D"], ["B", "C"], [], ["D"])


def test_the_default_is_one_hop_and_an_unknown_mode_is_refused():
    assert ReferenceGem().propagation == "one_hop"
    assert ReferenceGem().describe()["parameters"]["propagation"].startswith("one hop")
    with pytest.raises(ValueError):
        ReferenceGem(propagation="two_hops")


def test_the_walk_terminates_on_a_cycle_and_never_flags_the_updated_topic():
    gem = ReferenceGem(propagation="transitive")
    ids = [gem.ingest({"placement": "new_topic", "title": t,
                       "fields": [{"name": "F", "value": "1", "provenance": "t"}]})["topic_id"] for t in "XYZ"]
    for src, dst in ((0, 1), (1, 2), (2, 0)):
        gem.setup_write("add_edge", label="cycle edge", from_id=ids[src], to_topic_id=ids[dst], kind="extension")
    gem.ingest({"placement": "version_field", "topic_id": ids[0], "fields": [{"name": "F", "value": "2", "provenance": "t"}]})
    flagged = [bool(gem.read_topic(i)["revision_flag"]["flagged"]) for i in ids]
    assert flagged == [False, True, True]


def test_the_check_reports_both_runs_with_no_verdict():
    [v] = check().execute(Session.in_process(ReferenceGem), run_day=date(2026, 10, 21))
    assert v.verdict == NOT_SCORED
    one_hop, transitive = v.measurements["over_flagging"]["runs"]
    assert (one_hop["mode"], one_hop["flags_raised"], one_hop["flags_needed"], one_hop["flags_missed"],
            one_hop["flags_not_needed"]) == ("one hop", 1, 2, 1, 0)
    assert (transitive["mode"], transitive["flags_raised"], transitive["flags_needed"], transitive["flags_missed"],
            transitive["flags_not_needed"]) == ("transitive walk", 3, 2, 0, 1)
    json.dumps(v.to_dict())  # lands in results.json


def test_the_check_is_not_a_scorecard_row_and_runs_on_the_reference_gem_only():
    c = check()
    assert not c.rows[0].on_scorecard
    assert c.applies_to("reference-gem") and not c.applies_to("upstream") and not c.applies_to("step3")


def test_the_table_lists_both_runs_and_is_empty_without_one():
    [v] = check().execute(Session.in_process(ReferenceGem), run_day=date(2026, 10, 21))
    v.system = "reference-gem"
    table = render_over_flagging([v])
    assert "| reference-gem | one hop | 1 (B) | 2 (B, C) | 1 (C) | 0 (none) |" in table
    assert "| reference-gem | transitive walk | 3 (B, C, D) | 2 (B, C) | 0 (none) | 1 (D) |" in table
    assert "not a verdict" in table.lower()
    assert render_over_flagging([]) == ""
