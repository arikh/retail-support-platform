from langgraph.graph import END

from retail_support.config import MAX_STEPS
from retail_support.state import SupportState


def route(state: SupportState)->str:
    if state["step_count"] > MAX_STEPS:
        return END
    if state["next"] in {"support", "analysis"}:
        return state["next"]
    
    return END

def supervisor(state: SupportState)->dict:
    return {}