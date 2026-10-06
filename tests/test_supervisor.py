from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from retail_support.config import MAX_STEPS
from retail_support.finish_question import FAILED_ANSWER, finish_question
from retail_support.state import AnalysisFindings, SupportFindings, SupportState
from retail_support.supervisor import route, supervisor


def fake_support(state: SupportState)-> dict:
    return {
        "support_findings": SupportFindings(summary="fake", status="resolved"),
        "step_count": 1
    }

def fake_analysis(state)-> dict:
    return {
        "analysis_findings": AnalysisFindings(summary="fake", status="analyzed"),
        "step_count": 1
    }


def build_test_graph(checkpointer=None):
    builder = StateGraph(SupportState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("support", fake_support)
    builder.add_node("analysis", fake_analysis)
    builder.add_node("finish_question", finish_question)
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor", route, ["support", "analysis", "finish_question"]
    )
    builder.add_edge("support", "supervisor")
    builder.add_edge("analysis", "supervisor")
    builder.add_edge("finish_question", END)

    return builder.compile(checkpointer=checkpointer)


async def test_two_planned_workers_run_and_finish():
    graph = build_test_graph()
    question = "Status of P-100? Top rejection reasons in Q3?"
    state = {
            "messages": [HumanMessage(question)],
            "plan": {"support": "q1", "analysis": "q2"},
            "step_count": 0,
            "status": "running",
            "next": [],
            "errors": [],
            "pending_approval": None,
            "support_findings": None,
            "analysis_findings": None,
            "escalation_findings": None,
        }
    result = await graph.ainvoke(state)
    assert result["status"] == "done"
    assert result["step_count"] == 4
    assert result["support_findings"] is not None
    assert result["analysis_findings"] is not None
    assert result["errors"] == []
    assert result["messages"][-1].content == "fake\n\nfake"
    
async def test_empty_plan_fails_with_no_worker_matched():
    graph = build_test_graph()
    question = "Status of P-100? Top rejection reasons in Q3?"
    state = {
            "messages": [HumanMessage(question)],
            "plan": {},
            "step_count": 0,
            "status": "running",
            "next": [],
            "errors": [],
            "pending_approval": None,
            "support_findings": None,
            "analysis_findings": None,
            "escalation_findings": None,
        }
    result = await graph.ainvoke(state)
    assert result["status"] == "failed"
    assert result["errors"] == ["no worker matched"]
    assert result["step_count"] == 1
    assert result["support_findings"] is None
    assert result["analysis_findings"] is None
    assert result["messages"][-1].content == FAILED_ANSWER


# --- supervisor(): one call, no graph, no LLM --------------------------------


def new_state(**changes):
    state = {
        "messages": [HumanMessage("question")],
        "plan": None,
        "step_count": 0,
        "errors": [],
        "support_findings": None,
        "analysis_findings": None,
    }
    state.update(changes)
    return state


async def test_planner_merges_duplicates_and_skips_empty(use_planner):
    use_planner([("support", " a "), ("support", "b"), ("analysis", "   ")])

    result = await supervisor(new_state())

    assert result["plan"] == {"support": "a b"}
    assert result["next"] == ["support"]
    assert result["step_count"] == 1


async def test_planner_error_is_recorded(use_planner):
    use_planner(error=RuntimeError("down"))

    result = await supervisor(new_state())

    assert result == {
        "next": [],
        "status": "failed",
        "errors": ["RuntimeError: down"],
        "step_count": 1,
    }


async def test_existing_plan_is_not_planned_again(use_planner):
    planner = use_planner()

    result = await supervisor(new_state(plan={"support": "q"}))

    assert result["next"] == ["support"]
    assert planner.seen == []


async def test_errors_stop_the_run_before_anything_else(use_planner):
    planner = use_planner()
    filled = SupportFindings(summary="x", status="resolved")
    state = new_state(
        plan={"support": "q"}, support_findings=filled, errors=["boom"]
    )

    result = await supervisor(state)

    assert result == {"next": [], "status": "failed", "step_count": 1}
    assert planner.seen == []


async def test_max_steps_fails_the_run(use_planner):
    use_planner()
    state = new_state(plan={"support": "q"}, step_count=MAX_STEPS + 1)

    result = await supervisor(state)

    assert result["status"] == "failed"
    assert result["errors"] == ["max steps exceeded"]


# --- route(): the allowlist gate ---------------------------------------------


def test_route_lets_only_known_workers_through():
    assert route({"next": ["support", "analysis"]}) == ["support", "analysis"]
    assert route({"next": ["support", "escalation", "rm -rf"]}) == ["support"]
    assert route({"next": ["escalation"]}) == "finish_question"
    assert route({"next": []}) == "finish_question"
