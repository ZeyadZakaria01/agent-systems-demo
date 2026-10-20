"""Render the storyline as the human-reviewable draft `.scratch/gem-conformance-suite/storyline-draft.md` (ticket 11).

`python -m demo.storyline_draft` rewrites the file from `demo/storyline.py` (the data stays the single source; edit the
data, then regenerate). A test checks that every event and question id in the data appears in the committed draft.
"""

from __future__ import annotations

from collections import Counter

from demo.paths import REPO_ROOT
from demo.storyline import ABILITIES, DEPARTURES_FROM_PAPER, KEPT_FROM_PAPER, WEBSITE_REDESIGN, Event, Storyline

DRAFT_PATH = REPO_ROOT / ".scratch" / "gem-conformance-suite" / "storyline-draft.md"


def _esc(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _writes(event: Event) -> str:
    out = []
    for w in event.writes:
        extra = [f"why: {w.why_changed}"] if w.why_changed else []
        extra += [f"impact: {w.impact_expected}"] if w.impact_expected else []
        out.append(f"{w.name} = {w.value} (provenance {w.provenance}{''.join('; ' + x for x in extra)})")
    return "<br>".join(out) or "—"


def render(story: Storyline = WEBSITE_REDESIGN) -> str:
    titles = story.titles
    abilities = Counter(q.ability for q in story.questions)
    final = story.expected_after(story.events[-1].id)
    lines = [
        "# Storyline draft: the Website Redesign example (for review, ticket 11)",
        "",
        "Generated from `demo/storyline.py` by `python -m demo.storyline_draft`; edit the data there and regenerate. "
        "Recorded-run numbers (triage counts, reinforcement precision, unexpected-state counts) live in "
        "`docs/findings.md` under the storyline F-entry for the date of that run; they are not copied here.",
        "",
        f"**{len(story.events)} events** (each one `/v1/ingest` placement) and "
        f"**{len(story.questions)} questions** (each with a LongMemEval ability, a ground-truth answer and the topic "
        f"that holds the answer), on the paper's example.",
        "",
        "## From the paper, and where this draft departs",
        "",
        "Kept: " + " ".join(KEPT_FROM_PAPER),
        "",
        "Departures:",
        *[f"- {d}" for d in DEPARTURES_FROM_PAPER],
        "",
        "## How the storyline is used",
        "",
        "- Every system receives the same events, in order, on a fresh database. The `When` label on each event is "
        "for the reader only; no dates are sent.",
        "- After every event the run compares title, current field values, and (where the system reports them) the "
        "topic's outgoing related edges with the folded expected state; the baseline has no edges, so those are n/a.",
        "- Each question is asked as a plain read: default stages, `top_k` 8 on MemState, the baseline's own top 10. "
        "**Answered** = the read returned the answer topic and the ground-truth value is current in the labelled field. "
        "A wrong answer is a **search failure** if the answer topic was not returned, a **memory failure** if it was "
        "returned with a wrong stored value.",
        "- **Reinforcement precision** = salience increments to the answer topic ÷ all increments over the questions "
        "(equals Precision@k because every returned topic is bumped); no verdict, n/a on the baseline.",
        "",
        "## Topics",
        "",
        "| Key | Title | Kind | Created by | Summary (embedded with the title) |",
        "|---|---|---|---|---|",
    ]
    for e in story.events:
        if e.placement == "new_topic":
            lines.append(f"| `{e.topic}` | {_esc(e.title)} | {_esc(e.topic_kind)} | {e.id} | {_esc(e.summary)} |")
    lines += ["", "## Events", "",
              "| Event | The user says | Topic | Fields written | Edges |",
              "|---|---|---|---|---|"]
    for e in story.events:
        edges = ", ".join(f"→ {titles[x.to]} ({x.kind})" for x in e.edges) or "—"
        lines.append(f"| {e.id} | {_esc(e.said)} | {_esc(titles[e.topic])} | {_esc(_writes(e))} | {_esc(edges)} |")
    lines += ["", "## Expected state at the end (one row per topic)", "",
              "| Topic | Title | Current fields | Outgoing edges |",
              "|---|---|---|---|"]
    for key, state in final.items():
        fields = "; ".join(f"{k} = {v}" for k, v in state.fields.items())
        edges = ", ".join(f"→ {titles[t]} ({k})" for t, k in state.edges) or "—"
        lines.append(f"| `{key}` | {_esc(state.title)} | {_esc(fields)} | {_esc(edges)} |")
    lines += ["", "## Questions", "",
              "| Q | Ability | Question | Ground-truth answer | Answer topic | Field |", "|---|---|---|---|---|---|"]
    for q in story.questions:
        lines.append(f"| {q.id} | {q.ability} | {_esc(q.text)} | {_esc(q.truth)} | {_esc(titles[q.topic])} (`{q.topic}`) "
                     f"| {_esc(q.field)} |")
    lines += ["", "Abilities: " + ", ".join(f"{a} {abilities[a]}" for a in ABILITIES if abilities[a])
              + ". Abstention (answer: \"not stored\") is not labelled: it has no answer topic.",
              "",
              "## Points to decide in review",
              "",
              "- **Temporal reasoning** is labelled where the answer is a date that moved or was set (Q08, Q09, Q15); no "
              "date arithmetic is asked of the memory. Say if you want these relabelled or a real arithmetic "
              "question added (it would need a stored value that is the computed answer).",
              "- **Multi-session reasoning** has one question (Q06): the team list was built over two sessions "
              "(E02 kickoff, E21 standup after Erin joined and Alice was promoted). More would need answers that "
              "combine two topics, which one answer topic cannot label.",
              "- Several questions share ground-truth strings with other topics (April 20 is both the redesign "
              "deadline and the launch milestone); the labelled topic decides which one counts.",
              "- Dependent topics (milestones, Alice's role in the team list) are updated by explicit events here "
              "(E15–E17, E21), because every event is a perfect placement; whether MemState would propagate a deadline "
              "change by itself is C3's question, not this one.",
              "- All values are strings so a read is judged by exact match; changing a value's wording changes the "
              "ground truth in the same place.",
              f"- **The store is small.** The storyline creates {len(titles)} topics, so a `top_k` 8 read returns "
              f"most of them and the baseline's top 10 returns nearly all. Phase 2, Marketing Budget and Design Review "
              f"Meeting are look-alikes so a paraphrased question can rank the wrong topic; they do not guarantee a "
              f"search failure. Report whatever the recorded run gives.",
              ""]
    return "\n".join(lines)


def main() -> None:
    DRAFT_PATH.write_text(render())
    print(f"wrote {DRAFT_PATH}")


if __name__ == "__main__":
    main()
