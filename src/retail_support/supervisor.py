# ruff: noqa: E501
from typing import Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from retail_support.config import MAX_STEPS
from retail_support.model_provider import ModelProvider
from retail_support.prompt_store import call_metadata, load_prompt
from retail_support.state import FINDINGS_FIELD, SupportState

ROUTING_SYSTEM_PROMPT = load_prompt("routing_system")

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
            messages = [SystemMessage(content=ROUTING_SYSTEM_PROMPT.text), *state["messages"]]
            decision = await classifier.ainvoke(
                messages,
                config={"metadata": call_metadata("supervisor", ROUTING_SYSTEM_PROMPT)},
            )
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
