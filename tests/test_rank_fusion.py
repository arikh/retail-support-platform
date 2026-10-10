"""Two ranked lists merged into one by reciprocal rank fusion (Piece 2, step 2).

No database and no model: lists in, one list out.

A passage gets 1 / (RRF_K + rank) from every list it is in, with rank 1 for
the first row, and the points are added. Only the position in a list counts,
never the list's own score: a distance and a word-match score cannot be
compared, but "first" and "third" can.
"""

import pytest

from retail_support.rank_fusion import RRF_K, fuse


def row(heading: str, source: str = "a.md") -> dict:
    return {"source": source, "heading": heading, "content": f"{heading}\ntext"}


def headings(rows: list[dict]) -> list[str]:
    return [r["heading"] for r in rows]


def test_the_constant_is_the_usual_one():
    assert RRF_K == 60


def test_points_are_added_across_the_two_lists():
    dense = [row("A"), row("B"), row("C")]
    keyword = [row("C"), row("B"), row("D")]

    fused = fuse(dense, keyword, limit=4)

    # C is third in one list and first in the other; B is second in both.
    assert headings(fused) == ["C", "B", "A", "D"]
    assert [r["score"] for r in fused] == pytest.approx(
        [1 / 63 + 1 / 61, 1 / 62 + 1 / 62, 1 / 61, 1 / 63]
    )


def test_a_passage_in_both_lists_beats_the_top_of_one_list():
    dense = [row("only dense"), row("in both")]
    keyword = [row("only keyword"), row("in both")]

    assert headings(fuse(dense, keyword, limit=1)) == ["in both"]


def test_the_limit_is_respected():
    dense = [row("A"), row("B"), row("C")]
    keyword = [row("C"), row("B"), row("D")]

    assert len(fuse(dense, keyword, limit=2)) == 2


def test_an_empty_keyword_list_keeps_the_dense_order():
    # Keyword search returns nothing when no word of the question matches.
    dense = [row("A"), row("B"), row("C")]

    assert headings(fuse(dense, [], limit=3)) == ["A", "B", "C"]


def test_two_empty_lists_give_an_empty_list():
    assert fuse([], [], limit=3) == []


def test_a_row_keeps_its_text_and_gets_the_fused_score():
    dense = [{**row("A"), "distance": 0.2}]
    keyword = [{**row("A"), "score": 0.9}]

    (fused,) = fuse(dense, keyword, limit=3)

    # The lists' own numbers (distance, word score) are not carried over.
    assert fused == {
        "source": "a.md",
        "heading": "A",
        "content": "A\ntext",
        "score": pytest.approx(2 / 61),
    }


def test_the_same_heading_in_two_files_is_two_passages():
    dense = [row("Overview", source="a.md")]
    keyword = [row("Overview", source="b.md")]

    fused = fuse(dense, keyword, limit=3)

    assert [(r["source"], r["heading"]) for r in fused] == [
        ("a.md", "Overview"),
        ("b.md", "Overview"),
    ]


def test_a_tie_is_broken_by_source_then_heading():
    # Same points: one is first in dense only, the other first in keyword only.
    dense = [row("Zebra")]
    keyword = [row("Apple")]

    assert headings(fuse(dense, keyword, limit=2)) == ["Apple", "Zebra"]


def test_the_two_lists_are_left_unchanged():
    dense = [row("A")]
    keyword = [row("A")]

    fuse(dense, keyword, limit=1)

    assert dense == [row("A")]
    assert keyword == [row("A")]
