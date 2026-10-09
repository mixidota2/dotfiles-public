# Fresh executor contract

Use a new isolated agent or process for each trial. The executor must not inherit
the creator's conversation, evaluation checklist, expected output, earlier
failures, or prior trial results.

## Dispatch prompt

Adapt only the bracketed values:

```text
Act as the executor for one realistic user request.

User request:
[scenario text]

Available inputs:
[paths, tools, and constraints that a real user would have]

Use the skill at [absolute or discoverable skill path] when its trigger applies.
Complete the request as far as the environment permits. Do not inspect evaluator
files under evals/ and do not ask for the expected answer.

Return:
1. The result or produced artifact paths.
2. A phase trace for Understanding, Planning, Execution, and Formatting.
3. Every unclear point as Issue / Cause / General Fix Rule.
4. Discretionary fill-ins, retry count and reasons, and uncompleted work.
```

For a no-skill baseline, omit the skill path and prevent access to the target
skill while keeping the scenario, model, tools, and all other inputs equal. Grade
both outputs independently against the same hidden checklist, then compute the
delta. Do not ask a judge which answer it merely prefers.

## Evaluator procedure

After the executor returns:

1. Inspect the actual output and artifacts.
2. Apply the hidden requirement checklist.
3. Mark each requirement `pass`, `fail`, or `unclear` and cite evidence.
4. Classify failures as routing, instruction, tool, environment, or evaluator
   defects.
5. Append the result to the ledger.

Apply both the deterministic text grader and the isolated semantic grader to each
requirement. Save the raw executor and grader artifacts before writing the
summary. A surface/semantic disagreement is an evaluation result, not permission
to choose whichever verdict is convenient.

Do not let the executor grade itself. Self-reported success is evidence only when
confirmed by the produced output.

## Trial independence

Use a new context for each scenario and trial. Do not send a follow-up to the same
executor for another measured trial. A corrective follow-up can be used for
diagnosis, but it does not count as an independent result.
