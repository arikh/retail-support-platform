# ADR-0011: Supervisor plans a list of workers and runs them together

## Status
Accepted. Amends ADR-0004 and ADR-0009. Amended on 6 Oct 2026 (see the end).

## Context
INC-003 showed a gap. A question with two parts — one for `support`, one for
`analysis` — was sent to one worker only, and the run still reported `done`.

Two things caused it. The classifier could return only one worker name. And
the stop rule was "any findings field filled → done", which assumes one
question needs exactly one worker.

## Decision
1. The supervisor asks the LLM once for a list of workers and saves it in a
   new state field, `plan` (`list[WorkerName] | None`, overwrite,
   supervisor-owned). `None` means "not planned yet".

2. The planned workers run together. The supervisor writes the workers that
   still have an empty findings field into `next`, and `route()` returns that
   list, so LangGraph runs them in the same step.

3. The run is `done` only when every planned findings field is filled. Code
   checks this. The LLM is never asked "are we done?".

4. An empty plan means "no worker fits, or the model is unsure". The run stops
   with `failed` and the error `no worker matched`. The model is told not to
   guess. In Module 6 this same rule will send the request to escalation.

5. The LLM may pick only `support` and `analysis`. It never picks
   `escalation`; code will add it (Module 6).

`route()` stays an allowlist gate: it lets through only worker names that are
built, and returns `END` when none are left.

## Alternatives considered
- One worker per question, recorded as a known limit. Rejected: it reports
  success on half a job.
- After each worker, ask the LLM "anything left?". Rejected: the LLM would
  decide when to stop, and stopping must stay in code.
- Run planned workers one by one. Rejected: Module 5 would then change
  `route()`, the type of `next`, and the routing tests again.

## Consequences
- Gain: compound questions are handled; the LLM plans and code stops; the plan
  is in state, so it cannot change in the middle of a run and it survives a
  restart; an honest "I don't know" path costs one step and no worker call.
- Gain: parallel execution needed no new state design. Per-worker findings
  fields (ADR-0002) and the `operator.add` reducers on `step_count` and
  `errors` (ADR-0009) were already safe for workers writing at the same time.
- Cost: the state schema changed after the freeze in ADR-0009 — `plan` was
  added and `next` changed from `str` to `list[str]`. This was done before the
  graph is compiled with a checkpointer, so no saved checkpoints had to be
  migrated. ADR-0004 is amended the same way: `next` holds a list of worker
  names, not one.
- Cost: if one worker fails, the other has already run. One LLM call is wasted.
- Known limit: every planned worker receives the whole question, not only its
  own part.

## Proof
- Real runs (2 Oct 2026): one-part questions stop at `step_count: 3`, the
  two-part question at `step_count: 4`, an off-topic question at
  `step_count: 1` with `no worker matched`.
- `tests/test_supervisor.py::test_two_planned_workers_run_and_finish` — both
  findings filled, `step_count: 4`, `status: done`, no LLM call.

## Amendment — 6 Oct 2026: the plan holds one question per worker

The text above is the decision as made on 2 Oct. Two things have changed.

**1. `plan` is now `dict[str, str] | None`: worker → the question for that
worker.** The planner returns a list of tasks, each with a `worker` (a fixed
choice of `support` or `analysis`) and a `question` (text). The supervisor
builds the plan from them: an empty question is skipped, and two tasks for the
same worker are joined. Each worker's agent receives the earlier conversation
plus only its own question.

Why: the known limit above ("every planned worker receives the whole
question") caused real faults. See INC-011. Two prompt changes failed in two
different ways, so the cause was removed instead.

What did not change: the stop rule (every planned findings field filled),
running the planned workers together, and the allowlist in `route()`. The
question text is input for a worker. It is never read by a routing decision,
so "the model classifies, the code routes" still holds.

Risk accepted: the planner writes the questions, so it could drop a name or
change the meaning. The prompt tells it to use the user's own words and to
copy plan names and material IDs exactly. Code skips an empty question.
Nothing in code checks the meaning.

**2. `route()` sends the run to the `finish_question` node when no worker is
left, not to `END`.** See ADR-0013.

The known limit is closed. A new limit replaces it: when one planned worker
fails, the whole question is reported as failed, and the other worker's
answer is not shown to the user.

### Proof
- Real runs (6 Oct 2026): the two-part question, 2 of 2 runs — the plan held
  two separate questions, `step_count: 4`, statuses `resolved` and `analyzed`.
- `tests/test_graph.py::test_two_part_question_gives_each_worker_its_own_part`
- `tests/test_supervisor.py::test_planner_merges_duplicates_and_skips_empty`
- `tests/test_graph.py::test_one_worker_fails_and_the_run_ends_failed`

