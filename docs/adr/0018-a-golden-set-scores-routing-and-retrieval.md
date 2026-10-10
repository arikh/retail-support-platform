# ADR-0018: A Golden Set Scores Routing and Retrieval in Plain Code

## Status
Accepted

## Context

Until now, whether a change made the platform better or worse was judged by asking a few
questions by hand. Two decisions were waiting for something better:

- ADR-0017 kept the worker's policy tool on dense search because four questions could not
  say whether hybrid search was better.
- PROMPT_GOVERNANCE.md asks for the same questions to be run on the old and the new
  version of a prompt before a merge. There was no fixed set of questions to run.

The capstone left 10 evaluation cases (ADR-0001). Each has a question and a list of words
the answer should contain. They were written for a single agent, so they do not say which
worker should handle a question or which passage a search should find. Only one of the 10
is a policy question.

## Decision

A golden set is kept in the repository: a fixed list of questions, each with its expected
outcome. It is data, in evals/golden_set.json. Two things are scored against it, both in
plain code, with no model as judge.

The cases. 20 cases. TC001 to TC010 are the capstone's 10, with their ids and their
keywords kept. TC011 to TC020 are new: seven policy questions, one question for the
analysis worker, one two-part question and one off-topic question. Every case has
expected_workers, the workers the supervisor must plan, as a set; an empty list means the
question must be refused. A policy case also has expected_passages, the sections of the
policy files that answer it. Nine cases are policy cases.

The answer key. The expected values were written by reading the policy files and the seed
data, and approved before the first run. They were never taken from what the system
returned. A miss is a finding about the system; it is not a reason to change the key.

The scoring. Three functions in eval_metrics.py say what "correct" means:

- is_hit(rows, expected, k): one of the expected passages is among the first k rows a
  search returned. A passage is itself by its source and its heading. Any one expected
  passage is enough.
- rate(results): the share of cases that passed.
- same_workers(planned, expected): the planned workers and the expected workers are the
  same set.

The runner. scripts/run_golden_set.py has two parts.

- retrieval: for each policy case it runs the dense, the keyword and the hybrid search for
  3 passages and records the place of the first expected passage: 1, 2, 3 or a miss. It
  makes no LLM call.
- routing: for each case it calls the supervisor node once, with the state a question has
  when it reaches that node, and compares the plan with expected_workers. That is one LLM
  call for each case, and no worker runs. The per-call logger (ADR-0016) is attached, and
  each case has its own thread id (golden-<run>-<case id>), so the cost of a run and the
  rows of one case can be read from llm_calls.

Not scored: the text of an answer. The capstone's keywords are kept in the file and are
not checked. Whether an answer is supported by its passages needs a model as judge, and
that is not built here (see "Not built").

Alternatives considered:

- RAGAS inside the platform's environment, for answer faithfulness. Tried on 10 Oct 2026
  and removed the same day: it installed, and failed at import against the platform's
  langchain-community (INC-013). Downgrading the platform's LangChain for an evaluation
  tool was rejected.
- RAGAS in its own environment, reading questions, answers and passages that the platform
  writes to a file. Not rejected, not built. It is the known way around the clash.
- Checking answers by the capstone's keywords. Not built: it needs a full run of the graph
  for each case, and a keyword in an answer does not show that the answer is right.
- A hosted evaluation tool. Not considered for this slice: routing and retrieval need only
  a comparison with the key.

## Consequences

Shown by a run (10 Oct 2026, one run each).

Retrieval, 9 policy cases, place of the first expected passage:

| | Dense | Keyword | Hybrid |
|---|---|---|---|
| First (hit rate at 1) | 8 of 9 | 6 of 9 | 7 of 9 |
| In the first three (hit rate at 3) | 9 of 9 | 8 of 9 | 9 of 9 |

- Dense search alone was the best. Keyword search missed or ranked low the questions
  worded differently from the text (TC014, TC017, and TC015 at second place).
- Hybrid was not better than dense. In TC014 the right passage went from second place
  (dense) to third (hybrid), and in TC017 from first to second: a weak keyword list pulls
  a right passage down in the fusion.
- So the decision of ADR-0017 stands, now on a measurement: the worker's tool stays on
  dense search.
- The retrieval run makes no LLM call and gives the same result every time.

Routing, 20 cases: 17 planned the expected workers (0.85). The three misses:

- TC006 "Can you update the price of M-1009 to 100?" and TC016 "Can you start the pricing
  run again for the two items that were skipped?": an empty plan, where the support worker
  was expected. The planner refuses a request for an action itself. The user then gets
  the fixed "I could not answer this question." and not the worker's explanation, or the
  policy text that says who to contact.
- TC009 "Something is wrong with the system. Materials keep getting excluded even after
  fixes.": planned for the analysis worker, where the support worker was expected. Its
  real answer is escalation, which is not built (Module 6).
- All three misses are on the safe side: nothing was changed and nothing was invented. The
  cases that must be refused were refused (TC007, TC020), and the two-part question got
  both workers (TC019).
- Cost of the routing run, from llm_calls: 20 calls, 13,415 input tokens, $0.0036.

Covered by tests (168 in the suite, 20 of them new, none needs a database or a model):
the three scoring functions (14), and the golden set file (6): 20 cases with the same
fields, unique ids, every expected worker is a worker that is built, every expected
passage is a section of the policy files.

Not built:

- A score for the text of an answer: faithfulness to the passages, or correctness against
  a reference answer. No reference answers are written.
- A run of the whole graph for each case, and a check of the capstone's keywords.
- A run on every pull request, a stored history of runs, and a number below which a
  change is refused. The runner prints to the screen.
- Repeated runs to see how much the routing result varies.
- A new version of the routing prompt for the two action requests. It is the next change
  this set should gate.

Known gaps:

- 20 cases, 9 of them for retrieval, on a corpus of 16 passages. The retrieval result is
  true for this corpus; it says little about a large one.
- The routing result is one run, and a model does not return the same plan every time.
- The answer key was drafted and approved in one sitting by one person. No second person
  reviewed it.
- The key for TC009 is weak: with no escalation worker, no plan is fully right for it.
- A policy case scores a hit only on the passages named in the key. Another passage that
  also answers the question counts as a miss.
- The routing run builds the supervisor's input state by hand in the script. If
  start_question.py changes, the script must change with it; nothing checks that.
- The routing run calls the supervisor node directly, not through the graph. It measures
  the plan, not what the workers then do with it.

## Trigger

This ADR is revisited when any of these happens:

- A prompt changes. Then the routing run is done before and after, and both results go in
  the pull request (PROMPT_GOVERNANCE.md, the evaluation gate).
- The policy corpus or the search changes. Then the retrieval run is done again, and the
  decision to stay on dense search is checked again.
- Answer quality must be scored. Then RAGAS in its own environment, or a judge call
  written here, is built, and reference answers are written.
- The escalation worker is built (Module 6). Then the key for TC009 changes, and cases for
  approval and refusal by a human are added.
- An application entry point and a pipeline exist (Module 8). Then the set runs
  automatically and its results are stored.

## References
- ADR-0001 — rebuild rather than refactor (the 10 capstone cases)
- ADR-0011 — the supervisor plans one question per worker (what routing accuracy
  measures)
- ADR-0016 — the per-call log (the cost of a routing run)
- ADR-0017 — policy search, and its amendment on keyword and hybrid search
- INC-013 — RAGAS could not be imported next to the platform's LangChain
- PROMPT_GOVERNANCE.md — the evaluation gate
- evals/golden_set.json, golden_set.py, eval_metrics.py
- scripts/run_golden_set.py (the runs of 10 Oct 2026)
- tests/test_eval_metrics.py, tests/test_golden_set.py
- Build plan — Piece 3 (evaluation harness)
