"""Ask the platform one question, with the per-call log attached.

    uv run python scripts/ask.py "What is the status of plan SUMMER_LATAM_V2?"
    uv run python scripts/ask.py "your question" my-thread-id

This calls the real model. Every model call writes one row to llm_calls under
the thread id (a new one for each run unless you give one).
"""

import asyncio
import sys
import uuid

from langchain_core.messages import HumanMessage

from retail_support.graph import graph
from retail_support.llm_call_logger import LLMCallLogger


async def main():
    if len(sys.argv) < 2:
        sys.exit('usage: uv run python scripts/ask.py "question" [thread-id]')
    question = sys.argv[1]
    thread_id = sys.argv[2] if len(sys.argv) > 2 else f"ask-{uuid.uuid4().hex[:8]}"

    config = {
        "callbacks": [LLMCallLogger()],
        "configurable": {"thread_id": thread_id},
    }
    result = await graph.ainvoke({"messages": [HumanMessage(question)]}, config=config)

    print("thread:", thread_id)
    print("plan:  ", result["plan"])
    print("status:", result["status"])
    print("errors:", result["errors"])
    print("answer:", result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
