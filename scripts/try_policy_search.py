"""Ask the policy search a few questions and print what each stage finds.

    uv run python scripts/try_policy_search.py
    uv run python scripts/try_policy_search.py "your own question"

Three lists for each question:
  dense    by meaning; the number is a distance, smaller is nearer
  keyword  by matching words; the number is a word score, larger is better
  hybrid   the two lists merged; the number is the fused score, larger is better
"""

import asyncio
import sys
import time

from retail_support.policy_search import (
    hybrid_passages,
    keyword_passages,
    search_passages,
)

QUESTIONS = [
    "What does PENDING mean?",
    "Why would a material with a 2-month expiry be left out of my plan?",
    "Who fixes a wrong market mapping?",
    "What is CATEGORY_CHANNEL_RULE?",
]

# stage name, the search, and the key that holds its number
STAGES = [
    ("dense", search_passages, "distance"),
    ("keyword", keyword_passages, "score"),
    ("hybrid", hybrid_passages, "score"),
]


async def main():
    questions = sys.argv[1:] or QUESTIONS
    for question in questions:
        print(f"\n{question}")
        for stage, search, number in STAGES:
            start = time.perf_counter()
            rows = await search(question)
            milliseconds = (time.perf_counter() - start) * 1000
            print(f"  {stage}   ({milliseconds:.0f} ms)")
            if not rows:
                print("    nothing found")
            for row in rows:
                print(f"    {row[number]:.4f}  {row['source']}  |  {row['heading']}")


if __name__ == "__main__":
    asyncio.run(main())
