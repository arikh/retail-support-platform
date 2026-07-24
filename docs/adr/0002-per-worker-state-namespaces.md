# ADR-002: Per-worker state namespaces, not a shared findings list

**Status:** Accepted · 24 July 2026

## Context

Three workers — `support`, `analytics`, `escalation` — each produce findings the
supervisor reads. Two ways to hold them in state:

1. One shared `findings: Annotated[list, add]` that all workers append to.
2. A separate field per worker, each with the default replace reducer.

Both are safe under parallel execution.

## Decision

Separate field per worker.

## Consequences

**Gained**

- One writer per field. No reducer needed — default replace is safe because
  nothing competes for the key.
- Provenance is structural. No filtering by source to find out who wrote what.
- The supervisor can test one field for `None` to ask "has this worker run yet?"
- Workers are independently testable.

**Paid**

- Adding a fourth worker changes the state schema. After Module 2 that is a
  migration against live checkpoints, not an edit.

**Why the cost is acceptable**

Workers are not dynamically registered. Adding one is a deliberate
architectural act. Making it visible in the schema is honest, not a defect.
