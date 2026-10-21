from demo.chat.lexical_grade import normalise, pool_label, token_f1


def test_normalise_drops_articles_punctuation_and_case():
    assert normalise("The deadline, is an April 20!") == ["deadline", "is", "april", "20"]


def test_identical_after_normalisation_scores_one():
    assert token_f1("The Deadline.", "deadline") == 1.0


def test_paraphrase_scores_low():
    assert token_f1("20/04", "April 20") == 0.0
    assert token_f1("The deadline is the twentieth of April", "April 20") < 0.5


def test_negated_answer_scores_high():
    assert token_f1("The deadline is not April 20", "April 20") >= 0.5


def test_pool_label_both_values_is_ambiguous():
    assert pool_label("The deadline moved to April 20, no longer March 15") == "ambiguous"
    assert pool_label("The deadline is march 15") == "March 15"
    assert pool_label("20/04") == "other"


def _two_weeks(*candidates):
    start = {"truth": "2026-09-23", "tolerance_days": 1, "candidates": list(candidates)}
    return {"case": "two-weeks", "turns": [{"stored_start_date": start}]}


def test_two_weeks_state_is_right_only_through_valid_from():
    from demo.chat.lexical_grade import _state_wrong

    value = {"source": "value", "date": "2026-09-23"}
    right = {"source": "valid_from", "date": "2026-09-23"}
    default = {"source": "valid_from", "date": "2026-10-07"}
    assert _state_wrong(_two_weeks(value, default))
    assert not _state_wrong(_two_weeks(value, right))
