"""Read-only access to the pricing-operations tables.

Tools call fetch_all() and nothing else. Every connection is set read-only,
so a tool cannot change pricing data even by mistake ("read, don't mutate").
"""

import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# TODO(env): temporary — centralize at app entry point, strip from modules
load_dotenv()

APP_DATABASE_URL = os.environ["APP_DATABASE_URL"]


async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Run one SELECT and return the rows as a list of dicts."""
    async with await psycopg.AsyncConnection.connect(
        APP_DATABASE_URL, row_factory=dict_row
    ) as conn:
        await conn.set_read_only(True)
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()
