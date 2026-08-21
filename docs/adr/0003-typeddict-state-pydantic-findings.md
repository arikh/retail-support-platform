# ADR-003: TypedDict for graph state, Pydantic for worker findings

**Status:** Accepted · 24 July 2026

## Context

LangGraph accepts either `TypedDict` or a Pydantic `BaseModel` as the state
schema. Pydantic appears safer because it validates. The LangGraph docs say
otherwise:

- Runtime validation runs only on input to the first node — not on what workers
  return, and not on output.
- The validation error does not identify which node caused it.
- Graph output is not returned as a Pydantic instance.
- Recursive validation is slow, and it re-runs on a growing object every step.

The untrusted data in this system is LLM output produced inside workers. A
Pydantic state schema does not check that, and taxes every step for protection
we do not receive.

## Decision

`TypedDict` for the graph state container.
Pydantic `BaseModel` for the value held in each worker's namespace field.

```python
class SupportFindings(BaseModel):
    resolution: str
    confidence: float = Field(ge=0, le=1)
    refund_amount: int | None = None

class SupportState(TypedDict):
    messages: Annotated[list, add_messages]
    support_findings: SupportFindings | None
```

## Consequences

- Validation happens inside the worker, at construction, where the stack trace
  points at the real cause and bad data never reaches state or Postgres.
- No validation cost on the graph state at every superstep.
- Reducers keep native LangGraph ergonomics.
- The graph state itself is unchecked at runtime. Mitigated by static checking
  and by the fact that its fields are simple control values, not LLM output.

## Principle

Validate at the edge where untrusted data enters. The graph state is not that
edge. The LLM response is.
