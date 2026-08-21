# Retail Support Platform

A production-grade multi-agent retail customer-support system built on
LangGraph — a supervisor agent orchestrating specialist workers over a shared,
typed state, designed for durable checkpointing, human-in-the-loop approval,
and end-to-end observability.

This is a ground-up rebuild of an earlier IITM Pravartak capstone prototype —
not a version bump, a distinct system. The prototype is archived read-only as
reference (ADR-001). Design decisions are recorded as ADRs under `docs/adr/`;
the decision log is the point of this repo as much as the code.

## Architecture at a glance

- **Supervisor + specialist workers.** One router over three workers
  (`support`, `analysis`, `escalation`). Workers never call each other — all
  coordination flows through the supervisor, all data through shared state.
- **Typed state contract.** `TypedDict` graph state; Pydantic findings
  validated at the LLM output boundary, not the graph layer (ADR-003).
- **Durable by design.** Postgres is the system of record — checkpoints,
  thread metadata, pgvector. Redis is ephemeral only: locks and hot-path
  cache, never a checkpointer (ADR-005).
- **Human-in-the-loop.** For high-blast-radius actions such as refunds, the
  graph pauses as a durable database row. Irreversible work sits behind the
  approval gate (ADR-007, ADR-008).
- **PII by design.** Personal data is tokenized at ingestion; a vault table
  holds the token-to-value mapping; erasure is a single vault-row delete
  (ADR-006).

## Status

Architecture phase closed — ADRs 001–008 accepted. Module 1, the state
contract (`src/retail_support/state.py`), is built and test-proven. Module 2
(persistence & memory) is in progress; the state schema freezes once Postgres
checkpointing lands.

There is no end-to-end runnable system yet, and that is deliberate (ADR-001):
shape before code. The platform is built one module at a time.

## Stack

Python 3.12 · LangGraph · Pydantic · PostgreSQL · Redis · FastAPI · `uv` · `ruff`

## Layout

```
src/retail_support/        # state contract (Module 1); services land per module
tests/                     # contract tests
docs/adr/                  # architecture decision records — the design log
docs/technical-design.md   # technical design document
```

## Decision log

The ADRs are the substance of this project. Start there:

| ADR | Decision |
|---|---|
| 001 | Rebuild rather than refactor the capstone prototype |
| 002 | Per-worker state namespaces, not a shared findings list |
| 003 | TypedDict for graph state, Pydantic for worker findings |
| 004 | Hybrid supervisor routing — rules first, LLM fallback |
| 005 | Postgres as system of record, Redis for ephemeral coordination |
| 006 | PII handling and right-to-erasure |
| 007 | Human-in-the-loop control |
| 008 | Irreversibility barrier (side-effect placement) |
