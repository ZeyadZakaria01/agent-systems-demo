"""The blind review: export prompts without Sonnet's grade, apply the reviewer's grades, report agreement."""

import json

import pytest

from demo import review_grade
from demo.model_grade import grading_prompt


def _turn(question, model=("correct", "fine"), **extra):
    return {"question": question, "text": f"msg {question}", "ground_truth": f"truth {question}",
            "answer": "  an   answer\n", "answer_contains_ground_truth": True, "state_violation": "lost",
            "route": {"intent": "x"},
            "model_grade": {"grade": model[0], "note": model[1], "grader": "sonnet-x", "graded_at": "t"}, **extra}


def _dump(rec):
    return json.dumps(rec, indent=2, ensure_ascii=False) + "\n"


@pytest.fixture
def root(tmp_path):
    folder = tmp_path / "series" / "a"
    folder.mkdir(parents=True)
    rec1 = {"schema": 1, "case": "two-weeks", "other": {"k": "é"},
            "turns": [_turn("W1", written=[{"title": "Job", "field": "start", "value": "Oct 7", "valid_from": "x"}],
                            reference_time="2026-10-07", graded_on="the stored start date"),
                      _turn("W2", model=("incorrect", "wrong")), _turn("W3")]}
    rec2 = {"schema": 1, "case": "bad-merge", "turns": [_turn("Q02", model=("partially correct", "half"))]}
    (folder / "one.json").write_text(_dump(rec1))
    (folder / "two.json").write_text(_dump(rec2))
    return tmp_path


def _export(root):
    out = root / "items.json"
    count = review_grade.export_items([root / "series" / "a"], out, root=root)
    return out, count, json.loads(out.read_text())


def _graded(root, entries):
    path = root / "graded.json"
    path.write_text(json.dumps([{"id": i, "grade": g, "note": n} for i, g, n in entries]))
    return path


def _snapshot(root):
    return {p: p.read_text() for p in (root / "series" / "a").glob("*.json")}


def test_export_hides_model_grades_and_hints_and_ids_round_trip(root):
    out, count, items = _export(root)
    assert count == 4 and [i["id"] for i in items] == [
        "series/a/one.json#0", "series/a/one.json#1", "series/a/one.json#2", "series/a/two.json#0"]
    assert set(items[0]) == {"id", "case", "question", "prompt"}
    assert (items[0]["case"], items[0]["question"], items[3]["case"]) == ("two-weeks", "W1", "bad-merge")
    text = out.read_text(encoding="utf-8")
    for hidden in ("sonnet-x", "fine", "wrong", "half", "answer_contains", "state_violation", "lost"):
        assert hidden not in text
    for item in items:  # the id points back at the turn its prompt was made from
        rel, _, index = item["id"].rpartition("#")
        turn = json.loads((root / rel).read_text())["turns"][int(index)]
        assert item["prompt"] == grading_prompt(turn)


def test_export_takes_files_and_folders(root):
    out = root / "items.json"
    count = review_grade.export_items([root / "series/a/two.json", root / "series/a"], out, root=root)
    assert count == 5


def test_apply_writes_reviewer_grade_and_keeps_everything_else(root):
    graded = _graded(root, [("series/a/one.json#0", "correct", "ok"), ("series/a/two.json#0", "incorrect", "")])
    assert review_grade.apply_grades(graded, "rev-1", root=root) == 2
    raw = (root / "series/a/one.json").read_text()
    one = json.loads(raw)
    review = one["turns"][0]["reviewer_grade"]
    assert (review["grade"], review["note"], review["grader"]) == ("correct", "ok", "rev-1")
    assert review["graded_at"].endswith("+00:00") and len(review["graded_at"]) == 25
    assert "reviewer_grade" not in one["turns"][1]
    assert one["other"] == {"k": "é"} and one["turns"][0]["model_grade"]["grader"] == "sonnet-x"
    assert raw == _dump(one) and "é" in raw
    assert json.loads((root / "series/a/two.json").read_text())["turns"][0]["reviewer_grade"]["note"] == ""


@pytest.mark.parametrize("bad", [("series/a/one.json#1", "mostly", "x"), ("series/a/one.json#9", "correct", "x"),
                                 ("series/a/nope.json#0", "correct", "x"), ("series/a/one.json", "correct", "x"),
                                 ("series/a/one.json#0", "correct", "dup")])
def test_apply_rejects_a_bad_item_and_writes_nothing(root, bad):
    before = _snapshot(root)
    graded = _graded(root, [("series/a/two.json#0", "correct", "fine"), ("series/a/one.json#0", "correct", "ok"), bad])
    with pytest.raises(ValueError):
        review_grade.apply_grades(graded, "rev-1", root=root)
    assert _snapshot(root) == before


def test_apply_refuses_to_overwrite_without_force(root):
    review_grade.apply_grades(_graded(root, [("series/a/one.json#0", "correct", "first")]), "rev-1", root=root)
    before = _snapshot(root)
    again = _graded(root, [("series/a/one.json#1", "correct", "new"), ("series/a/one.json#0", "incorrect", "second")])
    with pytest.raises(ValueError, match="--force"):
        review_grade.apply_grades(again, "rev-2", root=root)
    assert _snapshot(root) == before
    review_grade.apply_grades(again, "rev-2", root=root, force=True)
    turns = json.loads((root / "series/a/one.json").read_text())["turns"]
    assert (turns[0]["reviewer_grade"]["grade"], turns[0]["reviewer_grade"]["grader"]) == ("incorrect", "rev-2")
    assert turns[1]["reviewer_grade"]["note"] == "new"


def test_main_reports_an_error_with_exit_code_1(root, capsys):
    graded = _graded(root, [("series/a/one.json#0", "mostly", "")])
    assert review_grade.main(["apply", str(graded), "--grader", "rev-1"]) == 1
    assert "mostly" in capsys.readouterr().err


def test_agreement_counts_both_graders_and_lists_disagreements(root):
    review_grade.apply_grades(_graded(root, [
        ("series/a/one.json#0", "correct", "ok"), ("series/a/one.json#1", "correct", "nah"),
        ("series/a/two.json#0", "partially correct", "same")]), "rev-1", root=root)
    report = review_grade.agreement([root / "series" / "a"], root=root)
    assert "Sonnet: correct 2, partially correct 1, incorrect 1" in report
    assert "reviewer: correct 2, partially correct 1, incorrect 0" in report
    assert "two-weeks: 1/2" in report and "bad-merge: 1/1" in report
    assert "two-weeks W1: 1/1" in report and "two-weeks W2: 0/1" in report
    disagreements = report.split("Disagreements:")[1]
    assert "series/a/one.json#1" in disagreements and "series/a/one.json#0" not in disagreements
    assert "reviewer (rev-1): correct; Sonnet: incorrect" in disagreements
    assert "reviewer's note: nah" in disagreements and "Sonnet's note: wrong" in disagreements


def test_agreement_before_any_review_counts_zero(root):
    report = review_grade.agreement([root / "series" / "a"], root=root)
    assert "reviewer: correct 0, partially correct 0, incorrect 0" in report
    assert "none reviewed" in report and report.endswith("  none")
