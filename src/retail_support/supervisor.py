# ruff: noqa: E501
from typing import Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END
from pydantic import BaseModel

from retail_support.config import MAX_STEPS
from retail_support.model_provider import ModelProvider
from retail_support.state import SupportState

ROUTING_SYSTEM_PROMPT = """You are a routing classifier for a retail pricing-operations support platform. This platform generates country-specific retail prices for a retailer's materials (products) from submitted pricing plans. You do NOT answer the user's question — you only decide which specialist workers should handle it.

Choose "support" when the request is about ONE specific pricing plan or material:
- the status of a named plan
- why a specific material was rejected or excluded
- which materials are missing from a named plan
- whether a named plan's prices propagated downstream
These are answered by a single lookup on one plan or material.

Choose "analysis" when the request is about PATTERNS ACROSS MANY plans, materials, countries, or time:
- most common rejection reasons across plans
- pricing trends or comparisons over time or across countries
- anomalies or spikes in rejections or failures
- aggregate breakdowns across the dataset
These require investigating data broadly, not a single lookup.

Return every worker the request needs, as a list.
If the request names one specific plan or material, include "support".
If it asks about trends, patterns, comparisons, or anomalies across many, include "analysis".
If the request has both kinds of parts, return both.
If the request fits neither worker, or you are genuinely unsure, return an empty list. Do not guess."""

class RoutingPlan(BaseModel):
    workers: list[Literal["support", "analysis"]]


FINDINGS_FIELD: dict[str, str] = {
    "support": "support_findings",
    "analysis": "analysis_findings",
}


def pending_workers(state: SupportState, plan: list[str]) -> list[str]:
    """Workers in the plan whose drawer is still empty."""
    return [worker for worker in plan if state[FINDINGS_FIELD[worker]] is None]


def route(state: SupportState) -> list[str] | str:
    allowed = [worker for worker in state["next"] if worker in FINDINGS_FIELD]
    if allowed:
        return allowed
    return END


async def supervisor(state: SupportState) -> dict:
    plan = state["plan"]

    if state["errors"]:
        return {
            "next": [],
            "status": "failed",
            "step_count": 1,
        }

    if plan and not pending_workers(state, plan):
        return {
            "next": [],
            "status": "done",
            "step_count": 1,
        }

    if state["step_count"] > MAX_STEPS:
        return {
            "next": [],
            "status": "failed",
            "errors": ["max steps exceeded"],
            "step_count": 1,
        }

    if plan is None:
        try:
            llm = ModelProvider.get(role="supervisor")
            classifier = llm.with_structured_output(RoutingPlan)
            messages = [SystemMessage(content=ROUTING_SYSTEM_PROMPT), *state["messages"]]
            decision = await classifier.ainvoke(messages)
        except Exception as e:
            return {
                "next": [],
                "status": "failed",
                "errors": [f"{type(e).__name__}: {e}"],
                "step_count": 1,
            }
        plan = list(dict.fromkeys(decision.workers))

    if not plan:
        return {
            "plan": [],
            "next": [],
            "status": "failed",
            "errors": ["no worker matched"],
            "step_count": 1,
        }

    return {
        "plan": plan,
        "next": pending_workers(state, plan),
        "step_count": 1,
    }
    
