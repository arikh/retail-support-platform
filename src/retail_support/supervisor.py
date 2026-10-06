# ruff: noqa: E501
from typing import Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from retail_support.config import MAX_STEPS
from retail_support.model_provider import ModelProvider
from retail_support.state import FINDINGS_FIELD, SupportState

ROUTING_SYSTEM_PROMPT = """
You are a routing planner for a retail pricing-operations support platform. 
This platform generates country-specific retail prices for a retailer's materials (products) from submitted pricing plans. 
You do NOT answer the user's question — you decide which specialist workers should handle it, and what each one should be asked.

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

Return one task for every worker the request needs. Each task has a worker and a question.
- If the request names one specific plan or material, include a "support" task.
- If it asks about trends, patterns, comparisons, or anomalies across many, include an "analysis" task.
- If the request has both kinds of parts, return both tasks.
- At most one task per worker.

How to write each question:
- It contains only the part of the request that belongs to that worker.
- Use the user's own words. Do not add anything the user did not ask.
- Copy plan names and material IDs exactly as the user wrote them.
- It must make sense when read alone. If the user says "that plan" or "it", replace it with the actual name from the conversation.
- If the whole request is for one worker, the question is the user's message, unchanged.

If the request fits neither worker, or you are genuinely unsure, return an empty list of tasks. Do not guess.
Plan only for the latest user message. Earlier messages and answers are context only."""

class WorkerTask(BaseModel):
    worker: Literal["support", "analysis"]
    question: str

class RoutingPlan(BaseModel):
    tasks: list[WorkerTask]

def pending_workers(state: SupportState, plan: dict[str, str]) -> list[str]:
    """Workers in the plan whose drawer is still empty."""
    return [worker for worker in plan if state[FINDINGS_FIELD[worker]] is None]


def route(state: SupportState) -> list[str] | str:
    allowed = [worker for worker in state["next"] if worker in FINDINGS_FIELD]
    if allowed:
        return allowed
    
    return "finish_question"


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
        
        plan = {}
        for task in decision.tasks:
            question = task.question.strip()

            if not question:
                continue
            elif task.worker in plan:
                plan[task.worker] += " " +question 
            else:
                plan[task.worker] = question

    if not plan:
        return {
            "plan": {},
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
    
