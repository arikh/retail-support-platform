# ADR-009: Control-plane fields frozen into the state schema

## Status
Accepted

## Context
Module 2 introduces Postgres checkpointing. Once a checkpoint is written, the
state shape is serialized into DB rows — after that, any change to the schema
is a data migration against live checkpoints, not a code edit. This is the
last moment the state contract is free to change, so we decide it now.

Module 1 shipped only data-carrying fields (messages, next, findings). Four
control-plane fields were deferred: step_count, errors, pending_approval, and
a typed status. This ADR decides each before the freeze.

## Decision
Freeze all four in now.

1. step_count — Annotated[int, operator.add]
   Purpose: Holds the graph's step count to guarantee termination. LangGraph's
   built-in recursion_limit is a hard backstop that throws an exception on
   overrun; step_count lives in state so the supervisor can read it and exit
   gracefully — escalate or fail with a reason — before the backstop fires.
   operator.add so every node returns +1 and the reducer sums (no node reads
   the old value; safe under concurrency).

2. errors — Annotated[list[str], operator.add]
   Purpose: Each node appends a short failure reason instead of crashing the
   run. Append (operator.add on a list), not overwrite, so the full failure
   trail survives for the supervisor to route on and for audit. Short strings
   only — full detail (stack traces, payloads) lives in observability traces,
   not state, keeping the field from bloating.

3. pending_approval — <Model> | None, overwrite, supervisor-owned
   Purpose: The HITL request object sent to a human before a verdict exists.
   Not used until Module 6, but reserved now: adding it later would be a
   migration against live checkpoints, while an unused None field costs
   nothing. Single writer (supervisor), same ownership pattern as findings.

4. status — Literal["running","awaiting_human","done","failed"]
   Purpose: A closed set of lifecycle values makes illegal states
   unrepresentable — a typo is caught at the boundary instead of flowing
   through and breaking a routing check later. Same discipline as the Literal
   status enums on the findings models (ADR-003).

## Consequences
- Gain: controlled, graceful termination (step_count); an auditable failure
  trail that informs routing (errors); no Module 6 migration (pending_approval);
  illegal lifecycle states caught early (status).
- Cost: three fields sit in the schema before they're exercised. Near zero —
  an unused None or empty accumulator carries no runtime weight, and it buys us
  out of a migration against live checkpoints later.
- pending_approval's contents are designed later (Module 6); this ADR only
  reserves the field.