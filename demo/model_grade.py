"""A model's grade of each chat turn, stored beside the blind reviewer's grade (`python -m demo.model_grade FILE...`).

The grader sees what a reviewer needs: the question, the ground truth, what the turn is graded on (the answer, or
for the two-weeks W1 turn the stored entries and the reference time) and the answer. It never sees the automatic match
hints, the date-match result, the reviewer's grade or the bad merge's state evidence. Its grade goes under `model_grade`
(`grade`, `note`, `grader` = the exact model id, `graded_at`); `reviewer_grade` is not touched (`demo/review_grade.py`). The default grader is
Sonnet through the Claude Code CLI, run in an empty folder with no tools and no MCP servers, so it reads nothing
but the prompt.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

GRADES = ("correct", "partially correct", "incorrect")

SYSTEM_PROMPT = f"""You grade one turn of a recorded chat with an AI memory assistant against its ground truth.
Grade only what the turn is graded on: either the assistant's answer, or the entries the turn stored.
- correct: it states the ground truth (wording may differ; a date within the stated tolerance counts).
- partially correct: some of the ground truth is right and some is missing or wrong, or it is right but hedged by a
  contradiction.
- incorrect: it does not state the ground truth (a refusal, a question back, nothing stored, or a wrong value).
Reply with JSON only: {{"grade": one of {list(GRADES)}, "note": "one sentence saying why"}}."""

Ask = Callable[[str, str], "tuple[str, str]"]


class GradeError(Exception):
    pass


def grading_prompt(turn: dict) -> str:
    graded_on = turn.get("graded_on") or "the answer"
    lines = [f"Graded on: {graded_on}", f"User message: {turn['text']}"]
    if turn.get("reference_time"):
        lines.append(f"Date of the user message (reference time): {turn['reference_time']}")
    lines.append(f"Ground truth: {turn['ground_truth']}")
    if "written" in turn:
        stored = [{k: e.get(k) for k in ("title", "field", "value", "valid_from")} for e in turn["written"]]
        lines.append(f"Entries the turn stored: {json.dumps(stored) if stored else 'none'}")
    lines.append(f"Assistant's answer: {' '.join(str(turn['answer']).split()) or '(empty)'}")
    return "\n".join(lines)


def parse_grade(reply: str) -> dict:
    match = re.search(r"\{.*\}", reply, flags=re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict) or data.get("grade") not in GRADES:
        raise GradeError(f"the grader did not return one of {GRADES}: {reply!r}")
    return {"grade": data["grade"], "note": str(data.get("note") or "")}


def claude(model: str = "sonnet") -> Ask:
    """The Claude Code CLI as a grader: an empty working folder, no tools, no MCP servers, our system prompt."""
    def ask(system: str, prompt: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as empty:
            out = subprocess.run(
                ["claude", "-p", "--model", model, "--tools", "", "--strict-mcp-config", "--no-session-persistence",
                 "--system-prompt", system, "--output-format", "json", prompt],
                cwd=empty, capture_output=True, text=True, timeout=300)
        try:
            data = json.loads(out.stdout)
        except json.JSONDecodeError:
            raise GradeError(f"claude CLI gave no JSON (exit {out.returncode}): {out.stderr.strip()[:300]}")
        if data.get("is_error"):
            raise GradeError(f"claude CLI error: {data.get('result')}")
        models = list(data.get("modelUsage") or {})
        return data["result"], models[0] if models else model
    return ask


def grade_recording(path: Path, ask: Ask, force: bool = False) -> list[dict]:
    rec = json.loads(Path(path).read_text())
    if not force and any("model_grade" in t for t in rec["turns"]):
        raise GradeError(f"{path} is already model-graded; pass force=True (--force) to grade it again")
    for turn in rec["turns"]:
        reply, grader = ask(SYSTEM_PROMPT, grading_prompt(turn))
        turn["model_grade"] = {**parse_grade(reply), "grader": grader,
                               "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    Path(path).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return [t["model_grade"] for t in rec["turns"]]


def tally(root: Path) -> dict[tuple[str, str], dict[str, int]]:
    """Model grades counted per (case, turn) over every recording under `root`; a turn with none counts as ungraded."""
    counts: dict[tuple[str, str], dict[str, int]] = {}
    for path in sorted(Path(root).rglob("*.json")):
        rec = json.loads(path.read_text())
        if "turns" not in rec:
            continue
        for turn in rec["turns"]:
            grade = (turn.get("model_grade") or {}).get("grade", "ungraded")
            key = (rec["case"], turn["question"])
            counts.setdefault(key, {})
            counts[key][grade] = counts[key].get(grade, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m demo.model_grade", description=__doc__.split("\n\n")[0])
    ap.add_argument("recordings", nargs="*", type=Path)
    ap.add_argument("--tally", type=Path, help="print the model grades counted per case and turn under a folder, then exit")
    ap.add_argument("--model", default="sonnet", help="Claude Code model alias or full name (default sonnet)")
    ap.add_argument("--force", action="store_true", help="grade again a recording that already has model grades")
    args = ap.parse_args(argv)
    if args.tally:
        for (case, question), grades in sorted(tally(args.tally).items()):
            n = sum(grades.values())
            print(f"{case} {question}: " + ", ".join(f"{g} {c}/{n}" for g, c in sorted(grades.items())))
        return 0
    if not args.recordings:
        ap.error("give recordings to grade, or --tally FOLDER")
    ask = claude(args.model)
    for path in args.recordings:
        try:
            grades = grade_recording(path, ask, force=args.force)
        except GradeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        for turn, g in zip(json.loads(path.read_text())["turns"], grades):
            print(f"{path.name} {turn['question']}: {g['grade']} ({g['grader']}): {g['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
