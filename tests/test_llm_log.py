"""Price table and the per-call log writer (Piece 4, step 2)."""

import os
import uuid
from decimal import Decimal

import psycopg
import pytest

from retail_support.llm_log import save_llm_call
from retail_support.llm_prices import cost_usd

MODEL = "openai/gpt-oss-120b"


def test_cost_of_the_measured_probe_call():
    # The 9 Oct probe: 76 input tokens, 62 output tokens.
    assert cost_usd(MODEL, 76, 62) == Decimal("0.0000486")


def test_cached_input_is_billed_at_the_cached_price():
    assert cost_usd(MODEL, 1000, 0, cached_tokens=1000) == Decimal("0.000075")


def test_unknown_model_raises_and_names_it():
    with pytest.raises(ValueError, match="'no-such-model'"):
        cost_usd("no-such-model", 1, 1)


@pytest.fixture
def run_id():
    value = uuid.uuid4()
    yield value
    with psycopg.connect(os.environ["APP_DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM llm_calls WHERE run_id = %s", (value,))


def a_call(run_id, prompts):
    return {
        "run_id": run_id,
        "thread_id": None,
        "node": "support",
        "model": MODEL,
        "prompts": prompts,
        "input_tokens": 76,
        "output_tokens": 62,
        "reasoning_tokens": 52,
        "cached_tokens": 0,
        "latency_ms": 430,
        "cost_usd": cost_usd(MODEL, 76, 62),
    }


async def test_save_llm_call_writes_one_row(run_id):
    prompts = {"format_findings": "v1", "support_status_guide": "v2"}

    await save_llm_call(a_call(run_id, prompts))

    with psycopg.connect(os.environ["APP_DATABASE_URL"]) as conn:
        row = conn.execute(
            "SELECT node, prompts, reasoning_tokens, cost_usd"
            " FROM llm_calls WHERE run_id = %s",
            (run_id,),
        ).fetchone()

    assert row == ("support", prompts, 52, Decimal("0.00004860"))


async def test_a_call_can_be_found_by_one_prompt_and_its_version(run_id):
    await save_llm_call(
        a_call(run_id, {"format_findings": "v1", "support_status_guide": "v2"})
    )

    def found(prompt: str) -> bool:
        with psycopg.connect(os.environ["APP_DATABASE_URL"]) as conn:
            return (
                conn.execute(
                    "SELECT 1 FROM llm_calls"
                    " WHERE run_id = %s AND prompts @> %s::jsonb",
                    (run_id, prompt),
                ).fetchone()
                is not None
            )

    assert found('{"support_status_guide": "v2"}')
    assert not found('{"support_status_guide": "v1"}')


@pytest.mark.parametrize("prompts", [{}, None])
async def test_a_call_with_no_prompt_is_refused(run_id, prompts):
    # The table's CHECK: a row must name at least one prompt.
    with pytest.raises(psycopg.errors.CheckViolation):
        await save_llm_call(a_call(run_id, prompts))
