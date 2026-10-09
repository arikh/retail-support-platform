# Prompt Governance

How prompts are owned, changed, rolled back and audited in this repository.

Two words are kept apart here:

- **Prompt management** is the mechanics: prompts are files, each has a name and a
  version, and one function loads them. That part is built (ADR-0016).
- **Prompt governance** is the rules and the people: who owns a prompt, how it may
  change, what must be shown before a change is merged, and how to tell afterwards which
  prompt produced an answer. That part is this page.

A rule on this page is marked with how it is held today: by **code** (a test or a
database check fails if it is broken), by **convention** (a person must follow it), or
**not yet** (it needs something that is not built).

## The prompts

| Prompt | Used by | Owner | Live version |
|---|---|---|---|
| `routing_system` | The supervisor's planning call | Arikh | v1 |
| `support_system` | The support worker's agent | Arikh | v1 |
| `support_status_guide` | The support worker's formatting call | Arikh | v1 |
| `analysis_system` | The analysis worker's agent | Arikh | v1 |
| `analysis_status_guide` | The analysis worker's formatting call | Arikh | v1 |
| `format_findings` | The formatting call of both workers | Arikh | v1 |

The files are in `src/retail_support/prompts/`, named `<name>.<version>.txt`. The live
version of each prompt is set in `ACTIVE_VERSIONS` in
`src/retail_support/prompt_store.py`. That dict is the source of truth; this table is a
copy for the reader.

## The rules

| Rule | In this repository | Held by |
|---|---|---|
| **Ownership** | Every prompt has a named owner (the table above). The owner approves every change to it. | Convention. This is a one-person repository; there is no `CODEOWNERS` file. |
| **Standards** | A prompt holds instructions only: no secrets, no credentials, no personal data. A worker prompt says what the worker is for, that it must use its tools and never answer from memory, that it is read-only, and what to say when the data is missing. Plain text, no markdown. | Convention, checked by reading the pull request. No automated check. |
| **Change control** | A prompt changes only by pull request. A change is a **new version file**; a version file that has been merged is never edited. | Convention. Nothing detects an edit to a merged file. |
| **Evaluation gate** | The pull request shows what the change did: the same questions run on the old and the new version, with quality, cost and latency side by side. No run, no merge. | Not yet. The evaluation harness is not built. Until it is, the pull request shows one real run before and one after, with the rows from `llm_calls`. |
| **Rollout and rollback** | Old version files are kept. A rollback sets the prompt's entry in `ACTIVE_VERSIONS` back to the old version, by pull request. A new version goes live for every call at once. | Code, in part: a test loads every live version, so a missing file fails the suite. No rollback has been done yet, and there is no gradual rollout. |
| **Audit** | Every model call is recorded in the table `llm_calls` with the name and version of each prompt it used. | Code, when the logger is attached: a database check refuses a row with no prompt, and tests check that each call site names its prompts. No entry point attaches the logger yet. |
| **Security** | Tool output is data, never instructions. | Code, in part. See "Security" below. |

## Changing a prompt

1. Copy the live file to the next version, for example
   `support_system.v1.txt` to `support_system.v2.txt`. Edit the new file only.
2. Set that prompt's entry in `ACTIVE_VERSIONS` to the new version.
3. Run the questions the prompt affects on the old and the new version. Keep the
   answers and the rows from `llm_calls`.
4. Open a pull request with both sets of results and one sentence on why the prompt
   changed.
5. The owner reviews and merges. The old file stays in the repository.

## Rolling back

Set the prompt's entry in `ACTIVE_VERSIONS` back to the old version, by pull request.
It is a one-line change. The newer file stays, so the log rows that name it can still
be explained.

## Auditing

Which prompts and versions ran, and what the calls that used them cost:

```sql
SELECT p.key AS prompt, p.value AS version, count(*) AS calls,
       sum(cost_usd) AS cost_of_those_calls
FROM llm_calls, jsonb_each_text(prompts) AS p
GROUP BY 1, 2
ORDER BY 1, 2;
```

A call that used two prompts is counted under both, so this column does not add up to
the total cost.

Every call that used one prompt at one version:

```sql
SELECT created_at, thread_id, node, input_tokens, output_tokens, cost_usd
FROM llm_calls
WHERE prompts @> '{"support_status_guide": "v1"}'
ORDER BY created_at;
```

Cost by agent and by prompt set:

```sql
SELECT node, prompts, count(*) AS calls, sum(cost_usd) AS cost_usd
FROM llm_calls
GROUP BY node, prompts
ORDER BY cost_usd DESC;
```

A row leads to a thread, not to one question: a thread can hold many questions, and
the rows of one question are found by their time.

## Security

Prompt injection is one part of governance, not all of it. What the code does today:

- The supervisor's plan can name only workers from a fixed set, and `route()` lets
  through only names that exist. Text in a tool result cannot add a route.
- A worker's status is one value from a fixed set.
- The stop rules read only whether a worker's findings are filled. They do not read
  the text.
- Every tool is read-only. Text in a tool result cannot change pricing data.

What the code does not do:

- No prompt tells the model to treat tool output as data, and nothing filters tool
  output.
- Text in a tool result can still change the wording of an answer.
- Earlier answers stay in the conversation, and the planner reads the conversation.
  The planner also writes the question for each worker, and nothing checks that it kept
  the meaning.

The tools read our own seed data today. These gaps matter from the day a tool reads
text written by someone else: a document, a ticket, or a server we do not own.

## Not in place yet

- The evaluation harness, so the evaluation gate is a manual run.
- A check that a merged version file has not been edited.
- A second version of any prompt. No comparison and no rollback has been done.
- A gradual rollout of a new version.
- An entry point that attaches the logger to every request.
- A link from a log row to one question or one evaluation case.

See ADR-0016 for the design and for the numbers from the first logged runs.
