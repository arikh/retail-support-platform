# Retail Support Platform

A multi-agent support system for **retail pricing operations**, built on
LangGraph. A supervisor plans each question, specialist workers answer it from
real data in Postgres, and code — not the model — decides when the work is
done.

The users are internal pricing-operations teams. Their questions look like:

- What is the status of plan `SUMMER_LATAM_V2`?
- Which materials are missing from a plan, and what rule excluded them?
- Did a plan's prices reach the downstream systems?
- What are the most common rejection reasons across all plans?

The platform reads and explains. It never changes pricing data.

This is a ground-up rebuild of an earlier IITM Pravartak capstone prototype
(ADR-0001). The design decisions are recorded as ADRs in `docs/adr/`, and the
real bugs found on the way are recorded in [`INCIDENTS.md`](INCIDENTS.md).
Those two logs are as much the point of this repo as the code.

## Status

Modules 1 to 3 of 8 are built. "Built" here means: the code exists and a test
covers it.

### Built and tested

| Part | What it does | Tests |
|---|---|---|
| State contract | `TypedDict` graph state, Pydantic findings validated where LLM output enters (ADR-0003) | `tests/test_state.py` |
| Checkpointing | Postgres checkpoints; a paused run resumes from a new checkpointer instance | `tests/test_checkpointer.py` |
| Supervisor | Plans once with an LLM: which workers, and one question for each. Stop rules run in code: errors, plan complete, step limit (ADR-0011) | `tests/test_supervisor.py` |
| Routing gate | `route()` lets through only worker names that exist | `tests/test_supervisor.py` |
| Graph | Planned workers run together; one failing worker ends the run as `failed`; an off-topic question stops in one step | `tests/test_graph.py` |
| Question lifecycle | Every question starts clean and its answer is written back to the conversation (ADR-0013) | `tests/test_graph.py` |
| Workers | A tool-calling agent finds the facts, a second call formats the findings; failures become errors in state (ADR-0012) | `tests/test_workers.py`, `tests/test_agent_runner.py` |
| Support tools | Plan status, missing materials, downstream status, rejection reason | `tests/test_support_tools.py` |
| Analysis tools | Rejection reasons across plans, downstream summary, plan list | `tests/test_analysis_tools.py` |
| Data access | One read-only path to the pricing tables | `tests/test_db.py` |
| Model provider | Models are chosen by role behind one interface; Groq is the only provider | `tests/test_model_provider.py` |

No test calls a real LLM. The graph, supervisor and worker tests use fakes.
The tool, data-access and checkpointer tests need the local Postgres.

Behaviour with the real model is recorded as dated runs in `INCIDENTS.md`,
not as automated tests.

### Designed, not built

| Part | Where it is designed |
|---|---|
| Escalation worker and human approval | ADR-0007, ADR-0008 (Module 6) |
| PII tokenization and erasure (the vault table exists; no code uses it) | ADR-0006 |
| Redis locks and cache | ADR-0005, ADR-0010 |
| Rules-first worker choice and the fallback log | ADR-0004 (see its amendment) |
| Retrieval over the FAQ and policy corpus | `docs/domain-and-requirements.md` |
| Tracing, cost tracking, evaluation | Module 7 |
| API layer, auth, deployment | Module 8 |
| A second model provider | `ModelProvider` has the seam |

### Known limits

- The full graph has been run with the in-memory checkpointer only. The
  Postgres checkpointer is tested on small graphs, not yet on the full one.
- Checkpoints are loaded with an allowlist of the platform's own types
  (`checkpointer.py`). No test asserts that an unlisted type is refused.
- When one of two planned workers fails, the whole question is reported as
  failed. The other worker's answer is not shown.
- The answer to a two-part question is the two summaries one after the other.
  No step writes a single combined answer.
- A worker's status (`resolved`, `not_found`, `analyzed`, `bad_data`, ...) is
  chosen by a model that reads the answer text. It has been wrong before
  (INC-010).
- The analysis tools take no filters (period, region). A question about one
  quarter came back `bad_data` in real runs.
- The planner writes the question for each worker, so it could change the
  meaning. Nothing in code checks that.
- Everything is proven on one provider and one model
  (Groq, `openai/gpt-oss-120b`).

## How a question flows

```
START
  │
  ▼
start_question      resets what belongs to one question
  │
  ▼
supervisor  ◀────────────────┐   1. errors?              → failed
  │                          │   2. plan complete?       → done
  │ route(): allowlist       │   3. too many steps?      → failed
  ├──▶ support  ─────────────┤   4. no plan yet?         → ask the LLM once
  ├──▶ analysis ─────────────┘   5. run the workers still pending
  │
  ▼
finish_question     writes the answer into the conversation
  │
  ▼
END
```

- The LLM plans; code decides when to stop. The model is never asked "are we
  done?".
- Workers never call each other. They write only their own findings field.
- A worker name is a value from a fixed set. Free text never reaches a
  routing decision.

## Run it

You need Python 3.12, [`uv`](https://docs.astral.sh/uv/) and Docker.

```bash
uv sync
docker compose up -d
```

Create a `.env` file in the repo root. The database user and password are the
development values from `docker-compose.yml`:

```
GROQ_API_KEY=your-key
DATABASE_URL=postgresql://retail:retail_dev_pw@localhost:5432/retail_support?options=-csearch_path%3Dcheckpoints
APP_DATABASE_URL=postgresql://retail:retail_dev_pw@localhost:5432/retail_support
```

`DATABASE_URL` is for the checkpoint tables, which live in their own schema.
`APP_DATABASE_URL` is for the pricing tables.

Create the tables and load the sample data, then the checkpoint tables:

```bash
for f in sql/*.sql; do
  docker exec -i retail-postgres psql -U retail -d retail_support < "$f"
done
uv run python scripts/init_db.py
```

Run the tests:

```bash
uv run pytest
```

Ask a question (this calls the real model):

```python
import asyncio

from langchain_core.messages import HumanMessage

from retail_support.graph import graph


async def main():
    question = "What is the status of plan SUMMER_LATAM_V2?"
    result = await graph.ainvoke({"messages": [HumanMessage(question)]})
    print(result["messages"][-1].content)


asyncio.run(main())
```

## Stack

In use: Python 3.12 · LangGraph · LangChain (`create_agent`) · Pydantic ·
PostgreSQL · psycopg · Groq · `uv` · `ruff` · `pytest`

Planned: Redis · pgvector · FastAPI

## Layout

    src/retail_support/
      state.py              # the state contract
      graph.py              # the wiring
      supervisor.py         # planner, stop rules, route()
      start_question.py     # opens a question (reset)
      finish_question.py    # closes a question (answer)
      support_worker.py     # support worker and its prompts
      analysis_worker.py    # analysis worker and its prompts
      agent_runner.py       # shared: run the agent, format the findings
      support_tools.py      # 4 tools on the pricing tables
      analysis_tools.py     # 3 tools on the pricing tables
      db.py                 # read-only data access
      checkpointer.py       # Postgres checkpointer
      model_provider.py     # models by role
      config.py             # step limits
    sql/                    # table definitions and sample data, in order
    scripts/init_db.py      # creates the checkpoint tables
    tests/                  # no test calls a real LLM
    docs/adr/               # architecture decision records
    docs/                   # domain and technical design
    INCIDENTS.md            # real bugs: symptom, cause, fix, numbers

## Decision log

| ADR | Decision |
|---|---|
| 0001 | Rebuild rather than refactor the capstone prototype |
| 0002 | Per-worker state namespaces, not a shared findings list |
| 0003 | TypedDict for graph state, Pydantic for worker findings |
| 0004 | Hybrid supervisor routing — rules first, LLM fallback (partly built) |
| 0005 | Postgres as system of record, Redis for ephemeral coordination |
| 0006 | PII handling and right-to-erasure |
| 0007 | Human-in-the-loop control |
| 0008 | Irreversibility barrier (side-effect placement) |
| 0009 | Control-plane fields frozen into the state schema |
| 0010 | Concurrency safety — locking deferred to exactly-once operations |
| 0011 | The supervisor plans one question per worker and runs them together |
| 0012 | A worker finds facts with tools, then formats its findings in a second call |
| 0013 | Each question is opened and closed by its own node |

## Incident log

[`INCIDENTS.md`](INCIDENTS.md) records every real bug found while building:
what happened, why, what changed, and the numbers before and after. Twelve so
far, all from Module 3.
