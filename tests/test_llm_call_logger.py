"""LLMCallLogger: one llm_calls row per model call (Piece 4, step 2).

No model and no database here. A fake clock replaces time.perf_counter and a
fake save_llm_call collects the rows, so every number below is exact.
"""

import logging
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from retail_support import llm_call_logger
from retail_support.llm_call_logger import LLMCallLogger
from retail_support.prompt_store import Prompt, call_metadata

MODEL = "openai/gpt-oss-120b"
METADATA = {
    "thread_id": "thread-1",
    "node": "support",
    "prompts": {"support_system": "v1"},
}


def reply(model=MODEL, input_tokens=76, output_tokens=62, **details):
    """A model reply shaped like the one ChatGroq returns."""
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        **details,
    }
    message = AIMessage(
        content="hi",
        usage_metadata=usage,
        response_metadata={"model_name": model},
    )
    return LLMResult(generations=[[ChatGeneration(message=message)]])


@pytest.fixture
def saved(monkeypatch):
    """The rows the logger tried to save, instead of a real insert."""
    rows = []

    async def fake_save(row):
        rows.append(row)

    monkeypatch.setattr(llm_call_logger, "save_llm_call", fake_save)
    return rows


@pytest.fixture
def clock(monkeypatch):
    """A clock the test moves by hand: clock.now = 100.5."""
    fake = SimpleNamespace(now=100.0)
    fake.perf_counter = lambda: fake.now
    monkeypatch.setattr(llm_call_logger, "time", fake)
    return fake


async def start(handler, run_id, metadata=METADATA):
    await handler.on_chat_model_start({}, [[]], run_id=run_id, metadata=metadata)


async def test_one_call_writes_one_row_with_every_field(saved, clock):
    handler, run_id = LLMCallLogger(), uuid.uuid4()

    await start(handler, run_id)
    clock.now = 100.5
    await handler.on_llm_end(
        reply(output_token_details={"reasoning": 52}), run_id=run_id
    )

    assert saved == [
        {
            "run_id": run_id,
            "thread_id": "thread-1",
            "node": "support",
            "model": MODEL,
            "prompts": {"support_system": "v1"},
            "input_tokens": 76,
            "output_tokens": 62,
            "reasoning_tokens": 52,
            "cached_tokens": 0,
            "latency_ms": 500,
            "cost_usd": Decimal("0.0000486"),
        }
    ]


async def test_cached_input_is_read_and_billed_at_the_cached_price(saved, clock):
    handler, run_id = LLMCallLogger(), uuid.uuid4()

    await start(handler, run_id)
    await handler.on_llm_end(
        reply(
            input_tokens=1000,
            output_tokens=0,
            input_token_details={"cache_read": 1000},
        ),
        run_id=run_id,
    )

    assert saved[0]["cached_tokens"] == 1000
    assert saved[0]["cost_usd"] == Decimal("0.000075")


async def test_two_calls_at_the_same_time_keep_their_own_start(saved, clock):
    # The support and analysis workers run together, so calls overlap.
    handler, first, second = LLMCallLogger(), uuid.uuid4(), uuid.uuid4()

    await start(handler, first)
    clock.now = 100.25
    await start(handler, second, {**METADATA, "node": "analysis"})
    clock.now = 101.0
    await handler.on_llm_end(reply(), run_id=first)
    await handler.on_llm_end(reply(), run_id=second)

    assert [(row["node"], row["latency_ms"]) for row in saved] == [
        ("support", 1000),
        ("analysis", 750),
    ]


async def test_missing_metadata_gives_none_not_a_crash(saved, clock):
    handler, run_id = LLMCallLogger(), uuid.uuid4()

    await start(handler, run_id, metadata=None)
    await handler.on_llm_end(reply(), run_id=run_id)

    row = saved[0]
    assert (row["node"], row["prompts"], row["thread_id"]) == (None, None, None)


async def test_a_failed_save_is_logged_and_does_not_raise(monkeypatch, clock, caplog):
    async def broken_save(row):
        raise RuntimeError("database is down")

    monkeypatch.setattr(llm_call_logger, "save_llm_call", broken_save)
    handler, run_id = LLMCallLogger(), uuid.uuid4()

    await start(handler, run_id)
    with caplog.at_level(logging.ERROR):
        await handler.on_llm_end(reply(), run_id=run_id)

    assert f"could not log LLM call {run_id}" in caplog.text
    assert "database is down" in caplog.text


async def test_a_model_with_no_price_is_logged_and_does_not_raise(saved, clock, caplog):
    handler, run_id = LLMCallLogger(), uuid.uuid4()

    await start(handler, run_id)
    with caplog.at_level(logging.ERROR):
        await handler.on_llm_end(reply(model="no-such-model"), run_id=run_id)

    assert saved == []
    assert "no price for model: 'no-such-model'" in caplog.text


async def test_a_failed_model_call_leaves_nothing_behind(saved, clock):
    handler, run_id = LLMCallLogger(), uuid.uuid4()

    await start(handler, run_id)
    await handler.on_llm_error(RuntimeError("rate limit"), run_id=run_id)

    assert handler._started == {}
    await handler.on_llm_end(reply(), run_id=run_id)
    assert saved == []


async def test_an_end_without_a_start_writes_nothing(saved, clock):
    await LLMCallLogger().on_llm_end(reply(), run_id=uuid.uuid4())

    assert saved == []


async def test_the_logger_reads_the_keys_call_metadata_writes(saved, clock):
    # The call sites write the keys, the logger reads them: they must agree.
    handler, run_id = LLMCallLogger(), uuid.uuid4()
    prompt = Prompt(name="support_system", version="v2", text="...")

    await start(handler, run_id, call_metadata("support", prompt))
    await handler.on_llm_end(reply(), run_id=run_id)

    row = saved[0]
    assert (row["node"], row["prompts"]) == ("support", {"support_system": "v2"})
