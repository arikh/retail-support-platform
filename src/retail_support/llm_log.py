"""Writes one row per LLM call to the llm_calls table (sql/006_llm_calls.sql).

The row holds counts and names only, never prompt or answer text (ADR-0015).
The prompts of a call are stored in one jsonb column as name -> version.
Writes go to the application database (APP_DATABASE_URL), not through db.py,
whose connections are read-only on purpose.
"""

import os

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

# TODO(env): temporary — centralize at app entry point, strip from modules
load_dotenv()

INSERT_LLM_CALL = """
    INSERT INTO llm_calls (
        run_id, thread_id, node, model, prompts,
        input_tokens, output_tokens, reasoning_tokens, cached_tokens,
        latency_ms, cost_usd
    ) VALUES (
        %(run_id)s, %(thread_id)s, %(node)s, %(model)s, %(prompts)s,
        %(input_tokens)s, %(output_tokens)s, %(reasoning_tokens)s,
        %(cached_tokens)s, %(latency_ms)s, %(cost_usd)s
    )
"""


async def save_llm_call(row: dict) -> None:
    """Insert one row. One short connection per call: fine for a thin slice;
    a connection pool comes with the application entry point."""
    # psycopg does not send a plain dict to a jsonb column; Jsonb(...) does.
    values = {**row, "prompts": Jsonb(row["prompts"])}
    async with await psycopg.AsyncConnection.connect(
        os.environ["APP_DATABASE_URL"]
    ) as conn:
        await conn.execute(INSERT_LLM_CALL, values)
