# Evaluation schema

## Manifest

Use `evals/eval.yaml` to declare behavior tasks, representative baseline cases,
routing smoke tests, trial counts, thresholds, and convergence gates.

```yaml
name: example-skill
version: 2
tier: standard
trials_per_task: 1
tasks:
  - tasks/typical.yaml
routing:
  profiles: [isolated]
  trials_per_case: 1
  cases:
    - routing/positive.yaml
    - routing/negative.yaml
    - routing/near-miss.yaml
  thresholds:
    positive_activation_rate: 0.9
    negative_false_activation_rate: 0.05
    near_miss_false_activation_rate: 0.1
```

## Behavioral task

Pair a broad surface grader and a semantic rubric on every requirement.

```yaml
id: typical
kind: typical
scenario: |
  A realistic user request.
requirements:
  - id: inspect-existing
    critical: true
    description: Searches for an existing implementation before creating one.
    text:
      required: false
      regex_any:
        - '(?i)(existing|overlap|duplicate|already installed)'
    semantic:
      rubric: The deliverable explicitly checks for an existing implementation.
```

Use stable requirement ids so ledger history survives wording improvements.
Set `text.required: true` only for a literal token, command, or artifact shape
whose exact presence is part of the contract. Otherwise a semantic pass survives
a surface-text miss while the disagreement is recorded.

## Baseline comparison

Run a representative task with `--baseline`. The runner stores separate
`with_skill` and `without_skill` outputs and reports deltas for task pass rate,
requirement pass rate, duration, and tool use. Apply the same hidden requirements
to both configurations; do not tell either executor the expected answer.

## Routing group

Do not mention the target skill in prompts.

```yaml
kind: positive
expected_activation: true
cases:
  - id: create-domain-skill
    critical: true
    prompt: Create a reusable Codex workflow for warehouse incident diagnosis.
```

Keep positive, negative, and near-miss groups separate. Negative cases are
unrelated requests with overlapping vocabulary. Near misses are adjacent tasks
that should use `AGENTS.md`, a deterministic tool, documentation, or another
skill.

## Run artifacts

`scripts/run_eval.py` writes one directory per run and one directory per trial:

```text
evals/results/<run-id>/
  summary.yaml
  routing/<profile>/<case>/trial-N/
  behavior/<task>/<with_skill|without_skill>/trial-N/
    executor-output.json
    executor-events.jsonl
    semantic-grade.json
    semantic-events.jsonl
    result.yaml
```

A compact summary is appended to `evals/ledger.yaml`. Keep raw artifacts locally
unless they are reviewed and intentionally selected as durable fixtures.

### Ledger paths

New automated ledger records use this path contract:

- `results_dir_scope: skill`: `results_dir` is a POSIX path relative to the skill
  directory, normally `evals/results/<run-id>`.
- `results_dir_scope: external`: `results_dir` is `null`. The selected result
  directory is outside the skill, so its location is deliberately not retained
  in the ledger. Use the local CLI output or `summary.yaml` to locate this run;
  the ledger alone cannot resolve it on another computer.
- Behavioral `output_path` and `events_path` are POSIX paths relative to that
  run's result directory, including when the result directory is external.
  A reference outside the run directory is `null`, with its field name listed
  in that trial's `unresolved_artifacts`. Such references are not copied,
  silently converted to absolute paths, or recoverable from the ledger.

Default results go under the skill's `evals/results`. `--results-dir` selects a
custom parent directory; relative values are based on the invocation's current
working directory, absolute values are used directly, and `~` is expanded.
Containment is checked after resolving `..` and symlinks. Missing artifacts can
still have relative references; a reference is not proof that a file exists.

Existing ledger entries are not migrated or reinterpreted when a run is appended.
Older entries may lack the scope/unresolved fields and retain their historical
path formats. Treat those as legacy records rather than assuming the new contract.

Only these structured ledger path fields are normalized. Local `summary.yaml`,
per-trial `result.yaml`, executor outputs, and traces retain their original data.
Free-text evidence, issue descriptions, fix rules, and other user/model-provided
content are not redacted. Review them separately before committing or sharing;
portable paths do not guarantee anonymous or shareable content.
