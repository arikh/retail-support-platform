import uuid
import asyncio
import pytest
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from retail_support.state import SupportState
from retail_support.checkpointer import get_checkpointer


def bump(state):
    return {"step_count": 1, "messages": [HumanMessage(content="tick")]}


async def test_state_persists_across_invocations():
    thread_id = str(uuid.uuid4())

    graph = StateGraph(SupportState)
    graph.add_node("bump", bump)
    graph.add_edge(START, "bump")
    graph.add_edge("bump", END)

    async with get_checkpointer() as saver:
        app = graph.compile(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        await app.ainvoke({"step_count": 0, "messages": []}, config)
        result = await app.ainvoke(
            {"messages": [HumanMessage(content="ping-pong")]}, config
        )
        assert result["step_count"] == 2


async def test_checkpoint_survives_new_instance():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # build graph once
    graph = StateGraph(SupportState)
    graph.add_node("bump", bump)
    graph.add_edge(START, "bump")
    graph.add_edge("bump", END)

    # Writer scope — first checkpointer instance
    async with get_checkpointer() as saver1:
        app = graph.compile(
            checkpointer=saver1
        )  # your minimal test graph, compiled with saver1
        await app.ainvoke({"step_count": 0, "messages": []}, config)

    # saver1 now closed. Fresh instance:
    async with get_checkpointer() as saver2:
        app = graph.compile(checkpointer=saver2)  # ← the read-back method
        snapshot = await app.aget_state(config)
        assert snapshot.values["step_count"] == 1


def node_a(state):
    return {"step_count": 1}


def node_b(state):
    return {"step_count": 1}


async def test_checkpoint_resume_after_crash():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # build graph once
    graph = StateGraph(SupportState)
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", END)

    # Writer scope — first checkpointer instance
    async with get_checkpointer() as saver1:
        app = graph.compile(checkpointer=saver1, interrupt_before=["node_b"])
        await app.ainvoke({"step_count": 0, "messages": []}, config)
        snapshot = await app.aget_state(config)
        assert snapshot.values["step_count"] == 1
        assert snapshot.next == ("node_b",)
        await app.ainvoke(None, config)
        snapshot = await app.aget_state(config)
        assert snapshot.values["step_count"] == 2

# @pytest.mark.xfail(reason="no lock yet; expected 3, gets 2 — passes when Redis lock lands")
async def test_concurrent_lost_update_without_lock():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # build graph
    graph = StateGraph(SupportState)
    graph.add_node("bump", bump)
    graph.add_edge(START, "bump")
    graph.add_edge("bump", END)

    async with get_checkpointer() as saver:
        app = graph.compile(checkpointer=saver)
        await app.ainvoke({"step_count": 0, "messages": []}, config)
        try:
            await asyncio.gather(
                app.ainvoke({"step_count": 0, "messages": []}, config),
                app.ainvoke({"step_count": 0, "messages": []}, config),
            )
        except Exception as e: 
            print(repr(e))

        snapshot = await app.aget_state(config)
        print(snapshot.values["step_count"])
        assert snapshot.values["step_count"] == 2  # lost update — one concurrent +1 dropped. With Redis lock → 3.


async def test_durable_resume_new_instance():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Build the graph
    graph = StateGraph(SupportState)
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", END)

    # Scope 1 hit interrupt and check next
    async with get_checkpointer() as saver1:
        app = graph.compile(checkpointer=saver1, interrupt_before=["node_b"])
        await app.ainvoke({"step_count": 0, "messages": []}, config)
        snapshot = await app.aget_state(config)
        assert snapshot.values["step_count"] == 1
        assert snapshot.next == ("node_b",)
    
    async with get_checkpointer() as saver2:
        app = graph.compile(checkpointer=saver2)
        await app.ainvoke(None, config)
        snapshot = await app.aget_state(config)
        assert snapshot.values["step_count"] == 2


