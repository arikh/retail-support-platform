"""Dense search over the policy passages.

The question is turned into a vector, and Postgres returns the passages whose
vectors are nearest to it. "<=>" is pgvector's cosine distance: 0 means the
same direction, larger means further apart. Only the order is meaningful;
there is no distance below which a passage is "relevant".
"""

import asyncio

from retail_support.db import fetch_all
from retail_support.embedder import EMBEDDING_MODEL, embed_query, vector_literal
from retail_support.rank_fusion import fuse

DEFAULT_LIMIT = 3
CANDIDATES = 10
NOTHING_LOADED = "No policy passages are loaded."

NEAREST_PASSAGES = """
    SELECT source, heading, content, embedding <=> %s::vector AS distance
    FROM policy_passages
    WHERE embedding_model = %s
    ORDER BY distance
    LIMIT %s
"""

KEYWORD_PASSAGES = """
    SELECT source, heading, content, ts_rank(content_tsv, query) AS score
    FROM policy_passages,
         (SELECT replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery
                 AS query) AS q
    WHERE content_tsv @@ query
    ORDER BY score DESC, source, heading
    LIMIT %s
"""


async def search_passages(question: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """The `limit` passages nearest to the question, nearest first.

    Each row has source, heading, content and distance."""
    # The model runs on the CPU; a thread keeps the event loop free meanwhile.
    vector = await asyncio.to_thread(embed_query, question)
    return await fetch_all(
        NEAREST_PASSAGES, (vector_literal(vector), EMBEDDING_MODEL, limit)
    )

async def keyword_passages(question: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    return await fetch_all(
        KEYWORD_PASSAGES, (question, limit)
    )  

async def hybrid_passages(question: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    dense = await search_passages(question, CANDIDATES)
    keyword = await keyword_passages(question, CANDIDATES)
    return fuse(dense, keyword, limit)


async def search_policy(question: str) -> str:
    """
    Search the policy and FAQ texts of the pricing process and return the
    passages closest to the question, each with its source.
    Use this when the user asks what a term, a status or a pricing rule
    means, how a step of the process works, or who to contact.
    Pass the user's question in full.
    """
    rows = await search_passages(question)
    if not rows:
        return NOTHING_LOADED
    return "\n\n".join(
        f"[{number}] {row['source']} > {row['heading']}\n{row['content']}"
        for number, row in enumerate(rows, start=1)
    )
