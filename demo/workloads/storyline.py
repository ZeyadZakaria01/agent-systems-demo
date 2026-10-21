"""The storyline: one scenario on the paper's Website Redesign example, shared by the triage check, the chat runs
and the review draft (`.scratch/gem-conformance-suite/storyline-draft.md`, written by `demo/reporting/storyline_draft.py`).

An `Event` is one `/v1/ingest` placement (what a perfect acquirer would send for one thing the user said); topics are
named by a stable key (`redesign`, `alice`), because the server picks the topic ids. The state expected after an event
is derived, not typed twice: every system must end up with the written value current in its field, so
`Storyline.expected_after(event_id)` folds the writes up to that event. A `Question` is labelled with a LongMemEval
ability, the topic (and field) that holds the answer and the ground-truth value, which must be the field's current
value at the end of the storyline (checked on construction, so a typo cannot hide behind the fold).

Scope notes for the reviewer: all values are strings and every ground truth is one stored current value, so a question
is answered or not without a judge (spec: "answered when the read returns the labelled topic with the ground-truth
value current"). Abstention is not labelled: it has no answer topic. Temporal reasoning here means the answer is a
date or time that moved or was resolved; no arithmetic is asked of the memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# What the storyline keeps from the paper's example (Figures 1 and 3) and where it departs; the draft prints both.
KEPT_FROM_PAPER = (
    "Deadline March 15 → April 20 after a vendor delay; Team `[Alice (Frontend), Bob (Backend)]`; Status ending at "
    '`Complete` ("Project completed"); Alice split out of Website Redesign with an extension edge; a new project idea '
    "with an association edge; a lunch-preferences note as noise.",
)
DEPARTURES_FROM_PAPER = (
    "The paper's `Meeting` field (Figure 3(a), Feb 10, low salience) is its own topic, Weekly Sync Meeting, with a "
    "recurring time instead of a date.",
    '"Discussed lunch preferences" is a Lunch Preferences topic with invented content (cuisine, dietary note).',
    "Invented: the design vendor, milestones, budgets, brand guidelines, analytics, hiring, Phase 2 and Design Review "
    "topics, and the dates, names and amounts in them. Phase 2, Marketing Budget and Design Review Meeting are "
    "deliberate look-alikes of Website Redesign, Redesign Budget and Weekly Sync Meeting.",
    'Events are only `/v1` placements: no re-explained duplicate (the paper\'s "stored twice" at Week 1), because a '
    "same-title topic would be merged and C2 tests that.",
)

ROW = "Storyline"  # the id of the check's row, shared by the check and its tables

# Two of LongMemEval's five abilities (docs/papers/2512.12818.md:539-546): every storyline answer is one stored value,
# the latest (knowledge update) or the only one written (information extraction). Temporal reasoning and multi-session
# reasoning are not asked: time validity is tested by the time probes and the "two weeks ago" chat run, and
# multi-session reasoning is not measured. Abstention has no answer topic, so triage cannot sort it; it is not measured.
INFORMATION_EXTRACTION = "information extraction"
KNOWLEDGE_UPDATE = "knowledge update"
ABILITIES = (INFORMATION_EXTRACTION, KNOWLEDGE_UPDATE)


@dataclass(frozen=True)
class Write:
    name: str
    value: Any
    provenance: str
    why_changed: str | None = None
    impact_expected: str | None = None

    def payload(self) -> dict:
        out = {"name": self.name, "value": self.value, "provenance": self.provenance}
        if self.why_changed is not None:
            out["why_changed"] = self.why_changed
        if self.impact_expected is not None:
            out["impact_expected"] = self.impact_expected
        return out


@dataclass(frozen=True)
class Edge:
    to: str  # topic key
    kind: str  # "extension" (a change here can entail a change there) or "association"


@dataclass(frozen=True)
class Event:
    id: str
    when: str  # label for the reader only ("Week 1"); never sent to a system
    said: str  # what the user said, in words
    placement: str  # new_topic | extend_topic | version_field
    topic: str  # key of the topic written
    writes: tuple[Write, ...] = ()
    title: str | None = None  # new_topic only
    summary: str | None = None
    topic_kind: str | None = None
    edges: tuple[Edge, ...] = ()

    def request(self, ids: dict[str, str]) -> dict:
        """The `/v1/ingest` body; `ids` maps topic keys to the ids the system returned for the topics created so far."""
        body: dict = {"placement": self.placement, "fields": [w.payload() for w in self.writes]}
        if self.placement == "new_topic":
            body.update(title=self.title, summary=self.summary, topic_kind=self.topic_kind)
        else:
            body["topic_id"] = ids[self.topic]
        if self.edges:
            body["edges"] = [{"to_topic_id": ids[e.to], "kind": e.kind} for e in self.edges]
        return body


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    ability: str
    topic: str  # key of the topic that holds the answer
    field: str
    truth: Any  # the ground-truth value: that field's current value at the end of the storyline


@dataclass(frozen=True)
class TopicState:
    """Expected stored state of one topic after an event: its title, current value per field, outgoing edges."""

    title: str
    fields: dict[str, Any]
    edges: tuple[tuple[str, str], ...]  # (target topic key, kind)


@dataclass(frozen=True)
class Storyline:
    events: tuple[Event, ...]
    questions: tuple[Question, ...]

    def __post_init__(self) -> None:
        created: dict[str, str] = {}
        seen_events: set[str] = set()
        for e in self.events:
            if e.id in seen_events:
                raise ValueError(f"duplicate event id {e.id}")
            seen_events.add(e.id)
            if e.placement == "new_topic":
                if e.topic in created or not e.title:
                    raise ValueError(f"{e.id}: new_topic needs a fresh key and a title")
                if e.title in created.values():
                    raise ValueError(f"{e.id}: title {e.title!r} is already used (same-title topics get merged)")
                created[e.topic] = e.title
            elif e.topic not in created:
                raise ValueError(f"{e.id}: writes topic {e.topic!r} before it is created")
            if e.placement == "version_field" and len(e.writes) != 1:
                raise ValueError(f"{e.id}: version_field carries exactly one write")
            for edge in e.edges:
                if edge.to not in created:
                    raise ValueError(f"{e.id}: edge to {edge.to!r}, which does not exist yet")
        final = self.expected_after(self.events[-1].id)
        seen_questions: set[str] = set()
        for q in self.questions:
            if q.id in seen_questions:
                raise ValueError(f"duplicate question id {q.id}")
            seen_questions.add(q.id)
            if q.ability not in ABILITIES:
                raise ValueError(f"{q.id}: unknown ability {q.ability!r}")
            held = final.get(q.topic, TopicState("", {}, ())).fields.get(q.field)
            if held != q.truth:
                raise ValueError(
                    f"{q.id}: ground truth {q.truth!r} is not the end-of-storyline value of "
                    f"{q.topic}.{q.field} ({held!r})"
                )

    @property
    def titles(self) -> dict[str, str]:
        return {e.topic: e.title or "" for e in self.events if e.placement == "new_topic"}

    def expected_after(self, event_id: str) -> dict[str, TopicState]:
        """Expected stored state of every topic after `event_id`: the last write to a field is its current value."""
        fields: dict[str, dict[str, Any]] = {}
        edges: dict[str, list[tuple[str, str]]] = {}
        titles: dict[str, str] = {}
        for e in self.events:
            if e.placement == "new_topic":
                titles[e.topic] = e.title or ""
                fields[e.topic], edges[e.topic] = {}, []
            for w in e.writes:
                fields[e.topic][w.name] = w.value
            for edge in e.edges:
                if (edge.to, edge.kind) not in edges[e.topic]:
                    edges[e.topic].append((edge.to, edge.kind))
            if e.id == event_id:
                break
        else:
            raise KeyError(event_id)
        return {k: TopicState(titles[k], dict(fields[k]), tuple(edges[k])) for k in fields}


def _w(name: str, value: Any, provenance: str, why: str | None = None, impact: str | None = None) -> Write:
    return Write(name, value, provenance, why, impact)


WEBSITE_REDESIGN = Storyline(
    events=(
        # Week 0: the project is set up (the paper's Figure 1 and 3: Deadline, Team, Status; Alice; a new project idea)
        Event(
            "E01",
            "Week 0",
            "Kickoff: the website redesign is due March 15 and is in planning.",
            "new_topic",
            "redesign",
            title="Website Redesign",
            topic_kind="project",
            summary="Project to redesign the company website: deadline, status and team.",
            writes=(_w("Deadline", "March 15", "kickoff-notes"), _w("Status", "Planning", "kickoff-notes")),
        ),
        Event(
            "E02",
            "Week 0",
            "The team is Alice on the frontend and Bob on the backend.",
            "extend_topic",
            "redesign",
            writes=(_w("Team", "Alice (Frontend), Bob (Backend)", "kickoff-notes"),),
        ),
        Event(
            "E03",
            "Week 0",
            "Lunch preferences: the team likes Thai food, and two people are vegetarian.",
            "new_topic",
            "lunch",
            title="Lunch Preferences",
            topic_kind="note",
            summary="What the team likes to eat when ordering lunch together.",
            writes=(_w("Favorite cuisine", "Thai", "chat"), _w("Dietary note", "Two vegetarians", "chat")),
        ),
        Event(
            "E04",
            "Week 0",
            "Carol floats an idea for a mobile app, unrelated to the redesign for now.",
            "new_topic",
            "newproj",
            title="New Project Idea: Mobile App",
            topic_kind="project",
            summary="Early brainstorm for a possible mobile app; nothing is planned yet.",
            writes=(_w("Status", "Brainstorming", "chat"), _w("Owner", "Carol", "chat")),
            edges=(Edge("redesign", "association"),),
        ),
        Event(
            "E05",
            "Week 0",
            "The weekly sync is on Tuesdays at 10:00 in Room 4B.",
            "new_topic",
            "meeting",
            title="Weekly Sync Meeting",
            topic_kind="meeting",
            summary="Recurring weekly team meeting: day, time and room.",
            writes=(
                _w("Day", "Tuesday", "calendar"),
                _w("Time", "10:00", "calendar"),
                _w("Location", "Room 4B", "calendar"),
            ),
        ),
        Event(
            "E06",
            "Week 0",
            "The redesign budget is $40,000, approved by Dana.",
            "new_topic",
            "budget",
            title="Redesign Budget",
            topic_kind="budget",
            summary="Money approved for the website redesign and who signs it off.",
            writes=(_w("Total", "$40,000", "finance-email"), _w("Approver", "Dana", "finance-email")),
            edges=(Edge("redesign", "association"),),
        ),
        Event(
            "E07",
            "Week 0",
            "The design vendor Pixel Forge, contact Priya, delivers the mockups by February 15.",
            "new_topic",
            "vendor",
            title="Design Vendor: Pixel Forge",
            topic_kind="vendor",
            summary="External agency producing the website mockups.",
            writes=(
                _w("Mockups due", "February 15", "vendor-email"),
                _w("Contact", "Priya", "vendor-email"),
                _w("Delivery status", "Pending", "vendor-email"),
            ),
        ),
        Event(
            "E08",
            "Week 0",
            "Milestones follow the deadline: content freeze March 1, user testing March 8, launch March 15.",
            "new_topic",
            "milestones",
            title="Redesign Milestones",
            topic_kind="schedule",
            summary="Dated milestones that depend on the Website Redesign deadline.",
            writes=(
                _w("Content freeze", "March 1", "pm-email"),
                _w("User testing start", "March 8", "pm-email"),
                _w("Launch", "March 15", "pm-email"),
            ),
            edges=(Edge("redesign", "extension"),),
        ),
        Event(
            "E09",
            "Week 0",
            "Brand guidelines: primary colour #1A73E8, logo version 3.",
            "new_topic",
            "brand",
            title="Brand Guidelines",
            topic_kind="guidelines",
            summary="Colours and logo files the website has to follow.",
            writes=(_w("Primary color", "#1A73E8", "design-wiki"), _w("Logo version", "v3", "design-wiki")),
        ),
        # Confusable neighbours: same words as the topics above, different facts
        Event(
            "E10",
            "Week 0",
            "A second phase is planned for later: Website Redesign Phase 2, due September 30.",
            "new_topic",
            "phase2",
            title="Website Redesign Phase 2",
            topic_kind="project",
            summary="Follow-up project after the Website Redesign: deadline, status and team.",
            writes=(
                _w("Deadline", "September 30", "pm-email"),
                _w("Status", "Not started", "pm-email"),
                _w("Team", "Alice (Frontend), Carol (Design)", "pm-email"),
            ),
            edges=(Edge("redesign", "association"),),
        ),
        Event(
            "E11",
            "Week 0",
            "Marketing has its own budget: $15,000, approved by Frank.",
            "new_topic",
            "marketing",
            title="Marketing Budget",
            topic_kind="budget",
            summary="Money approved for the website launch campaign and who signs it off.",
            writes=(_w("Total", "$15,000", "finance-email"), _w("Approver", "Frank", "finance-email")),
        ),
        Event(
            "E12",
            "Week 0",
            "Design reviews are on Thursdays at 14:00 in Room 2A.",
            "new_topic",
            "designreview",
            title="Design Review Meeting",
            topic_kind="meeting",
            summary="Recurring design review meeting: day, time and room.",
            writes=(
                _w("Day", "Thursday", "calendar"),
                _w("Time", "14:00", "calendar"),
                _w("Location", "Room 2A", "calendar"),
            ),
        ),
        # Week 1: the vendor is late, the deadline and its dependents move (the paper's March 15 -> April 20)
        Event(
            "E13",
            "Week 1",
            "The vendor is late: mockups now due March 22.",
            "version_field",
            "vendor",
            writes=(_w("Mockups due", "March 22", "vendor-email", "vendor delay"),),
        ),
        Event(
            "E14",
            "Week 1",
            "Because of the vendor delay the redesign deadline moves to April 20.",
            "version_field",
            "redesign",
            writes=(_w("Deadline", "April 20", "pm-email", "vendor delay", "milestones slip about five weeks"),),
        ),
        Event(
            "E15",
            "Week 1",
            "The launch milestone moves to April 20 with the deadline.",
            "version_field",
            "milestones",
            writes=(_w("Launch", "April 20", "pm-email", "deadline moved"),),
        ),
        Event(
            "E16",
            "Week 1",
            "User testing now starts April 13.",
            "version_field",
            "milestones",
            writes=(_w("User testing start", "April 13", "pm-email", "deadline moved"),),
        ),
        Event(
            "E17",
            "Week 1",
            "Content freeze moves to April 6.",
            "version_field",
            "milestones",
            writes=(_w("Content freeze", "April 6", "pm-email", "deadline moved"),),
        ),
        Event(
            "E18",
            "Week 1",
            "The vendor charges a rush fee, so the budget grows to $46,500.",
            "version_field",
            "budget",
            writes=(_w("Total", "$46,500", "finance-email", "vendor rush fee"),),
        ),
        Event(
            "E19",
            "Week 1",
            "Alice comes up in every thread, so she gets her own topic: frontend developer, prototyping the homepage.",
            "new_topic",
            "alice",
            title="Alice",
            topic_kind="person",
            summary="Alice, frontend developer on the Website Redesign team.",
            writes=(_w("Role", "Frontend developer", "standup"), _w("Working on", "Homepage prototype", "standup")),
            edges=(Edge("redesign", "extension"),),
        ),
        Event(
            "E20",
            "Week 1",
            "Alice is promoted to frontend lead.",
            "version_field",
            "alice",
            writes=(_w("Role", "Frontend lead", "standup", "promoted after the homepage prototype"),),
        ),
        Event(
            "E21",
            "Week 1",
            "Erin joins as QA, and Alice is now the frontend lead on the team.",
            "version_field",
            "redesign",
            writes=(_w("Team", "Alice (Frontend lead), Bob (Backend), Erin (QA)", "standup", "Erin joined"),),
        ),
        Event(
            "E22",
            "Week 1",
            "The weekly sync moves to 11:30 because of a design review.",
            "version_field",
            "meeting",
            writes=(_w("Time", "11:30", "calendar", "clash with the design review"),),
        ),
        Event(
            "E23",
            "Week 1",
            "The redesign is now in progress.",
            "version_field",
            "redesign",
            writes=(_w("Status", "In progress", "standup"),),
        ),
        Event(
            "E24",
            "Week 1",
            "Website traffic: about 48,000 visitors a month, the pricing page is the top page.",
            "new_topic",
            "analytics",
            title="Website Analytics Report",
            topic_kind="report",
            summary="Monthly traffic numbers for the current website.",
            writes=(
                _w("Monthly visitors", "48,000", "analytics-export"),
                _w("Top page", "Pricing", "analytics-export"),
            ),
        ),
        Event(
            "E25",
            "Week 1",
            "Phase 2 slips to October 15 until phase 1 is done.",
            "version_field",
            "phase2",
            writes=(_w("Deadline", "October 15", "pm-email", "waiting for phase 1"),),
        ),
        # Week 1, the paper's last entry: "Project completed" (Status: Complete); then noise
        Event(
            "E26",
            "Week 1",
            "The vendor delivered the mockups.",
            "version_field",
            "vendor",
            writes=(_w("Delivery status", "Delivered", "vendor-email"),),
        ),
        Event(
            "E27",
            "Week 1",
            "Project completed.",
            "version_field",
            "redesign",
            writes=(_w("Status", "Complete", "standup"),),
        ),
        Event(
            "E28",
            "Week 2",
            "Hiring: three candidates are being interviewed for a backend engineer.",
            "new_topic",
            "hiring",
            title="Backend Engineer Hiring",
            topic_kind="hiring",
            summary="Open backend engineer position and the interview pipeline.",
            writes=(_w("Status", "Interviewing", "recruiter-email"), _w("Candidates", "3", "recruiter-email")),
        ),
        Event(
            "E29",
            "Week 2",
            "The team now wants Mexican for lunch.",
            "version_field",
            "lunch",
            writes=(_w("Favorite cuisine", "Mexican", "chat", "tired of Thai"),),
        ),
    ),
    questions=(
        Question(
            "Q01", "Who is our contact at the design vendor?", INFORMATION_EXTRACTION, "vendor", "Contact", "Priya"
        ),
        Question(
            "Q02", "What is the deadline of the Website Redesign?", KNOWLEDGE_UPDATE, "redesign", "Deadline", "April 20"
        ),
        Question(
            "Q03", "What is the total budget for the website redesign?", KNOWLEDGE_UPDATE, "budget", "Total", "$46,500"
        ),
        Question("Q04", "What time is the weekly sync meeting?", KNOWLEDGE_UPDATE, "meeting", "Time", "11:30"),
        Question(
            "Q05", "On which day is the weekly sync meeting held?", INFORMATION_EXTRACTION, "meeting", "Day", "Tuesday"
        ),
        Question(
            "Q06",
            "Who is on the website redesign team?",
            KNOWLEDGE_UPDATE,
            "redesign",
            "Team",
            "Alice (Frontend lead), Bob (Backend), Erin (QA)",
        ),
        Question(
            "Q07", "What is Alice's role on the website project?", KNOWLEDGE_UPDATE, "alice", "Role", "Frontend lead"
        ),
        Question(
            "Q08",
            "When does user testing start for the website redesign?",
            KNOWLEDGE_UPDATE,
            "milestones",
            "User testing start",
            "April 13",
        ),
        Question("Q09", "When is the website launch milestone?", KNOWLEDGE_UPDATE, "milestones", "Launch", "April 20"),
        Question("Q10", "Who approves the redesign budget?", INFORMATION_EXTRACTION, "budget", "Approver", "Dana"),
        Question(
            "Q11",
            "What is the current status of the website redesign project?",
            KNOWLEDGE_UPDATE,
            "redesign",
            "Status",
            "Complete",
        ),
        # Paraphrased: no title words, so the labelled topic competes with its confusable neighbours
        Question(
            "Q12", "How much money is set aside for the site revamp?", KNOWLEDGE_UPDATE, "budget", "Total", "$46,500"
        ),
        Question(
            "Q13",
            "Which room do the weekly team gatherings use?",
            INFORMATION_EXTRACTION,
            "meeting",
            "Location",
            "Room 4B",
        ),
        Question(
            "Q14",
            "What cuisine does the team want for lunch?",
            KNOWLEDGE_UPDATE,
            "lunch",
            "Favorite cuisine",
            "Mexican",
        ),
        Question(
            "Q15",
            "When is the design vendor's mockup delivery due?",
            KNOWLEDGE_UPDATE,
            "vendor",
            "Mockups due",
            "March 22",
        ),
    ),
)
