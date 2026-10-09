"""The policy passages in Postgres, and the dense search over them (Piece 2).

These tests need the local Postgres (with pgvector) and the embedding model.
Each one loads the real files first, so the table always ends as their copy.
"""

from pathlib import Path

import pytest

from retail_support import policy_search
from retail_support.db import fetch_all
from retail_support.policy_ingest import ingest_policies
from retail_support.policy_search import search_passages, search_policy

POLICIES = Path(__file__).parents[1] / "data" / "policies"
PENDING = 'What does "PENDING" downstream status mean?'


async def count_passages() -> int:
    rows = await fetch_all("SELECT count(*) AS passages FROM policy_passages")
    return rows[0]["passages"]


@pytest.fixture
async def ingested():
    return await ingest_policies(POLICIES)


# --- ingest: the table is a copy of the files --------------------------------


async def test_ingest_loads_every_passage(ingested):
    assert ingested == 16
    assert await count_passages() == 16


async def test_ingest_twice_keeps_one_copy(ingested):
    await ingest_policies(POLICIES)

    assert await count_passages() == 16


async def test_a_section_that_left_the_files_leaves_the_table(ingested, tmp_path):
    (tmp_path / "small.md").write_text("## Only one\nA single section.\n")
    try:
        await ingest_policies(tmp_path)

        rows = await fetch_all("SELECT source, heading FROM policy_passages")
        assert rows == [{"source": "small.md", "heading": "Only one"}]
    finally:
        await ingest_policies(POLICIES)


async def test_a_bad_file_changes_nothing(ingested, tmp_path):
    (tmp_path / "bad.md").write_text("## Empty\n\n## Next\nSome text.\n")

    with pytest.raises(ValueError, match="empty section"):
        await ingest_policies(tmp_path)

    assert await count_passages() == 16


async def test_an_empty_directory_is_refused(ingested, tmp_path):
    with pytest.raises(ValueError, match="no passages found"):
        await ingest_policies(tmp_path)

    assert await count_passages() == 16


# --- search: the nearest passages, nearest first ------------------------------


async def test_search_returns_rows_nearest_first(ingested):
    rows = await search_passages("What does PENDING mean?")

    assert len(rows) == 3
    assert set(rows[0]) == {"source", "heading", "content", "distance"}
    distances = [row["distance"] for row in rows]
    assert distances == sorted(distances)


async def test_search_respects_the_limit(ingested):
    assert len(await search_passages("What does PENDING mean?", limit=1)) == 1


async def test_a_heading_asked_word_for_word_finds_its_own_section(ingested):
    rows = await search_passages(PENDING)

    assert (rows[0]["source"], rows[0]["heading"]) == ("general_faq.md", PENDING)
    assert rows[0]["content"].startswith(PENDING)


async def test_a_question_in_other_words_finds_the_rule(ingested):
    rows = await search_passages(
        "Why would a material with a 2-month expiry be left out of my plan?"
    )

    assert "EXPIRY_HORIZON_RULE" in [row["heading"] for row in rows]


# --- search_policy: what the support worker's tool returns --------------------


async def test_the_tool_returns_numbered_passages_with_their_source(ingested):
    text = await search_policy(PENDING)

    assert text.startswith(f"[1] general_faq.md > {PENDING}\n{PENDING}\nPENDING means")
    assert "\n\n[2] " in text
    assert "\n\n[3] " in text
    assert "[4]" not in text


async def test_the_tool_says_so_when_nothing_is_loaded(monkeypatch):
    async def no_rows(question):
        return []

    monkeypatch.setattr(policy_search, "search_passages", no_rows)

    assert await search_policy("anything") == "No policy passages are loaded."
