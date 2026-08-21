# ADR-004: Hybrid supervisor routing — rules first, LLM fallback

**Status:** Accepted · 24 July 2026

## Context

The supervisor must choose the next worker on every turn. Three options:

| Option | Strength | Weakness |
|---|---|---|
| LLM decides | Handles anything | Model call every turn; nondeterministic; hard to test |
| Rules decide | Free, deterministic, testable | Fails on unanticipated requests |
| Hybrid | Cheap and predictable for common cases, flexible otherwise | Two paths to test |

Retail support traffic is highly repetitive. Most turns are order status,
returns, refunds, and policy questions.

## Decision

Rules first. LLM on miss. Every miss is logged.

```python
decision = rules.match(state)
if decision is None:
    decision = llm.decide(state)
    log_fallback(state, decision)
return {"next": decision}
```

The routing decision is always a value, never prose. Routing that depends on
parsing a sentence is nondeterministic and untestable.

## Consequences

- Majority of turns cost nothing and are deterministic.
- The fallback log is the improvement loop: read the misses, find the patterns,
  promote them to rules.
- **Promotion is a policy change, not a cache write-back.** A rule is a guess
  about correct routing, unlike a cached copy of a known-correct origin
  response. Promotion requires human review.

## Risks to monitor

1. **Stale rules.** A rising fallback rate means the cheap path stopped working.
   Fallback rate is a tracked metric (Block 5).
2. **Wrong rules.** A rule that confidently matches and routes incorrectly never
   consults the LLM, so the error is invisible. Rules must be narrow and
   specific rather than broad.

## Rejected

- **Fixed pipeline** — cannot adapt to what the customer asked.
- **Swarm** — coordination logic spreads across workers; no single place to
  pause for human approval; weak audit trail.
- **Hierarchical** — unnecessary at three workers.

Accepted cost of the supervisor pattern: it is a bottleneck and a single point
of failure.
