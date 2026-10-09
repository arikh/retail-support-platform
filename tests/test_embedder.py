"""Text to vectors, with the real model on this machine (Piece 2).

The model is downloaded once (about 67 MB) and then read from the local cache.
"""

import math

from retail_support.embedder import (
    EMBEDDING_DIMENSIONS,
    embed_passages,
    embed_query,
    vector_literal,
)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.hypot(*a) * math.hypot(*b))


def test_vector_literal_is_the_form_pgvector_reads():
    assert vector_literal([0.5, -1.0, 2.0]) == "[0.5,-1.0,2.0]"


def test_a_question_vector_has_the_size_the_table_expects():
    vector = embed_query("What does PENDING mean?")

    assert len(vector) == EMBEDDING_DIMENSIONS
    assert all(isinstance(number, float) for number in vector)


def test_one_vector_for_each_passage():
    vectors = embed_passages(["first text", "second text", "third text"])

    assert [len(vector) for vector in vectors] == [EMBEDDING_DIMENSIONS] * 3


def test_a_question_is_nearer_to_its_answer_than_to_another_passage():
    question = embed_query("What does PENDING downstream status mean?")
    answer, other = embed_passages(
        [
            "PENDING means the price was generated but not yet sent to the"
            " client system.",
            "Materials marked as inactive are excluded from price generation.",
        ]
    )

    assert cosine(question, answer) > cosine(question, other)
