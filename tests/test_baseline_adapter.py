"""The system adapter, exercised through the baseline (in-process, no server)."""

import pytest

from demo.baseline import Baseline
from demo.client import Rejected
from demo.reads import NO_VALUE, current_value


def field(name, value, provenance="test"):
    return {"name": name, "value": value, "provenance": provenance}


def read_topic_fields(system, topic_id, explain=False):
    resp = system.query({"q": "x", "stages": ["temporal"], "topic_ids": [topic_id], "explain": explain})
    (cand,) = resp["candidates"]
    return {f["name"]: f for f in cand["fields"]}


def test_last_write_wins_and_second_new_topic_with_same_title_upserts():
    b = Baseline()
    first = b.ingest({"placement": "new_topic", "title": "Website Redesign",
                      "fields": [field("Deadline", "March 15")]})
    b.ingest({"placement": "version_field", "topic_id": first["topic_id"],
              "fields": [field("Deadline", "April 20")]})
    again = b.ingest({"placement": "new_topic", "title": "Website Redesign",
                      "fields": [field("Owner", "Alice")]})

    assert again["topic_id"] == first["topic_id"]
    assert len(b.read_state()["topics"]) == 1
    fields = read_topic_fields(b, first["topic_id"])
    assert fields["Deadline"]["current"]["value"] == "April 20"
    assert fields["Owner"]["current"]["value"] == "Alice"


def test_empty_and_null_values_are_accepted_and_become_current():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "April 20")]})
    b.ingest({"placement": "version_field", "topic_id": t["topic_id"], "fields": [field("Deadline", "")]})
    assert read_topic_fields(b, t["topic_id"])["Deadline"]["current"]["value"] == ""
    b.ingest({"placement": "version_field", "topic_id": t["topic_id"], "fields": [field("Deadline", None)]})
    assert read_topic_fields(b, t["topic_id"])["Deadline"]["current"]["value"] is None


def test_missing_capabilities_read_as_nothing_values_not_errors():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "salience": 0.01,
                  "fields": [field("Deadline", "April 20")],
                  "edges": [{"to_topic_id": "nowhere", "kind": "extension"}]})
    topic = b.read_topic(t["topic_id"])
    assert topic["salience"] is None and topic["archived"] is None
    assert topic["fields"]["Deadline"]["history"] is None
    assert b.read_state()["edges"] is None
    assert b.setup_write("patch_topic", label="x", topic_id=t["topic_id"], archived=True) is None
    # as-of dates are accepted and ignored: the answer does not change
    plain = b.query({"q": "x", "stages": ["temporal"], "topic_ids": [t["topic_id"]]})
    asof = b.query({"q": "x", "stages": ["temporal"], "topic_ids": [t["topic_id"]],
                    "valid_at": "2020-01-01T00:00:00+00:00"})
    assert asof["candidates"] == plain["candidates"]


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
        b.query({"q": "T", "stages": ["temporal"], "topic_ids": ["T"]})
    assert b.read_state() == before


def test_semantic_query_embeds_with_minilm_and_returns_the_top_10():
    b = Baseline()
    for i in range(12):
        b.ingest({"placement": "new_topic", "title": f"Garden topic {i}", "summary": "tomatoes and basil"})
    b.ingest({"placement": "new_topic", "title": "Quarterly budget", "summary": "finance forecast spreadsheet"})
    resp = b.query({"q": "how much money is budgeted this quarter", "top_k": 3})
    assert len(resp["candidates"]) == 10
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


def test_every_field_has_an_explicit_current_and_a_null_write_is_not_no_value():
    b = Baseline()
    t = b.ingest({"placement": "new_topic", "title": "T", "fields": [field("Deadline", "April 20")]})
    b.ingest({"placement": "version_field", "topic_id": t["topic_id"], "fields": [field("Deadline", None)]})
    for f in (b.read_topic(t["topic_id"])["fields"]["Deadline"],
              b.read_state()["topics"][t["topic_id"]]["fields"]["Deadline"]):
        assert f["current"] == {"value": None}  # a null write that became current, not "no value"
        assert current_value(f) is None
    assert current_value({"current": None, "history": [{"value": "Dec"}]}) is NO_VALUE  # server states: nothing is current


def test_the_stored_topic_shape_without_a_current_key_reads_its_newest_history_entry():
    assert current_value({"history": [{"value": "April 20"}, {"value": "March 15"}]}) == "April 20"
    assert current_value({"history": []}) is NO_VALUE
    assert current_value(None) is NO_VALUE


def test_the_baseline_declares_that_it_keeps_no_history():
    assert Baseline().describe()["keeps_history"] is False


def test_a_failing_call_records_its_error_text_on_the_log_entry():
    b = Baseline()
    with pytest.raises(KeyError):
        b.ingest({"title": "no placement"})
    (entry,) = b.log.of_kind("scored")
    assert "KeyError" in entry["error"]


def test_reading_state_is_logged_with_its_own_timestamps():
    b = Baseline()
    b.read_state()
    (entry,) = b.log.of_kind("read")
    assert entry["op"] == "read_state" and entry["started_at"] <= entry["finished_at"]
    assert entry["latency_ms"] is not None
    assert entry["response"] == {"topics": 0, "edges": None}
