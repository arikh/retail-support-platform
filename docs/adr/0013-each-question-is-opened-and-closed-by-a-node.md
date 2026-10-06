# ADR-0013: Each question is opened and closed by its own node

## Status
Accepted

## Context
With a checkpointer, state is saved for the whole conversation. Without
care, the second question starts with what the first one left behind:

- An old `plan` and old findings. The supervisor would see "plan complete"
  and report `done` at once, with the old answer.
- A `step_count` that keeps growing across questions (3, 6, 9, ...) until it
  passes `MAX_STEPS` and fails a run that never looped.
- `step_count` and `errors` use `operator.add` (ADR-0009). Writing `0` or
  `[]` to them adds nothing; it does not clear them.

A second problem showed up once the reset worked (INC-006). `messages` kept
the user's questions but not the answers, so the planner and the workers saw
the first question as still open and answered it again.

## Decision
Two nodes frame every question.

1. **`start_question`** is the first node (`START → start_question →
   supervisor`). It resets everything that belongs to one question: `plan`,
   `next`, `status`, the findings fields, `pending_approval`, and — using
   LangGraph's `Overwrite` — `step_count` and `errors`. It does not touch
   `messages`. Callers send only the new message.

2. **`finish_question`** is the last node (`supervisor → finish_question →
   END`). It writes the answer into `messages` as an AI message: the planned
   workers' summaries when the run is `done`, a fixed sentence when it is
   `failed`.

State keeps "current truth only": the fields describe the question being
answered now. Earlier questions live in the checkpoint history.

## Alternatives considered
- A question tracker inside state (a list of past questions with their plans
  and answers). Rejected: the checkpoints already hold this, the field would
  grow without limit, and state would stop being "current truth only".
- Let the caller send the reset values with every message. Rejected: every
  caller must remember it, and one that forgets gets silent wrong answers.
- A custom reducer with a reset signal. Not needed: `Overwrite` is built in.
- Do not reset `step_count`; raise `MAX_STEPS` instead. Rejected: a limit
  that grows with the length of the conversation no longer catches loops.

## Consequences
- Gain: each question gets its own step budget, plan and findings, and the
  loop breaker still works inside a question.
- Gain: the conversation reads question, answer, question, answer, so a
  closed question looks closed to the model.
- A run that is paused or crashes and then resumes does not pass `START`
  again, so it is not reset. This follows from where the node sits; it is not
  tested yet in this graph (resume is tested on small graphs in
  `tests/test_checkpointer.py`).
- Cost: after a question ends, state no longer shows its findings once the
  next question starts. To see them, read the checkpoint history.
- Limit: the answer for a two-worker question is the two summaries joined
  with an empty line. There is no step that writes one combined answer.
- Limit: a `failed` question is closed with one fixed sentence. The reason
  stays in `errors` and is not shown to the user.

## Proof
- `tests/test_state.py::test_overwrite_resets_add_fields` — `Overwrite`
  replaces the value on the installed LangGraph version.
- `tests/test_graph.py::test_second_question_starts_clean_and_sees_the_first_answer`
  — two questions in one conversation, no LLM: fresh `step_count`, fresh
  plan, old findings cleared, four messages, and the planner sees the first
  answer.
- Real run (4 Oct 2026, INC-006): for the second question, the planned
  workers went from 2 to 1 and `step_count` from 4 to 3.
