# ruff: noqa: E501
from typing import Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END
from pydantic import BaseModel

from retail_support.config import MAX_STEPS
from retail_support.model_provider import ModelProvider
from retail_support.state import SupportState

ROUTING_SYSTEM_PROMPT = """You are a routing classifier for a retail pricing-operations support platform. This platform generates country-specific retail prices for a retailer's materials (products) from submitted pricing plans. You do NOT answer the user's question — you only decide which specialist worker should handle it.

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

If the request names one specific plan or material, choose "support".
If it asks about trends, patterns, comparisons, or anomalies across many, choose "analysis".
When genuinely unsure, choose "support"."""

class RoutingDecision(BaseModel):
    next: Literal["support", "analysis"]


def route(state: SupportState)->str:
    if state["step_count"] > MAX_STEPS:
        return END
    if state["next"] in {"support", "analysis"}:
        return state["next"]
    
    return END

async def supervisor(state: SupportState)->dict:
    try:
        llm = ModelProvider.get(role="supervisor")
        classifier = llm.with_structured_output(RoutingDecision)
        messages = [SystemMessage(content=ROUTING_SYSTEM_PROMPT), *state["messages"]]
        decision = await classifier.ainvoke(messages)
    except Exception as e:
        return {
            "next": "terminate",
            "status": "failed",
            "errors": [f"{type(e).__name__}: {e}"],
            "step_count": 1,
        }
    
    return {"next": decision.next, "step_count": 1}