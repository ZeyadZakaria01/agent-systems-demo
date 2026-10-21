"""The over-flagging measurement (ticket 28; spec story 68): a transitive walk over extension edges on one chain, no
verdict. Serves report §5.5 ("how many hops") and the over-propagation cost of a StateMem-style walk.

The scenario (`demo/scenarios/over_flagging_chain.json`) is one chain A <- B <- C <- D joined by extension edges, one
update to A's field, and a label per dependent: B and C need revision, D does not (the anti-trap). `measure` builds the
chain on a system, updates A, reads each dependent's revision flag and reports flags raised against flags needed. The
reference GEM runs it twice: one hop (its default) and the transitive walk (`propagation="transitive"`, a mode used
only here). No MemState system is measured: none propagates (F17).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from demo.adapter import System

SCENARIO_PATH = Path(__file__).parent / "scenarios" / "over_flagging_chain.json"
EDGE_KIND = "extension"


def load_scenario(path: Path = SCENARIO_PATH) -> dict:
    return json.loads(path.read_text())


@dataclass(frozen=True)
class Counts:
    """Flags raised against flags needed, over the chain's dependents (A, the updated topic, is not a dependent)."""

    mode: str
    raised: list[str]
    needed: list[str]
    missed: list[str]  # needed and not raised
    not_needed: list[str]  # raised and not needed

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "flags_raised": len(self.raised),
            "flags_needed": len(self.needed),
            "flags_missed": len(self.missed),
            "flags_not_needed": len(self.not_needed),
        }


def measure(system: System, mode: str, scenario: dict | None = None) -> Counts:
    scenario = scenario or load_scenario()
    ids: dict[str, str] = {}
    for key, spec in scenario["topics"].items():  # insertion order: a dependent's edge target already exists
        edges = [{"to_topic_id": ids[spec["depends_on"]], "kind": EDGE_KIND}] if spec.get("depends_on") else []
        f = spec["field"]
        ids[key] = system.ingest(
            {
                "placement": "new_topic",
                "title": spec["title"],
                "topic_kind": spec["topic_kind"],
                "fields": [{"name": f["name"], "value": f["value"], "provenance": "scenario"}],
                "edges": edges,
            }
        )["topic_id"]
    state = system.read_state()
    if state["edges"] is not None:
        stored = {(e["from"], e["to"]) for e in state["edges"] if e.get("kind") == EDGE_KIND}
        missing = [
            k
            for k, s in scenario["topics"].items()
            if s.get("depends_on") and (ids[k], ids[s["depends_on"]]) not in stored
        ]
        if missing:
            raise RuntimeError(f"over-flagging setup failed: no extension edge stored for {missing}")
    update = scenario["update"]
    system.ingest(
        {
            "placement": "version_field",
            "topic_id": ids[update["topic"]],
            "fields": [{"name": update["field"], "value": update["value"], "provenance": "scenario"}],
        }
    )
    dependents = [k for k in scenario["topics"] if k != update["topic"]]
    raised = [k for k in dependents if ((system.read_topic(ids[k]) or {}).get("revision_flag") or {}).get("flagged")]
    needed = [k for k in dependents if scenario["needs_revision"][k]]
    return Counts(mode, raised, needed, [k for k in needed if k not in raised], [k for k in raised if k not in needed])
