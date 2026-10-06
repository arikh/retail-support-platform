# retail-support-platform — Technical Design Document

**Status:** Living document · Modules 1–3 built and tested · Modules 4–8 planned
**Owner:** Arikh Akher
**Last updated:** 6 October 2026

This document describes the design. Where the design and the code differ, the
difference is marked **(planned)**. The README lists what is built and tested.

---

## 1. What we are building

A support platform for **retail pricing operations**, built on LangGraph. Its
users are internal pricing-operations teams, not shoppers. See
`docs/domain-and-requirements.md` for the domain.

A **supervisor** receives a question and plans it: which **specialist
workers** are needed, and what each one should be asked. Workers get their
facts from real data through tools and write their findings to a shared state
object. The supervisor reads the findings and decides in code what happens
next — run a worker, finish, or fail. A human approval step is planned.

The conversation is saved after every step, so it survives a crash and can
pause and resume.

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
- Human-in-the-loop approval for high-risk actions **(planned, Module 6)**
- Full observability: tracing, cost tracking, evaluation **(planned, Module 7)**
- Production hardening: auth, RBAC, streaming, Docker **(planned, Module 8)**

### Non-goals

- Not a chatbot demo
- Not a framework. We build one real solution properly. Shared framework
  extraction is deferred until patterns repeat across projects.
- No dynamic worker registration. Adding a worker is a deliberate
  architectural act, and it is allowed to cost a schema change.

---

## 3. Architecture

What is built today:

```
   ┌───────────────────────────────────────────────────────────────┐
   │                        LANGGRAPH                              │
   │                                                               │
   │   START ─▶ start_question ─▶ supervisor ─▶ finish_question ─▶ END
   │                                │   ▲                          │
   │                 route():       │   │  workers always          │
   │                 allowlist      ▼   │  return here             │
   │                          ┌──────────────┐                     │
   │                          │   support    │  planned workers    │
   │                          │   analysis   │  run together       │
   │                          └──────┬───────┘                     │
   │                                 │ tools (read-only)           │
   └─────────────────────────────────┼─────────────────────────────┘
                                     ▼
                          ┌─────────────────────┐
                          │      Postgres       │
                          │ pricing tables      │
                          │ checkpoints (schema)│
                          └─────────────────────┘
```

Planned around it: an API layer (FastAPI) in front, the `escalation` worker
and a human approval gate inside the graph, Redis for locks and cache, and
tracing (Langfuse or LangSmith).

### Nodes

| Node | Responsibility |
|---|---|
| `start_question` | Resets everything that belongs to one question (ADR-0013) |
| `supervisor` | Plans once with an LLM; applies the stop rules in code (ADR-0011) |
| `support` | Questions about one plan or material. Four tools. The rebuilt capstone agent |
| `analysis` | Patterns across many plans. Three tools |
| `finish_question` | Writes the answer into the conversation (ADR-0013) |
| `escalation` | Human handoff **(planned, Module 6)** |

Workers never call each other. All coordination goes through the supervisor.
All data goes through state.

### Inside a worker

A worker does two jobs in two calls (ADR-0012): an agent with tools finds the
facts and writes a text answer, then a second call with no tools turns that
text into the validated findings. A failure in either becomes an entry in
`errors`; a worker node never raises.

---

## 4. Memory model

This is the design. Today only **State** is in use; Context and Store are
**(planned)**.

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

As in `src/retail_support/state.py`:

```python
class SupportState(TypedDict):
    # conversation — kept across questions
    messages: Annotated[list[AnyMessage], add_messages]

    # control plane — supervisor owns these
    status: Literal["running", "awaiting_human", "done", "failed"]
    next: list[str]                    # workers to run now
    plan: dict[str, str] | None        # worker -> its question
    step_count: Annotated[int, operator.add]
    errors: Annotated[list[str], operator.add]
    pending_approval: PendingApproval | None

    # worker namespaces — one owner each
    support_findings: SupportFindings | None
    analysis_findings: AnalysisFindings | None
    escalation_findings: EscalationFindings | None
```

Everything except `messages` belongs to the question being answered now and
is reset by `start_question`. Earlier questions live in the checkpoint
history, not in state.

### Schema types

`TypedDict` for graph state — fast, native, no validation cost on every step.

Pydantic `BaseModel` for worker findings — validated at construction, inside the
worker, where LLM output actually enters and where the stack trace is useful.

Reason for the split: LangGraph only validates Pydantic state on input to the
first node, not on worker returns, and its recursive validation is slow. It
does not protect against the real risk, and it taxes every step.

### Schema freeze point

The schema was frozen in Module 2 (ADR-0009), because a saved checkpoint
holds the state shape and a later change becomes a data migration.

Module 3 changed it twice on purpose: `plan` was added and `next` became a
list (ADR-0011). Both changes were made before any real checkpoints were
saved, so nothing had to be migrated. From the Module 3 merge on, the freeze
applies again.

---

## 6. Supervisor routing

The supervisor runs these rules in order, in code:

```
1. errors in state            -> status failed, stop
2. every planned worker done  -> status done, stop
3. step_count over the limit  -> status failed, stop
4. no plan yet                -> ask the LLM once for the plan
5. plan is empty              -> status failed ("no worker matched"), stop
6. otherwise                  -> run the planned workers still pending
```

- The LLM plans; code stops. The model is never asked "are we done?".
- The plan is a list of tasks. Each names one worker from a fixed set and
  carries the question for that worker.
- `route()` is a separate allowlist gate. It lets through only worker names
  that exist, so a wrong value in `next` cannot move control anywhere new.
- An empty plan is the honest "I don't know" path. In Module 6 the same rule
  will send the request to a human.

**Target, not yet built (ADR-0004):** rules that choose the worker without an
LLM call for common questions, with every LLM fallback logged and reviewed.

Rejected alternatives: fixed pipeline (cannot adapt), swarm (no single place to
pause for human approval, no clean audit trail), hierarchical (unnecessary at
three workers).

Known cost: the supervisor is a bottleneck and a single point of failure.
Accepted for now.

---

## 7. Technology

| Layer | Choice | State |
|---|---|---|
| Language | Python 3.12, `uv`, `ruff` | in use |
| Orchestration | LangGraph `StateGraph` for the platform graph | in use |
| Worker tool loop | LangChain `create_agent`, inside each worker node | in use |
| Checkpoints | PostgreSQL (`AsyncPostgresSaver`), own schema | in use |
| Business data | PostgreSQL, read-only access through `db.py` | in use |
| Models | `ModelProvider.get(role=...)`; Groq, `openai/gpt-oss-120b` | in use, one provider |
| Tests | `pytest`, `pytest-asyncio`; no test calls a real LLM | in use |
| Locks + cache | Redis | planned |
| API | FastAPI | planned |
| Observability | Langfuse or LangSmith, OpenTelemetry | planned |
| Packaging, CI | Docker, GitHub Actions | planned |

---

## 8. Decision record index

| ADR | Decision |
|---|---|
| 001 | Rebuild, not refactor. Capstone archived as read-only reference. |
| 002 | Per-worker state namespaces, not a shared findings list. Ownership over extensibility. |
| 003 | TypedDict for graph state, Pydantic for worker findings. |
| 004 | Hybrid routing — rules first, LLM fallback, fallbacks logged for review. Partly built; see its amendment. |
| 005 | Postgres as system of record; Redis ephemeral only (locks + cache). |
| 006 | PII handling and right-to-erasure — tokenize at ingestion, vault mapping. |
| 007 | Human-in-the-loop — pause as durable row; accept/reject/edit, expired on TTL. |
| 008 | Irreversibility barrier — no side effect before interrupt(). |
| 009 | Control-plane fields frozen into the state schema. |
| 010 | Concurrency safety — locking deferred to exactly-once operations. |
| 011 | The supervisor plans one question per worker and runs the workers together. |
| 012 | A worker finds facts with tools, then formats its findings in a second call. |
| 013 | Each question is opened and closed by its own node. |

---

## 9. Module roadmap

| # | Module | Delivers | State |
|---|---|---|---|
| 1 | State Contract & Service Boundaries | The state schema, worker interfaces | Built |
| 2 | Persistence & Memory Architecture | Postgres checkpoints, metadata and vault tables | Built (Redis not started) |
| 3 | Supervisor Topology & Worker Wrapping | Planner, stop rules, support and analysis workers on real data | Built |
| 4 | Checkpointing & Recovery | Crash recovery, resume, time travel | Planned. Per-question reset was built in Module 3 |
| 5 | Multi-Worker Orchestration | Parallel workers, `analysis` and `escalation` | Planned. Parallel workers and `analysis` were built in Module 3 |
| 6 | Human-in-the-Loop | `escalation` worker, approval gate, review surface | Planned |
| 7 | Observability & Cost | Tracing, cost tracking, eval dashboard | Planned |
| 8 | Production Hardening | Auth, RBAC, streaming, Docker | Planned |

Module lifecycle is strict, one at a time:
Architectural Concepts → Code Blueprint → Testing Suite → Interactive Challenge.

---

## 10. Open questions

Resolved questions live in their ADRs, not here. What remains open, tagged to
the module that closes it:

**Module 4 — checkpointing & recovery**
- Running the full platform graph on the Postgres checkpointer. So far it has
  run on the in-memory one; Postgres is tested on small graphs.
- Resume of a paused or crashed question in the full graph.

**Module 6 — human-in-the-loop**
- The reviewer surface: what a human sees, and what state must hold for it
  (the contents of `pending_approval`).
- Where code adds the `escalation` worker to a plan.

**Module 7 — observability & cost**
- Trace granularity, cost attribution, evaluation harness design.
- Whether routing rules and the fallback log (ADR-004) are built from traces.

**Not assigned to a module yet**
- One combined answer for a two-part question.
- Showing a partial answer when one of two workers fails.
- Filters (period, region) for the analysis tools.
- A second model provider.
