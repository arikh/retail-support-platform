# ADR-008: Irreversibility Barrier (Side-Effect Placement)

## Status
Accepted

## Context
On resume, an interrupted node re-runs from the top, not from
the line after interrupt(). So anything above interrupt() executes more than
once.

## Decision
In any node that calls `interrupt()`, no irreversible side effect runs before
the `interrupt()` line. The interrupt goes first; irreversible work goes after.
Idempotency keys at the provider boundary as a backstop.
Rationale: The irreversible work always takes place after an human input received Previous work jus calculation so data changes, so starting from begining has no harm.

## Consequences
This one rule protects two features:
- Resume-safety: The pre interrupt work just preparing the data and calculation no data modification
- Abandonment-safety: As there is no permannet change of data, it is safe to abandon

Negative / cost: A reversible pre-interrupt read is fine, but the discipline is on the developer, he needs to make sure every permanent changes to data takes place post interruption

## Related
- ADR-007 (HITL — depends on this barrier)