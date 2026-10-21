"""The reference GEM, phase 1: our own in-process system built to the paper's definitions of C1-C6 behind the system
adapter (ADR 0007; spec "Reference GEM"). No server, no LLM. Every decision below is fixed in the spec's parameter
table before the build and declared in the report; the result is worded "passes the suite's checks, with declared
simplifications", never "satisfies C1-C6".

State: topics with fields; each field a list of entries `{id, value, provenance, why_changed, valid_from, source_id}`
with ONE timestamp, `valid_from` (when the value became true; an undated write gets the write time); extension and
association edges; policies as data; per topic a salience, the interaction of its last touch and an archived flag.
Each ingest and each query is one interaction; the counter drives decay, the forgetting check and the windows.

Phase 1 reading of Definition 4: the current value is the entry with the latest timestamp not after the asked date.
No end date and no recorded time, so `describe()["accepts"]` is true for `valid_from` (writes) and `valid_at` (reads,
the asked date) only; `invalid_at` and `recorded_at` are not accepted (T4, T5 read absent).

Phase 2 (`ReferenceGem(phase=2)`, the same class: phase 1 plus C1', report §9.5, ADR 0005 as narrowed, and the same
rules as the patch, `patches/0002-bitemporal-field-histories.patch`): entries also carry `invalid_at`, `created_at`
and `expired_at`, and all four dates are accepted. An entry with no end of its own is valid until the next such
entry's `valid_from`; an entry with its own end layers over the others, the shorter validity wins, and a plain
statement ends every value whose stored validity contains its start, overrides included. An ordinary update stores
no end date and expires nothing. Keep and copy (`operation: "interval_corrected"`, `replaces_entry_id`,
`corrected_by_entry_id`, the original provenance on the copy) runs only when a stored end changes or `retract` is
called; expired entries are hidden unless history is requested. `valid_at` and `recorded_at` (what memory held then)
reads are history requests and raise salience like any read; a field with no value valid reads `current: None`.
Merge interleaves by valid time and tags entries as on step 3.

Transitions (`_ingest`): the request is validated, the proposed next state is built on copies, the policies are
evaluated against it, and it commits all or nothing. Policies are ⟨event, condition, action⟩ dicts stored in the
state (`add_policy`). Conditions: a comparison on the topic being written ({"field", "op", "other_field" | "value"};
`op` `empty` tests the written value, field `*` any written field) or "a neighbour exists via an extension or an
association edge" ({"neighbour": kind}, either edge direction). Actions: `reject` and `flag`. Events: `write` (every
ingest) and `field_updated` (a write of fields to an existing topic). Two policies ship: reject empty and null values
(`write`), and Listing 1, `propagate-on-change` (`field_updated`, a neighbour via an extension edge, flag): an update
flags every topic connected by an extension edge, whatever its direction, with evidence `{source_topic_id,
updated_field, timestamp}`; association edges never flag; a flag clears when the flagged topic is next written (a
write of fields), and that write flags its own neighbours. One hop, no repair (`propagation="transitive"`, a walk with a visited set, is a mode for
the over-flagging measurement only).

History: a field holds at most `HISTORY_CAP` active entries; the oldest overflow is archived, not deleted, and stays
readable (`archived_history` on a stored field, `archived_entry(id)`). The entry valid at the asked date is chosen
among all entries; when it is archived the field reads no current value plus a `note`. Every write stores its source
message (`source_message`) in a source store; `resolve_source(entry)` returns it.

Forgetting: salience rises by `BUMP` per returned topic (as-of reads included, no cap), decays by `LAMBDA` per
interaction of disuse (lazily: s * LAMBDA ** interactions since the last touch), and any read or write of a topic
resets its decay clock. A touch at interaction n materialises the decayed value of interaction n - 1 (the touching
interaction itself does not decay the topic) and adds the bump. After every interaction, topics whose salience is
below `THETA_ARCHIVE` are archived and their salience halved (MemState, `executor.py:360`). Archived topics are
neither retrieved nor decayed; a write to one is stored and leaves it archived.

Revision: after every ingest, as a separate step after the write commits (`revise`, as MemState's Reasoner does,
`reasoner/engine.py:36-37`): non-archived topics sharing one title are merged into the lowest id (the survivor keeps
both histories, each entry tagged `operation: "merged"` and `merged_from_topic_id`, and the edges), the dropped
topic is deleted. The current value is then the entry with the latest timestamp, the later write. A system built
with `revise_after_ingest=False` shows both copies until `revise()` runs.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from demo.adapter import Rejected, System
from demo.embedding import MODEL, unit_vector, unit_vectors

PHASES = (1, 2)


def reference_gem_id(phase: int) -> str:
    """The id a phase is registered under (`demo/systems.py`), the one place the pattern is written."""
    return f"reference-gem-p{phase}"


# the parameter table (spec "Reference GEM")
THETA_ARCHIVE = 0.05  # MemState's forget_salience_threshold
DECAY_HORIZON = 400  # an untouched topic at 1.0 falls below THETA_ARCHIVE after this many interactions
LAMBDA = THETA_ARCHIVE ** (1 / DECAY_HORIZON)  # ~0.9925 per interaction
BETA = 500  # declared bound on active topics (MemState's topic_count_soft_limit)
BUMP = 0.1  # per returned topic (MemState's query_salience_bump)
ARCHIVE_FACTOR = 0.5  # salience is halved when a topic is archived (MemState executor.py:360)
HISTORY_CAP = 500  # active entries per field; overflow is archived
TOP_K = 8
C6_CLAUSE_2_SEEDS = {"target": 0.06, "control": 0.06}  # a seed below THETA_ARCHIVE is archived by its own interaction
EPS = 1e-9
EDGE_KINDS = ("extension", "association")
EVENTS = ("write", "field_updated")
ACTIONS = ("reject", "flag")
PROPAGATIONS = (
    "one_hop",
    "transitive",
)  # `transitive` (a walk with a visited set) exists only for the over-flagging measurement
OPS = ("<", "<=", ">", ">=", "==", "!=", "empty")

DEFAULT_POLICIES = (
    {"name": "reject-empty-values", "event": "write", "condition": {"field": "*", "op": "empty"}, "action": "reject"},
    {
        "name": "propagate-on-change",
        "event": "field_updated",
        "condition": {"neighbour": "extension"},
        "action": "flag",
    },  # the paper's Listing 1
)


@dataclass
class Entry:
    id: str
    value: Any
    provenance: str
    why_changed: str | None
    impact_expected: str | None
    valid_from: datetime
    seq: int  # global write order: breaks ties between equal timestamps
    source_id: str | None = None
    operation: str | None = None
    merged_from_topic_id: str | None = None
    invalid_at: datetime | None = None  # phase 2: the entry's own stored end ("for October only")
    created_at: datetime | None = None  # when memory recorded the entry
    expired_at: datetime | None = None  # phase 2: when memory stopped holding it (keep and copy)
    replaces_entry_id: str | None = None  # on a corrected copy: the expired original
    corrected_by_entry_id: str | None = None  # on an expired original: its corrected copy

    def view(self, phase: int = 1) -> dict:
        out = {
            "id": self.id,
            "value": self.value,
            "provenance": self.provenance,
            "why_changed": self.why_changed,
            "impact_expected": self.impact_expected,
            "valid_from": self.valid_from.isoformat(),
            "expired_at": None,
            "source_id": self.source_id,
        }
        if phase >= 2:
            out.update(
                invalid_at=_iso(self.invalid_at),
                created_at=_iso(self.created_at),
                expired_at=_iso(self.expired_at),
                replaces_entry_id=self.replaces_entry_id,
                corrected_by_entry_id=self.corrected_by_entry_id,
            )
        if self.operation:
            out.update(operation=self.operation, merged_from_topic_id=self.merged_from_topic_id)
        return out

    @property
    def order(self) -> tuple:
        return (self.valid_from, self.seq)


@dataclass
class Field:
    field_type: str = "string"
    ref_topic_id: str | None = None
    entries: list[Entry] = field(default_factory=list)  # active, in insertion order
    archived: list[Entry] = field(default_factory=list)  # overflow of the cap, in insertion order

    def copy(self) -> Field:
        return Field(self.field_type, self.ref_topic_id, list(self.entries), list(self.archived))


@dataclass
class Topic:
    id: str
    title: str
    summary: str | None
    topic_kind: str | None
    salience: float
    touch: int  # the interaction of the last read or write; `salience` is the value materialised then
    created_at: str
    updated_at: str
    archived: bool = False
    fields: dict[str, Field] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    flag: dict | None = None  # the evidence of the pending revision flag, None when not flagged

    def copy(self) -> Topic:
        return replace(self, fields={n: f.copy() for n, f in self.fields.items()}, events=list(self.events))


@dataclass
class Proposal:
    """The proposed next state of one transition: the written topic (a copy), new edges and sources, flags to raise."""

    topic: Topic
    created: bool
    edges: list[tuple[str, str, str]] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    flags: dict[str, dict] = field(default_factory=dict)  # topic id -> evidence
    written: list[tuple[str, Any]] = field(default_factory=list)  # (field name, value) of this write
    seqs: int = 0  # write-order numbers taken by this transition (entries and corrected copies)
    applied: list[str] = field(default_factory=list)  # what the response reports as applied
    version_ids: dict[str, str] = field(default_factory=dict)  # field name -> id of the entry this write appended
    updated: bool = False  # an existing topic was written to (its own flag clears)


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat()


def _utc(text: Any, what: str) -> datetime:
    if not isinstance(text, str):
        raise Rejected(422, f"{what} must be an ISO date or timestamp, got {text!r}")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        raise Rejected(422, f"{what} is not an ISO date or timestamp: {text!r}") from None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _compare(left: Any, op: str, right: Any) -> bool:
    try:
        left, right = float(left), float(right)  # numbers compare as numbers, everything else as ISO strings
    except (TypeError, ValueError):
        left, right = str(left), str(right)
    return {
        "<": left < right,
        "<=": left <= right,
        ">": left > right,
        ">=": left >= right,
        "==": left == right,
        "!=": left != right,
    }[op]


class ReferenceGem(System):
    def __init__(
        self,
        label: str | None = None,
        clock: Callable[[], datetime] | None = None,
        revise_after_ingest: bool = True,
        propagation: str = "one_hop",
        phase: int = 1,
    ) -> None:
        if phase not in PHASES:
            raise ValueError(f"phase is one of {PHASES}, got {phase!r}")
        super().__init__(label or f"reference GEM (phase {phase})")
        self.phase = phase
        self.bitemporal = phase >= 2  # the one switch phase 2 turns on: dated ends, recorded time, keep-and-copy
        if propagation not in PROPAGATIONS:
            raise ValueError(f"propagation is one of {PROPAGATIONS}, got {propagation!r}")
        self.propagation = propagation
        self._clock = clock or (lambda: datetime.now(UTC))
        self.revise_after_ingest = revise_after_ingest
        self._topics: dict[str, Topic] = {}
        self._active: set[str] = set()
        self._edges: list[tuple[str, str, str]] = []  # (from, to, kind)
        self._policies: list[dict] = [dict(p, condition=dict(p["condition"])) for p in DEFAULT_POLICIES]
        self._sources: dict[str, str] = {}
        self._interactions = 0
        self._seq = 0

    @property
    def interactions(self) -> int:
        """Interactions so far: every ingest and every query (rejected ones too) counts as one."""
        return self._interactions

    # -- salience: lazy decay, resets on touch
    def _effective(self, topic: Topic, at: int) -> float:
        """Salience as of the end of interaction `at`. An archived topic no longer decays."""
        if topic.archived:
            return topic.salience
        return topic.salience * LAMBDA ** max(0, at - topic.touch)

    def _touch(self, topic: Topic, at: int, bump: float = 0.0) -> None:
        topic.salience = self._effective(topic, at - 1) + bump
        topic.touch = at

    def _set_archived(self, topic: Topic, archived: bool) -> None:
        topic.archived = archived
        (self._active.discard if archived else self._active.add)(topic.id)

    def _forget(self, at: int) -> None:
        """The forgetting check, after every interaction: archive what fell below the threshold, halving its salience."""
        for tid in list(self._active):
            topic = self._topics[tid]
            salience = self._effective(topic, at)
            if salience < THETA_ARCHIVE - EPS:
                topic.salience, topic.touch = salience * ARCHIVE_FACTOR, at
                self._set_archived(topic, True)
                topic.events.append(
                    {
                        "ts": self._clock().isoformat(),
                        "kind": "archived",
                        "detail": {"salience_before": salience, "salience_after": topic.salience},
                    }
                )

    # -- field values
    def _live(self, f: Field, recorded: datetime | None) -> list[Entry]:
        """The entries memory holds: all of them in phase 1; in phase 2 those not expired, or, asked what memory held
        at `recorded`, those recorded by then and not yet expired then (an entry that has expired since counts as live)."""
        entries = (*f.entries, *f.archived)
        if not self.bitemporal:
            return list(entries)
        if recorded is None:
            return [e for e in entries if e.expired_at is None]
        return [e for e in entries if e.created_at <= recorded and (e.expired_at is None or e.expired_at > recorded)]

    @staticmethod
    def _resolve(live: list[Entry], asked: datetime) -> Entry | None:
        """Phase 2 (report §9.5): an entry with no end of its own is valid until the next such entry's `valid_from`;
        an entry with its own end is valid until that end and layers over the others. Of several valid at `asked`,
        the shorter validity wins, then the later recorded."""
        plain = sorted((e for e in live if e.invalid_at is None), key=lambda e: e.order)
        ends: dict[str, datetime | None] = {
            e.id: plain[i + 1].valid_from if i + 1 < len(plain) else None for i, e in enumerate(plain)
        }
        ends.update({e.id: e.invalid_at for e in live if e.invalid_at is not None})
        best: tuple[float, int] | None = None
        found: Entry | None = None
        for e in live:
            end = ends[e.id]
            if e.valid_from > asked or (end is not None and end <= asked):
                continue
            key = (float("inf") if end is None else (end - e.valid_from).total_seconds(), -e.seq)
            if best is None or key < best:
                best, found = key, e
        return found

    def _valid_entry(
        self, f: Field, asked: datetime, recorded: datetime | None = None
    ) -> tuple[Entry | None, str | None]:
        """The entry valid at `asked`, among all entries memory holds (phase 1: the latest timestamp not after it;
        phase 2: `_resolve`). When that entry was archived as overflow there is no current value and a note says so."""
        live = self._live(f, recorded)
        if not self.bitemporal:
            best = max((e for e in live if e.valid_from <= asked), key=lambda e: e.order, default=None)
        else:
            best = self._resolve(live, asked)
        if best is not None and any(best is e for e in f.archived):
            return None, f"no current value: the value valid then ({best.value!r}, entry {best.id}) is archived"
        return best, None

    def _corrected_copy(self, f: Field, old: Entry, invalid_at: datetime, now: datetime, seq: int) -> Entry:
        """Keep and copy (ADR 0005): `old` is kept with `expired_at` = now, and a corrected copy with the original
        provenance and the new stored end is appended. `f` is replaced in place (a proposed copy, or the merge)."""
        copy = replace(
            old,
            id=str(uuid.uuid4()),
            invalid_at=invalid_at,
            created_at=now,
            expired_at=None,
            seq=seq,
            operation="interval_corrected",
            replaces_entry_id=old.id,
            corrected_by_entry_id=None,
        )
        f.entries[f.entries.index(old)] = replace(old, expired_at=now, corrected_by_entry_id=copy.id)
        f.entries.append(copy)
        return copy

    def retract(self, topic_id: str, field_name: str, entry_id: str) -> str:
        """Retract a value (phase 2): it is kept with `expired_at`, and a linked copy valid nowhere (its end is its
        start) is appended. Returns the copy's id. A store-level operation like the patch's `retract_field_entry`:
        the adapter has no request for it, and it is not an interaction."""
        if not self.bitemporal:
            raise ValueError("phase 1 has no retraction")
        f = self._topics[topic_id].fields[field_name]
        old = next((e for e in f.entries if e.id == entry_id and e.expired_at is None), None)
        if old is None:
            raise ValueError(f"no live history entry: {entry_id}")
        self._seq += 1
        copy = self._corrected_copy(f, old, old.valid_from, self._clock(), self._seq)
        self._cap(f)
        return copy.id

    def _field_view(self, f: Field, asked: datetime, history: bool, recorded: datetime | None = None) -> dict:
        current, note = self._valid_entry(f, asked, recorded)
        out = {
            "field_type": f.field_type,
            "ref_topic_id": f.ref_topic_id,
            "current": None if current is None else current.view(self.phase),
            "history": [e.view(self.phase) for e in sorted(f.entries, key=lambda e: e.order, reverse=True)]
            if history
            else None,
        }
        if history:
            out["archived_history"] = [
                e.view(self.phase) for e in sorted(f.archived, key=lambda e: e.order, reverse=True)
            ]
        if note:
            out["note"] = note
        return out

    def _flag_view(self, topic: Topic) -> dict:
        return {"flagged": True, "evidence": dict(topic.flag)} if topic.flag else {"flagged": False}

    def _topic_view(self, topic: Topic, asked: datetime | None = None) -> dict:
        asked = asked or self._clock()
        return {
            "id": topic.id,
            "title": topic.title,
            "summary": topic.summary,
            "topic_kind": topic.topic_kind,
            "salience": self._effective(topic, self._interactions),
            "failed_salience": None,
            "archived": topic.archived,
            "revision_flag": self._flag_view(topic),
            "fields": {n: self._field_view(f, asked, history=True) for n, f in topic.fields.items()},
            "topic_history": list(topic.events),
            "created_at": topic.created_at,
            "updated_at": topic.updated_at,
        }

    # -- policies
    def _add_policy(self, rule: dict) -> dict:
        condition = rule.get("condition")
        if rule.get("event") not in EVENTS or rule.get("action") not in ACTIONS or not isinstance(condition, dict):
            raise ValueError(f"a policy is {{name, event in {EVENTS}, condition, action in {ACTIONS}}}: {rule!r}")
        if "neighbour" in condition:
            valid = condition["neighbour"] in EDGE_KINDS
        else:
            valid = (
                condition.get("op") in OPS
                and isinstance(condition.get("field"), str)
                and (condition["op"] == "empty" or "other_field" in condition or "value" in condition)
            )
        if not valid or not rule.get("name"):
            raise ValueError(
                f"unsupported policy condition (the fixed vocabulary is field comparisons and a "
                f"neighbour via an extension or association edge): {rule!r}"
            )
        stored = {"name": rule["name"], "event": rule["event"], "condition": dict(condition), "action": rule["action"]}
        self._policies = [p for p in self._policies if p["name"] != stored["name"]] + [stored]
        return dict(stored, condition=dict(condition))

    def _neighbours(self, topic_id: str, kind: str, extra: list[tuple[str, str, str]]) -> list[str]:
        """Topics linked to `topic_id` by an edge of `kind`, whatever its direction."""
        found = {
            (b if a == topic_id else a)
            for a, b, k in (*self._edges, *extra)
            if k == kind and topic_id in (a, b) and a != b
        }
        return sorted(found)

    def _flag_targets(self, topic_id: str, kind: str, extra: list[tuple[str, str, str]]) -> list[str]:
        """The topics an update flags: the neighbours (one hop, the default), or in `transitive` mode every topic
        reachable over edges of `kind`, each once (visited set), the updated topic excluded."""
        if self.propagation == "one_hop":
            return self._neighbours(topic_id, kind, extra)
        seen, frontier = {topic_id}, [topic_id]
        while frontier:
            frontier = [n for t in frontier for n in self._neighbours(t, kind, extra) if n not in seen]
            frontier = sorted(set(frontier))
            seen.update(frontier)
        return sorted(seen - {topic_id})

    def _holds(self, condition: dict, proposal: Proposal) -> bool:
        if "neighbour" in condition:
            return bool(self._neighbours(proposal.topic.id, condition["neighbour"], proposal.edges))
        name, op = condition["field"], condition["op"]
        if op == "empty":
            return any(
                v is None or (isinstance(v, str) and not v.strip()) for n, v in proposal.written if name in ("*", n)
            )
        f = proposal.topic.fields.get(name)
        entry = None if f is None else self._valid_entry(f, self._clock())[0]
        if entry is None:
            return False
        if "other_field" in condition:
            other = proposal.topic.fields.get(condition["other_field"])
            other_entry = None if other is None else self._valid_entry(other, self._clock())[0]
            return other_entry is not None and _compare(entry.value, op, other_entry.value)
        return _compare(entry.value, op, condition["value"])

    def _apply_policies(self, proposal: Proposal, now: datetime) -> None:
        """Evaluate every stored policy on the proposed next state. A `reject` that fires aborts the transition; a
        `flag` that fires collects evidence for the topics to flag (the neighbours, or the written topic itself)."""
        for policy in self._policies:
            if policy["event"] == "field_updated" and not proposal.updated:
                continue
            condition = policy["condition"]
            if not self._holds(condition, proposal):
                continue
            if policy["action"] == "reject":
                raise Rejected(409, f"policy {policy['name']!r} rejects this write")
            names = [n for n, _ in proposal.written]
            if not names:
                continue  # a flag names the updated field: a write of no fields has none
            evidence = {
                "source_topic_id": proposal.topic.id,
                "updated_field": names[0],
                "updated_fields": names,
                "timestamp": now.isoformat(),
                "policy": policy["name"],
            }
            targets = (
                self._flag_targets(proposal.topic.id, condition["neighbour"], proposal.edges)
                if "neighbour" in condition
                else [proposal.topic.id]
            )
            for target in targets:
                proposal.flags[target] = evidence

    # -- transitions
    def _tick(self) -> int:
        self._interactions += 1
        return self._interactions

    def _ingest(self, request: dict) -> dict:
        at = self._tick()
        try:
            response = self._transact(request, at)
            if self.revise_after_ingest:
                self.revise()
            return response
        finally:
            self._forget(at)

    def _propose(self, request: dict, at: int) -> Proposal:
        placement = request["placement"]
        writes = request.get("fields") or []
        now = self._clock()
        stamp = now.isoformat()
        if placement == "new_topic":
            topic = Topic(
                str(uuid.uuid4()),
                request.get("title") or "untitled",
                request.get("summary"),
                request.get("topic_kind"),
                float(request.get("salience", 1.0)),
                at,
                stamp,
                stamp,
            )
            created = True
        elif placement in ("extend_topic", "version_field"):
            base = self._topics.get(request.get("topic_id"))
            if base is None:
                raise Rejected(400, "topic not found")
            if placement == "version_field" and len(writes) != 1:
                raise Rejected(400, "version_field requires topic_id and exactly one field")
            topic, created = base.copy(), False
        else:
            raise Rejected(422, f"unknown placement {placement!r}")
        proposal = Proposal(topic, created, updated=bool(writes) and not created)
        if created:
            proposal.applied.append(f"created_topic:{topic.id}")
        for w in writes:
            name = w.get("name")
            if not isinstance(name, str) or not name:
                raise Rejected(422, "a field needs a name")
            ref = w.get("ref_topic_id")
            if ref is not None and ref not in self._topics:
                raise Rejected(400, f"ref_topic_id not found: {ref}")
            moment = _utc(w["valid_from"], "valid_from") if w.get("valid_from") is not None else now
            ends = _utc(w["invalid_at"], "invalid_at") if self.bitemporal and w.get("invalid_at") is not None else None
            f = topic.fields.setdefault(name, Field(w.get("field_type") or "string"))
            if ref is not None:
                f.ref_topic_id = ref
            source = None
            if w.get("source_message") is not None:
                source = str(uuid.uuid4())
                proposal.sources[source] = w["source_message"]
            if self.bitemporal and ends is None:
                # a plain statement ends every value whose stored validity contains its start, overrides included:
                # a changed stored end, so each is kept, expired and copied
                for old in [
                    e
                    for e in f.entries
                    if e.invalid_at is not None and e.expired_at is None and e.valid_from <= moment < e.invalid_at
                ]:
                    self._corrected_copy(f, old, moment, now, self._take_seq(proposal))
            entry = Entry(
                str(uuid.uuid4()),
                w.get("value", ""),
                w.get("provenance") or "api",
                w.get("why_changed"),
                w.get("impact_expected"),
                moment,
                self._take_seq(proposal),
                source,
                invalid_at=ends,
                created_at=now,
            )
            f.entries.append(entry)
            self._cap(f)
            proposal.written.append((name, entry.value))
            proposal.version_ids[name] = entry.id
            proposal.applied.append(f"version:{name}" if placement == "version_field" else f"field:{name}")
        for e in request.get("edges") or []:
            target, kind = e.get("to_topic_id"), e.get("kind")
            if kind not in EDGE_KINDS:
                raise Rejected(422, f"edge kind must be one of {EDGE_KINDS}, got {kind!r}")
            if target not in self._topics:
                raise Rejected(400, f"edge target topic not found: {target}")
            if (topic.id, target, kind) not in proposal.edges:
                proposal.edges.append((topic.id, target, kind))
            proposal.applied.append(f"edge:{target}")
        return proposal

    def _take_seq(self, proposal: Proposal) -> int:
        """The next write-order number inside a transition (committed to `_seq` with it)."""
        proposal.seqs += 1
        return self._seq + proposal.seqs

    def _cap(self, f: Field) -> None:
        """The history cap: the oldest entries beyond `HISTORY_CAP` leave the active history and are archived."""
        while len(f.entries) > HISTORY_CAP:
            oldest = min(f.entries, key=lambda e: e.seq)
            f.entries.remove(oldest)
            f.archived.append(oldest)

    def _transact(self, request: dict, at: int) -> dict:
        """Validate, build the proposed next state, check the policies against it, commit all or nothing."""
        proposal = self._propose(request, at)
        now = self._clock()
        topic = proposal.topic
        if proposal.updated:
            topic.flag = None  # the flag clears when the topic is next written
        self._apply_policies(proposal, now)
        if topic.id in proposal.flags:
            topic.flag = proposal.flags[topic.id]
        # commit: nothing below can fail
        if not proposal.created:
            self._touch(topic, at)
        topic.updated_at = now.isoformat()
        self._topics[topic.id] = topic
        if proposal.created:
            self._active.add(topic.id)
        self._edges.extend(proposal.edges)
        self._sources.update(proposal.sources)
        self._seq += proposal.seqs
        for tid, evidence in proposal.flags.items():
            if tid != topic.id:
                target = self._topics[tid]
                target.flag = evidence
                target.events.append({"ts": now.isoformat(), "kind": "flagged", "detail": evidence})
        return {
            "topic_id": topic.id,
            "applied": proposal.applied,
            "version_ids": proposal.version_ids,
            "similar_topic_ids": [],
        }

    # -- revision (merge)
    def revise(self) -> list[str]:
        """Merge non-archived topics that share a title into the lowest id. Returns the merge actions."""
        groups: dict[str, list[str]] = {}
        for tid in self._active:
            title = self._topics[tid].title
            if title:
                groups.setdefault(title, []).append(tid)
        actions = []
        for title, ids in groups.items():
            keep, *dropped = sorted(ids)
            for drop in dropped:
                self._merge(keep, drop)
                actions.append(f"merged:{drop}->:{keep}:{title}")
        return actions

    def _end_overrides_across(self, kf: Field, moved_ids: set[str]) -> None:
        """Merge by valid time (phase 2, step 3): interleaving two histories, a plain entry of one side that starts
        inside the stored validity of an end-dated entry of the other ends it: that entry is kept, expired and copied,
        with the end moved to the earliest such start."""
        now = self._clock()
        live = [e for e in kf.entries if e.expired_at is None]
        plains = [e for e in live if e.invalid_at is None]
        for o in live:
            if o.invalid_at is None:
                continue
            starts = [
                p.valid_from
                for p in plains
                if (p.id in moved_ids) != (o.id in moved_ids) and o.valid_from <= p.valid_from < o.invalid_at
            ]
            if starts:
                self._seq += 1
                self._corrected_copy(kf, o, min(starts), now, self._seq)

    def _merge(self, keep_id: str, drop_id: str) -> None:
        keep, drop = self._topics[keep_id], self._topics[drop_id]
        for name, df in drop.fields.items():
            kf = keep.fields.setdefault(name, Field(df.field_type, df.ref_topic_id))
            tag = {"operation": "merged", "merged_from_topic_id": drop_id}
            moved = [replace(e, **tag) for e in df.entries]
            kf.entries.extend(moved)
            kf.archived.extend(replace(e, **tag) for e in df.archived)
            if self.bitemporal:
                self._end_overrides_across(kf, {e.id for e in moved})
            self._cap(kf)
        rewired: list[tuple[str, str, str]] = []
        for a, b, kind in self._edges:
            edge = (keep_id if a == drop_id else a, keep_id if b == drop_id else b, kind)
            if edge[0] != edge[1] and edge not in rewired:
                rewired.append(edge)
        self._edges = rewired
        keep.flag = keep.flag or drop.flag
        keep.events.append({"ts": self._clock().isoformat(), "kind": "merged", "detail": {"from_topic_id": drop_id}})
        del self._topics[drop_id]
        self._active.discard(drop_id)

    # -- retrieval
    def _query(self, request: dict) -> dict:
        at = self._tick()
        try:
            return self._retrieve(request, at)
        finally:
            self._forget(at)

    def _retrieve(self, request: dict, at: int) -> dict:
        stages = request.get("stages") or ["semantic", "structural", "temporal"]
        top_k = request.get("top_k") or TOP_K
        allowed = request.get("topic_ids")
        sims: dict[str, float | None]
        if "semantic" in stages:
            ids = sorted(self._active)
            if ids:
                texts = [f"{self._topics[t].title}\n{self._topics[t].summary or ''}" for t in ids]
                scores = unit_vectors(texts) @ unit_vector(request["q"])
                ranked = sorted(zip(scores.tolist(), ids), reverse=True)[:top_k]
            else:
                ranked = []
            sims = {t: s for s, t in ranked if allowed is None or t in allowed}
        else:
            ids = allowed if allowed is not None else sorted(self._active)
            sims = {t: None for t in ids[:top_k] if t in self._topics}
        asked = _utc(request["valid_at"], "valid_at") if request.get("valid_at") is not None else self._clock()
        recorded = (
            _utc(request["recorded_at"], "recorded_at")
            if self.bitemporal and request.get("recorded_at") is not None
            else None
        )
        as_of = self.bitemporal and (request.get("valid_at") is not None or recorded is not None)
        names = request.get("field_names")
        explain = bool(request.get("explain"))
        candidates = []
        for tid, sim in sims.items():
            topic = self._topics[tid]
            if topic.archived:
                continue
            fields = []
            if "structural" in stages or "temporal" in stages:
                fields = [
                    {"name": n, **self._field_view(f, asked, explain or as_of, recorded)}
                    for n, f in sorted(topic.fields.items())
                    if names is None or n in names
                ]
            neighbours = (
                [
                    {"topic_id": b if a == tid else a, "kind": k, "direction": "out" if a == tid else "in"}
                    for a, b, k in self._edges
                    if tid in (a, b)
                ]
                if "structural" in stages
                else []
            )
            candidates.append(
                {
                    "topic_id": tid,
                    "title": topic.title,
                    "summary": topic.summary,
                    "topic_kind": topic.topic_kind,
                    "salience": self._effective(topic, at - 1),
                    "failed_salience": None,
                    "neighbors": neighbours,
                    "fields": fields,
                    "revision_flag": self._flag_view(topic),
                    "similarity": sim,
                }
            )
            self._bump(topic, at)
        return {"query": request["q"], "candidates": candidates, "summary_text": ""}

    def _bump(self, topic: Topic, at: int) -> None:
        self._touch(topic, at, BUMP)

    # -- reads of stored state (no interaction, no touch)
    def _read_topic(self, topic_id: str) -> dict | None:
        topic = self._topics.get(topic_id)
        return None if topic is None else self._topic_view(topic)

    def _read_state(self) -> dict:
        return {
            "topics": {tid: self._topic_view(t) for tid, t in self._topics.items()},
            "edges": [{"from": a, "to": b, "kind": k} for a, b, k in self._edges],
            "policies": [dict(p, condition=dict(p["condition"])) for p in self._policies],
            "interactions": self._interactions,
        }

    def _list_topic_ids(self, include_archived: bool) -> list[str]:
        return [t for t, topic in self._topics.items() if include_archived or not topic.archived]

    def _resolve_source(self, entry: dict) -> Any:
        return self._sources.get(entry.get("source_id"))

    def archived_entry(self, entry_id: str) -> dict | None:
        """An entry archived as history overflow, by id; `None` when no archived entry has it."""
        for topic in self._topics.values():
            for f in topic.fields.values():
                for e in f.archived:
                    if e.id == entry_id:
                        return e.view()
        return None

    # -- editor paths: setup writes, never scored, no interaction
    def _setup_write(self, action: str, params: dict) -> dict | None:
        at = self._interactions
        if action == "create_topic":
            tid = params.get("topic_id") or str(uuid.uuid4())
            stamp = self._clock().isoformat()
            self._topics[tid] = Topic(
                tid,
                params.get("title") or "untitled",
                params.get("summary"),
                params.get("topic_kind"),
                float(params.get("salience", 1.0)),
                at,
                stamp,
                stamp,
            )
            self._active.add(tid)
            return {"topic_id": tid}
        if action == "patch_topic":
            topic = self._topics.get(params["topic_id"])
            if topic is None:
                raise Rejected(404, "topic not found")
            for key in ("title", "summary", "topic_kind"):
                if params.get(key) is not None:
                    setattr(topic, key, params[key])
            if params.get("salience") is not None:
                topic.salience, topic.touch = float(params["salience"]), at
            if params.get("archived") is not None and params["archived"] != topic.archived:
                if params["archived"]:
                    topic.salience, topic.touch = self._effective(topic, at), at
                else:
                    topic.touch = at
                self._set_archived(topic, bool(params["archived"]))
            return {"topic_id": topic.id}
        if action == "add_edge":
            source, target, kind = params["from_id"], params["to_topic_id"], params["kind"]
            if source not in self._topics or target not in self._topics:
                raise Rejected(404, "topic not found")
            if kind not in EDGE_KINDS:
                raise Rejected(422, f"edge kind must be one of {EDGE_KINDS}, got {kind!r}")
            if (source, target, kind) not in self._edges:
                self._edges.append((source, target, kind))
            return {"ok": "true"}
        raise ValueError(f"unknown setup action {action!r}")

    def variant(self, name: str) -> ReferenceGem | None:
        if name != "transitive":
            return None
        return ReferenceGem(
            f"{self.label}, transitive walk",
            clock=self._clock,
            revise_after_ingest=self.revise_after_ingest,
            propagation="transitive",
            phase=self.phase,
        )

    def _describe(self) -> dict:
        return {
            "engine": f"in-process reference GEM, phase {self.phase}",
            "keeps_history": True,
            "embedder": MODEL,
            "top_k": TOP_K,
            "latency_comparable": False,
            "accepts": {
                "valid_from": True,
                "invalid_at": self.bitemporal,
                "valid_at": True,
                "recorded_at": self.bitemporal,
            },
            "declared_bound": {"topics": BETA, "name": "β"},
            "accepts_source": True,
            "source_surface": {"request_properties": ["source_message"], "paths": []},
            "c6_clause_2_seeds": C6_CLAUSE_2_SEEDS,
            "parameters": {
                "theta_archive": THETA_ARCHIVE,
                "lambda": LAMBDA,
                "decay_horizon": DECAY_HORIZON,
                "beta": BETA,
                "bump": BUMP,
                "history_cap": HISTORY_CAP,
                "top_k": TOP_K,
                "salience_on_archive": ARCHIVE_FACTOR,
                "propagation": self.propagation.replace("_", " ") + ", extension edges, either direction",
                "revision": "after every ingest" if self.revise_after_ingest else "only on revise()",
                "phase": self.phase,
            },
        }
