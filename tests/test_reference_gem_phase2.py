"""The reference GEM, phase 2 (ticket 27): phase 1 plus C1' (report §9.5, ADR 0005 as narrowed), through the system
adapter, in-process. Pins the phase 2 column of the spec's "Expected verdicts" and the chain phase 1 -> phase 2: it
changes exactly T4 and T5 (absent -> pass) and no other row. The unit tests state the patch's rules (the same rules
as `patches/0002-bitemporal-field-histories.patch`)."""

from datetime import UTC, date, datetime, timedelta

import pytest

from demo.reads import NO_VALUE, current_value, field_in_response, read_request
from demo.reference_gem import BUMP, ReferenceGem
from demo.verdict import ABSENT, PASS
from tests.reference_runs import unmutated

RUN_DAY = date(2026, 10, 20)
ROWS = [
    "C1",
    "C2(a)",
    "C2(b)",
    "C2(c)",
    "C2(d)",
    "C3",
    "C4",
    "C5-1",
    "C5-2",
    "C6-1",
    "C6-2",
    "C4′",
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
]


@pytest.fixture(scope="module")
def phase1():
    return unmutated(1)


@pytest.fixture(scope="module")
def phase2():
    return unmutated(2)


# ---------------------------------------------------------------- the phase 2 column of "Expected verdicts"


@pytest.mark.parametrize("row", [r for r in ROWS if r != "C2(a)"])
def test_the_phase_2_column_passes(phase2, row):
    v = phase2[row]
    assert v.verdict == PASS, [(c.name, c.held, c.observation) for c in v.cases]
    assert all(c.held is not None for c in v.cases), "no case is n/a on the reference GEM"


def test_c2a_passes_with_no_violation_on_phase_2(phase2):
    v = phase2["C2(a)"]
    assert v.verdict == PASS and v.measurements["violations"] == 0 and v.measurements["arrangement_not_met"] == 0


def test_phase_1_to_phase_2_changes_exactly_t4_and_t5(phase1, phase2):
    assert phase1.keys() == phase2.keys()
    changed = {row for row in phase1 if phase1[row].verdict != phase2[row].verdict}
    assert changed == {"T4", "T5"}
    assert phase1["T4"].verdict == ABSENT and phase2["T4"].verdict == PASS
    assert phase1["T5"].verdict == ABSENT and phase2["T5"].verdict == PASS
    for row in set(phase1) - changed:  # no other row moves: not the verdict, not one case
        assert [(c.name, c.held) for c in phase1[row].cases] == [(c.name, c.held) for c in phase2[row].cases], row


# ---------------------------------------------------------------- the model


class StepClock:
    """A clock every reading of which is a second after the last: a moment noted between two writes is strictly
    between them, whatever the machine's clock resolution."""

    def __init__(self):
        self.now = datetime(2026, 10, 20, tzinfo=UTC)

    def __call__(self):
        self.now += timedelta(seconds=1)
        return self.now

    def iso(self):
        return self().isoformat()


@pytest.fixture
def clock():
    return StepClock()


def day(month, d, year=2026):
    return datetime(year, month, d, tzinfo=UTC).isoformat()


def new(s, title, **fields):
    return s.ingest({"placement": "new_topic", "title": title, "fields": [_field(n, **w) for n, w in fields.items()]})


def put(s, topic_id, name, value, **dates):
    return s.ingest({"placement": "version_field", "topic_id": topic_id, "fields": [_field(name, value, **dates)]})


def _field(name, value=None, **dates):
    return {"name": name, "value": value, "provenance": "test", **dates}


def ask(s, topic_id, name, **when):
    return current_value(field_in_response(s.query({**read_request(topic_id), **when}), topic_id, name))


def stored(s, topic_id, name):
    return s.read_topic(topic_id)["fields"][name]


@pytest.fixture
def gem(clock):
    return ReferenceGem(phase=2, clock=clock)


def test_phase_2_is_a_mode_of_the_same_adapter_and_accepts_all_four_dates(gem):
    assert type(gem) is ReferenceGem and gem.label == "reference GEM (phase 2)"
    assert gem.describe()["accepts"] == {"valid_from": True, "invalid_at": True, "valid_at": True, "recorded_at": True}
    assert ReferenceGem().describe()["accepts"]["invalid_at"] is False
    assert gem.describe()["parameters"]["phase"] == 2
    with pytest.raises(ValueError):
        ReferenceGem(phase=3)


def test_entries_carry_the_four_dates(gem):
    t = new(gem, "Plan", Budget={"value": "$80", "valid_from": day(10, 1), "invalid_at": day(11, 1)})["topic_id"]
    (entry,) = stored(gem, t, "Budget")["history"]
    assert entry["valid_from"] == day(10, 1) and entry["invalid_at"] == day(11, 1)
    assert entry["created_at"] and entry["expired_at"] is None
    assert entry["replaces_entry_id"] is None and entry["corrected_by_entry_id"] is None


def test_an_ordinary_update_leaves_exactly_two_entries_and_stores_no_end(gem):
    t = new(gem, "Plan", Deadline={"value": "April 20", "valid_from": day(1, 5)})["topic_id"]
    put(gem, t, "Deadline", "May 1", valid_from=day(2, 1))
    history = stored(gem, t, "Deadline")["history"]
    assert len(history) == 2
    assert all(e["invalid_at"] is None and e["expired_at"] is None for e in history)
    assert not any("operation" in e for e in history)  # nothing expired, nothing copied
    assert ask(gem, t, "Deadline") == "May 1"
    assert ask(gem, t, "Deadline", valid_at=day(1, 20)) == "April 20"


def test_an_entry_is_valid_until_the_next_entrys_valid_from_unless_it_carries_its_own_end(gem):
    t = new(gem, "Plan", Tier={"value": "basic", "valid_from": day(6, 1)})["topic_id"]
    put(gem, t, "Tier", "pro", valid_from=day(8, 1))
    put(gem, t, "Tier", "trial", valid_from=day(7, 1), invalid_at=day(7, 10))  # layered, ends on its own
    assert [ask(gem, t, "Tier", valid_at=day(*d)) for d in ((5, 1), (6, 15), (7, 5), (7, 20), (8, 5))] == [
        NO_VALUE,
        "basic",
        "trial",
        "basic",
        "pro",
    ]


def test_the_late_older_value_ends_where_the_later_one_begins_with_no_stored_end(gem):
    t = new(gem, "Plan", Tier={"value": "pro", "valid_from": day(10, 1)})["topic_id"]
    put(gem, t, "Tier", "basic", valid_from=day(8, 1))
    assert ask(gem, t, "Tier", valid_at=day(9, 1)) == "basic" and ask(gem, t, "Tier", valid_at=day(10, 5)) == "pro"
    assert len(stored(gem, t, "Tier")["history"]) == 2


def test_a_future_value_with_nothing_valid_reads_current_null(gem):
    t = new(gem, "Plan", Tier={"value": "premium", "valid_from": "2999-12-01T00:00:00+00:00"})["topic_id"]
    response = gem.query(read_request(t))
    field = next(f for c in response["candidates"] if c["topic_id"] == t for f in c["fields"] if f["name"] == "Tier")
    assert field["current"] is None
    assert stored(gem, t, "Tier")["current"] is None
    assert ask(gem, t, "Tier") is NO_VALUE


def test_a_scoped_override_layers_and_the_shorter_validity_wins_then_lapses(gem):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    assert ask(gem, t, "Budget", valid_at=day(9, 15)) == "$50"
    assert ask(gem, t, "Budget", valid_at=day(10, 15)) == "$80"
    assert ask(gem, t, "Budget", valid_at=day(11, 5)) == "$50"  # the override lapsed, the base was never closed
    assert len(stored(gem, t, "Budget")["history"]) == 2  # nothing expired, nothing copied


def test_a_plain_statement_ends_the_override_it_starts_inside_by_keep_and_copy(gem):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    before = stored(gem, t, "Budget")["history"]
    override = next(e for e in before if e["value"] == "$80")
    put(gem, t, "Budget", "$100", valid_from=day(10, 10))
    assert [ask(gem, t, "Budget", valid_at=day(10, d)) for d in (5, 15)] == ["$80", "$100"]  # not "shorter wins" alone
    assert ask(gem, t, "Budget", valid_at=day(11, 5)) == "$100" and ask(gem, t, "Budget") == "$100"
    history = stored(gem, t, "Budget")["history"]
    assert len(history) == 4  # $50, $100, the expired $80 and its copy
    original = next(e for e in history if e["id"] == override["id"])
    copy = next(e for e in history if e["replaces_entry_id"] == override["id"])
    assert original["expired_at"] and original["corrected_by_entry_id"] == copy["id"]
    assert copy["operation"] == "interval_corrected" and copy["invalid_at"] == day(10, 10)
    assert copy["value"] == "$80" and copy["provenance"] == original["provenance"] and copy["expired_at"] is None
    assert copy["source_id"] == original["source_id"]


def test_a_plain_statement_outside_an_overrides_validity_does_not_touch_it(gem):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    put(gem, t, "Budget", "$60", valid_from=day(11, 15))
    put(gem, t, "Budget", "$40", valid_from=day(9, 15))
    history = stored(gem, t, "Budget")["history"]
    assert len(history) == 4 and not any(e["expired_at"] for e in history)


def test_an_end_dated_write_changes_no_stored_end_so_it_never_copies(gem):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    put(gem, t, "Budget", "$90", valid_from=day(10, 10), invalid_at=day(10, 20))  # layered over the $80
    assert not any(e["expired_at"] for e in stored(gem, t, "Budget")["history"])
    assert ask(gem, t, "Budget", valid_at=day(10, 15)) == "$90" and ask(gem, t, "Budget", valid_at=day(10, 25)) == "$80"


def test_a_retraction_keeps_the_value_and_appends_a_copy_valid_nowhere(gem):
    r = new(gem, "Plan", Tier={"value": "basic", "valid_from": day(6, 1)})
    t = r["topic_id"]
    pro = put(gem, t, "Tier", "pro", valid_from=day(8, 1))["version_ids"]["Tier"]
    copy_id = gem.retract(t, "Tier", pro)
    history = stored(gem, t, "Tier")["history"]
    original = next(e for e in history if e["id"] == pro)
    copy = next(e for e in history if e["id"] == copy_id)
    assert original["expired_at"] and original["corrected_by_entry_id"] == copy_id and original["value"] == "pro"
    assert copy["replaces_entry_id"] == pro and copy["operation"] == "interval_corrected"
    assert copy["invalid_at"] == copy["valid_from"] == original["valid_from"]
    assert ask(gem, t, "Tier") == "basic" and ask(gem, t, "Tier", valid_at=day(9, 1)) == "basic"
    with pytest.raises(ValueError):
        gem.retract(t, "Tier", pro)  # already expired
    with pytest.raises(ValueError):
        ReferenceGem().retract(t, "Tier", pro)  # phase 1 has none


def test_expired_entries_are_hidden_unless_history_is_requested(gem):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    put(gem, t, "Budget", "$100", valid_from=day(10, 10))

    def history_of(**extra):
        response = gem.query({**read_request(t), **extra})
        return next(f for c in response["candidates"] for f in c["fields"] if f["name"] == "Budget")["history"]

    assert history_of() is None  # a default read returns the value valid now and no history
    shown = history_of(explain=True)
    assert sum(1 for e in shown if e["expired_at"]) == 1 and len(shown) == 4
    assert ask(gem, t, "Budget", valid_at=day(10, 15)) == "$100"  # the expired original never answers a valid_at read


def test_recorded_at_reads_what_memory_held_then(clock):
    s2 = ReferenceGem(phase=2, clock=clock)
    t2 = new(s2, "Plan", Deadline={"value": "April 20", "valid_from": day(1, 5)})["topic_id"]
    noted = clock.iso()
    put(s2, t2, "Deadline", "May 1", valid_from=day(2, 1))
    assert ask(s2, t2, "Deadline", valid_at=day(2, 10)) == "May 1"  # true on Feb 10
    assert ask(s2, t2, "Deadline", valid_at=day(2, 10), recorded_at=noted) == "April 20"  # believed on that day
    assert ask(s2, t2, "Deadline", recorded_at=noted) == "April 20"
    assert ask(s2, t2, "Deadline", recorded_at=clock.iso()) == "May 1"


def test_recorded_at_sees_an_entry_that_has_expired_since_as_live(gem, clock):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    noted = clock.iso()
    put(gem, t, "Budget", "$100", valid_from=day(10, 10))
    assert ask(gem, t, "Budget", valid_at=day(10, 15), recorded_at=noted) == "$80"  # before the $100 was recorded
    assert ask(gem, t, "Budget", valid_at=day(10, 15)) == "$100"


def test_as_of_reads_on_both_axes_count_as_history_requests_and_raise_salience(gem, clock):
    t = new(gem, "Plan", Deadline={"value": "April 20", "valid_from": day(1, 5)})["topic_id"]
    for extra in ({"valid_at": day(2, 1)}, {"recorded_at": clock.iso()}):
        before = gem.read_topic(t)["salience"]
        response = gem.query({**read_request(t), **extra})
        field = next(f for c in response["candidates"] if c["topic_id"] == t for f in c["fields"])
        assert field["history"] and len(field["history"]) == 1
        # one interaction passed: the topic decayed a little before the bump
        assert gem.read_topic(t)["salience"] > before * 0.99 + BUMP - 1e-6


def test_phase_1_ignores_the_phase_2_dates_and_shows_the_phase_1_entry_shape():
    s = ReferenceGem()
    t = new(s, "Plan", Budget={"value": "$80", "valid_from": day(10, 1), "invalid_at": day(11, 1)})["topic_id"]
    (entry,) = stored(s, t, "Budget")["history"]
    assert "invalid_at" not in entry and entry["expired_at"] is None and "created_at" not in entry


def test_a_correction_uses_two_entries_toward_the_history_cap(gem):
    from demo.reference_gem import HISTORY_CAP

    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    put(gem, t, "Budget", "$100", valid_from=day(10, 10))
    f = stored(gem, t, "Budget")
    assert len(f["history"]) + len(f["archived_history"]) == 4 and HISTORY_CAP == 500


def test_a_failed_write_changes_nothing_not_even_an_expiry(gem):
    t = new(gem, "Plan", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    put(gem, t, "Budget", "$80", valid_from=day(10, 1), invalid_at=day(11, 1))
    before = gem.read_state()
    with pytest.raises(Exception):  # the second field is empty: the default policy rejects the whole transition
        gem.ingest(
            {
                "placement": "extend_topic",
                "topic_id": t,
                "fields": [_field("Budget", "$100", valid_from=day(10, 10)), _field("Other", "")],
            }
        )
    after = gem.read_state()
    assert before["topics"][t]["fields"] == after["topics"][t]["fields"]
    assert not any(e["expired_at"] for e in after["topics"][t]["fields"]["Budget"]["history"])


# ---------------------------------------------------------------- merge


def merged_pair(gem):
    a = new(gem, "Plan A", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    gem.revise_after_ingest = False
    b = new(gem, "Plan A", Budget={"value": "$70", "valid_from": day(10, 1)})["topic_id"]
    return a, b


def test_merge_keeps_provenance_tags_and_the_current_value_is_the_later_valid_date(gem):
    a, b = merged_pair(gem)
    gem.revise()
    survivor = min(a, b)
    assert gem.read_topic(max(a, b)) is None
    history = stored(gem, survivor, "Budget")["history"]
    assert {e["value"] for e in history} == {"$50", "$70"}
    dropped = max(a, b)
    tagged = [e for e in history if e.get("operation") == "merged"]
    assert len(tagged) == 1 and tagged[0]["merged_from_topic_id"] == dropped and tagged[0]["provenance"] == "test"
    assert value_now(gem, survivor) == "$70"
    assert ask(gem, survivor, "Budget", valid_at=day(9, 15)) == "$50"


def value_now(gem, topic_id):
    return current_value(gem.read_topic(topic_id)["fields"]["Budget"])


def test_merge_where_the_earlier_valid_date_was_written_last_still_reads_the_later_valid_date(gem):
    a = new(gem, "Plan A", Budget={"value": "$70", "valid_from": day(10, 1)})["topic_id"]
    gem.revise_after_ingest = False
    b = new(gem, "Plan A", Budget={"value": "$50", "valid_from": day(9, 1)})["topic_id"]
    gem.revise()
    assert value_now(gem, min(a, b)) == "$70"


def test_merge_ends_an_override_that_a_plain_entry_of_the_other_side_starts_inside(gem):
    a = new(gem, "Plan A", Budget={"value": "$80", "valid_from": day(10, 1), "invalid_at": day(11, 1)})["topic_id"]
    gem.revise_after_ingest = False
    b = new(gem, "Plan A", Budget={"value": "$100", "valid_from": day(10, 10)})["topic_id"]
    gem.revise()
    history = stored(gem, min(a, b), "Budget")["history"]
    expired = [e for e in history if e["expired_at"]]
    assert len(expired) == 1 and expired[0]["value"] == "$80"
    copy = next(e for e in history if e["replaces_entry_id"] == expired[0]["id"])
    assert copy["invalid_at"] == day(10, 10) and copy["operation"] == "interval_corrected"
    assert [ask(gem, min(a, b), "Budget", valid_at=day(10, d)) for d in (5, 15)] == ["$80", "$100"]
