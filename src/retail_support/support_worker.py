from retail_support.model_provider import ModelProvider
from retail_support.state import SupportState


async def support_worker(state: SupportState) -> dict:
    try:
        llm = ModelProvider.get(role="support")
        response = await llm.ainvoke(state["messages"])
    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"messages": [response], "step_count": 1}
