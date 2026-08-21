import pytest
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from retail_support.state import SupportState, SupportFindings


def test_messages_append():
    existing = [HumanMessage(content="hi")]
    new = [AIMessage(content="hello")]
    merged = add_messages(existing, new)
    assert len(merged) == 2


def test_findings_rejects_bad_status():
    with pytest.raises(ValidationError):
        SupportFindings(summary="x", status="wrong")


def test_findings_overwrite():
    def writer(state: SupportState):
        return {"support_findings": SupportFindings(summary="new", status="resolved")}

    graph = StateGraph(SupportState)
    graph.add_node("writer", writer)
    graph.add_edge(START, "writer")
    graph.add_edge("writer", END)
    app = graph.compile()

    initial = {
        "messages": [],
        "support_findings": SupportFindings(summary="old", status="not_found"),
    }
    result = app.invoke(initial)

    assert result["support_findings"].summary == "new"