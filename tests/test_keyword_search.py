"""Keyword search over the policy passages (Piece 2, step 2).

These tests need the local Postgres with sql/008 applied, and the embedding
model (the ingest uses it).
"""

from pathlib import Path

import pytest

from retail_support.policy_ingest import ingest_policies
from retail_support.policy_search import keyword_passages

POLICIES = Path(__file__).parents[1] / "data" / "policies"


@pytest.fixture
async def ingested():
    return await ingest_policies(POLICIES)


async def test_keyword_returns_rows_best_first(ingested):
    rows = await keyword_passages("What does PENDING mean?")

    assert rows
    assert set(rows[0]) == {"source", "heading", "content", "score"}
    scores = [row["score"] for row in rows]
    assert scores == sorted(scores, reverse=True)


async def test_keyword_respects_the_limit(ingested):
    rows = await keyword_passages("Why are materials missing?", limit=1)

    assert len(rows) == 1


async def test_keyword_finds_a_rule_by_its_exact_name(ingested):
    rows = await keyword_passages("What is CATEGORY_CHANNEL_RULE?")

    assert rows[0]["heading"] == "CATEGORY_CHANNEL_RULE"


async def test_keyword_does_not_need_every_word_to_match(ingested):
    # No passage has all of these words. With AND between the words this
    # question matched nothing; the query joins them with OR.
    rows = await keyword_passages(
        "Why would a material with a 2-month expiry be left out of my plan?"
    )

    assert rows[0]["heading"] == "EXPIRY_HORIZON_RULE"


async def test_keyword_ranks_the_rule_that_names_the_words_first(ingested):
    # Dense search put this rule third, behind two near ties (10 Oct run).
    rows = await keyword_passages("Who fixes a wrong market mapping?")

    assert rows[0]["heading"] == "MARKET_MAPPING_RULE"


async def test_keyword_returns_nothing_for_a_question_off_the_topic(ingested):
    # Unlike dense search, which always returns its nearest rows.
    assert await keyword_passages("What is the capital of France?") == []


async def test_keyword_returns_nothing_when_only_common_words_are_left(ingested):
    assert await keyword_passages("What is the?") == []
