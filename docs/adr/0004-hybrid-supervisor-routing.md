# ADR-0004: Hybrid supervisor routing — rules first, LLM fallback

**Status:** Accepted · 24 July 2026 · Amended 6 Oct 2026 (see the end)

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

## Amendment — 6 Oct 2026: what is built, and what is not

This ADR was written before the code. Module 3 built part of it.

**The domain changed.** The context above talks about order status, returns
and refunds. The platform serves retail pricing operations (plan status,
missing materials, rejection reasons, downstream propagation). See
`docs/domain-and-requirements.md`.

**Built: rules first for stopping.** Before any LLM call, the supervisor
checks facts in code, in this order: errors → `failed`; every planned
findings field filled → `done`; too many steps → `failed`.

**Built: the decision is a value.** The LLM returns a plan — a list of tasks,
each naming one worker from a fixed set (ADR-0011). `route()` lets through
only worker names that exist. `next` is a list of worker names, not one.

**Not built: rules first for choosing the worker.** Every new question goes
to the LLM planner. There are no routing rules yet.

**Not built: the fallback log.** Planner calls are not logged, so there is no
fallback rate and no promotion of misses to rules.

Both unbuilt parts need data about real questions before rules can be
written. Tracing (Module 7) is the likely source of that data; when to build
the rules is not decided yet. Until then this ADR describes the target, and
this amendment describes the system.

