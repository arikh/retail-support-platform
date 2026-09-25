from retail_support.model_provider import ModelProvider
from retail_support.state import AnalysisFindings, SupportState


async def analysis_worker(state: SupportState) -> dict:
    try:
        llm = ModelProvider.get(role="analysis")
        structured = llm.with_structured_output(AnalysisFindings)
        response = await structured.ainvoke(state["messages"])
    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"analysis_findings": response, "step_count": 1}
