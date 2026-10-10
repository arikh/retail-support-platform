"""How one case of the golden set is scored (Piece 3).

No database and no model: rows in, a verdict out.
"""

import pytest

from retail_support.eval_metrics import is_hit, rate, same_workers


def passage(heading: str, source: str = "a.md") -> dict:
    return {"source": source, "heading": heading}


def row(heading: str, source: str = "a.md") -> dict:
    # A search row has more keys than a passage name; only two are compared.
    return {"source": source, "heading": heading, "content": "...", "score": 0.5}


# --- is_hit: was an expected passage among the first k rows? ------------------


def test_a_hit_when_the_expected_passage_is_first():
    assert is_hit([row("A"), row("B")], [passage("A")], k=1) is True


def test_no_hit_at_one_when_the_expected_passage_is_second():
    rows = [row("B"), row("A"), row("C")]

    assert is_hit(rows, [passage("A")], k=1) is False
    assert is_hit(rows, [passage("A")], k=3) is True


def test_rows_after_the_first_k_do_not_count():
    rows = [row("B"), row("C"), row("D"), row("A")]

    assert is_hit(rows, [passage("A")], k=3) is False


def test_any_one_of_several_expected_passages_is_enough():
    assert is_hit([row("B"), row("C")], [passage("A"), passage("C")], k=3) is True


def test_the_same_heading_in_another_file_is_not_a_hit():
    rows = [row("A", source="b.md")]

    assert is_hit(rows, [passage("A", source="a.md")], k=1) is False


def test_no_rows_is_no_hit():
    # Keyword search returns nothing when no word matches.
    assert is_hit([], [passage("A")], k=3) is False


# --- rate: the share of cases that passed -------------------------------------


def test_rate_is_the_share_of_true():
    assert rate([True, False, True, True]) == pytest.approx(0.75)


def test_rate_of_all_false_is_zero():
    assert rate([False, False]) == 0.0


def test_rate_of_nothing_is_zero():
    assert rate([]) == 0.0


# --- same_workers: did the supervisor plan the expected workers? --------------


def test_the_order_of_the_workers_does_not_matter():
    assert same_workers(["support", "analysis"], ["analysis", "support"]) is True


def test_an_empty_plan_matches_an_empty_expectation():
    assert same_workers([], []) is True


def test_a_missing_worker_is_a_miss():
    assert same_workers(["support"], ["analysis", "support"]) is False


def test_an_extra_worker_is_a_miss():
    assert same_workers(["support", "analysis"], ["support"]) is False


def test_a_plan_where_none_was_expected_is_a_miss():
    assert same_workers(["support"], []) is False
