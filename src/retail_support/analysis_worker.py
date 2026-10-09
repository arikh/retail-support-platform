# ruff: noqa: E501
from langchain.agents import create_agent

from retail_support.agent_runner import run_agent, to_findings, worker_messages
from retail_support.analysis_tools import (
    get_downstream_summary,
    get_rejection_reason_counts,
    list_plans,
)
from retail_support.model_provider import ModelProvider
from retail_support.prompt_store import call_metadata, load_prompt
from retail_support.state import AnalysisFindings, SupportState

ANALYSIS_SYSTEM_PROMPT = load_prompt("analysis_system")
ANALYSIS_STATUS_GUIDE = load_prompt("analysis_status_guide")

async def analysis_worker(state: SupportState) -> dict:
    try:
        agent = create_agent(
            model = ModelProvider.get(role="analysis"),
            tools = [get_rejection_reason_counts, get_downstream_summary, list_plans],
            system_prompt = ANALYSIS_SYSTEM_PROMPT.text,
        )
        analysis = await run_agent(
            agent,
            worker_messages(state, "analysis"),
            call_metadata("analysis", ANALYSIS_SYSTEM_PROMPT),
        )
        findings = await to_findings("analysis", AnalysisFindings, ANALYSIS_STATUS_GUIDE, analysis)
    
    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"analysis_findings": findings, "step_count": 1}
