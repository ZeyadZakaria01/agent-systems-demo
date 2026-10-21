"""Play the storyline on a system, ask its questions, triage every answer, measure reinforcement precision.

Only the system adapter is used. `play` sends each event as a scored `/v1` placement and, after each, reads the touched
topic back (a UI read: no salience bump) to compare its title and current values, and, for an event that writes edges
and a system that reports them, its related edges, with the state the storyline expects; a difference is a write-path
finding reported apart from the questions. `ask` sends each question as a plain query (the
default stages, `top_k` 8, the baseline's top 8 too) and sorts it with StateMemBench's first triage question
(`docs/papers/2608.19652v1.md:455`, "is the gold fact in context? (no -> retrieval failure)"):

- answered: the read returned the labelled topic and the ground-truth value is current in the labelled field;
- search failure: the labelled topic was not returned (a wrong answer);
- memory failure: the labelled topic was returned and its stored value is wrong (or the field has no value).

Reinforcement precision = salience increments to the labelled topic / all salience increments over the questions,
measured by reading every topic's salience before and after each question (reads through the UI bump nothing). The
read's own `salience` is the value before its bump (`executor.py:310-339`), so it cannot show the effect. Because every
returned topic is bumped, this equals the micro-averaged Precision@k of the retrieval; the same ratio is computed from
the returned lists and reported beside it, so the equality is observed, not assumed. A system with no salience reads as
`None` (not applicable).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from demo.adapter import System
from demo.reads import NO_VALUE, current_value, field_in_response
from demo.storyline import Event, Question, Storyline

CORRECT, SEARCH_FAILURE, MEMORY_FAILURE = "correct", "search failure", "memory failure"
DEFAULT_TOP_K = 8  # MemState's default; a system declares its own in `describe()["top_k"]` (the baseline's is 8 as well)
EPS = 1e-6


@dataclass
class EventResult:
    event: str
    topic_id: str
    matched: bool
    observation: str
    edges_declared: bool = False  # the event writes edges
    edges_compared: bool = False  # ... and the system reports edges, so they were compared (n/a where it does not)


@dataclass
class QuestionOutcome:
    question: str
    ability: str
    text: str
    truth: Any
    topic: str  # the labelled topic's key
    topic_id: str  # ... and the id the system gave it
    outcome: str
    returned: bool
    rank: int | None  # 1-based position of the labelled topic among the candidates
    returned_ids: list[str]
    stored: Any  # the labelled field's current value as read; None when not returned, "<no value>" when empty
    increments_labelled: float | None  # salience gained by the labelled topic over this question; None = not measurable
    increments_all: float | None  # ... by every topic


@dataclass
class Reinforcement:
    labelled_increments: float
    all_increments: float
    precision: float | None  # None when nothing was bumped
    questions_bumped: int  # questions whose labelled topic was bumped at all
    questions: int
    precision_at_k: float | None  # same ratio from the returned lists: labelled returned / candidates returned
    matches_precision_at_k: bool | None


@dataclass
class StorylineRun:
    top_k: int
    topic_ids: dict[str, str]
    events: list[EventResult] = field(default_factory=list)
    outcomes: list[QuestionOutcome] = field(default_factory=list)
    reinforcement: Reinforcement | None = None

    @property
    def triage(self) -> dict[str, int]:
        return {"questions": len(self.outcomes), "correct": self._count(CORRECT),
                "search_failures": self._count(SEARCH_FAILURE), "memory_failures": self._count(MEMORY_FAILURE)}

    def _count(self, outcome: str) -> int:
        return sum(1 for o in self.outcomes if o.outcome == outcome)

    def to_measurements(self) -> dict:
        """What the check stores on its verdict and the renderer reads (`demo/storyline_tables.py`)."""
        return {"storyline": {
            "top_k": self.top_k, "triage": self.triage,
            "events": {"total": len(self.events), "matched": sum(e.matched for e in self.events),
                       "with_edges": sum(1 for e in self.events if e.edges_declared),
                       "edges_compared": sum(e.edges_compared for e in self.events),
                       "mismatches": [asdict(e) for e in self.events if not e.matched]},
            "questions": [asdict(o) for o in self.outcomes],
            "reinforcement": None if self.reinforcement is None else asdict(self.reinforcement),
        }}


def run_storyline(system: System, storyline: Storyline) -> StorylineRun:
    run = StorylineRun(top_k=system.describe().get("top_k") or DEFAULT_TOP_K, topic_ids={})
    run.events = play(system, storyline, run.topic_ids)
    run.outcomes, run.reinforcement = ask(system, storyline, run.topic_ids, run.top_k)
    return run


def play(system: System, storyline: Storyline, ids: dict[str, str]) -> list[EventResult]:
    """Send every event as a scored placement, filling `ids` (topic key -> the id the system returned)."""
    results = []
    scope = system.describe().get("title_scope")  # live mode scopes titles: " [live <scope>]" (demo/live.py)
    suffix = f" [live {scope}]" if scope else ""
    for event in storyline.events:
        response = system.ingest(event.request(ids))
        if event.placement == "new_topic":
            ids[event.topic] = response["topic_id"]
        results.append(_check_event(system, storyline, event, ids, suffix))
    return results


def _check_event(system: System, storyline: Storyline, event: Event, ids: dict[str, str],
                 title_suffix: str) -> EventResult:
    """Compare what the system stores for the touched topic with the storyline: title, the current value of every
    field, and (when the event writes edges and the system reports them) the topic's related edges."""
    topic_id = ids[event.topic]
    expected = storyline.expected_after(event.id)[event.topic]
    stored = system.read_topic(topic_id)
    if stored is None:
        return EventResult(event.id, topic_id, False, "topic reads as deleted", bool(event.edges))
    differences = []
    title = stored.get("title") or ""
    if title.removesuffix(title_suffix) != expected.title:
        differences.append(f"title: expected {expected.title!r}, stored {title!r}")
    for name, value in expected.fields.items():
        got = current_value(stored["fields"].get(name))
        if got is NO_VALUE or got != value:
            differences.append(f"{name}: expected {value!r}, stored {'no value' if got is NO_VALUE else repr(got)}")
    compared = False
    if event.edges:
        edges = system.read_state()["edges"]
        if edges is not None:
            compared = True
            reported = {(e["to"], e["kind"]) for e in edges
                        if e["from"] == topic_id and e.get("edge_type", "related") == "related"}
            wanted = {(ids[to], kind) for to, kind in expected.edges}
            if reported != wanted:
                differences.append(f"edges: expected {sorted(wanted)}, stored {sorted(reported)}")
    return EventResult(event.id, topic_id, not differences, "; ".join(differences) or "stored state as expected",
                       bool(event.edges), compared)


def _saliences(system: System, ids: dict[str, str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for tid in ids.values():
        topic = system.read_topic(tid)
        out[tid] = None if topic is None else topic.get("salience")
    return out


def _increment(before: dict, after: dict, topic_id: str) -> float | None:
    """Salience gained over a question; a fall is decay on disuse (the reference GEM), not an increment, so it is 0."""
    b, a = before.get(topic_id), after.get(topic_id)
    return None if b is None or a is None else max(0.0, round(a - b, 6))


def ask(system: System, storyline: Storyline, ids: dict[str, str], top_k: int
        ) -> tuple[list[QuestionOutcome], Reinforcement | None]:
    outcomes: list[QuestionOutcome] = []
    before = _saliences(system, ids)
    for q in storyline.questions:
        response = system.query({"q": q.text, "top_k": top_k})
        after = _saliences(system, ids)
        outcomes.append(_triage(q, ids[q.topic], response, before, after))
        before = after
    return outcomes, _reinforcement(outcomes)


def _triage(q: Question, topic_id: str, response: dict, before: dict, after: dict) -> QuestionOutcome:
    returned_ids = [c["topic_id"] for c in response["candidates"]]
    returned = topic_id in returned_ids
    stored: Any = None
    if not returned:
        outcome = SEARCH_FAILURE
    else:
        value = current_value(field_in_response(response, topic_id, q.field))
        stored = "<no value>" if value is NO_VALUE else value
        outcome = CORRECT if value is not NO_VALUE and value == q.truth else MEMORY_FAILURE
    labelled = _increment(before, after, topic_id)
    every = [_increment(before, after, tid) for tid in after]
    return QuestionOutcome(
        question=q.id, ability=q.ability, text=q.text, truth=q.truth, topic=q.topic, topic_id=topic_id,
        outcome=outcome, returned=returned, rank=returned_ids.index(topic_id) + 1 if returned else None,
        returned_ids=returned_ids, stored=stored, increments_labelled=labelled,
        increments_all=None if labelled is None or None in every else round(sum(every), 6))


def _reinforcement(outcomes: list[QuestionOutcome]) -> Reinforcement | None:
    if not outcomes or any(o.increments_all is None for o in outcomes):
        return None  # the system keeps no salience (or lost a topic): not applicable
    labelled = round(sum(o.increments_labelled for o in outcomes), 6)
    everything = round(sum(o.increments_all for o in outcomes), 6)
    precision = labelled / everything if everything > EPS else None
    returns = sum(len(o.returned_ids) for o in outcomes)
    at_k = sum(o.returned for o in outcomes) / returns if returns else None
    return Reinforcement(
        labelled_increments=labelled, all_increments=everything, precision=precision,
        questions_bumped=sum(1 for o in outcomes if o.increments_labelled > EPS), questions=len(outcomes),
        precision_at_k=at_k,
        matches_precision_at_k=None if precision is None or at_k is None else abs(precision - at_k) < EPS)
