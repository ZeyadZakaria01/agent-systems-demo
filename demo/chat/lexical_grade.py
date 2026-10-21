"""Offline "state masking" analysis: a lexical metric (token F1) beside Sonnet's and the reviewer's answer grades and the
stored-state verdict of every recorded chat turn. No LLM call, no server; it reads the recordings only.

Token F1 is the SQuAD metric: both strings are lowercased, punctuation is removed, the articles "a", "an" and
"the" are dropped, the rest is split on whitespace, and F1 is the harmonic mean of token precision and recall over the
multiset overlap (both empty: 1.0; one empty: 0.0). It rewards shared words and ignores meaning, so a negated answer
scores high and a paraphrase scores low (the [P2] "Negation Trap" and "Paraphrase Penalty").

State verdict, per take (every turn of a take carries it):
- bad merge: wrong when the merge lost deadline history (`state.loss.lost_entries` non-empty; F37, F39);
- two weeks: wrong unless a stored start-date candidate read from `valid_from` is within tolerance of the truth
  (`turns[0].stored_start_date`; F38-F40): C1' reads by `valid_from`, so a date only in the value text is not
  enough (F42).

F1 is computed against the turn's `ground_truth` and the `answer`. The two-weeks W1 turn is graded on the stored
entries, not on the answer, and its ground truth is a description, so its F1 is shown but kept out of the mean and out
of lists (b) and (c); it still counts for list (a).

    .venv/bin/python -m demo.chat.lexical_grade [folders...]   # default: runs/chat-series/*/* and runs/recordings
"""

from __future__ import annotations

import argparse
import re
import string
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from demo.chat.model_grade import GRADES
from demo.chat.recording import load_recording
from demo.chat.review_grade import _files, _rel
from demo.paths import RECORDINGS_ROOT, REPO_ROOT

HIGH_F1 = 0.5
_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = str.maketrans("", "", string.punctuation)


def normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation, drop articles, split on whitespace."""
    text = text.lower().translate(_PUNCT)
    return _ARTICLES.sub(" ", text).split()


def token_f1(answer: str, truth: str) -> float:
    a, t = normalise(answer), normalise(truth)
    if not a or not t:
        return float(a == t)
    common = sum((Counter(a) & Counter(t)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(a), common / len(t)
    return 2 * precision * recall / (precision + recall)


POOL = ("April 20", "March 15")


def pool_label(answer: str) -> str:
    """Closed-pool label: the pool value the answer names (case-insensitive, word-boundary match), "ambiguous" when it
    names both, "other" when it names none."""
    named = [v for v in POOL if re.search(rf"\b{re.escape(v)}\b", answer, flags=re.IGNORECASE)]
    return "ambiguous" if len(named) > 1 else named[0] if named else "other"


ILLUSTRATION = (
    "April 20",
    "20/04",
    "The deadline moved to April 20, no longer March 15",
    "March 15",
    "The deadline is March 15",
)


def illustration_table(gold: str = "April 20") -> str:
    lines = [
        '| Answer to "What is the deadline?" (gold: April 20) | token F1 | closed-pool label |',
        "|---|---|---|",
    ]
    lines += [f"| {a} | {token_f1(a, gold):.2f} | {pool_label(a)} |" for a in ILLUSTRATION]
    return "\n".join(lines)


def _state_wrong(rec: dict) -> bool:
    if rec["case"] == "bad-merge":
        return bool(rec["state"]["loss"]["lost_entries"])
    start = rec["turns"][0]["stored_start_date"]
    truth = date.fromisoformat(start["truth"])
    return not any(
        c["source"] == "valid_from" and abs((date.fromisoformat(c["date"]) - truth).days) <= start["tolerance_days"]
        for c in start["candidates"]
    )


def collect(targets: list[Path], root: Path = REPO_ROOT) -> list[dict]:
    """One row per recorded turn: id, series, case, question, F1, graded_on_answer, both grades, state verdict."""
    rows = []
    for path in _files(targets):
        rec = load_recording(path)
        series = Path(_rel(path, root)).parent.as_posix()
        wrong = _state_wrong(rec)
        for i, turn in enumerate(rec["turns"]):
            rows.append(
                {
                    "id": f"{_rel(path, root)}#{i}",
                    "series": series.removeprefix("runs/chat-series/"),
                    "case": rec["case"],
                    "question": turn["question"],
                    "f1": token_f1(turn["answer"], turn["ground_truth"]),
                    "on_answer": (turn.get("graded_on") or "the answer") == "the answer",
                    "sonnet": (turn.get("model_grade") or {}).get("grade"),
                    "reviewer": (turn.get("reviewer_grade") or {}).get("grade"),
                    "state_wrong": wrong,
                    "take": f"{_rel(path, root)}",
                }
            )
    return rows


def masking(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["sonnet"] == "correct" and r["state_wrong"]]


def negation_trap(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["on_answer"] and r["f1"] >= HIGH_F1 and r["sonnet"] == "incorrect"]


def paraphrase_penalty(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["on_answer"] and r["f1"] < HIGH_F1 and r["sonnet"] == "correct"]


def _counts(rows: list[dict], who: str) -> str:
    c = Counter(r[who] for r in rows)
    return " / ".join(str(c[g]) for g in GRADES)


def _summary_row(label: str, rows: list[dict]) -> str:
    scored = [r["f1"] for r in rows if r["on_answer"]]
    mean = f"{sum(scored) / len(scored):.2f}" if scored else "n/a"
    takes = {r["take"] for r in rows}
    wrong = len({r["take"] for r in rows if r["state_wrong"]})
    return (
        f"| {label} | {len(rows)} | {mean} | {_counts(rows, 'sonnet')} | {_counts(rows, 'reviewer')} "
        f"| {wrong} of {len(takes)} takes wrong |"
    )


def summary_table(rows: list[dict]) -> str:
    header = [
        f"| Group | turns | mean F1 (answer-graded turns) | Sonnet {'/'.join(GRADES)} | reviewer {'/'.join(GRADES)} | state |",
        "|---|---|---|---|---|---|",
    ]
    body = [
        _summary_row(f"case {case}", [r for r in rows if r["case"] == case])
        for case in sorted({r["case"] for r in rows})
    ]
    body += [
        _summary_row(f"{case}: {series}", [r for r in rows if r["series"] == series and r["case"] == case])
        for series, case in sorted({(r["series"], r["case"]) for r in rows})
    ]
    return "\n".join(header + body + [_summary_row("all", rows)])


def _id_list(title: str, rows: list[dict]) -> str:
    return "\n".join([f"{title}: {len(rows)}"] + [f"  {r['id']} ({r['question']}, F1 {r['f1']:.2f})" for r in rows])


def report(targets: list[Path], root: Path = REPO_ROOT) -> str:
    rows = collect(targets, root)
    return "\n\n".join(
        [
            f"Turns: {len(rows)}. Token F1 against the ground truth; state verdict per take.",
            summary_table(rows),
            _id_list("(a) State masking: Sonnet correct, stored state wrong", masking(rows)),
            _id_list(f"(b) F1 >= {HIGH_F1} but Sonnet incorrect (Negation Trap analogue)", negation_trap(rows)),
            _id_list(f"(c) F1 < {HIGH_F1} but Sonnet correct (Paraphrase Penalty analogue)", paraphrase_penalty(rows)),
            'Constructed, not recorded: answers to "What is the deadline?" on the Website Redesign\n'
            + illustration_table(),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m demo.chat.lexical_grade", description=__doc__.split("\n\n")[0])
    ap.add_argument("folders", nargs="*", type=Path)
    args = ap.parse_args(argv)
    targets = args.folders or [
        *sorted(p for p in (REPO_ROOT / "runs" / "chat-series").glob("*/*") if p.is_dir()),
        RECORDINGS_ROOT,
    ]
    print(report(targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
