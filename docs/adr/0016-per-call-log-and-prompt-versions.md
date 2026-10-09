# ADR-0016: Every Model Call Is Logged With Its Cost and Its Prompt Versions

## Status
Accepted

## Context

Two questions could not be answered from the platform's own data: what does one question
cost, and which prompt text produced an answer.

Cost. ADR-0015 allows full traces for seed data only. For anything else the two hide
switches are set, and then a trace has no token counts. That ADR says token and cost
numbers must come from our own log, in our own database. The log did not exist.

Prompts. The six prompts were strings inside four Python modules. A prompt could change in
the same commit as the code around it, and nothing recorded which text a model call had
used. A change in cost or in answer quality could not be tied to a prompt change.

One fact shaped the design. The call that formats a worker's findings is built from two
prompts joined together: the shared format prompt and that worker's status guide. So one
model call can use more than one prompt.

## Decision

Prompts are versioned files. Each prompt lives in
src/retail_support/prompts/<name>.<version>.txt. prompt_store.py loads a prompt by name
and returns its name, version and text. One dict in that module, ACTIVE_VERSIONS, says
which version of each prompt is live. It is code, not an environment variable: the live
version is part of a release and changes only by pull request.

Every model call writes one row to the table llm_calls in our own Postgres
(sql/006_llm_calls.sql). The row holds the LangChain run id, the thread id, the node, the
model, the prompts, the token counts, the latency and the cost. It holds no prompt text
and no answer text. So the table has no user content, and the rule of ADR-0015 does not
restrict it.

The row is written by a LangChain callback handler, LLMCallLogger. The caller attaches it
once, in the config of the graph call, and LangChain calls it at the start and at the end
of every model call inside that graph. This includes the calls inside a worker's tool
loop, which our own code never makes directly. The handler never raises: any failure is
written to the Python log and the answer continues.

Each place that calls a model names itself. It passes metadata with two keys, built by
call_metadata() in prompt_store.py: node (supervisor, support or analysis) and prompts.
There are three such places: the supervisor's planning call, the worker's agent, and the
formatting call. The formatting call is recorded under its worker's node, so that the
cost of a worker is the sum of all its rows.

prompts is one jsonb column that maps each prompt name to its version, for example
{"format_findings": "v1", "support_status_guide": "v1"}. A check in the table refuses a
row with no prompt. The first build used two text columns and joined the two names and
the two versions with "+". It was replaced on the same day, before the merge: a joined
string pairs a name with its version only by position, and finding "every call that used
this prompt at this version" needed string matching.

Cost is worked out in code when the row is written: tokens times a price table in
llm_prices.py, which records the date the prices were checked. The cost is stored in the
row, so a later price change does not rewrite old rows. Reasoning tokens are stored in
their own column but are already inside the output tokens, so they are not added again.

The run id is the primary key. A second row for the same model call is refused.

The log writes through APP_DATABASE_URL, with one short connection for each row. It does
not use db.py, whose connections are read-only on purpose. The MCP role has no grant on
the table.

Alternatives considered and rejected:

- Read tokens and cost from LangSmith traces. Rejected: the numbers would sit with a
  third party and disappear when the hide switches are set (ADR-0015).
- Log by hand inside each node. Rejected: three places to keep the same, and the model
  calls inside the agent's tool loop would be missed.
- Two text columns for prompt name and version. Built first, then replaced (see above).
- A second table with one row for each prompt of each call. Not rejected, not built: a
  call uses one or two prompts, and one jsonb column answers today's questions without a
  join.
- Prompts in a database table or in a hosted prompt registry. Not rejected, not built:
  files in git already give review, history and rollback.

## Consequences

Shown by a run (9 Oct 2026, try_graph.py with the logger attached, the question "What is
the status of plan SUMMER_LATAM_V2?", two runs):

- Four rows in each run: one for the supervisor (routing_system v1), two for the support
  agent (support_system v1), and one for the formatting call (format_findings v1 and
  support_status_guide v1).
- The token counts were the same in both runs: 2,044 input and 304 output. The cost was
  $0.000489 for the question, about $0.49 for 1,000 such questions. The supervisor's one
  call was 30% of it ($0.000148); the support worker's three calls were 70% ($0.000341).
- In the run where they were read, 142 of the 304 output tokens were reasoning tokens.
- Latency of the four calls: 860, 627, 662 and 567 milliseconds in the first run; 722,
  736, 526 and 755 in the second. The totals were 2,716 and 2,739.
- The thread id was set once, at the graph call, and reached all four rows.
- The cached-token count was 0 in every row.

Covered by tests (99 in the suite): the prompt store (13), the logger with a fake clock
and a fake writer (9), the price table and the writer (7, of which 4 need the local
Postgres), and one check at each call site that it sends its node and its prompts. No
test calls a real model.

Not built:

- No entry point attaches the logger. A caller must pass it in the config. Only
  try_graph.py did, by hand.
- A link from a row to one question or to one evaluation case. A row carries the thread
  id only, and a thread can hold many questions.
- A token budget for each node.
- A second version of any prompt, and the before-and-after comparison of two versions. A
  rollback has never been done.
- A row for a model call that failed. The logger only forgets such a call.
- Time and cost of tool calls and of database lookups. The log covers model calls only.
- Percentiles, a dashboard and alerts.

Known gaps:

- A model with no entry in the price table writes no row at all. The error goes to the
  Python log, and the token counts of that call are lost.
- A version file can be edited in place. Nothing detects it, and "v1" in the log would
  then mean two different texts.
- The price table is updated by hand.
- The latency is measured in our process. It includes the network and the provider's
  queue.
- The time the insert adds to each model call was not measured.
- The log connects as the Postgres superuser retail, like the agent's own path
  (ADR-0014).
- The key that carries cached tokens (input_token_details.cache_read) was never seen in a
  real reply. No call used the cache.
- Every number above comes from two runs of one question.

## Trigger

This ADR is revisited when any of these happens:

- A second provider or model is added. It needs a price entry first, or its calls are not
  logged. Its replies may also name tokens differently.
- An application entry point exists (Module 8). Then the logger is attached there, once,
  and the writer uses a connection pool.
- The evaluation harness is built. Then a row needs a case id.
- A prompt gets its second version. Then the comparison is run, and a check that a merged
  version file has not changed becomes worth building.
- Real traffic arrives. Then percentiles, a retention period for the table and a failed
  call's row are needed.

## References
- ADR-0012 — a worker finds facts, then formats its findings (the two-prompt call)
- ADR-0014 — in-process tools versus MCP (the superuser gap)
- ADR-0015 — what may enter a trace (token numbers must come from our own log)
- PROMPT_GOVERNANCE.md — the rules for changing a prompt
- sql/006_llm_calls.sql, prompt_store.py, llm_call_logger.py, llm_log.py, llm_prices.py
- try_graph.py (the two logged runs)
- Groq model page for openai/gpt-oss-120b (prices, checked 9 Oct 2026)
- LangChain reference — AsyncCallbackHandler
- Build plan — Piece 4 (cost, latency and prompt versions)
