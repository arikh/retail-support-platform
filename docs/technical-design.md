# retail-support-platform — Technical Design Document

**Status:** Living document · Architecture phase closed (ADRs 001–008) · Module 2 (persistence) in progress
**Owner:** Arikh Akher
**Last updated:** 21 August 2026

---

## 1. What we are building

A production-grade retail customer-support platform built on LangGraph.

A **supervisor agent** receives a customer request and decides which **specialist
worker** should handle it. Workers do the work and write their findings to a
shared state object. The supervisor reads the findings and decides what happens
next — another worker, a human approval, or finish.

The conversation is saved after every step, so it survives a crash and can pause
for hours waiting for a human.

### Why this project exists

Two goals, served by one build:

1. Master Agentic AI at architecture depth, not tutorial depth.
2. Produce evidence of AI Architect capability for job search and enterprise
   credibility.

Architects are judged on decisions, not code. Every significant decision becomes
an ADR in `docs/adr/`.

---

## 2. Goals and non-goals

### Goals

- Multi-agent orchestration with a supervisor and specialist workers
- Durable state — a paused conversation survives a process restart
- Human-in-the-loop approval for high-risk actions such as refunds
- Full observability: tracing, cost tracking, evaluation
- Production hardening: auth, RBAC, streaming, Docker

### Non-goals

- Not a chatbot demo
- Not a framework. We build one real solution properly. Shared framework
  extraction is deferred until patterns repeat across projects.
- No dynamic worker registration. Adding a worker is a deliberate
  architectural act, and it is allowed to cost a schema change.

---

## 3. Architecture

```
            ┌────────────────────────────────────────────┐
            │  API layer (FastAPI)                       │
            │  auth · tenant resolution · streaming      │
            └───────────────────┬────────────────────────┘
                                │ invoke(state, context)
                                ▼
   ┌───────────────────────────────────────────────────────────────┐
   │                        LANGGRAPH                              │
   │                                                               │
   │                   ┌──────────────┐                            │
   │             ┌────▶│  supervisor  │  rules first,              │
   │             │     └──────┬───────┘  LLM on miss               │
   │             │            │ writes next                        │
   │             │  ┌─────────┼──────────┬──────────┐              │
   │             │  ▼         ▼          ▼          ▼              │
   │             │ support  analysis   escalation  human_gate      │
   │             │  │         │          │          │              │
   │             └──┴─────────┴──────────┴──────────┘              │
   │                                                               │
   └───────────────────────────────────────────────────────────────┘
         │                    │                       │
         ▼                    ▼                       ▼
   ┌───────────┐      ┌──────────────┐        ┌──────────────┐
   │  Postgres │      │    Redis     │        │  LangSmith / │
   │checkpoints│      │locks + cache │        │   Langfuse   │
   └───────────┘      └──────────────┘        └──────────────┘
```

### Workers

| Worker | Responsibility |
|---|---|
| `support` | Order lookup, policy questions, RAG over the support corpus. This is the migrated capstone agent. |
| `analysis` | Structured data questions — order history, spend patterns, trends |
| `escalation` | Human handoff, refund preparation, complaint routing |

Workers never call each other. All coordination goes through the supervisor.
All data goes through state.

---

## 4. Memory model

Three places to put a fact. The choice is decided by one question: **how long
must this fact live?**

| | Context | State | Store |
|---|---|---|---|
| Set by | Caller, at invoke time | Nodes, during the run | Nodes, explicitly |
| Changes during run | Never | Constantly | Rarely |
| Persisted | No | Yes, every step | Yes, separately |
| Lifetime | One call | One conversation | Forever |
| Examples | `tenant_id`, `customer_id`, auth roles, DB handle, model config | `messages`, `next`, worker findings, `pending_approval` | Past resolutions, customer preferences |

Rule of thumb: **Store holds facts about the customer. State holds facts about
the conversation.**

---

## 5. State design

### The four rules

1. Each fact lives in exactly one place — context, state, or store — chosen by
   required lifetime.
2. Each worker owns its own field. **One writer per field.**
3. The reducer declares who may write concurrently. Default `replace` means
   exactly one writer per step. `add` means any number may write at once.
4. Validation happens where LLM output enters the system, not at the graph
   layer.

### Shape

```python
class SupportState(TypedDict):
    # conversation
    messages: Annotated[list, add_messages]

    # control plane — supervisor owns these
    next: str | None
    status: Literal["running", "awaiting_human", "done", "failed"]
    step_count: Annotated[int, operator.add]
    errors: Annotated[list[str], operator.add]
    pending_approval: ApprovalRequest | None

    # worker namespaces — one owner each
    support_findings: SupportFindings | None
    analysis_findings: AnalysisFindings | None
    escalation_findings: EscalationFindings | None
```

Field names are provisional. **The four rules are not.**

### Schema types

`TypedDict` for graph state — fast, native, no validation cost on every step.

Pydantic `BaseModel` for worker findings — validated at construction, inside the
worker, where LLM output actually enters and where the stack trace is useful.

Reason for the split: LangGraph only validates Pydantic state on input to the
first node, not on worker returns, and its recursive validation is slow. It
does not protect against the real risk, and it taxes every step.

### Schema freeze point

Schema changes are free until **Module 2**, when Postgres checkpointing lands.
After that, paused conversations hold the old shape serialized in the database,
and a change becomes a data migration.

---

## 6. Supervisor routing

Hybrid, rules-first:

```
decision = rules.match(state)          # cheap, deterministic, testable
if decision is None:
    decision = llm.decide(state)       # flexible fallback
    log_fallback(state, decision)      # every miss is recorded
return {"next": decision}
```

- The routing decision is always a **value**, never prose.
- Fallback rate is a tracked metric. A rising rate means the rules went stale.
- Logged fallbacks are reviewed by a human and promoted to rules deliberately.
  Promotion is a policy change, not an automatic cache write-back.

Rejected alternatives: fixed pipeline (cannot adapt), swarm (no single place to
pause for human approval, no clean audit trail), hierarchical (unnecessary at
three workers).

Known cost: the supervisor is a bottleneck and a single point of failure.
Accepted for now.

---

## 7. Technology

| Layer | Choice |
|---|---|
| Language | Python 3.12, `uv`, `ruff` |
| Orchestration | LangGraph (`StateGraph`, not prebuilts) |
| API | FastAPI |
| Checkpoints | PostgreSQL |
| Locks + cache | Redis |
| Models | Provider abstraction with fallback — `ModelProvider.get(role=...)` |
| Observability | LangSmith / Langfuse, OpenTelemetry |
| Packaging | Docker |
| CI | GitHub Actions |

---

## 8. Decision record index

| ADR | Decision |
|---|---|
| 001 | Rebuild, not refactor. Capstone archived as read-only reference. |
| 002 | Per-worker state namespaces, not a shared findings list. Ownership over extensibility. |
| 003 | TypedDict for graph state, Pydantic for worker findings. |
| 004 | Hybrid routing — rules first, LLM fallback, fallbacks logged for review. |
| 005 | Postgres as system of record; Redis ephemeral only (locks + cache). |
| 006 | PII handling and right-to-erasure — tokenize at ingestion, vault mapping. |
| 007 | Human-in-the-loop — pause as durable row; accept/reject/edit, expired on TTL. |
| 008 | Irreversibility barrier — no side effect before interrupt(). |

---

## 9. Module roadmap

| # | Module | Delivers |
|---|---|---|
| 1 | State Contract & Service Boundaries | The state schema, worker interfaces |
| 2 | Persistence & Memory Architecture | Postgres checkpoints, Redis locks + cache. **Schema freezes here.** |
| 3 | Supervisor Topology & Worker Wrapping | Routing, capstone agent migrated to `support` |
| 4 | Checkpointing & Recovery | Crash recovery, resume, time travel |
| 5 | Multi-Worker Orchestration | Parallel workers, `analysis` and `escalation` |
| 6 | Human-in-the-Loop | Approval gate, review surface |
| 7 | Observability & Cost | Tracing, cost tracking, eval dashboard |
| 8 | Production Hardening | Auth, RBAC, streaming, Docker |

Module lifecycle is strict, one at a time:
Architectural Concepts → Code Blueprint → Testing Suite → Interactive Challenge.

---

## 10. Open questions

Resolved architecture questions now live in their ADRs, not here: Redis role
(ADR-005), PII retention in checkpoints (ADR-006), pause and resume mechanics
(ADR-007, ADR-008). What remains genuinely open, tagged to the module that
closes it:

**Module 2 — persistence & memory**
- What a checkpoint contains, and how resume reconstructs a run
- Thread identity — how a conversation is addressed for checkpointing

**Module 6 — human-in-the-loop**
- The reviewer surface: what a human sees, and what state must hold for it
  (the `pending_approval` object — decided at the schema freeze, Module 2)

**Module 7 — observability & cost**
- Trace granularity, cost attribution, evaluation harness design
