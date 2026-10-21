"""Blind review of each chat turn by an independent grader (an AI agent), stored beside Sonnet's `model_grade`.

`export FILE_OR_FOLDER... --out items.json` writes one item per turn: `{id, case, question, prompt}`, where `prompt` is
`demo.model_grade.grading_prompt(turn)`, so the reviewer sees what Sonnet sees and never a model grade, a reviewer
grade or a match hint. `apply graded.json --grader NAME` takes `[{id, grade, note}]`, checks every grade and id, and
only then writes `reviewer_grade` {grade, note, grader, graded_at} into the recordings (the recorder's JSON
formatting, every other key kept); an existing `reviewer_grade` needs `--force`. `agreement FILE_OR_FOLDER...` counts
both graders' grades and reports their agreement with Sonnet. Item id: the recording's path relative to the repo,
`#`, the turn index. A folder stands for the recordings directly under it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from demo.chat_recording import load_recording, recording_files
from demo.model_grade import GRADES, grading_prompt
from demo.paths import REPO_ROOT


def _rel(path: Path, root: Path) -> str:
    path = Path(path).resolve()
    try:
        return path.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _files(targets: list[Path]) -> list[Path]:
    files = []
    for target in targets:
        target = Path(target)
        files += [target] if target.is_file() else recording_files(target)
    return files


def _split_id(item_id: str) -> tuple[str, int]:
    path, sep, index = str(item_id).rpartition("#")
    if not sep or not index.isdigit():
        raise ValueError(f"id {item_id!r} is not '<path>#<turn index>'")
    return path, int(index)


def export_items(targets: list[Path], out: Path, root: Path = REPO_ROOT) -> int:
    """Write the review items for every recording in `targets`; return the item count."""
    items = []
    for path in _files(targets):
        rec = load_recording(path)
        items += [{"id": f"{_rel(path, root)}#{i}", "case": rec["case"], "question": turn["question"],
                   "prompt": grading_prompt(turn)} for i, turn in enumerate(rec["turns"])]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    return len(items)


def apply_grades(graded: Path, grader: str, root: Path = REPO_ROOT, force: bool = False) -> int:
    """Write the graded items' `reviewer_grade` into the recordings; return how many. Nothing is written if any id,
    grade or overwrite is bad."""
    items = json.loads(Path(graded).read_text())
    if not isinstance(items, list):
        raise ValueError("the graded file must be a JSON array of {id, grade, note}")
    if not grader.strip():
        raise ValueError("grader name is empty")
    recordings: dict[str, dict] = {}
    seen: set[str] = set()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for item in items:
        if not isinstance(item, dict) or "id" not in item:
            raise ValueError(f"item {item!r} has no id")
        item_id = item["id"]
        if item_id in seen:
            raise ValueError(f"id {item_id!r} appears twice")
        seen.add(item_id)
        if item.get("grade") not in GRADES:
            raise ValueError(f"{item_id}: grade {item.get('grade')!r} is not one of {list(GRADES)}")
        rel, index = _split_id(item_id)
        if rel not in recordings:
            path = Path(root) / rel
            if not path.is_file():
                raise ValueError(f"{item_id}: no recording at {rel}")
            recordings[rel] = load_recording(path)
        turns = recordings[rel]["turns"]
        if index >= len(turns):
            raise ValueError(f"{item_id}: the recording has {len(turns)} turns")
        if turns[index].get("reviewer_grade") and not force:
            raise ValueError(f"{item_id}: already has a reviewer_grade (use --force to overwrite)")
        turns[index]["reviewer_grade"] = {"grade": item["grade"], "note": str(item.get("note") or ""),
                                          "grader": grader, "graded_at": stamp}
    for rel, rec in recordings.items():
        (Path(root) / rel).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return len(items)


def agreement(targets: list[Path], root: Path = REPO_ROOT) -> str:
    """Grade counts for both graders and the reviewer's agreement with Sonnet, per case and per turn."""
    sonnet = {g: 0 for g in GRADES}
    reviewer = {g: 0 for g in GRADES}
    by_case: dict[str, list[bool]] = {}
    by_turn: dict[tuple[str, str], list[bool]] = {}
    misses = []
    for path in _files(targets):
        rec = load_recording(path)
        for i, turn in enumerate(rec["turns"]):
            model = (turn.get("model_grade") or {}).get("grade")
            review = turn.get("reviewer_grade") or {}
            if model in sonnet:
                sonnet[model] += 1
            if review.get("grade") in reviewer:
                reviewer[review["grade"]] += 1
            if model and review.get("grade"):
                agree = model == review["grade"]
                by_case.setdefault(rec["case"], []).append(agree)
                by_turn.setdefault((rec["case"], turn["question"]), []).append(agree)
                if not agree:
                    misses.append((f"{_rel(path, root)}#{i}", turn, turn["model_grade"], review))
    lines = ["Grades:"]
    lines += [f"  Sonnet: " + ", ".join(f"{g} {n}" for g, n in sonnet.items()),
              f"  reviewer: " + ", ".join(f"{g} {n}" for g, n in reviewer.items())]
    lines += ["", "Agreement with Sonnet, per case:"]
    lines += [f"  {c}: {sum(a)}/{len(a)}" for c, a in sorted(by_case.items())] or ["  none reviewed"]
    lines += ["", "Agreement with Sonnet, per turn:"]
    lines += [f"  {c} {q}: {sum(a)}/{len(a)}" for (c, q), a in sorted(by_turn.items())] or ["  none reviewed"]
    lines += ["", "Disagreements:"]
    for item_id, turn, model, review in misses:
        lines += [f"  {item_id} ({turn['question']})", f"    reviewer ({review.get('grader')}): {review['grade']}; "
                  f"Sonnet: {model['grade']}", f"    reviewer's note: {review.get('note')}",
                  f"    Sonnet's note: {model.get('note')}"]
    if not misses:
        lines.append("  none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m demo.review_grade", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="write the review items for the recordings in FILE_OR_FOLDER")
    ex.add_argument("targets", nargs="+", type=Path)
    ex.add_argument("--out", type=Path, required=True)
    ap_ = sub.add_parser("apply", help="write the reviewer's grades into the recordings")
    ap_.add_argument("graded", type=Path)
    ap_.add_argument("--grader", required=True)
    ap_.add_argument("--force", action="store_true", help="overwrite an existing reviewer_grade")
    ag = sub.add_parser("agreement", help="count both graders' grades and report agreement")
    ag.add_argument("targets", nargs="+", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "export":
            print(f"{export_items(args.targets, args.out)} items -> {args.out}")
        elif args.cmd == "apply":
            print(f"{apply_grades(args.graded, args.grader, force=args.force)} reviewer grades written")
        else:
            print(agreement(args.targets))
    except (ValueError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
