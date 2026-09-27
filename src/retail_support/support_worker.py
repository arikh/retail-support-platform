from retail_support.model_provider import ModelProvider
from retail_support.state import SupportFindings, SupportState


async def support_worker(state: SupportState) -> dict:
    try:
        llm = ModelProvider.get(role="support")
        structured = llm.with_structured_output(SupportFindings)
        response = await structured.ainvoke(state["messages"])
    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"support_findings": response, "step_count": 1}
