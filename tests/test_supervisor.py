from langchain_core.messages import HumanMessage
from langgraph.graph import START, StateGraph

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
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route)
    builder.add_edge("support", "supervisor")
    builder.add_edge("analysis", "supervisor")

    return builder.compile(checkpointer=checkpointer)


async def test_two_planned_workers_run_and_finish():
    app = build_test_graph()
    question = "Status of P-100? Top rejection reasons in Q3?"
    state = {
            "messages": [HumanMessage(question)],
            "plan": ["support", "analysis"],
            "step_count": 0,
            "status": "running",
            "next": [],
            "errors": [],
            "pending_approval": None,
            "support_findings": None,
            "analysis_findings": None,
            "escalation_findings": None,
        }
    result = await app.ainvoke(state)
    assert result["status"] == "done"
    assert result["step_count"] == 4
    assert result["support_findings"] is not None
    assert result["analysis_findings"] is not None
    assert result["errors"] == []

