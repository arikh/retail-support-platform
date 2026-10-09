"""LangChain callback: one llm_calls row per model call."""

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from retail_support.llm_log import save_llm_call
from retail_support.llm_prices import cost_usd

logger = logging.getLogger(__name__)


class LLMCallLogger(AsyncCallbackHandler):
    def __init__(self) -> None:
        # run_id -> (start time, metadata)
        self._started: dict[UUID, tuple[float, dict[str, Any]]] = {}

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._started[run_id] = (time.perf_counter(), metadata or {})

    async def on_llm_end(
        self, response: LLMResult, *, run_id: UUID, **kwargs: Any
    ) -> None:
        try:
            popped = self._started.pop(run_id, None)
            if popped is None:
                return

            started_at, metadata = popped
            latency_ms = int((time.perf_counter() - started_at) * 1000)

            message = response.generations[0][0].message
            usage = message.usage_metadata
            model = message.response_metadata["model_name"]
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            reasoning = usage.get("output_token_details", {}).get("reasoning", 0)
            cached = usage.get("input_token_details", {}).get("cache_read", 0)

            await save_llm_call(
                {
                    "run_id": run_id,
                    "thread_id": metadata.get("thread_id"),
                    "node": metadata.get("node"),
                    "model": model,
                    "prompts": metadata.get("prompts"),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "reasoning_tokens": reasoning,
                    "cached_tokens": cached,
                    "latency_ms": latency_ms,
                    "cost_usd": cost_usd(
                        model, input_tokens, output_tokens, cached_tokens=cached
                    ),
                }
            )
        except Exception:
            logger.exception("could not log LLM call %s", run_id)

    async def on_llm_error(
        self, error: BaseException, *, run_id: UUID, **kwargs: Any
    ) -> None:
        self._started.pop(run_id, None)