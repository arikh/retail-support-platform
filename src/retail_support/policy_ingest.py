"""Copies the policy files into the policy_passages table.

Every run replaces the whole table in one transaction, so the table always
mirrors the files: a section removed from a file is removed from the table.
If anything fails, the old rows stay.

Writes go to the application database (APP_DATABASE_URL), not through db.py,
whose connections are read-only on purpose.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from retail_support.embedder import EMBEDDING_MODEL, embed_passages, vector_literal
from retail_support.policy_corpus import load_passages

# TODO(env): temporary — centralize at app entry point, strip from modules
load_dotenv()

INSERT_PASSAGE = """
    INSERT INTO policy_passages (
        source, heading, content, embedding_model, embedding
    ) VALUES (
        %(source)s, %(heading)s, %(content)s, %(embedding_model)s,
        %(embedding)s::vector
    )
"""


async def ingest_policies(directory: Path) -> int:
    """Replace the table with the passages of the files. Returns the count."""
    passages = load_passages(directory)
    if not passages:
        raise ValueError(f"no passages found in {directory}")

    vectors = embed_passages([passage.content for passage in passages])
    rows = [
        {
            "source": passage.source,
            "heading": passage.heading,
            "content": passage.content,
            "embedding_model": EMBEDDING_MODEL,
            "embedding": vector_literal(vector),
        }
        for passage, vector in zip(passages, vectors, strict=True)
    ]

    async with await psycopg.AsyncConnection.connect(
        os.environ["APP_DATABASE_URL"]
    ) as conn:
        await conn.execute("DELETE FROM policy_passages")
        async with conn.cursor() as cur:
            await cur.executemany(INSERT_PASSAGE, rows)
    return len(rows)
