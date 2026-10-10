"""Ask the policy search a few questions and print what it finds.

    uv run python scripts/try_policy_search.py
    uv run python scripts/try_policy_search.py "your own question"
"""

import asyncio
import sys
import time

from retail_support.policy_search import search_passages

QUESTIONS = [
    "What does PENDING mean?",
    "Why would a material with a 2-month expiry be left out of my plan?",
    "Who fixes a wrong market mapping?",
    "What is CATEGORY_CHANNEL_RULE?",
]


async def main():
    questions = sys.argv[1:] or QUESTIONS
    for question in questions:
        start = time.perf_counter()
        rows = await search_passages(question)
        milliseconds = (time.perf_counter() - start) * 1000
        print(f"\n{question}   ({milliseconds:.0f} ms)")
        for row in rows:
            print(f"  {row['distance']:.3f}  {row['source']}  |  {row['heading']}")


if __name__ == "__main__":
    asyncio.run(main())
