from langgraph.types import Overwrite

from retail_support.state import SupportState


async def start_question(state: SupportState) -> dict:
    return {
        "plan": None,
        "next": [],
        "status": "running",
        "support_findings": None,
        "analysis_findings": None,
        "escalation_findings": None,
        "pending_approval": None,
        "step_count": Overwrite(0),
        "errors": Overwrite([]),
    }
