# Retail Support Platform — Domain & Requirements

> Purpose of this doc: a single, stable reference for **what we are building and
> why**, in domain terms. Architecture decisions live in the ADRs; this doc holds
> the *problem*, the *domain*, and the *worker responsibilities* so future
> sessions don't re-derive them. Grounded in the capstone README (salvaged
> domain knowledge, ADR-0001) and the current platform README.

---

## 1. What this platform is

A **production-grade, multi-agent support system for retail pricing operations.**

It is a ground-up rebuild of an IITM Pravartak capstone prototype
(`retail-ai-support-agent`), archived read-only as reference (ADR-0001). This is
a distinct system, not a version bump — orchestration, state, and persistence
are rebuilt from explicit decisions, not inherited from a library default.

## 2. The domain — who we serve and what they ask

**Users:** internal **retail pricing operations teams** — not end shoppers.

**Their problem:** they field hundreds of repetitive, investigation-heavy
support requests a day. The answers are buried across multiple systems and
poorly documented. Typical questions:

- Why are materials **missing** from a pricing plan?
- What **rule caused an exclusion / rejection**?
- Did prices **propagate downstream**?
- What is the **status** of a given plan?

The platform answers these **safely, consistently, at scale — without modifying
any underlying data.** It reads and explains; it does not mutate pricing data
directly. Actions with real blast radius go through a human.

## 3. The three workers (specialists under one supervisor)

Coordination flows only through the supervisor; workers never call each other;
all data flows through shared typed state. Worker names match the frozen state
contract (`state.py`, ADR-0009).

### `support` — the everyday resolver
Answers the common pricing-ops questions using structured tools + grounded
retrieval (RAG) over the FAQ/policy corpus. This is the current single-agent
ReAct logic, becoming one worker under the supervisor.

**Salvaged tool concepts (5), to be rebuilt against the new state/persistence:**
- `get_plan_status` — status of a pricing plan
- `get_missing` — why materials are missing from a plan
- `get_downstream` — whether prices propagated downstream
- `get_rejection` — what rule caused an exclusion/rejection
- `escalate` — hand off unresolved/anomalous cases (becomes the escalation path)

Writes: `support_findings` (`summary`, `status: resolved | not_found | needs_escalation`).

### `analysis` — deeper data investigation
For questions a single tool lookup can't resolve: patterns across plans,
anomalies, multi-material breakdowns. Investigates the pricing **data**, not
just a single record.

Writes: `analysis_findings` (`summary`, `status: analyzed | bad_data`).
No human-in-the-loop dependency — architecturally independent, which is why it
is the clean **second worker** to build for real routing.

### `escalation` — human handoff (HITL)
When the agent cannot resolve a request or detects an anomaly, it escalates to a
**human developer/analyst**. This is the salvaged `escalate` concept promoted to
a real worker, gated by human-in-the-loop approval (ADR-007, ADR-008).

Writes: `escalation_findings` (`summary`, `status: approved | rejected | edited | expired`)
— note the statuses are **human decisions**; `expired` = no human response in time.

**Deferred to Module 6** with the HITL gate, `pending_approval`, and the
approval state model — do not build its real flow early (ADR-0001: don't build
on a data model we'll rip out).

## 4. Non-negotiables (Labs philosophy)

- Production-quality only; zero tutorial code.
- Every decision answers: *"why would an enterprise AI platform need this?"*
- Shape/architecture before code — never build features on a data model we'll
  later replace.
- Surface trade-offs, alternatives, failure modes; design as a top-tier company
  (Anthropic / Databricks / AWS) would.

## 5. Safety posture (carried from the capstone, hardened here)

- **Read, don't mutate.** Refuses to modify data or trigger system actions
  directly; high-blast-radius actions (e.g. refunds, overrides) go behind the
  HITL approval gate.
- **No fabrication.** Does not invent policies or pricing rules; grounded in RAG.
- **Escalate anomalies** to humans rather than guessing.
- **PII by design** (ADR-0006): personal data tokenized at ingestion; a vault
  table maps token→value; erasure is a single vault-row delete.
- **Loop prevention:** deterministic step-limit breaker in the supervisor shell
  (not model-controlled).

## 6. Security thesis (shapes the supervisor)

> You can't constrain what an LLM *says*, only what it can *do*. Security lives
> in the deterministic shell, never the model.

The supervisor's routing decision (`next`) is control flow and must never be
moved by untrusted text (user input, tool output, or worker findings). The
router reads only sanitized, finite-domain signals (allowlisted worker names);
worker free-text never reaches a routing decision.

## 7. Target stack

Python 3.12 · LangGraph · Pydantic · PostgreSQL (system of record, pgvector) ·
Redis (ephemeral: locks, cache — never a checkpointer, ADR-0005) · FastAPI ·
`uv` · `ruff`.

## 8. What is salvaged vs. rebuilt (ADR-0001)

| Salvaged (correctness independent of architecture) | Rebuilt (never truly decided before) |
|---|---|
| Domain knowledge (pricing-ops questions) | State model |
| Tool **concepts** (the 5 tools) | Agent wiring / orchestration |
| 10 evaluation cases | Persistence |
| RAG corpus | Supervisor routing |
