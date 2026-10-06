# ruff: noqa: E501
from langchain.agents import create_agent

from retail_support.agent_runner import run_agent, to_findings, worker_messages
from retail_support.analysis_tools import (
    get_downstream_summary,
    get_rejection_reason_counts,
    list_plans,
)
from retail_support.model_provider import ModelProvider
from retail_support.state import AnalysisFindings, SupportState

ANALYSIS_SYSTEM_PROMPT = """You are the analysis worker for a retail pricing-operations platform. You answer questions about PATTERNS ACROSS MANY pricing plans, using only your tools.

Rules:
- Always call a tool to get the numbers. Never answer from memory.
- Never invent plans, counts, percentages, dates, or reasons.
- Include the numbers from the tools in your answer.
- Answer the latest user message. Earlier messages and answers are context only.
- If the request names a period, quarter, season, region, or group, call list_plans first and check that the data contains it. If it does not, say so, say what the data does cover, and stop. Do not give other numbers in its place.
- If a tool returns no data, say so plainly.
- You are read-only. If asked to change anything, say that you cannot.

Write a short, factual final answer in plain text. No markdown."""

ANALYSIS_STATUS_GUIDE = """Status guide:
- "analyzed": the answer reports figures or findings taken from the data. This includes findings about problems, such as failures or rejections.
- "bad_data": the answer says the requested data is missing, is not covered, or is inconsistent, so the question could not be answered as asked.
The status says whether the question could be answered, not whether the news is good or bad."""

async def analysis_worker(state: SupportState) -> dict:
    try:
        agent = create_agent(
            model = ModelProvider.get(role="analysis"),
            tools = [get_rejection_reason_counts, get_downstream_summary, list_plans],
            system_prompt = ANALYSIS_SYSTEM_PROMPT,
        )
        analysis = await run_agent(agent, worker_messages(state, "analysis"))
        findings = await to_findings("analysis", AnalysisFindings, ANALYSIS_STATUS_GUIDE, analysis)
    
    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"analysis_findings": findings, "step_count": 1}
