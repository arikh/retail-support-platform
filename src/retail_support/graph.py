from langgraph.graph import END, START, StateGraph

from retail_support.analysis_worker import analysis_worker
from retail_support.finish_question import finish_question
from retail_support.start_question import start_question
from retail_support.state import SupportState
from retail_support.supervisor import route, supervisor
from retail_support.support_worker import support_worker


def build_graph(checkpointer=None):
    builder = StateGraph(SupportState)
    builder.add_node("start_question", start_question)
    builder.add_node("supervisor", supervisor)
    builder.add_node("support", support_worker)
    builder.add_node("analysis", analysis_worker)
    builder.add_node("finish_question", finish_question)
    builder.add_edge(START, "start_question")
    builder.add_edge("start_question", "supervisor")
    builder.add_conditional_edges(
        "supervisor", route, ["support", "analysis", "finish_question"]
    )
    builder.add_edge("support", "supervisor")
    builder.add_edge("analysis", "supervisor")
    builder.add_edge("finish_question", END)

    return builder.compile(checkpointer=checkpointer)

graph = build_graph()