import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from retail_support.state import SupportFindings, SupportState


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


def test_messages_append_through_graph():
    def emit_message(state: SupportState):
        return {"messages": [HumanMessage(content="hi")]}

    graph = StateGraph(SupportState)
    graph.add_node("emit_message", emit_message)
    graph.add_edge(START, "emit_message")
    graph.add_edge("emit_message", END)
    app = graph.compile()

    initial = {"messages": [AIMessage(content="hello")]}
    result = app.invoke(initial)

    assert len(result["messages"]) == 2
