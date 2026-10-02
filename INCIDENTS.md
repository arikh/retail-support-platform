# Incidents

Real bugs, failures, and surprises found while building this platform.
Each entry: what happened, why, what changed, and the numbers.

| ID | Title | Module | Status |
|---|---|---|---|
| INC-001 | Supervisor never stopped | 3 | Fixed |
| INC-002 | Run ended but status still said `running` | 3 | Fixed |
| INC-003 | Compound question only half answered | 3 | Open |
| INC-004 | Model invented an answer for a plan that doesn't exist | 3 | Open |
| INC-005 | Worker crashed when the model refused to fill the schema | 3 | Open |

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
**Status:** Open (fix planned)

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
Planned:
- Build the 5 support tools against real Postgres data (Module 3, B4).
- Add a test: an unknown plan must return `not_found`, never `resolved`.

### Before / after
| Metric | Before | After |
|---|---|---|
| Unknown plan → status | `resolved` (fabricated) | — |
| Expected | `not_found` | — |

### Lesson
Structured output guarantees the **shape** of an answer, not its **truth**.
An agent without grounding will still fill every field.

---

## INC-005 · Worker crashed when the model refused to fill the schema

**Date:** 2026-10-01
**Module:** 3 · Supervisor Topology & Worker Wrapping
**Status:** Open (fix planned)

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
Planned, with the B4 support tools:
- Give each worker a system prompt that defines when to use `not_found`
  (support) and `bad_data` (analysis).
- Ground workers in real tool data so "no data" becomes an explicit result,
  not a guess.
- Decide whether `tool_use_failed` deserves one retry before failing.

### Before / after
| Metric | Before | After |
|---|---|---|
| Result on "no data" | crash (`tool_use_failed`) or fabricated answer | — |
| Expected | `not_found` / `bad_data` | — |
| Steps to stop on worker error | 3 (errors rule worked) | — |

### Lesson
Structured output forces an answer's shape, but gives the model no honest
way out unless the schema and prompt define one. Missing "I don't know"
paths turn honesty into crashes — or into fabrication.

---