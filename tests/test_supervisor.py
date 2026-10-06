from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

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