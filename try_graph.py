# ruff: noqa: E501
import asyncio

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from retail_support.checkpointer import build_serde
from retail_support.graph import build_graph

# # Support Questions
# QUESTIONS = [
#     "What is the status of plan SUMMER_LATAM_V2?",
#     "What is the status of plan P-100?",
#     "Which materials are missing from SUMMER_LATAM_V2?",
#     "Why was M-1009 excluded from SUMMER_LATAM_V2?",
# ]
# Analysis Questions
QUESTIONS = [
    "What are the most common rejection reasons across all plans?",
    "Which plans have downstream failures?",
    "What are the most common rejection reasons across all our Q3 plans?",
    "What is the status of plan SUMMER_LATAM_V2? What are the most common rejection reasons across all plans?",
]

async def run(graph, config, question: str):
    state = {
        "messages": [HumanMessage(question)],
    }
    result = await graph.ainvoke(state, config)
    print("question:", question)
    print("messages so far:", len(result["messages"]))
    print("plan:", result["plan"])
    print("step_count:", result["step_count"])
    print("support_findings:", result["support_findings"])
    print("analysis_findings:", result["analysis_findings"])
    print("errors:", result["errors"])
    print("status:", result["status"])
    print("-" * 60)
    # printing image of the graph
    # png = graph.get_graph().draw_mermaid_png()
    # with open("graph.png", "wb") as f:
    #     f.write(png)


async def main():
    graph = build_graph(InMemorySaver(serde=build_serde()))
    for number, question in enumerate(QUESTIONS):
        config = {"configurable": {"thread_id": f"t{number}"}}
        await run(graph, config, question)


asyncio.run(main())