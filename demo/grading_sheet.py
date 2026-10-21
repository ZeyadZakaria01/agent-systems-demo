"""Hand-grading sheet: one CSV row per recorded chat turn, for a person to grade in a spreadsheet.

`export FOLDER... --out sheet.csv` writes the sheet. It carries what the person needs to judge the turn (question,
message, reference time, what the turn is graded on, ground truth, what the turn stored, the answer) and never the
model grade, its note or grader, or a match hint, so none of them anchors the grade. `import sheet.csv` checks every
filled `hand_grade` against `demo.model_grade.GRADES` before writing anything, writes `hand_grade` {grade, note} into
the recordings (the recorder's JSON formatting, every other key kept) and prints the agreement with Sonnet's grade.
Row id: the recording's path relative to the repo, `#`, the turn index.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from demo.chat_recording import load_recording, recording_files
from demo.model_grade import GRADES
from demo.paths import REPO_ROOT

COLUMNS = ["id", "case", "question", "user_message", "reference_time", "graded_on", "ground_truth", "stored", "answer",
           "hand_grade", "hand_note"]


def _rel(path: Path, root: Path) -> str:
    path = Path(path).resolve()
    try:
        return path.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _stored(turn: dict) -> str:
    if "written" not in turn:
        return ""
    entries = [f"{e.get('title')} / {e.get('field')} = {e.get('value')} (valid_from {e.get('valid_from')})"
               for e in turn["written"]]
    return "; ".join(entries) or "none"


def _row(rec_id: str, case: str, turn: dict) -> dict:
    hand = turn.get("hand_grade") or {}
    return {"id": rec_id, "case": case, "question": turn["question"], "user_message": turn.get("text") or "",
            "reference_time": turn.get("reference_time") or "", "graded_on": turn.get("graded_on") or "the answer",
            "ground_truth": turn.get("ground_truth") or "", "stored": _stored(turn),
            "answer": " ".join(str(turn.get("answer") or "").split()),
            "hand_grade": hand.get("grade") or "", "hand_note": hand.get("note") or ""}


def export_sheet(folders: list[Path], out: Path, root: Path = REPO_ROOT) -> int:
    """Write the sheet for every recording directly under `folders`; return the row count."""
    rows = []
    for folder in folders:
        for path in recording_files(Path(folder)):
            rec = load_recording(path)
            rows += [_row(f"{_rel(path, root)}#{i}", rec["case"], t) for i, t in enumerate(rec["turns"])]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with Path(out).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _split_id(row_id: str) -> tuple[str, int]:
    path, _, index = row_id.rpartition("#")
    return path, int(index)


def import_sheet(sheet: Path, root: Path = REPO_ROOT) -> str:
    """Write the filled-in hand grades into the recordings; return the report. Nothing is written if any grade is
    not one of `GRADES`."""
    with Path(sheet).open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("hand_grade") or "").strip()]
    for r in rows:
        if r["hand_grade"].strip() not in GRADES:
            raise ValueError(f"row {r['id']}: hand_grade {r['hand_grade']!r} is not one of {list(GRADES)}")
    recordings: dict[str, dict] = {}
    graded = []
    for r in rows:
        rel, index = _split_id(r["id"])
        rec = recordings.setdefault(rel, load_recording(Path(root) / rel))
        turn = rec["turns"][index]
        grade, note = r["hand_grade"].strip(), (r.get("hand_note") or "").strip()
        turn["hand_grade"] = {"grade": grade, "note": note or None}
        graded.append((r["id"], rec["case"], turn, grade))
    for rel, rec in recordings.items():
        (Path(root) / rel).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return _report(graded)


def _report(graded: list[tuple[str, str, dict, str]]) -> str:
    lines = [f"{len(graded)} rows graded"]
    compared = [(i, c, t, g) for i, c, t, g in graded if (t.get("model_grade") or {}).get("grade")]
    by_case: dict[str, list[bool]] = {}
    by_turn: dict[tuple[str, str], list[bool]] = {}
    for _, case, turn, grade in compared:
        agree = grade == turn["model_grade"]["grade"]
        by_case.setdefault(case, []).append(agree)
        by_turn.setdefault((case, turn["question"]), []).append(agree)
    lines += ["", "Agreement with Sonnet, per case:"]
    lines += [f"  {c}: {sum(a)}/{len(a)}" for c, a in sorted(by_case.items())]
    lines += ["", "Agreement with Sonnet, per turn:"]
    lines += [f"  {c} {q}: {sum(a)}/{len(a)}" for (c, q), a in sorted(by_turn.items())]
    lines += ["", "Disagreements:"]
    miss = [(i, t, g) for i, _, t, g in compared if g != t["model_grade"]["grade"]]
    for rec_id, turn, grade in miss:
        m = turn["model_grade"]
        lines += [f"  {rec_id} ({turn['question']})", f"    you: {grade}; Sonnet: {m['grade']}", f"    Sonnet's note: {m.get('note')}"]
    if not miss:
        lines.append("  none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m demo.grading_sheet", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="write the CSV sheet for the recordings in FOLDERS")
    ex.add_argument("folders", nargs="+", type=Path)
    ex.add_argument("--out", type=Path, required=True)
    im = sub.add_parser("import", help="write the sheet's hand grades into the recordings and report agreement")
    im.add_argument("sheet", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "export":
        print(f"{export_sheet(args.folders, args.out)} rows -> {args.out}")
        return 0
    try:
        print(import_sheet(args.sheet))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
