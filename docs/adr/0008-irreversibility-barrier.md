# ADR-0008: Irreversibility Barrier (Side-Effect Placement)

## Status
Accepted

## Context
On resume, an interrupted node re-runs from the top, not from
the line after interrupt(). So anything above interrupt() executes more than once.
This is because LangGraph re-executes the node from the beginning on resume — it does not continue from the line after interrupt().

## Decision
In any node that calls `interrupt()`, no irreversible side effect runs before
the `interrupt()` line. The interrupt goes first; irreversible work goes after.
Idempotency keys at the provider boundary as a backstop.
Rationale: irreversible work always runs after human input is received. Everything before interrupt() is just calculation, so re-running from the top changes no external state and does no harm.

## Consequences
This one rule protects two features:
- Resume-safety: pre-interrupt() work only prepares data and calculates — no data modification, so re-running is harmless.
- Abandonment-safety: no permanent change happens before the gate, so an abandoned interrupt leaves no partial state behind.

Negative / cost: the barrier is a convention, not a mechanical guarantee — nothing in the type system or runtime prevents a developer from placing an irreversible side effect before interrupt(). Idempotency at the provider boundary is the only automated backstop. Requires reviewer discipline.

## Related
- ADR-007 (HITL — depends on this barrier)