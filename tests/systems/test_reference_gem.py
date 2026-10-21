"""The reference GEM, phase 1 (ticket 26), through the system adapter, in-process: the phase 1 column of the spec's
"Expected verdicts" (written before the build) and the behaviours a scorecard reader relies on. No server, no GPU; the
retrieval model comes from the cached MiniLM. The mutation tests of ticket 29 run the checks on broken subclasses."""

from datetime import date
from math import isclose

import pytest

from demo.systems.adapter import Rejected
from demo.systems.reads import NO_VALUE, current_value, field_in_response, read_request
from demo.systems.reference_gem import BETA, LAMBDA, ReferenceGem
from demo.verdict import ABSENT, PASS
from demo.workloads.storyline import WEBSITE_REDESIGN
from demo.workloads.triage import run_storyline
from tests.systems.reference_runs import unmutated

RUN_DAY = date(2026, 10, 20)


def field(name, value, provenance="test", **extra):
    return {"name": name, "value": value, "provenance": provenance, **extra}


def new(system, title, *fields, **extra):
    return system.ingest({"placement": "new_topic", "title": title, "fields": list(fields), **extra})["topic_id"]


def write(system, topic_id, *fields, placement="version_field", **extra):
    return system.ingest({"placement": placement, "topic_id": topic_id, "fields": list(fields), **extra})


def value(system, topic_id, name):
    return current_value(system.read_topic(topic_id)["fields"].get(name))


# ---------------------------------------------------------------- the phase 1 column of "Expected verdicts"


@pytest.fixture(scope="module")
def verdicts():
    return unmutated(1)


@pytest.mark.parametrize(
    "row", ["C1", "C2(b)", "C2(c)", "C2(d)", "C3", "C4", "C5-1", "C5-2", "C6-1", "C6-2", "C4′", "T1", "T2", "T3", "T6"]
)
def test_the_phase_1_column_passes(verdicts, row):
    v = verdicts[row]
    assert v.verdict == PASS, [(c.name, c.held, c.observation) for c in v.cases]
    assert all(c.held is not None for c in v.cases), "no case is n/a on the reference GEM"


def test_c2a_the_merge_makes_the_later_write_current_in_every_arranged_repetition(verdicts):
    v = verdicts["C2(a)"]
    assert v.verdict == PASS
    assert v.measurements["violations"] == 0 and v.measurements["arrangement_not_met"] == 0
    assert v.measurements["natural_count"] == "0/20"  # the current value is the later write whichever id survives


def test_the_time_probes_that_need_an_end_date_or_a_recorded_time_are_absent(verdicts):
    assert verdicts["T4"].verdict == ABSENT and verdicts["T4"].measurements["dates_missing"] == "invalid_at"
    assert verdicts["T5"].verdict == ABSENT and verdicts["T5"].measurements["dates_missing"] == "recorded_at"
    assert verdicts["T1"].measurements["accepts_dates"] == "yes"


def test_c5_states_the_declared_bound_beside_the_active_count_at_2000_topics(verdicts):
    v = verdicts["C5-2"]
    active = v.measurements["active_at_largest_n"]
    assert active["n"] == 2000 and 395 <= active["active"] <= 410  # about 400 against the bound
    assert f"declared bound {BETA} topics (β)" in v.cases[0].observation
    assert f"{active['active']} active topics at n=2000" in v.cases[0].observation


def test_c4_cap_case_finds_the_first_value_in_the_archived_overflow(verdicts):
    cap = verdicts["C4"].measurements["history_cap"]
    assert cap["first_present"] and cap["first_in_archived_overflow"] and not cap["first_in_history"]
    assert cap["length"] == 500


def test_c6_clause_2_runs_on_the_declared_seeds_to_the_first_forgetting_pass(verdicts):
    v = verdicts["C6-2"]
    assert v.verdict == PASS
    forgetting = next(o for o in v.observations if o["name"] == "forgetting pass")
    assert forgetting["first_pass_in_reads"] is True
    assert forgetting["control"]["archived"] is True and forgetting["target"]["archived"] is False
    assert forgetting["control"]["start"] == 0.06


def test_the_storyline_is_15_of_15_and_reinforcement_precision_is_one_eighth():
    run = run_storyline(ReferenceGem(), WEBSITE_REDESIGN)
    assert run.triage == {"questions": 15, "correct": 15, "search_failures": 0, "memory_failures": 0}
    assert isclose(run.reinforcement.precision, 1 / 8, rel_tol=1e-6)
    assert run.reinforcement.matches_precision_at_k and run.reinforcement.questions_bumped == 15


# ---------------------------------------------------------------- C1, Definition 4 phase 1 reading


def test_describe_declares_the_phase_1_dates_and_the_parameters():
    d = ReferenceGem().describe()
    assert d["accepts"] == {"valid_from": True, "invalid_at": False, "valid_at": True, "recorded_at": False}
    assert d["declared_bound"] == {"topics": 500, "name": "β"} and d["accepts_source"] is True
    assert d["c6_clause_2_seeds"] == {"target": 0.06, "control": 0.06} and d["keeps_history"] is True
    assert isclose(LAMBDA**400, 0.05)


def test_current_is_the_latest_timestamp_not_after_the_asked_date():
    s = ReferenceGem()
    t = new(s, "Plan", field("Tier", "pro", valid_from="2026-10-01T00:00:00+00:00"))
    write(s, t, field("Tier", "basic", valid_from="2026-08-01T00:00:00+00:00"))  # arrives later, older
    write(s, t, field("Tier", "premium", valid_from="2999-12-01T00:00:00+00:00"))  # a future value

    def asked(when):
        return current_value(field_in_response(s.query({**read_request(t), "valid_at": when}), t, "Tier"))

    assert value(s, t, "Tier") == "pro"
    assert asked("2026-09-01T00:00:00+00:00") == "basic"
    assert asked("2026-07-01T00:00:00+00:00") is NO_VALUE
    assert asked("3000-01-01T00:00:00+00:00") == "premium"


def test_a_future_value_with_nothing_before_it_reads_no_current_value():
    s = ReferenceGem()
    t = new(s, "Plan", field("Tier", "premium", valid_from="2999-12-01T00:00:00+00:00"))
    assert value(s, t, "Tier") is NO_VALUE
    assert len(s.read_topic(t)["fields"]["Tier"]["history"]) == 1  # kept, not current


def test_a_default_read_returns_no_history_and_an_explain_read_returns_it_newest_first():
    s = ReferenceGem()
    t = new(s, "Plan", field("Deadline", "March 15"))
    write(s, t, field("Deadline", "April 20"))
    assert field_in_response(s.query(read_request(t)), t, "Deadline")["history"] is None
    explained = field_in_response(s.query(read_request(t, explain=True)), t, "Deadline")
    assert [e["value"] for e in explained["history"]] == ["April 20", "March 15"]
    assert all(e["expired_at"] is None for e in explained["history"])


# ---------------------------------------------------------------- C2: policies, atomic commit


def test_empty_and_null_values_are_rejected_by_the_default_policy_and_nothing_is_saved():
    s = ReferenceGem()
    t = new(s, "Plan", field("Deadline", "April 20"))

    def stored():  # topics, fields and histories (a rejected ingest is still an interaction, so salience decays)
        return {
            tid: (t["title"], {n: f["history"] for n, f in t["fields"].items()})
            for tid, t in s.read_state()["topics"].items()
        }

    before = stored()
    for bad in ("", None):
        with pytest.raises(Rejected):
            write(s, t, field("Deadline", bad))
    with pytest.raises(Rejected):  # a good field beside a bad one: the whole write fails
        write(s, t, field("Owner", "Alice"), field("Deadline", ""), placement="extend_topic")
    assert stored() == before


def test_a_policy_added_at_runtime_rejects_the_violating_write_and_lets_an_ordinary_one_commit():
    s = ReferenceGem()
    rule = {
        "name": "deadline-not-before-start",
        "event": "write",
        "condition": {"field": "Deadline", "op": "<", "other_field": "Start"},
        "action": "reject",
    }
    stored = s.add_policy(rule)
    assert stored == rule and stored in s.read_state()["policies"]
    with pytest.raises(Rejected):
        new(s, "Bad", field("Start", "2026-03-10"), field("Deadline", "2026-03-01"))
    assert s.read_state()["topics"] == {}
    t = new(s, "Good", field("Start", "2026-03-10"), field("Deadline", "2026-03-20"))
    assert value(s, t, "Deadline") == "2026-03-20"
    with pytest.raises(Rejected):  # the proposed next state is checked on updates too
        write(s, t, field("Deadline", "2026-03-02"))
    assert value(s, t, "Deadline") == "2026-03-20"


def test_a_partial_commit_is_impossible_a_missing_reference_saves_neither_topic_nor_first_field():
    s = ReferenceGem()
    with pytest.raises(Rejected):
        new(s, "T", field("A", "1"), field("B", "2", ref_topic_id="missing"))
    assert s.read_state()["topics"] == {}


def test_a_policy_outside_the_fixed_vocabulary_is_refused_when_added():
    with pytest.raises(ValueError):
        ReferenceGem().add_policy(
            {"name": "x", "event": "write", "condition": {"query": "whole state"}, "action": "reject"}
        )


# ---------------------------------------------------------------- C3: Listing 1, one hop, undirected


def linked(s, kind="extension", direction="B->A", tag=""):
    a = new(s, f"A{tag}", field("Deadline", "March 15"))
    b = (
        new(s, f"B{tag}", field("Date", "March 20"), edges=[{"to_topic_id": a, "kind": kind}])
        if direction == "B->A"
        else new(s, f"B{tag}", field("Date", "March 20"))
    )
    if direction == "A->B":
        write(s, a, placement="extend_topic", edges=[{"to_topic_id": b, "kind": kind}])
    return a, b


@pytest.mark.parametrize("direction", ["B->A", "A->B"])
def test_an_update_flags_the_extension_neighbour_whatever_the_edge_direction(direction):
    s = ReferenceGem()
    a, b = linked(s, direction=direction)
    write(s, a, field("Deadline", "April 20"))
    flag = s.read_topic(b)["revision_flag"]
    assert flag["flagged"] and flag["evidence"]["source_topic_id"] == a
    assert flag["evidence"]["updated_field"] == "Deadline" and flag["evidence"]["timestamp"]
    assert field_in_response(s.query(read_request(b)), b, "Date") is not None
    assert s.query(read_request(b))["candidates"][0]["revision_flag"]["flagged"]


def test_an_association_edge_never_flags_and_there_is_no_repair():
    s = ReferenceGem()
    a, c = linked(s, kind="association")
    write(s, a, field("Deadline", "April 20"))
    assert s.read_topic(c)["revision_flag"] == {"flagged": False}
    a2, b = linked(s, tag="2")
    write(s, a2, field("Deadline", "April 20"))
    assert value(s, b, "Date") == "March 20"  # flagged, not repaired


def test_the_flag_clears_when_the_flagged_topic_is_written_and_that_write_flags_its_neighbours():
    s = ReferenceGem()
    a, b = linked(s)
    write(s, a, field("Deadline", "April 20"))
    assert s.read_topic(a)["revision_flag"] == {"flagged": False}
    write(s, b, field("Date", "April 25"))
    assert s.read_topic(b)["revision_flag"] == {"flagged": False}
    assert s.read_topic(a)["revision_flag"]["evidence"]["source_topic_id"] == b


def test_flagging_is_one_hop():
    s = ReferenceGem()
    a, b = linked(s)
    c = new(s, "C", field("Note", "x"), edges=[{"to_topic_id": b, "kind": "extension"}])
    write(s, a, field("Deadline", "April 20"))
    assert s.read_topic(b)["revision_flag"]["flagged"] and not s.read_topic(c)["revision_flag"]["flagged"]


# ---------------------------------------------------------------- C4: cap, archived overflow, sources


def test_the_501st_write_archives_the_oldest_entry_readable_by_id_and_a_valid_archived_value_reads_no_value():
    s = ReferenceGem()
    t = new(s, "T", field("F", "v000"))
    for i in range(1, 501):
        write(s, t, field("F", f"v{i:03d}"))
    stored = s.read_topic(t)["fields"]["F"]
    assert len(stored["history"]) == 500 and [e["value"] for e in stored["archived_history"]] == ["v000"]
    assert s.archived_entry(stored["archived_history"][0]["id"])["value"] == "v000"
    assert stored["current"]["value"] == "v500"
    # asked at a date when only the archived entry was valid: no current value plus a note
    s2 = ReferenceGem()
    t2 = new(s2, "T", field("F", "old", valid_from="2020-01-01T00:00:00+00:00"))
    for i in range(500):
        write(s2, t2, field("F", f"n{i}", valid_from="2021-01-01T00:00:00+00:00"))
    asked = field_in_response(s2.query({**read_request(t2), "valid_at": "2020-06-01T00:00:00+00:00"}), t2, "F")
    assert asked["current"] is None and "archived" in asked["note"]


def test_every_write_stores_its_source_message_and_resolve_source_returns_it():
    s = ReferenceGem()
    t = new(s, "T", field("Deadline", "March 15", source_message="Dana said March 15."))
    write(s, t, field("Deadline", "April 20", source_message="Dana said April 20."))
    history = s.read_topic(t)["fields"]["Deadline"]["history"]
    assert [s.resolve_source(e) for e in history] == ["Dana said April 20.", "Dana said March 15."]
    assert s.resolve_source({"source_id": None}) is None


# ---------------------------------------------------------------- C5 / C6: decay, forgetting, reinforcement


def filler(s, i):
    return s.ingest({"placement": "new_topic", "title": f"Filler {i}"})["topic_id"]


def test_an_untouched_topic_at_1_falls_below_the_threshold_after_400_interactions_and_is_archived_halved():
    s = ReferenceGem()
    t = filler(s, 0)  # interaction 1
    for i in range(1, 401):
        filler(s, i)  # interactions 2..401
    assert s.interactions == 401 and s.read_topic(t)["archived"] is False
    assert isclose(s.read_topic(t)["salience"], 0.05, rel_tol=1e-9)
    filler(s, 401)
    topic = s.read_topic(t)
    assert topic["archived"] is True and isclose(topic["salience"], 0.05 * LAMBDA / 2, rel_tol=1e-9)


def test_a_write_resets_the_decay_clock_without_changing_salience_and_a_retrieval_adds_0_1():
    s = ReferenceGem()
    written, read, idle = filler(s, 0), filler(s, 1), filler(s, 2)
    for i in range(3, 300):
        filler(s, i)
    before = s.read_topic(written)["salience"]
    write(s, written, field("F", "x"), placement="extend_topic")
    assert isclose(s.read_topic(written)["salience"], before, rel_tol=1e-12)  # the write adds nothing
    before = s.read_topic(read)["salience"]
    s.query(read_request(read))
    assert isclose(s.read_topic(read)["salience"], before + 0.1, abs_tol=1e-9)
    for i in range(300, 460):
        filler(s, i)
    assert s.read_topic(idle)["archived"] is True and s.read_topic(read)["archived"] is False  # the read one lives on


def test_a_seed_below_the_threshold_is_archived_by_its_own_interaction_and_an_as_of_read_bumps():
    s = ReferenceGem()
    low = s.ingest({"placement": "new_topic", "title": "Low", "salience": 0.03})["topic_id"]
    assert s.read_topic(low)["archived"] is True
    high = s.ingest({"placement": "new_topic", "title": "High", "salience": 0.5})["topic_id"]
    before = s.read_topic(high)["salience"]
    s.query({**read_request(high), "valid_at": "2026-01-01T00:00:00+00:00"})
    assert isclose(s.read_topic(high)["salience"], before + 0.1, abs_tol=1e-9)


def test_archived_topics_are_not_retrieved_but_stay_readable_with_their_fields():
    s = ReferenceGem()
    t = new(s, "Old", field("F", "x"), salience=0.01)
    assert s.query(read_request(t))["candidates"] == []
    assert value(s, t, "F") == "x" and t in s.list_topic_ids(include_archived=True)
    assert t not in s.list_topic_ids(include_archived=False)


# ---------------------------------------------------------------- revision: merge after every ingest


def test_same_title_topics_merge_after_the_ingest_the_survivor_keeps_both_histories_and_the_later_write_is_current():
    s = ReferenceGem()
    first = new(s, "Contract", field("Deadline", "March 15", "kickoff-notes"))
    second = new(s, "Contract", field("Deadline", "April 20", "pm-email"))
    low = min(first, second)
    assert s.read_topic(first if first != low else second) is None  # the higher id is gone
    survivor = s.read_topic(low)
    assert survivor["fields"]["Deadline"]["current"]["value"] == "April 20"
    history = survivor["fields"]["Deadline"]["history"]
    assert [(e["value"], e["provenance"]) for e in history] == [("April 20", "pm-email"), ("March 15", "kickoff-notes")]
    assert {e.get("merged_from_topic_id") for e in history} <= {None, first if low != first else second}


def test_until_revision_runs_a_read_can_see_both_copies():
    s = ReferenceGem(revise_after_ingest=False)
    first = new(s, "Contract", field("Deadline", "March 15"))
    second = new(s, "Contract", field("Deadline", "April 20"))
    assert s.read_topic(first) and s.read_topic(second)
    assert s.revise() and len(s.list_topic_ids()) == 1


def test_a_duplicate_with_an_archived_topic_is_not_merged():
    s = ReferenceGem()
    old = new(s, "Contract", field("Deadline", "March 15"), salience=0.01)  # archived by its own interaction
    new(s, "Contract", field("Deadline", "April 20"))
    assert s.read_topic(old)["archived"] is True and len(s.list_topic_ids()) == 2
