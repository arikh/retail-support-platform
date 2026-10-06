# ADR-0012: A worker finds facts with tools, then formats its findings in a second call

## Status
Accepted

## Context
A worker must return a small, validated result (`SupportFindings` or
`AnalysisFindings`, ADR-0003) and it must get its facts from real data.

The first workers were one LLM call with no tools. They invented answers
(INC-004) or crashed when the model refused to fill the schema (INC-005).

Giving the worker tools and asking the same agent for the structured result
failed in two more ways on Groq with `openai/gpt-oss-120b`:
- Passing the schema directly made LangChain pick the provider's JSON mode,
  and Groq rejects JSON mode in a request that also has tools (INC-007).
- Asking for the result as one more tool call (`ToolStrategy`) let the model
  misspell the name of that tool. One question failed in 2 of 3 runs, and a
  retry repeated the same mistake (INC-008).

## Decision
A worker does two jobs in two separate calls.

1. **Find the facts.** An agent (`create_agent`) with the worker's tools and
   a system prompt. It returns a plain text answer. Its tool loop has its own
   step limit (`WORKER_RECURSION_LIMIT`).
2. **Format the findings.** One more call with no tools, using strict JSON
   output (`with_structured_output(schema, method="json_schema")`). It turns
   the text into the findings model, guided by a short status guide.

Both jobs live in `agent_runner.py` (`run_agent`, `to_findings`) and are
shared by the support and analysis workers.

Around them:
- **Retry.** `run_agent` tries the agent `WORKER_ATTEMPTS` times (2). This is
  safe because every tool only reads. An empty answer counts as a failure.
- **Errors go into state.** A worker node never raises. Any failure becomes
  an entry in `errors`, and the supervisor ends the run as `failed`.
- **Read-only data access.** Tools reach Postgres only through `fetch_all`
  in `db.py`, which sets every connection read-only. Values are passed as
  query parameters, never pasted into SQL text.
- **Tools never guess.** For an unknown plan or material a tool returns a
  clear "not found" sentence.

## Alternatives considered
- One agent that also returns the structured result. Rejected: INC-007 and
  INC-008.
- Retry alone. Rejected: the failure repeated on the second attempt.
- A hand-written tool loop. Rejected for now: `create_agent` gives a tested
  loop, and our own work belongs in the parts the framework does not provide
  (planning, stop rules, safety checks).
- Deciding the status in code from the tool output. Not done: the answer is
  free text. Worth revisiting if tools return structured results.

## Consequences
- Gain: the fragile step is gone. The question that failed in 2 of 3 runs
  passed in 3 of 3 after the split.
- Gain: the agent's tool calls and tool results stay inside the worker. Only
  the findings enter shared state.
- Cost: one extra LLM call for every worker run.
- Cost: the status is chosen by a model that reads text, so it can be wrong.
  It has been (INC-010, and one run in INC-011). The fixes were a clearer
  status guide and cleaner input. No automated test covers this choice.
- Limit: the analysis tools take no filters (period, region), so the worker
  answers `bad_data` for such requests instead of filtering.
- Limit: this is proven on one provider and one model. The JSON-mode and
  tool-name behaviour may differ elsewhere.

## Proof
- `tests/test_agent_runner.py` — retry, giving up, empty answer, the strict
  JSON call, and the messages a worker receives. No LLM.
- `tests/test_workers.py` — each worker returns findings, and turns an agent
  failure or a formatting failure into an error in state. No LLM.
- `tests/test_support_tools.py`, `tests/test_analysis_tools.py`,
  `tests/test_db.py` — the tools and the read-only connection, on Postgres.
- Real runs on 5 and 6 Oct 2026, recorded in INC-004, INC-005, INC-008,
  INC-010 and INC-011.
