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

Architecture phase closed — ADRs 001–010 accepted. Module 1 (state contract,
`src/retail_support/state.py`) and Module 2 (persistence) are built and
test-proven: Postgres checkpointing via `AsyncPostgresSaver`, thread-metadata
and PII-vault tables, checkpoint-schema isolation, and tests covering
durability, resume-after-crash, and concurrent-writer behavior. The state
schema is frozen (ADR-0009). Module 3 (supervisor + first worker) is next.

There is no end-to-end runnable system yet, and that is deliberate (ADR-001):
shape before code. The platform is built one module at a time.

## Stack

Python 3.12 · LangGraph · Pydantic · PostgreSQL · Redis · FastAPI · `uv` · `ruff`

## Layout

    src/retail_support/        # state contract (Module 1); services land per module
    sql/                       # user-owned table DDL (metadata, PII vault)
    tests/                     # contract + persistence tests
    docs/adr/                  # architecture decision records — the design log
    docs/technical-design.md   # technical design document

## Decision log

The ADRs are the substance of this project. Start there:

| ADR | Decision |
|---|---|
| 0001 | Rebuild rather than refactor the capstone prototype |
| 0002 | Per-worker state namespaces, not a shared findings list |
| 0003 | TypedDict for graph state, Pydantic for worker findings |
| 0004 | Hybrid supervisor routing — rules first, LLM fallback |
| 0005 | Postgres as system of record, Redis for ephemeral coordination |
| 0006 | PII handling and right-to-erasure |
| 0007 | Human-in-the-loop control |
| 0008 | Irreversibility barrier (side-effect placement) |
| 0009 | Control-plane fields frozen into the state schema |
| 0010 | Concurrency safety — locking deferred to exactly-once operations |