# Incidents

Real bugs, failures, and surprises found while building this platform.
Each entry: what happened, why, what changed, and the numbers.

| ID | Title | Module | Status |
|---|---|---|---|
| INC-001 | Supervisor never stopped | 3 | Fixed |
| INC-002 | Run ended but status still said `running` | 3 | Fixed |
| INC-003 | Compound question only half answered | 3 | Fixed |
| INC-004 | Model invented an answer for a plan that doesn't exist | 3 | Fixed |
| INC-005 | Worker crashed when the model refused to fill the schema | 3 | Fixed |
| INC-006 | Old question answered again in the same conversation | 3 | Fixed |
| INC-007 | Groq rejected JSON mode together with tools | 3 | Fixed |
| INC-008 | Model misspelled the findings tool name; retry did not help | 3 | Fixed |
| INC-009 | Worker returned nothing and the supervisor silently ran it again | 3 | Fixed |
| INC-010 | A correct finding about failures was labelled `bad_data` | 3 | Fixed |
| INC-011 | Each worker got the whole question; two prompt fixes failed | 3 | Fixed |
| INC-012 | Tool said a priced material was both priced and not priced | 3 | Fixed |
| INC-013 | RAGAS installed but could not be imported | Piece 3 | Removed |

---

## INC-001 · Supervisor never stopped

**Date:** 2026-09-27
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
A single analysis question ran until the loop breaker fired. The classifier
chose `analysis` on every supervisor visit.

```
next: analysis
step_count: 11
errors: []
status: running
```

### Cause
Two gaps together:
1. The routing classifier could only answer `support` or `analysis` —
   it had no way to say "done", so every supervisor visit sent work out again.
2. Workers wrote results to their findings fields, but the supervisor only
   read `messages`. It saw the same question every turn and made the same
   decision every turn.

The only way out was the max-steps safety net.

### Fix
- Supervisor checks facts in code **before** calling the LLM, in order:
  errors → `failed`, findings filled → `done`, max steps → `failed`.
  The LLM only classifies when no rule matches. (commit `010e64b`)
- `support_worker` now writes structured `support_findings`, so both
  workers produce a result the supervisor can check. (commit `849d870`)

### Before / after
| Metric | Before | After |
|---|---|---|
| Graph steps | 11 | 3 |
| LLM calls | 11 | 2 |
| Stopped by | safety net | work completed |

### Lesson
"Is the work done?" is a fact, not a judgement — code decides it, never the
model.

---

## INC-002 · Run ended but status still said `running`

**Date:** 2026-09-27
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
The graph had finished, but the final state reported the run as still in
progress. Any caller trusting `status` would think the work was ongoing.

```
step_count: 11
status: running
```

### Cause
The max-steps stop lived in `route()`. `route()` is a conditional edge —
edges can only choose a direction, they cannot write state. So the run
stopped, but nothing updated `status`.

### Fix
Moved all stopping into the supervisor node, which owns `status` per the
state contract. Each stop rule writes the matching value: `done` or
`failed`. (commit `010e64b`)

### Before / after
| Metric | Before | After |
|---|---|---|
| Final `status` | `running` (wrong) | `done` (correct) |
| Where the stop happens | edge (`route`) | node (`supervisor`) |

### Lesson
Only nodes can write state, so the component that stops the run must be a
node. A stop that can't record why it stopped leaves state lying.

---

## INC-003 · Compound question only half answered

**Date:** 2026-09-27
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
A question with two parts — one for `support`, one for `analysis` — was
sent to `analysis` only. The run reported `done`. The analysis "summary"
just repeated the question instead of answering it.

Question: *"What is the status of plan P-100? What are the most common
rejection reasons across all our Q3 plans?"*

```
support_findings: None
analysis_findings: summary='Provide status of plan P-100 and most common rejection reasons across all Q3 plans.' status='analyzed'
status: done
```

### Cause
The stop rule is "any findings field filled → done". That quietly assumes
one question needs exactly one worker. The classifier can also return only
one label, so it can never ask for both workers.

### Fix
The supervisor now plans a list of workers and runs them together. The run
is `done` only when every planned findings field is filled.

**Proof:** `tests/test_supervisor.py::test_two_planned_workers_run_and_finish`
(both findings filled, `step_count: 4`, `status: done`).

**Note:** with the real LLM, this question now ends `failed`, because both
workers hit INC-005 (open). That is an honest failure, not a false `done`.

### Before / after
| Metric | Before | After |
|---|---|---|
| Workers run vs needed | 1 of 2 | 2 of 2 |
| Parts of the question answered | 1 of 2 | 2 of 2 in the test (fake workers); real run blocked by INC-005 |
| Reported `status` | `done` (wrong) | `done` only when both are filled; otherwise `failed` |

### Lesson
A stop rule encodes an assumption about the work. Test it with inputs that
break the assumption — not only the happy path.

---

## INC-004 · Model invented an answer for a plan that doesn't exist

**Date:** 2026-09-27
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
Asked about plan P-100. No such plan exists — there is no data and no tools
yet. The support worker still returned a confident answer marked `resolved`.

Question: *"What is the status of plan P-100?"*

```
support_findings: summary='Plan P-100 is currently active and on schedule with no pending issues.' status='resolved'
```

### Cause
The support worker has no tools and no data source yet. With nothing to
look up, the model filled the structured output from its imagination. The
schema allows `not_found`, but nothing forces the model to use it.

### Fix
The support worker now runs a tool-calling agent over real Postgres data
(four support tools, read-only connection). Its prompt says: always call a
tool, never invent, and say plainly when something is not found. The tools
return a clear "not found" sentence for an unknown plan or material.

**Proof:** in every real run on 2026-10-05, the P-100 question came back as
`not_found` with nothing invented. At tool level,
`tests/test_support_tools.py` checks that an unknown plan or material
returns "not found" for all four tools.

**Note:** there is no automated end-to-end test with a real LLM for this
question; the end-to-end evidence is the real runs.

### Before / after
| Metric | Before | After |
|---|---|---|
| Unknown plan → status | `resolved` (fabricated) | `not_found` |
| Source of the answer | the model's imagination | a tool reading Postgres |

### Lesson
Structured output guarantees the **shape** of an answer, not its **truth**.
An agent without grounding will still fill every field.

---

## INC-005 · Worker crashed when the model refused to fill the schema

**Date:** 2026-10-01
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
The compound question (plan P-100 status + Q3 rejection patterns) failed
with a provider error. The model's own reply, inside the error, was an
honest "I don't have this data — please share it."

```
support_findings: None
analysis_findings: None
errors: ["BadRequestError: Error code: 400 - {'error': {'message': 'Tool choice is required, but model did not call a tool', 'type': 'invalid_request_error', 'code': 'tool_use_failed', 'failed_generation': 'I'm not able to see the current details of plan P-100 or the rejection-reason data for your Q3 plans. Could you share the relevant information ...'}}"]
status: failed
```

The same question gave a made-up `analyzed` answer on an earlier run
(see INC-003). Same input, different behaviour across runs.

### Cause
Structured output works by forcing the model to call a "tool" that fills
the findings schema. The workers have **no system prompt**, so nothing
tells the model: "if you have no data, return `not_found` / `bad_data`."
With no data and no instruction, the model answered in plain text instead
of calling the tool, and Groq rejected the response (`tool_use_failed`).

### What worked
The supervisor's errors rule caught the worker error and stopped the run
at step 3 with `status: failed`. Before INC-001's fix, this would have
looped to the max-steps limit.

### Fix
Both workers now work the same way (support on 2026-10-05, analysis on
2026-10-06):
- Each has a system prompt and real tools, so "no data" is an explicit result
  (`not_found` for support, `bad_data` for analysis), not a refusal.
- Findings are no longer requested as a forced tool call. The agent writes a
  plain text answer; a second call with no tools turns it into findings with
  strict JSON output (see INC-008 and ADR-0012).
- A failed agent run is tried once more, then reported as an error in state.

**Proof:** real runs. The unknown plan P-100 came back `not_found` in every
run on 2026-10-05. The Q3 question came back `bad_data` in three runs on
2026-10-06, with no invented numbers. `tests/test_workers.py` checks, without
an LLM, that a failing agent or a failing formatting call becomes an error in
state and never a crash.

### Before / after
| Metric | Before | After |
|---|---|---|
| Support: result on "no data" | crash (`tool_use_failed`) or fabricated answer | `not_found` |
| Analysis: result on "no data" | crash or fabricated answer | `bad_data` |
| Steps to stop on worker error | 3 (errors rule worked) | 3 |

### Lesson
Structured output forces an answer's shape, but gives the model no honest
way out unless the schema and prompt define one. Missing "I don't know"
paths turn honesty into crashes — or into fabrication.

---

## INC-006 · Old question answered again in the same conversation

**Date:** 2026-10-04
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
Two questions were asked in one conversation (same `thread_id`, in-memory
checkpointer). The second question was only about rejection reasons, but the
supervisor planned both workers, and both workers answered the first question
(plan P-100) again.

Question 1: *"What is the status of plan P-100?"*
Question 2: *"What are the most common rejection reasons across all our Q3
plans?"*

```
messages so far: 2
plan: ['support', 'analysis']
step_count: 4
status: done
```

Expected for question 2: `plan: ['analysis']`, `step_count: 3`.

### Cause
`messages` keeps only the user's questions. Workers write their answers into
the findings fields, and those are cleared at the start of each new question.
Nothing writes the answer back into `messages`.

The planner and the workers read all of `messages`. They see question 1 with
no answer after it, so it looks like it is still open.

This was not visible before the checkpointer, because every run started with
an empty conversation.

### Fix
A new last node, `finish_question`, closes every question. It writes the
answer into `messages` as an AI message: the planned workers' summaries when
the run is `done`, a fixed sentence when it is `failed`. `route()` now sends
to `finish_question` instead of `END`. The planner prompt also says to plan
only for the latest user message.

**Proof:** the same two questions in one conversation (4 Oct 2026), and
`tests/test_supervisor.py::test_two_planned_workers_run_and_finish`, which
asserts the answer message.

**Note:** the real-LLM proof is a single run. The test checks the mechanism
without an LLM.

### Before / after
| Metric | Before | After |
|---|---|---|
| Workers planned for question 2 | 2 (expected 1) | 1 |
| `step_count` for question 2 | 4 (expected 3) | 3 |
| Old question answered again | yes | no |
| Messages after two questions | 2 | 4 |

### Lesson
Memory that keeps the questions but not the answers makes every old question
look open.

---

## INC-007 · Groq rejected JSON mode together with tools

**Date:** 2026-10-05
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
The first run of the support worker as a tool-calling agent failed on all
four test questions with the same provider error.

```
errors: ["BadRequestError: Error code: 400 - {'error': {'message': 'json mode cannot be combined with tool/function calling', 'type': 'invalid_request_error', 'param': 'response_format'}}"]
status: failed
```

### Cause
The agent was created with `response_format=SupportFindings`. Given a bare
schema, LangChain picks the method itself, and it picked the provider's JSON
mode. Groq does not allow JSON mode in the same request as tool calling.

### What worked
Every run stopped at step 3 with `status: failed` and the error in state.
No crash.

### Fix
First step: choose the method explicitly, `ToolStrategy(SupportFindings)`.
That answered 3 of 4 questions and exposed INC-008. The final design is the
split described there.

### Before / after
| Metric | Before | After |
|---|---|---|
| Test questions answered | 0 of 4 | 3 of 4 (then 4 of 4 after INC-008) |

### Lesson
A framework default that picks a method for you depends on the provider.
Choose the method explicitly, and prove it with a real call.

---

## INC-008 · Model misspelled the findings tool name; retry did not help

**Date:** 2026-10-05
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
With `ToolStrategy`, one question kept failing. The model had the right
answer but wrote the name of the findings tool wrongly, and Groq rejected
the reply.

Question: *"Why was M-1009 excluded from SUMMER_LATAM_V2?"*

```
errors: ["BadRequestError: Error code: 400 - ... attempted to call tool 'name=SupportFindings]' which was not in request.tools ... 'code': 'tool_use_failed' ..."]
status: failed
```

It failed in 2 of 3 runs. A retry (2 attempts) was added and the second
attempt made the same mistake.

### Cause
The findings were requested as one more tool call, next to the four real
tools. Nothing forces a model to spell a tool name correctly. The same input
at temperature 0 tends to give the same output, so a retry does little for
this kind of failure.

### Fix
Split the worker's two jobs:
1. The agent with tools finds the facts and writes a plain text answer.
2. A second call with no tools turns that text into the findings, using
   strict JSON output (`with_structured_output(..., method="json_schema")`).

Both live in `agent_runner.py` (`run_agent`, `to_findings`) and are shared by
the workers. The retry stays, for other kinds of failure.

**Proof:** the same question came back `resolved` in 3 of 3 runs after the
change. `tests/test_agent_runner.py` (4 tests, no LLM) covers retry, giving
up, an empty answer, and the strict JSON call.

**Cost:** one extra LLM call per worker run.

### Before / after
| Metric | Before | After |
|---|---|---|
| This question answered | 1 of 3 runs | 3 of 3 runs |
| Test questions answered | 3 of 4 | 4 of 4 |
| LLM calls per worker run | tool loop | tool loop + 1 |

### Lesson
If one step keeps failing the same way, a retry repeats the failure. Remove
the fragile step instead of repeating it.

---

## INC-009 · Worker returned nothing and the supervisor silently ran it again

**Date:** 2026-10-05
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
A question was answered correctly, but the run took 5 steps instead of 3.
No error was recorded.

```
question: What is the status of plan SUMMER_LATAM_V2?
step_count: 5
errors: []
status: done
```

At the same time a unit test failed with `DID NOT RAISE`.

### Cause
The first version of the retry helper did not raise after its last failed
attempt. The worker then returned no findings and no error. The supervisor
saw an empty findings field with no error, treated the worker as still
pending, and sent the question to it again.

### Fix
- `run_agent` raises the last real error when all attempts fail.
- An empty answer counts as a failed attempt.
- Tests: `test_run_agent_gives_up_after_all_attempts` and
  `test_run_agent_rejects_empty_answer`.

### Before / after
| Metric | Before | After |
|---|---|---|
| `step_count` for a one-worker question | 5 | 3 |
| Failed worker run recorded as an error | no | yes |

### Lesson
A step counter is also a detector. A right answer with an unexpected step
count means hidden work.

---

## INC-010 · A correct finding about failures was labelled `bad_data`

**Date:** 2026-10-06
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
The analysis worker found the right plan, but the findings carried the wrong
status. The count was also missing from the answer.

Question: *"Which plans have downstream failures?"*

```
analysis_findings: summary='SPRING_LATAM_2024 has downstream failures.' status='bad_data'
```

### Cause
The status is chosen by the formatting call, which reads the agent's text
answer and a short status guide. The guide described `bad_data` as data that
is "missing, not covered, or inconsistent". The answer contained the word
"failures", and the call read bad news as bad data. Nothing in the guide
separated the two.

### Fix
- The status guide now says that findings about problems (failures,
  rejections) are `analyzed`, and that the status says whether the question
  could be answered, not whether the news is good or bad.
- The worker prompt now says to include the numbers from the tools.

**Proof:** the same question came back `analyzed` with "2 failures" in the
two real runs after the change (2026-10-06). There is no automated test for
this: the label is chosen by an LLM.

### Before / after
| Metric | Before | After |
|---|---|---|
| Status for a finding about failures | `bad_data` | `analyzed` |
| Count in the answer | missing | 2 failures |

### Lesson
When a model picks a label, it reads the words, not the intent. Define each
label by what it means for the question, and say what it does not mean.

---

## INC-011 · Each worker got the whole question; two prompt fixes failed

**Date:** 2026-10-06
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
On a two-part question, the analysis worker also handled the part that
belonged to the support worker. Two prompt changes gave two different
failures.

Question: *"What is the status of plan SUMMER_LATAM_V2? What are the most
common rejection reasons across all plans?"*

First run — the prompt said to ignore the other part. The worker answered it
anyway, so the plan status appeared twice in the final answer:

```
analysis_findings: summary='Plan SUMMER_LATAM_V2 has status COMPLETED. Across all plans, the most common rejection reasons are: ...' status='analyzed'
```

Second run — the prompt said not to report a single plan's status. The worker
refused out loud, and the formatting call labelled a valid analysis `bad_data`:

```
analysis_findings: summary='I’m unable to provide the status of plan SUMMER_LATAM_V2. Across all plans, the most common rejection reasons are: ...' status='bad_data'
```

### Cause
Every planned worker received the user's whole message. This was the known
limit recorded in ADR-0011. A prompt can ask a model to ignore part of its
input, but it cannot remove that part.

### Fix
The planner now writes one question for each worker. `plan` changed from a
list of worker names to a mapping of worker → its question. Each worker's
agent receives the earlier conversation plus only its own question
(`worker_messages` in `agent_runner.py`). The "ignore the other part" rules
were deleted from both worker prompts.

Routing is unchanged: the worker name is still a fixed choice checked by
`route()`. The question text goes to the worker as input and never reaches a
routing decision.

**Proof:**
- Real runs (2026-10-06): the same question, 2 of 2 runs — the plan held two
  separate questions, the statuses were `resolved` and `analyzed`, and the
  analysis answer held only the rejection reasons.
- `tests/test_graph.py::test_two_part_question_gives_each_worker_its_own_part`
  checks, without an LLM, that each worker receives only its own question.

### Before / after
| Metric | Before | After |
|---|---|---|
| Input to each worker | the whole message | its own question |
| Plan status in the final answer | twice, or refused | once |
| Analysis status on the two-part question | `analyzed` or `bad_data` | `analyzed` (2 of 2 runs) |
| Rules in the worker prompts about the other part | 1 each | 0 |

### Lesson
If a model must not act on some text, do not show it that text. Two prompt
changes failed in two different ways; removing the input fixed both.

---

## INC-012 · Tool said a priced material was both priced and not priced

**Date:** 2026-10-06
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Fixed

### Symptom
Found in code review, not in a run. For a material that was priced,
`get_material_rejection_reason` returned two lines that contradict each other:

```
Material M-1001 (Winter Jacket XL) was successfully priced in plan 'SUMMER_LATAM_V2'.
Material M-1001 (Winter Jacket XL) was NOT priced.
Plan: SUMMER_LATAM_V2 | Reason: None | Expiry: 6 months
```

All 12 tool tests were green at the time.

### Cause
The tool was changed from "return on the first row" to "collect a line for
every row". The "not priced" line was left outside an `else`, so it was added
for every row, priced or not. The test for a priced material only checked that
the words "successfully priced" were present. It did not check that the
opposite words were absent.

### Fix
- The "not priced" line is now under `else`.
- The test also asserts that "NOT priced" is not in the result
  (`tests/test_support_tools.py::test_rejection_reason_priced_material`).

### Before / after
| Metric | Before | After |
|---|---|---|
| Lines for a priced material | 2, contradicting | 1 |
| Test catches the contradiction | no | yes |

### Lesson
A test that only checks for the right words passes when the wrong words are
there too. For an answer with two possible outcomes, assert the one you expect
and assert the other is absent.

---

## INC-013 · RAGAS installed but could not be imported

**Date:** 2026-10-10
**Module:** Piece 3 · Evaluation
**Status:** Removed (not fixed)

### Symptom
RAGAS was added to score how well an answer is supported by its passages
(faithfulness). `uv add --dev ragas` succeeded. The first import failed:

```
uv run python -c "import ragas; print(ragas.__version__)"
  File ".../ragas/llms/base.py", line 12, in <module>
    from langchain_community.chat_models.vertexai import ChatVertexAI
ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'
```

Installed versions: `ragas` 0.4.3, `langchain-community` 0.4.2.

### Cause
RAGAS imports a module from `langchain-community` at load time. The
`langchain-community` version that fits this platform's LangChain 1.x no
longer has that module. RAGAS declares no upper bound on the package, so the
resolver accepted the pair. The resolver reads what a package declares; it does
not run it.

This is the same kind of failure as the MCP adapter on 8 Oct (ADR-0014
amendment): a package that installs has only passed the resolver.

### Fix
None in this repository. RAGAS was removed the same day and the lock file was
restored:

```
git checkout pyproject.toml uv.lock
uv sync
```

Downgrading the platform's LangChain packages to suit an evaluation tool was
rejected: the platform runs on them.

The known way around it is a separate environment for evaluation. The platform
writes question, answer and passages to a file, and RAGAS reads that file with
its own, older LangChain. Not built here (ADR-0018).

### Before / after
| Metric | Before | After removal |
|---|---|---|
| `import ragas` | fails | not installed |
| Test suite | not run with RAGAS installed | 168 passed |
| Answer faithfulness scored | no | no |

### Lesson
Check that a new package can be imported before building on it, and run the
test suite after every install. An evaluation tool with heavy dependencies
belongs in its own environment, not in the environment of the system it
evaluates.
