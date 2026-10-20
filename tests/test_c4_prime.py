"""C4' provenance probe: one write with a source message; the entry's provenance must resolve to that stored message.
Stand-ins cover the three outcomes (stores and resolves, accepts a source but stores none, no source store); the
baseline stands in for the versioned row until ticket 20 lands. No MemState mock: upstream is proven by the smoke run."""

from demo.adapter import System
from demo.baseline import Baseline
from demo.checks import discover
from demo.checks.c4_prime import SOURCE_MESSAGE
from demo.memstate_system import request_properties, source_surface
from demo.verdict import ABSENT, FAIL, PASS

from tests.test_time_probes import _openapi


def c4_prime():
    return next(c for c in discover() if c.id == "C4′")


def run(system):
    (verdict,) = c4_prime().execute(system)
    return verdict


class SourceStore(Baseline):
    """Stores the source message with each write and links the entry to it by `source_id`."""

    def __init__(self):
        super().__init__("source-store")
        self.messages: dict[str, str] = {}
        self.entry_source: dict[tuple[str, str], str] = {}

    def _ingest(self, request):
        response = super()._ingest(request)
        for f in request.get("fields") or []:
            if f.get("source_message") is not None:
                sid = f"msg-{len(self.messages)}"
                self.messages[sid] = f["source_message"]
                self.entry_source[(response["topic_id"], f["name"])] = sid
        return response

    def _topic(self, row):
        topic = super()._topic(row)
        for name, f in topic["fields"].items():
            sid = self.entry_source.get((row["title"], name))
            f["current"] = {**f["current"], "source_id": sid}
        return topic

    def _resolve_source(self, entry):
        return self.messages.get(entry.get("source_id"))

    def _describe(self):
        return {**super()._describe(), "accepts_source": True}


class AcceptsButStoresNone(SourceStore):
    def _resolve_source(self, entry):
        return None


class DanglingSource(SourceStore):
    """Provenance points somewhere, but not at the message that was written."""

    def _resolve_source(self, entry):
        return "some other message"


def test_a_system_that_stores_and_resolves_the_source_passes():
    v = run(SourceStore())
    assert v.verdict == PASS
    assert [c.held for c in v.cases] == [True]


def test_a_system_that_accepts_a_source_but_stores_none_fails():
    v = run(AcceptsButStoresNone())
    assert v.verdict == FAIL
    assert "None" in v.cases[0].observation


def test_a_provenance_that_resolves_to_another_message_fails():
    assert run(DanglingSource()).verdict == FAIL


def test_the_versioned_row_baseline_and_any_system_with_no_source_store_are_absent_with_the_evidence():
    v = run(Baseline())
    assert v.verdict == ABSENT
    assert v.probe_evidence["accepts_source"] is False


def test_the_absent_system_is_not_sent_a_source_message():
    s = Baseline()
    run(s)
    assert not any("source_message" in f for e in s.log.of_kind("scored") for f in e["request"].get("fields", []))


def test_the_system_that_accepts_a_source_is_sent_exactly_the_message_and_the_resolution_is_logged_as_a_read():
    s = SourceStore()
    run(s)
    assert list(s.messages.values()) == [SOURCE_MESSAGE]
    assert [e["op"] for e in s.log.of_kind("read")].count("resolve_source") == 1


def test_the_row_is_in_the_probes_section_and_flagged_not_claimed_by_p1():
    (row,) = c4_prime().rows
    assert row.claim.startswith("Not claimed by [P1]")


def test_a_system_that_cannot_tell_whether_it_accepts_a_source_is_refused():
    class Unknown(Baseline):
        def _describe(self):
            return {**super()._describe(), "accepts_source": None, "accepts_error": "no schema"}

    import pytest
    with pytest.raises(RuntimeError, match="refusing to guess"):
        run(Unknown())


def test_the_schema_reading_finds_a_source_message_property_on_a_write_model_only():
    assert "source_message" not in request_properties(_openapi())
    assert "source_message" in request_properties(_openapi(write_fields=["source_message"]))
    assert "source_message" not in request_properties(_openapi(entry_fields=["source_message"]))


def test_the_surface_lists_every_source_named_property_and_path_the_schema_declares():
    doc = _openapi(write_fields=["source_id"])
    doc["paths"]["/v1/sources"] = {"get": {}}
    assert source_surface(doc) == {"request_properties": ["source_id"], "paths": ["/v1/sources"]}
    assert source_surface(_openapi()) == {"request_properties": [], "paths": []}


def test_the_prime_row_gets_its_own_snapshot_file():
    from demo.evidence import snapshot_path
    assert snapshot_path("baseline", "C4′") != snapshot_path("baseline", "C4")
