"""Tables for the storyline measurement: triage counts per system, a per-question outcome table, and reinforcement
precision (shown beside C6 clause 1, without a verdict). Reads `Verdict.measurements["storyline"]` written by
`demo/checks/triage.py`; `render_storyline` returns "" when no storyline ran, so the run output stays unchanged then.
"""

from __future__ import annotations

from demo.verdict import ERROR, Verdict

ROW = "Storyline"
NOT_APPLICABLE = "n/a"
PRECISION_NOTE = (
    "Reinforcement precision = salience increments to the labelled topic / all increments over the storyline "
    "questions. It carries no verdict. Because every returned topic is bumped, it equals Precision@k (micro-averaged "
    "over the questions: labelled topics returned / topics returned), at most 1/k per question with one labelled "
    "topic (1/8 at the default top_k of 8). n/a: the system keeps no salience.")


def _esc(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _by_system(verdicts: list[Verdict]) -> dict[str, Verdict]:
    out: dict[str, Verdict] = {}
    for v in verdicts:
        if v.row == ROW and v.system is not None and v.system not in out:
            out[v.system] = v
    return out


def _measured(v: Verdict) -> dict | None:
    return None if v.verdict == ERROR else v.measurements.get("storyline")


def _pct(x: float | None) -> str:
    return NOT_APPLICABLE if x is None else f"{x:.3f}"


def render_triage(verdicts: list[Verdict]) -> str:
    systems = _by_system(verdicts)
    lines = ["| System | top_k | Questions | Correct | Search failures | Memory failures | Events with unexpected stored state (titles, field values, edges) |",
             "|---|---|---|---|---|---|---|"]
    for sid, v in systems.items():
        m = _measured(v)
        if m is None:
            lines.append(f"| {_esc(sid)} | | error: {_esc((v.error or '').splitlines()[0] if v.error else '')} | | | | |")
            continue
        t, e = m["triage"], m["events"]
        edges = f"edges compared on {e['edges_compared']} of {e['with_edges']}" if e["edges_compared"] else "edges n/a"
        lines.append(f"| {_esc(sid)} | {m['top_k']} | {t['questions']} | {t['correct']} | {t['search_failures']} | "
                     f"{t['memory_failures']} | {e['total'] - e['matched']} of {e['total']} ({edges}) |")
    return "\n".join(lines)


def _cell(o: dict) -> str:
    if o["outcome"] == "correct":
        return f"correct (rank {o['rank']})"
    if o["outcome"] == "search failure":
        return f"search failure ({len(o['returned_ids'])} returned, topic not among them)"
    return f"memory failure (rank {o['rank']}, stored {o['stored']!r})"


def render_questions(verdicts: list[Verdict]) -> str:
    systems = {sid: m for sid, v in _by_system(verdicts).items() if (m := _measured(v)) is not None}
    if not systems:
        return ""
    first = next(iter(systems.values()))
    lines = ["| Q | Ability | Question | Ground truth | " + " | ".join(_esc(s) for s in systems) + " |",
             "|---|---|---|---|" + "---|" * len(systems)]
    for i, o in enumerate(first["questions"]):
        cells = " | ".join(_esc(_cell(m["questions"][i])) for m in systems.values())
        lines.append(f"| {o['question']} | {_esc(o['ability'])} | {_esc(o['text'])} | {_esc(o['truth'])} | {cells} |")
    return "\n".join(lines)


def render_reinforcement(verdicts: list[Verdict]) -> str:
    lines = ["| System | Increments to labelled topic | All increments | Reinforcement precision | "
             "Questions with labelled topic bumped | Precision@k from returned lists |",
             "|---|---|---|---|---|---|"]
    for sid, v in _by_system(verdicts).items():
        m = _measured(v)
        if m is None:
            continue
        r = m["reinforcement"]
        if r is None:
            lines.append(f"| {_esc(sid)} | {NOT_APPLICABLE} | {NOT_APPLICABLE} | {NOT_APPLICABLE} | "
                         f"{NOT_APPLICABLE} | {NOT_APPLICABLE} |")
            continue
        equal = {True: "equal", False: "DIFFERENT"}.get(r["matches_precision_at_k"], "")
        lines.append(f"| {_esc(sid)} | {r['labelled_increments']:g} | {r['all_increments']:g} | {_pct(r['precision'])} | "
                     f"{r['questions_bumped']} of {r['questions']} | {_pct(r['precision_at_k'])} ({equal}) |")
    return "\n".join(lines)


def render_storyline(verdicts: list[Verdict]) -> str:
    """The tables with headings, or "" when no storyline ran. Sections with nothing to show (every run errored) are
    left out rather than printed as an empty heading."""
    if not _by_system(verdicts):
        return ""
    sections = [("Storyline: search failures vs memory failures", render_triage(verdicts)),
                ("Storyline questions, per system", render_questions(verdicts)),
                ("Reinforcement precision (beside C6 clause 1; no verdict)", render_reinforcement(verdicts))]
    out = [f"### {title}\n\n{body}" for title, body in sections if not _empty_table(body)]
    if any(t.startswith("### Reinforcement") for t in out):
        out[-1] += "\n\n" + PRECISION_NOTE
    return "\n\n".join(out)


def _empty_table(body: str) -> bool:
    """A table with only its header and separator rows (or nothing)."""
    return len([line for line in body.splitlines() if line.startswith("|")]) <= 2
