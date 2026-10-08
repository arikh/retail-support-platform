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

Modules 1 to 3 of 8 are built, plus an MCP server over the support lookups.
The support worker can also act as an MCP host and load those lookups from
the server; that path is off by default.
"Built" here means: the code exists and a test covers it.

Tracing can be switched on for a single run (see "Tracing"). It has no test,
so it is not counted as built.

### Built and tested

| Part | What it does | Tests |
|---|---|---|
| State contract | `TypedDict` graph state, Pydantic findings validated where LLM output enters (ADR-0003) | `tests/test_state.py` |
| Checkpointing | Postgres checkpoints; a paused run resumes from a new checkpointer instance; the full graph keeps a conversation across instances | `tests/test_checkpointer.py`, `tests/test_graph.py` |
| Supervisor | Plans once with an LLM: which workers, and one question for each. Stop rules run in code: errors, plan complete, step limit (ADR-0011) | `tests/test_supervisor.py` |
| Routing gate | `route()` lets through only worker names that exist | `tests/test_supervisor.py` |
| Graph | Planned workers run together; one failing worker ends the run as `failed`; an off-topic question stops in one step | `tests/test_graph.py` |
| Question lifecycle | Every question starts clean and its answer is written back to the conversation (ADR-0013) | `tests/test_graph.py` |
| Workers | A tool-calling agent finds the facts, a second call formats the findings; failures become errors in state (ADR-0012) | `tests/test_workers.py`, `tests/test_agent_runner.py` |
| Support tools | Plan status, missing materials, downstream status, rejection reason. Plain functions, registered as agent tools | `tests/test_support_tools.py` |
| Analysis tools | Rejection reasons across plans, downstream summary, plan list | `tests/test_analysis_tools.py` |
| Data access | One read-only path to the pricing tables; each process chooses its database user | `tests/test_db.py` |
| MCP server | The same four support lookups as read-only MCP tools, running as their own database role (ADR-0014) | `tests/test_mcp_server.py` |
| MCP host | The support worker loads its four tools in-process (default) or from the MCP server over stdio, chosen by `SUPPORT_TOOL_SOURCE` (ADR-0014 amendment) | `tests/test_tool_source.py` |
| Model provider | Models are chosen by role behind one interface; Groq is the only provider | `tests/test_model_provider.py` |

No test calls a real LLM. The graph, supervisor and worker tests use fakes.
The tool, data-access, checkpointer and MCP tests need the local Postgres.
The MCP server tests talk to the server through an in-memory client: no
subprocess and no port. One test in `tests/test_tool_source.py` starts the
real server as a child process over stdio.

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
| Tracing on every request with the content rule enforced in code; cost tracking; evaluation | Module 7; ADR-0015 for the content rule |
| API layer, auth, deployment | Module 8 |
| A second model provider | `ModelProvider` has the seam |
| A deployed MCP server with sign-in; one MCP connection held for the life of the application | ADR-0014 (see its triggers and its amendment) |

### Known limits

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
- The MCP server has no sign-in and listens on `127.0.0.1` only. It is not
  deployed. Over HTTP it was tried with a client script only; that transport
  has no automated test. Stdio has one (`tests/test_tool_source.py`).
- Only the MCP server uses the restricted database role. The agent's own path
  still connects as the Postgres superuser `retail`, with read-only set per
  connection in `db.py` (ADR-0014).
- The limits of the MCP role (writes refused, `pii_vault` refused, 5-second
  statement timeout) were checked by hand with `psql`, not by a test.
- Tracing is switched on by hand, one command at a time. It was tried in two
  real runs; no test covers it. The rule about what may enter a trace
  (ADR-0015) is a convention: nothing in code enforces it.
- With the two hide switches on, a trace has no token counts. There is no
  per-call log yet, so such a run has no token numbers anywhere.
- On the MCP host path, every support question opens a new connection and
  starts the server as a new process: about 0.5 seconds each, measured once.
  A production host would keep one connection open for the life of the
  application; that needs an application entry point (Module 8).
- A wrong `SUPPORT_TOOL_SOURCE` does not stop the program at start. Each
  support question fails instead (`failed`, with the reason in `errors`), and
  the user sees only "I could not answer this question."
- The MCP host uses `langchain.mcp`, which is in beta and prints a warning
  when it loads.

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

You need Python 3.12, [`uv`](https://docs.astral.sh/uv/) and Docker. The MCP
Inspector also needs Node.js.

```bash
uv sync
docker compose up -d
```

Postgres is published on `127.0.0.1` only, so it cannot be reached from
another machine.

Create a `.env` file in the repo root. The database user and password are the
development values from `docker-compose.yml`. Choose your own password for the
MCP role (letters and digits only, because it sits inside a URL):

```
GROQ_API_KEY=your-key
DATABASE_URL=postgresql://retail:retail_dev_pw@localhost:5432/retail_support?options=-csearch_path%3Dcheckpoints
APP_DATABASE_URL=postgresql://retail:retail_dev_pw@localhost:5432/retail_support
MCP_DATABASE_URL=postgresql://retail_mcp_ro:your-mcp-password@localhost:5432/retail_support
```

`DATABASE_URL` is for the checkpoint tables, which live in their own schema.
`APP_DATABASE_URL` is for the pricing tables. `MCP_DATABASE_URL` is the
read-only role that the MCP server uses.

Create the tables, the sample data and the MCP role, then the checkpoint
tables:

```bash
for f in sql/*.sql; do
  docker exec -i retail-postgres psql -U retail -d retail_support < "$f"
done
uv run python scripts/init_db.py
```

Set the password of the MCP role to the one you put in `.env`. It is typed
here, not stored in a SQL file:

```bash
docker exec -it retail-postgres psql -U retail -d retail_support -c "\password retail_mcp_ro"
```

Run the command as written: `retail_mcp_ro` is the name of the role, not the
password. It asks for the new password twice, and nothing shows while you
type.

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

## The MCP server

The four support lookups are also offered as MCP tools, for hosts outside this
codebase (ADR-0014). By default the agent does not use MCP; it calls the same
functions in-process. There is one implementation, in `pricing_lookups.py`.

Open the server in the MCP Inspector (stdio):

```bash
uv run mcp dev src/retail_support/mcp_server.py
```

Serve it over Streamable HTTP on this machine, at `http://127.0.0.1:8000/mcp`:

```bash
uv run mcp run src/retail_support/mcp_server.py --transport streamable-http
```

Two small clients show both transports:

```bash
uv run python scripts/try_mcp_stdio.py     # starts the server itself
uv run python scripts/try_mcp_http.py      # needs the HTTP server running
```

The server has no sign-in. Do not expose it beyond this machine.

The support worker can also load its tools from this server, as an MCP host.
It starts the server itself over stdio, so no server needs to be running:

```bash
SUPPORT_TOOL_SOURCE=mcp uv run try_graph.py
```

The allowed values are `in_process` (the default) and `mcp`.
`scripts/try_mcp_host.py` loads the tools through the host library and times
one call and the whole connection.

## Tracing

Tracing is optional and off by default. It needs no code change: LangGraph
sends a trace to LangSmith, a hosted third-party service, when
`LANGSMITH_TRACING` is true.

Add a LangSmith API key to `.env`:

```
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=retail-support-platform
```

Switch tracing on for one command, on the command line. Keep
`LANGSMITH_TRACING` out of `.env`, so that the test suite does not send
traces:

```bash
LANGSMITH_TRACING=true uv run try_graph.py
```

A trace holds the prompts, the question, the tool results and the answers,
and all of it is stored on LangSmith's servers. Full traces are therefore for
seed data and questions typed by a developer only (ADR-0015). For anything
else, hide the content:

```bash
LANGSMITH_TRACING=true LANGSMITH_HIDE_INPUTS=true LANGSMITH_HIDE_OUTPUTS=true \
  uv run try_graph.py
```

That keeps the tree and the latency. It drops the inputs, the outputs and
the token counts.

One traced run on 8 Oct 2026 (one question, so one sample): 4 model calls,
2,404 tokens, 3.17 seconds. About 2.93 seconds were model time; the database
lookup took 0.06 seconds.

## Stack

In use: Python 3.12 · LangGraph · LangChain (`create_agent`) · Pydantic ·
PostgreSQL · psycopg · Groq · MCP Python SDK (`mcp` 2.3) · `langchain.mcp` (MCP host, beta) ·
`uv` · `ruff` · `pytest` · LangSmith (tracing, optional)

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
      pricing_lookups.py    # the 4 support lookups as plain functions
      support_tools.py      # registers the 4 lookups as agent tools
      mcp_server.py         # registers the same 4 lookups as MCP tools
      tool_source.py        # support tools: in-process or from the MCP server
      analysis_tools.py     # 3 tools on the pricing tables
      db.py                 # read-only data access; a process picks its database user
      checkpointer.py       # Postgres checkpointer
      model_provider.py     # models by role
      config.py             # step limits; allowed tool sources
    sql/                    # tables, sample data and the MCP role, in order
    scripts/init_db.py      # creates the checkpoint tables
    scripts/try_mcp_*.py    # small MCP clients: stdio, HTTP and the host library
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
| 0014 | The agent keeps in-process tools; an MCP server offers the same lookups to outside hosts (amended 8 Oct: the agent can also be an MCP host, off by default) |
| 0015 | Full-content traces for seed data only; tracing is off by default and switched on per command |

## Incident log

[`INCIDENTS.md`](INCIDENTS.md) records every real bug found while building:
what happened, why, what changed, and the numbers before and after. Twelve so
far, all from Module 3.
