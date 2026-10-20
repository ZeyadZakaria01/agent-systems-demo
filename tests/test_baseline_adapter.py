"""The system adapter, exercised through the baseline: a versioned row (in-process, no server)."""

import pytest

from demo.baseline import Baseline
from demo.adapter import Rejected
from demo.reads import NO_VALUE, current_value


def field(name, value, provenance="test"):
    return {"name": name, "value": value, "provenance": provenance}


def read_topic_fields(system, topic_id, explain=False, **extra):
    resp = system.query({"q": "x", "stages": ["temporal"], "topic_ids": [topic_id], "explain": explain, **extra})
    (cand,) = resp["candidates"]
    return {f["name"]: f for f in cand["fields"]}


def test_every_write_appends_and_a_second_new_topic_with_same_title_appends_to_the_same_topic():
    b = Baseline()
    first = b.ingest({"placement": "new_topic", "title": "Website Redesign",
                      "fields": [field("Deadline", "March 15")]})
    b.ingest({"placement": "version_field", "topic_id": first["topic_id"],
              "fields": [field("Deadline", "April 20")]})
    again = b.ingest({"placement": "new_topic", "title": "Website Redesign",
                      "fields": [field("Deadline", "May 1"), field("Owner", "Alice")]})

    assert again["topic_id"] == first["topic_id"]  # no merge ever occurs: one topic
    assert len(b.read_state()["topics"]) == 1
    fields = read_topic_fields(b, first["topic_id"])
    assert fields["Deadline"]["current"]["value"] == "May 1"
    assert fields["Owner"]["current"]["value"] == "Alice"
    history = b.read_topic(first["topic_id"])["fields"]["Deadline"]["history"]
    assert [e["value"] for e in history] == ["May 1", "April 20", "March 15"]  # newest first, nothing lost
    assert all(e["recorded_at"] for e in history) and all(e["provenance"] == "test" for e in history)


def test_history_is_in_the_explain_read_only():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "a")]})
    b.ingest({"placement": "version_field", "topic_id": t["topic_id"], "fields": [field("Deadline", "b")]})
    assert read_topic_fields(b, t["topic_id"])["Deadline"]["history"] is None
    explained = read_topic_fields(b, t["topic_id"], explain=True)["Deadline"]
    assert [e["value"] for e in explained["history"]] == ["b", "a"]


@pytest.mark.parametrize("bad", ["", None])
def test_empty_and_null_values_are_rejected_and_nothing_is_saved(bad):
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "April 20")]})
    before = b.read_state()
    with pytest.raises(Rejected):
        b.ingest({"placement": "version_field", "topic_id": t["topic_id"], "fields": [field("Deadline", bad)]})
    assert b.read_state() == before
    assert read_topic_fields(b, t["topic_id"])["Deadline"]["current"]["value"] == "April 20"


def test_a_write_is_one_transaction_a_bad_field_saves_none_of_it_and_creates_no_topic():
    b = Baseline()
    with pytest.raises(Rejected):
        b.ingest({"placement": "new_topic", "title": "Fresh",
                  "fields": [field("Owner", "Alice"), field("Deadline", None)]})
    assert b.read_state()["topics"] == {}  # not even the topic or the valid first field
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Owner", "Alice")]})
    with pytest.raises(Rejected):
        b.ingest({"placement": "extend_topic", "topic_id": t["topic_id"],
                  "fields": [field("Owner", "Bob"), field("Deadline", "")]})
    topic = b.read_topic(t["topic_id"])
    assert set(topic["fields"]) == {"Owner"} and len(topic["fields"]["Owner"]["history"]) == 1


def test_missing_capabilities_read_as_nothing_values_not_errors():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "salience": 0.01,
                  "fields": [field("Deadline", "April 20")],
                  "edges": [{"to_topic_id": "nowhere", "kind": "extension"}]})
    topic = b.read_topic(t["topic_id"])
    assert topic["salience"] is None and topic["archived"] is None
    assert b.read_state()["edges"] is None
    assert b.setup_write("patch_topic", label="x", topic_id=t["topic_id"], archived=True) is None
    # valid-time dates are accepted and ignored: the answer does not change
    plain = b.query({"q": "x", "stages": ["temporal"], "topic_ids": [t["topic_id"]]})
    asof = b.query({"q": "x", "stages": ["temporal"], "topic_ids": [t["topic_id"]],
                    "valid_at": "2020-01-01T00:00:00+00:00"})
    assert asof["candidates"] == plain["candidates"]


def test_describe_accepts_recorded_at_only_and_keeps_history():
    d = Baseline().describe()
    assert d["accepts"] == {"valid_from": False, "invalid_at": False, "valid_at": False, "recorded_at": True}
    assert d["keeps_history"] is True and d["top_k"] == 8


def test_a_recorded_at_read_is_answered_from_the_history():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "April 20")]})
    between = b.read_topic(t["topic_id"])["fields"]["Deadline"]["history"][0]["recorded_at"]
    b.ingest({"placement": "version_field", "topic_id": t["topic_id"], "fields": [field("Deadline", "May 1")]})
    assert read_topic_fields(b, t["topic_id"])["Deadline"]["current"]["value"] == "May 1"
    at = read_topic_fields(b, t["topic_id"], recorded_at=between)["Deadline"]
    assert at["current"]["value"] == "April 20"
    before = read_topic_fields(b, t["topic_id"], recorded_at="2000-01-01T00:00:00+00:00")["Deadline"]
    assert current_value(before) is NO_VALUE  # nothing was recorded yet


def test_a_missing_topic_reads_as_deleted():
    assert Baseline().read_topic("never-written") is None


def test_extending_a_missing_topic_is_rejected():
    with pytest.raises(Rejected):
        Baseline().ingest({"placement": "extend_topic", "topic_id": "nope", "fields": [field("a", "b")]})


def test_a_read_changes_nothing():
    b = Baseline()
    b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "April 20")]})
    before = b.read_state()
    for _ in range(3):
        b.query({"q": "T", "stages": ["temporal"], "topic_ids": ["T"], "explain": True})
    assert b.read_state() == before


def test_semantic_query_embeds_with_minilm_and_returns_the_top_8():
    b = Baseline()
    for i in range(12):
        b.ingest({"placement": "new_topic", "title": f"Garden topic {i}", "summary": "tomatoes and basil"})
    b.ingest({"placement": "new_topic", "title": "Quarterly budget", "summary": "finance forecast spreadsheet"})
    resp = b.query({"q": "how much money is budgeted this quarter", "top_k": 3})
    assert len(resp["candidates"]) == 8
    assert resp["candidates"][0]["title"] == "Quarterly budget"
    assert resp["candidates"][0]["similarity"] is not None


def test_wait_until_reports_success_and_timeout_explicitly_and_logs_waits_apart_from_transitions():
    b = Baseline()
    ok = b.wait_until(lambda: True, timeout=1)
    assert ok.timed_out is False and ok.elapsed >= 0  # an immediate success is not falsy-confusable with a timeout
    late = b.wait_until(lambda: False, timeout=0.2, interval=0.05)
    assert late.timed_out is True and late.elapsed >= 0.2
    waits = b.log.of_kind("wait")
    assert [w["response"]["timed_out"] for w in waits] == [False, True]
    assert b.log.of_kind("scored") == []


def test_every_field_has_an_explicit_current():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "April 20")]})
    for f in (b.read_topic(t["topic_id"])["fields"]["Deadline"],
              b.read_state()["topics"][t["topic_id"]]["fields"]["Deadline"]):
        assert current_value(f) == "April 20"
    assert current_value({"current": None, "history": [{"value": "Dec"}]}) is NO_VALUE  # server states: nothing is current
