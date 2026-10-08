# ADR-0015: What May Enter a Trace — Full Content for Seed Data Only

## Status
Accepted

## Context

The platform had no tracing. To see where time and tokens go inside one question, tracing
was switched on with LangSmith, a hosted service run by a third party. LangGraph sends
traces to it when the environment variable LANGSMITH_TRACING is true; no code change was
needed, and the langsmith package (0.11.1) was already installed.

The first real trace (one question, "What is the status of plan SUMMER_LATAM_V2?") showed
what a trace holds: the full system prompts, the user's question word for word, the tool
names, arguments and results (rows from the pricing tables), the answers, and the token
counts. All of it is stored on the third party's servers.

That matters because of ADR-0006. Its promise is that personal data is replaced by tokens
at ingestion and that erasure is one vault-row delete. Tokenization at ingestion is not
built yet, so a user's question reaches the model, and the trace, exactly as typed. A copy
of personal data in a trace store would sit outside the vault and would not be erased.

A second run with LANGSMITH_HIDE_INPUTS=true and LANGSMITH_HIDE_OUTPUTS=true showed what
the blunt protection costs: the tree and the latency stay, but the inputs, the outputs and
the token counts are all gone.

## Decision

Tracing is off by default. It is switched on for one command at a time, on the command
line (LANGSMITH_TRACING=true uv run ...). The switch is not written into .env, so the test
suite does not send traces.

Full-content traces are allowed only when both of these are true: the database holds seed
data, and the questions are typed by a developer.

Any run that carries real user input or real business data sets both hide switches
(LANGSMITH_HIDE_INPUTS and LANGSMITH_HIDE_OUTPUTS). Such a trace shows structure and
latency only.

Token and cost numbers must not depend on trace content. They will come from the
platform's own per-call log, stored in our own database (build plan, Piece 4).

Secrets and credentials never go into a prompt, so they never go into a trace.

LangSmith is the tool for this thin slice, not a platform commitment. The choice of
tracing tool for the full observability work stays open.

The rule we follow: a trace is a copy of the conversation in someone else's system; treat
it like any other copy of the data.

Alternatives considered and rejected:

- Trace everything, always. Rejected: it sends whatever a user types to a third party and
  breaks the erasure promise of ADR-0006.
- Never trace. Rejected: without a trace we cannot say which step is slow or which call
  spends the tokens. That is the question an operator asks first.
- Mask personal data with rules (the LangSmith anonymizer, regular expressions). Not
  rejected, not built: it keeps the content and the token counts, but a pattern only
  catches what it was written to catch, and it needs a client set up in code.
- Self-hosted tracing (for example Langfuse in our own infrastructure). Not rejected, not
  built: the data stays with us, at the price of one more service to run. Too large for
  this slice.

## Consequences

Shown by a run (8 Oct 2026, try_graph.py, one question each):

- Full trace: 4 model calls, 2,404 tokens, 3.17 seconds. About 2.93 seconds were model
  time; the database lookup took 0.06 seconds. The second visit to the supervisor made no
  model call. One call reported about 0.4 seconds of queue time at the provider.
- Trace with both hide switches: the tree and the latency (3.18 seconds) are visible; the
  inputs, the outputs and the token counts are not.
- With a wrong API key name in .env, sending failed with 401 and the question was still
  answered. A tracing failure did not break the run.

Not built:

- The per-call log. Until it exists, a run with the hide switches has no token numbers
  anywhere.
- Rule-based masking.
- Any check in code that the hide switches are set when real data is present.
- An automated test for tracing.

Known gaps:

- The rule is a convention. It depends on the person who runs the command. Nothing in the
  code enforces it.
- Each number above comes from one run. One run is one sample.
- LangSmith's retention period, storage region and deletion options were not reviewed.
- Run names (nodes, tools, model) are visible even with the hide switches. They are
  written in our code, not by users.

## Trigger

This ADR is revisited when any of these happens:

- Real user input first reaches the platform (an HTTP entry point or a deployment). Then
  the hide switches, or masking, must be enforced in code, not by convention.
- Tokenization at ingestion (ADR-0006) is built. Then prompts carry tokens instead of
  personal data, and full-content traces may become acceptable.
- The per-call log is built. Then the cost of the hide switches is known and small.
- The tracing tool for the full observability work is chosen.

## References
- ADR-0006 — PII vault (tokenization at ingestion, erasure)
- ADR-0014 — in-process tools versus MCP (the same idea: a rule in code is a sign, an
  enforced limit is a lock)
- try_graph.py (the two traced runs)
- LangSmith docs — "Trace LangGraph applications"
- LangSmith docs — "Prevent logging of sensitive data in traces"
- Build plan — stretch item "Tracing"; Piece 4 (per-call log)
