from langgraph.graph import START, StateGraph

from retail_support.analysis_worker import analysis_worker
from retail_support.state import SupportState
from retail_support.supervisor import route, supervisor
from retail_support.support_worker import support_worker


def build_graph(checkpointer=None):
    builder = StateGraph(SupportState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("support", support_worker)
    builder.add_node("analysis", analysis_worker)
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route)
    builder.add_edge("support", "supervisor")
    builder.add_edge("analysis", "supervisor")

    return builder.compile(checkpointer=checkpointer)

graph = build_graph()