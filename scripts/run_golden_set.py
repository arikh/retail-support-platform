"""Run the golden set and print the scores.

    uv run python scripts/run_golden_set.py              retrieval only
    uv run python scripts/run_golden_set.py routing      routing only
    uv run python scripts/run_golden_set.py all          both

retrieval  For each policy case, the three searches (dense, keyword, hybrid)
           and the place of the first expected passage: 1, 2, 3 or miss.
           No LLM call. Needs Postgres and the ingested passages.

routing    For each case, the supervisor's plan compared with the expected
           workers. One LLM call for each case (this costs money, a little).
           Every call writes a row to llm_calls under the run's thread ids.
"""

import asyncio
import sys
import uuid

from retail_support.eval_metrics import is_hit, rate, same_workers
from retail_support.golden_set import load_cases, policy_cases
from retail_support.policy_search import (
    hybrid_passages,
    keyword_passages,
    search_passages,
)

TOP = 3  # how many passages each search returns, as the worker's tool does

# stage name and the search behind it
STAGES = [
    ("dense", search_passages),
    ("keyword", keyword_passages),
    ("hybrid", hybrid_passages),
]


def first_place(rows: list[dict], expected: list[dict]) -> int | None:
    """The place (1, 2, 3) of the first expected passage, or None for a miss."""
    for k in range(1, TOP + 1):
        if is_hit(rows, expected, k):
            return k
    return None


async def run_retrieval(cases: list[dict]) -> None:
    policy = policy_cases(cases)
    places: dict[str, list[int | None]] = {stage: [] for stage, _ in STAGES}

    print(f"\nRetrieval: {len(policy)} policy cases, top {TOP} passages")
    print("place of the first expected passage: 1, 2, 3 or miss\n")
    print("  case    dense    keyword  hybrid   question")
    for case in policy:
        marks = []
        for stage, search in STAGES:
            rows = await search(case["question"], TOP)
            place = first_place(rows, case["expected_passages"])
            places[stage].append(place)
            marks.append(str(place) if place else "miss")
        print(
            f"  {case['id']}   {marks[0]:<8} {marks[1]:<8} {marks[2]:<8} "
            f"{case['question']}"
        )

    print()
    for k in (1, TOP):
        scores = []
        for stage, _ in STAGES:
            hits = [place is not None and place <= k for place in places[stage]]
            scores.append(f"{stage} {rate(hits):.2f} ({hits.count(True)}/{len(hits)})")
        print(f"  hit rate at {k}:  " + "   ".join(scores))


async def run_routing(cases: list[dict]) -> None:
    # Imported here so that a retrieval run needs no LLM key.
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableLambda

    from retail_support.llm_call_logger import LLMCallLogger
    from retail_support.supervisor import supervisor

    run = uuid.uuid4().hex[:8]
    planner = RunnableLambda(supervisor)
    logger = LLMCallLogger()
    results: list[bool] = []
    failed_calls = 0

    print(f"\nRouting: {len(cases)} cases, one LLM call each (run {run})\n")
    for case in cases:
        # The state a question has when it reaches the supervisor.
        state = {
            "messages": [HumanMessage(case["question"])],
            "plan": None,
            "next": [],
            "status": "running",
            "step_count": 0,
            "errors": [],
            "pending_approval": None,
            "support_findings": None,
            "analysis_findings": None,
            "escalation_findings": None,
        }
        thread_id = f"golden-{run}-{case['id']}"
        config = {
            "callbacks": [logger],
            "metadata": {"thread_id": thread_id},
            "configurable": {"thread_id": thread_id},
        }
        result = await planner.ainvoke(state, config=config)

        expected = sorted(case["expected_workers"])
        if "plan" not in result:  # the model call itself failed
            failed_calls += 1
            results.append(False)
            print(f"  {case['id']}  ERROR {result['errors'][0]}")
            continue

        planned = sorted(result["plan"])
        correct = same_workers(planned, expected)
        results.append(correct)
        mark = "ok  " if correct else "MISS"
        print(
            f"  {case['id']}  {mark}  planned {str(planned):<24} "
            f"expected {str(expected):<24} {case['question']}"
        )

    print(
        f"\n  routing accuracy: {rate(results):.2f} "
        f"({results.count(True)}/{len(results)})"
    )
    if failed_calls:
        print(f"  model calls that failed: {failed_calls} (counted as wrong)")
    print(
        "\n  cost of this run:\n"
        "  docker exec -i retail-postgres psql -U retail -d retail_support -c "
        f"\"SELECT count(*) AS calls, sum(input_tokens) AS input_tokens, "
        f"sum(cost_usd) AS cost_usd FROM llm_calls "
        f"WHERE thread_id LIKE 'golden-{run}-%'\""
    )


async def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "retrieval"
    if what not in ("retrieval", "routing", "all"):
        sys.exit("usage: run_golden_set.py [retrieval | routing | all]")

    cases = load_cases()
    if what in ("retrieval", "all"):
        await run_retrieval(cases)
    if what in ("routing", "all"):
        await run_routing(cases)


if __name__ == "__main__":
    asyncio.run(main())
