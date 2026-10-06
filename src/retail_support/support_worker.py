# ruff: noqa: E501
from langchain.agents import create_agent

from retail_support.agent_runner import run_agent, to_findings, worker_messages
from retail_support.model_provider import ModelProvider
from retail_support.state import SupportFindings, SupportState
from retail_support.support_tools import (
    get_downstream_status,
    get_material_rejection_reason,
    get_missing_materials,
    get_plan_status,
)

SUPPORT_SYSTEM_PROMPT = """You are the support worker for a retail pricing-operations platform. You answer questions about ONE specific pricing plan or material, using only your tools.

Rules:
- Always call a tool to get the facts. Never answer from memory.
- Never invent plans, materials, statuses, numbers, or rules.
- Answer the latest user message. Earlier messages and answers are context only.
- You are read-only. If asked to change, approve, or delete anything, do not do it, and say that you cannot.
- If a tool says a plan or material was not found, say so plainly. Do not guess.
- If the request names no plan or material you can look up, say what is missing.
- If the data looks inconsistent or the cause is unknown, say that a developer needs to look at it.

Plans are identified by plan name, for example SUMMER_LATAM_V2. Materials are identified by ID, for example M-1009.
Write a short, factual final answer in plain text. No markdown."""

SUPPORT_STATUS_GUIDE = """Status guide:
- "resolved": the answer gives facts about a plan or material.
- "not_found": the answer says a plan or material was not found, or that the request names nothing to look up.
- "needs_escalation": the answer says the data is inconsistent, the cause is unknown, a problem persists after a fix, or the user asked to change data."""


async def support_worker(state: SupportState) -> dict:
    try:
        agent = create_agent(
            model = ModelProvider.get(role="support"),
            tools=[get_downstream_status, get_material_rejection_reason, get_missing_materials, get_plan_status],
            system_prompt=SUPPORT_SYSTEM_PROMPT,
        )
        
        answer = await run_agent(agent, worker_messages(state, "support"))
        findings = await to_findings("support", SupportFindings, SUPPORT_STATUS_GUIDE, answer)


    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"support_findings": findings, "step_count": 1}
