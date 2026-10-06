"""Graph-level tests.

These use the real wiring from graph.py (build_graph), with a fake planner
and fake workers. No LLM and no database are used.
"""
import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from retail_support.agent_runner import worker_messages
from retail_support.checkpointer import build_serde, get_checkpointer
from retail_support.finish_question import FAILED_ANSWER
from retail_support.graph import build_graph
from retail_support.state import AnalysisFindings, SupportFindings


def make_workers():
    """Two fake workers, and a dict that records the question each one got."""
    seen = {}

    def support(state):
        seen["support"] = worker_messages(state, "support")[-1].content
        return {
            "support_findings": SupportFindings(
                summary="support answer", status="resolved"
            ),
            "step_count": 1,
        }

    def analysis(state):
        seen["analysis"] = worker_messages(state, "analysis")[-1].content
        return {
            "analysis_findings": AnalysisFindings(
                summary="analysis answer", status="analyzed"
            ),
            "step_count": 1,
        }

    return support, analysis, seen


def failing_support(state):
    return {"errors": ["RuntimeError: boom"], "step_count": 1}


def ask(question):
    return {"messages": [HumanMessage(question)]}


async def test_one_part_question_takes_three_steps(use_planner):
    planner = use_planner([("support", "status of X?")])
    support, analysis, seen = make_workers()
    graph = build_graph(support=support, analysis=analysis)

    result = await graph.ainvoke(ask("status of X?"))

    assert result["status"] == "done"
    assert result["step_count"] == 3
    assert result["plan"] == {"support": "status of X?"}
    assert result["messages"][-1].content == "support answer"
    assert seen == {"support": "status of X?"}
    assert len(planner.seen) == 1


async def test_two_part_question_gives_each_worker_its_own_part(use_planner):
    use_planner([("support", "part A?"), ("analysis", "part B?")])
    support, analysis, seen = make_workers()
    graph = build_graph(support=support, analysis=analysis)

    result = await graph.ainvoke(ask("part A? part B?"))

    assert result["status"] == "done"
    assert result["step_count"] == 4
    assert seen == {"support": "part A?", "analysis": "part B?"}
    assert result["messages"][-1].content == "support answer\n\nanalysis answer"


async def test_one_worker_fails_and_the_run_ends_failed(use_planner):
    use_planner([("support", "part A?"), ("analysis", "part B?")])
    _, analysis, _ = make_workers()
    graph = build_graph(support=failing_support, analysis=analysis)

    result = await graph.ainvoke(ask("part A? part B?"))

    assert result["status"] == "failed"
    assert result["errors"] == ["RuntimeError: boom"]
    assert result["step_count"] == 4
    assert result["support_findings"] is None
    assert result["analysis_findings"] is not None
    assert result["messages"][-1].content == FAILED_ANSWER


async def test_no_worker_matched_stops_in_one_step(use_planner):
    use_planner([])
    support, analysis, seen = make_workers()
    graph = build_graph(support=support, analysis=analysis)

    result = await graph.ainvoke(ask("What is the weather today?"))

    assert result["status"] == "failed"
    assert result["errors"] == ["no worker matched"]
    assert result["step_count"] == 1
    assert seen == {}
    assert result["messages"][-1].content == FAILED_ANSWER


async def test_second_question_starts_clean_and_sees_the_first_answer(use_planner):
    planner = use_planner(
        [("support", "first question")],
        [("analysis", "second question")],
    )
    support, analysis, _ = make_workers()
    graph = build_graph(
        InMemorySaver(serde=build_serde()), support=support, analysis=analysis
    )
    config = {"configurable": {"thread_id": "t1"}}

    first = await graph.ainvoke(ask("first question"), config)

    assert first["step_count"] == 3
    assert len(first["messages"]) == 2
    assert first["messages"][-1].content == "support answer"

    second = await graph.ainvoke(ask("second question"), config)

    # The reset: a fresh count, a fresh plan, and the old findings are gone.
    assert second["status"] == "done"
    assert second["step_count"] == 3
    assert second["plan"] == {"analysis": "second question"}
    assert second["support_findings"] is None
    assert second["analysis_findings"] is not None

    # The conversation is kept: question, answer, question, answer.
    assert len(second["messages"]) == 4
    assert second["messages"][-1].content == "analysis answer"

    # The planner saw the first question together with its answer (INC-006).
    asked = [message.content for message in planner.seen[1][1:]]
    assert asked == ["first question", "support answer", "second question"]

async def test_full_graph_on_the_postgres_checkpointer(use_planner):
    use_planner(
        [("support", "first question")],
        [("analysis", "second question")],
    )
    support, analysis, _ = make_workers()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    async with get_checkpointer() as saver:
        graph = build_graph(saver, support=support, analysis=analysis)
        await graph.ainvoke(ask("first question"), config)

    # A new checkpointer instance: the state must come back from Postgres.
    async with get_checkpointer() as saver:
        graph = build_graph(saver, support=support, analysis=analysis)
        second = await graph.ainvoke(ask("second question"), config)

    assert second["status"] == "done"
    assert second["step_count"] == 3
    assert second["plan"] == {"analysis": "second question"}
    assert second["support_findings"] is None
    assert len(second["messages"]) == 4
    assert second["messages"][-1].content == "analysis answer"
