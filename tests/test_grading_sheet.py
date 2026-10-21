"""The hand-grading sheet: export recordings to CSV, import the person's grades back."""

import csv
import json

import pytest

from demo import grading_sheet


def _turn(question, answer="  an   answer\n", *, grade=None, written=None, model=("correct", "fine"), **extra):
    turn = {"question": question, "text": f"msg {question}", "ground_truth": f"truth {question}", "answer": answer,
            "answer_contains_ground_truth": True, "state_violation": "lost", "route": {"intent": "x"},
            "hand_grade": {"grade": grade, "note": None} if grade is None else {"grade": grade, "note": "mine"},
            "model_grade": {"grade": model[0], "note": model[1], "grader": "sonnet-x", "graded_at": "t"}, **extra}
    if written is not None:
        turn["written"] = written
    return turn


@pytest.fixture
def root(tmp_path):
    folder = tmp_path / "series" / "a"
    folder.mkdir(parents=True)
    rec1 = {"schema": 1, "case": "two-weeks", "other": {"k": "é"},
            "turns": [_turn("W1", written=[{"title": "Job", "field": "start", "value": "Oct 7",
                                            "valid_from": "2026-10-07"}, {"title": "T", "field": "f", "value": "v",
                                                                           "valid_from": None}],
                            reference_time="2026-10-07", graded_on="the stored start date"),
                      _turn("W2", written=[], model=("incorrect", "wrong")), _turn("W3")]}
    rec2 = {"schema": 1, "case": "bad-merge", "turns": [_turn("Q02", model=("partially correct", "half"))]}
    (folder / "one.json").write_text(json.dumps(rec1, indent=2, ensure_ascii=False) + "\n")
    (folder / "two.json").write_text(json.dumps(rec2, indent=2, ensure_ascii=False) + "\n")
    return tmp_path


def _export(root):
    out = root / "sheet.csv"
    grading_sheet.export_sheet([root / "series" / "a"], out, root=root)
    with out.open(newline="", encoding="utf-8") as f:
        return out, list(csv.DictReader(f))


def _fill(out, values):
    with out.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["hand_grade"], row["hand_note"] = values.get(row["id"], ("", ""))
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_export_hides_model_grade_and_hints(root):
    out, rows = _export(root)
    assert list(rows[0]) == ["id", "case", "question", "user_message", "reference_time", "graded_on", "ground_truth",
                             "stored", "answer", "hand_grade", "hand_note"]
    text = out.read_text(encoding="utf-8")
    for hidden in ("sonnet-x", "fine", "wrong", "half", "answer_contains", "state_violation", "lost"):
        assert hidden not in text


def test_export_one_row_per_turn_in_order(root):
    _, rows = _export(root)
    assert [r["id"] for r in rows] == ["series/a/one.json#0", "series/a/one.json#1", "series/a/one.json#2",
                                      "series/a/two.json#0"]
    assert rows[0]["case"] == "two-weeks" and rows[3]["case"] == "bad-merge"
    assert rows[0]["question"] == "W1" and rows[0]["user_message"] == "msg W1"
    assert rows[0]["reference_time"] == "2026-10-07" and rows[0]["graded_on"] == "the stored start date"
    assert rows[0]["ground_truth"] == "truth W1"
    assert rows[0]["answer"] == "an answer"


def test_export_stored_entries(root):
    _, rows = _export(root)
    assert rows[0]["stored"] == "Job / start = Oct 7 (valid_from 2026-10-07); T / f = v (valid_from None)"
    assert rows[1]["stored"] == "none"
    assert rows[2]["stored"] == ""


def test_export_prefills_existing_hand_grade(root):
    path = root / "series" / "a" / "two.json"
    rec = json.loads(path.read_text())
    rec["turns"][0]["hand_grade"] = {"grade": "incorrect", "note": "mine"}
    path.write_text(json.dumps(rec))
    _, rows = _export(root)
    assert (rows[3]["hand_grade"], rows[3]["hand_note"]) == ("incorrect", "mine")
    assert (rows[0]["hand_grade"], rows[0]["hand_note"]) == ("", "")


def test_import_writes_and_reports_disagreements(root):
    out, _ = _export(root)
    _fill(out, {"series/a/one.json#0": ("correct", "ok"), "series/a/one.json#1": ("correct", "nah"),
                "series/a/two.json#0": ("partially correct", "")})
    report = grading_sheet.import_sheet(out, root=root)
    one = json.loads((root / "series/a/one.json").read_text())
    assert one["turns"][0]["hand_grade"] == {"grade": "correct", "note": "ok"}
    assert one["turns"][1]["hand_grade"] == {"grade": "correct", "note": "nah"}
    assert one["turns"][2]["hand_grade"] == {"grade": None, "note": None}
    assert one["other"] == {"k": "é"} and one["turns"][0]["model_grade"]["grader"] == "sonnet-x"
    raw = (root / "series/a/one.json").read_text()
    assert raw == json.dumps(one, indent=2, ensure_ascii=False) + "\n" and "é" in raw
    assert "3 rows graded" in report
    assert "two-weeks" in report and "1/2" in report and "bad-merge" in report and "1/1" in report
    assert "series/a/one.json#1" in report and "W2" in report and "wrong" in report
    assert "two-weeks W1: 1/1" in report and "two-weeks W2: 0/1" in report
    disagreements = report.split("Disagreements")[1]
    assert "series/a/one.json#1" in disagreements and "series/a/one.json#0" not in disagreements


def test_import_refuses_invalid_grade_and_writes_nothing(root):
    out, _ = _export(root)
    _fill(out, {"series/a/one.json#0": ("correct", ""), "series/a/two.json#0": ("mostly", "")})
    before = {p: p.read_text() for p in (root / "series/a").glob("*.json")}
    with pytest.raises(ValueError, match=r"series/a/two\.json#0.*'mostly'"):
        grading_sheet.import_sheet(out, root=root)
    assert {p: p.read_text() for p in before} == before


def test_import_skips_blank_rows(root):
    out, _ = _export(root)
    _fill(out, {})
    before = (root / "series/a/one.json").read_text()
    report = grading_sheet.import_sheet(out, root=root)
    assert "0 rows graded" in report
    assert (root / "series/a/one.json").read_text() == before
