from langgraph.graph import END

from retail_support.config import MAX_STEPS
from retail_support.state import SupportState


def route(state: SupportState)->str:
    if state["step_count"] > MAX_STEPS:
        return END

    return "support"

def supervisor(state: SupportState)->dict:
    return {}