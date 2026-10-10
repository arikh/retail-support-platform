"""Hybrid search over the policy passages: dense and keyword, merged (Piece 2, step 2).

These tests need the local Postgres with sql/008 applied, and the embedding
model.
"""

from pathlib import Path

import pytest

from retail_support.policy_ingest import ingest_policies
from retail_support.policy_search import hybrid_passages

POLICIES = Path(__file__).parents[1] / "data" / "policies"
PENDING = 'What does "PENDING" downstream status mean?'


@pytest.fixture
async def ingested():
    return await ingest_policies(POLICIES)


async def test_hybrid_returns_fused_rows(ingested):
    rows = await hybrid_passages("What does PENDING mean?")

    assert len(rows) == 3
    assert set(rows[0]) == {"source", "heading", "content", "score"}
    scores = [row["score"] for row in rows]
    assert scores == sorted(scores, reverse=True)


async def test_hybrid_respects_the_limit(ingested):
    assert len(await hybrid_passages("What does PENDING mean?", limit=1)) == 1


async def test_hybrid_puts_first_what_both_searches_put_first(ingested):
    rows = await hybrid_passages(PENDING)

    assert (rows[0]["source"], rows[0]["heading"]) == ("general_faq.md", PENDING)


async def test_hybrid_keeps_the_rule_the_keyword_search_found(ingested):
    rows = await hybrid_passages("Who fixes a wrong market mapping?")

    assert "MARKET_MAPPING_RULE" in [row["heading"] for row in rows]


async def test_hybrid_still_answers_when_no_word_matches(ingested):
    # Keyword search finds nothing; the dense rows come through alone.
    rows = await hybrid_passages("What is the capital of France?")

    assert len(rows) == 3
