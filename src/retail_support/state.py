"""State contract for the retail-support-platform graph.

Defines the shared state passed between graph nodes (SupportState) and the
per-worker output models the workers write into it (the *Findings models).

See ADR-002 (one writer per field), ADR-003 (TypedDict for state, Pydantic
for findings, validate at the LLM edge).
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

# --- Worker output models (Pydantic: validated at the LLM edge, ADR-003) ---


class SupportFindings(BaseModel):
    summary: str
    status: Literal["resolved", "not_found", "needs_escalation"]


class AnalysisFindings(BaseModel):
    summary: str
    status: Literal["analyzed", "bad_data"]


class EscalationFindings(BaseModel):
    summary: str
    status: Literal["approved", "rejected", "edited", "expired"]


class PendingApproval(BaseModel):
    action: str
    details: dict
    requested_by: str


# --- Shared graph state (TypedDict: trusted, program-written, ADR-003) ---


class SupportState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # history -> append

    status: Literal[
        "running", "awaiting_human", "done", "failed"
    ]  # current lifecycle value -> overwrite (supervisor owns)
    next: str  # routing decision, a value never prose -> overwrite (ADR-004)
    step_count: Annotated[int, operator.add]  # loop breaker -> accumulate
    errors: Annotated[list[str], operator.add]  # failure trail -> append
    pending_approval: (
        PendingApproval | None
    )  # HITL request -> overwrite, None until paused

    support_findings: SupportFindings | None  # overwrite (support owns)
    analysis_findings: AnalysisFindings | None  # overwrite (analysis owns)
    escalation_findings: EscalationFindings | None  # overwrite (escalation owns)
