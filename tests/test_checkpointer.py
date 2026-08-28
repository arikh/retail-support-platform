import uuid
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from retail_support.state import SupportState
from retail_support.checkpointer import get_checkpointer

def bump(state):
    return {"step_count": 1, "messages": [HumanMessage(content="tick")]}

async def test_state_persists_across_invocations():

    graph = StateGraph(SupportState)

    graph.add_node("bump", bump)
    graph.add_edge(START, "bump")
    graph.add_edge("bump", END)

    async with get_checkpointer() as saver:
        app = graph.compile(checkpointer=saver)
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        await app.ainvoke({"step_count": 0, "messages": []}, config)
        result = await app.ainvoke({"messages": [HumanMessage(content="ping-pong")]}, config)
        assert result["step_count"] == 2


