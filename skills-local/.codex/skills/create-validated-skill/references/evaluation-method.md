# Evaluation method

## Start with iteration zero

Before editing the target skill, inspect its current description, body, and
observable behavior. Record whether the body delivers the outcomes promised by
the description and select the smallest useful change.

## Make task outcomes observable

Use two or three fixed scenarios: one median use case and one or two edge,
refusal, or non-applicability cases. Each scenario needs an `id`, `kind`,
user-facing `scenario`, and three to seven observable `requirements`. Mark a
requirement `critical: true` when failure makes the deliverable unusable.

Good:

```yaml
requirements:
  - id: reuse-existing
    critical: true
    description: Searches existing installed skills before creating a new one.
```

Weak:

```yaml
requirements:
  - id: quality
    critical: true
    description: Produces a high-quality answer.
```

Keep scenarios fixed while iterating. Do not make a scenario easier because the
skill failed it. Add a regression scenario only when a newly discovered failure
represents a distinct recurring use case.

Narrative skills do not need a fixture repository. Supply a realistic hypothetical
system with enough current-state facts, actors, constraints, protected contracts,
recurring changes, and non-goals to judge the deliverable. Use a real or fixture
repository only when files, commands, diffs, or tests are part of the promised
outcome.

## Establish value before routing

Run a representative task with the skill and without it using the same scenario,
inputs, model, tools, and hidden requirements. Record:

- Critical-task success and total requirement achievement.
- Unclear points, discretionary fill-ins, and retries.
- Tool uses and duration as secondary cost signals.
- The delta between with-skill and without-skill results.

The primary question is whether the skill helps solve the task. Routing only asks
whether the agent can reach that behavior. Do not optimize routing for a skill
that has not demonstrated useful task behavior.

Grade both outputs independently against the fixed checklist. Do not use a single
subjective A/B preference as the baseline result. If qualitative pairwise judgment
is necessary, counterbalance output order and accept it only when both orderings
agree.

If the baseline performs equally well, simplify the skill or reconsider whether
it is warranted. A skill may still earn its cost by making critical constraints,
repeatability, or error prevention more reliable; record that concrete difference
instead of claiming generic quality improvement.

## Test routing proportionately

Create one representative case in each of three trigger categories after task
value is established:

- **Positive:** requests that clearly require the skill.
- **Negative:** unrelated requests that share some vocabulary.
- **Near miss:** adjacent requests that should use another skill, `AGENTS.md`,
  documentation, or a deterministic tool.

Do not mention the skill name or path in a routing prompt. Count activation only
when the trace shows a read of the target `SKILL.md`.

Use the isolated profile for the default smoke test. Use the normal profile only
for selected cases where installed sibling skills or global instructions could
plausibly change selection. One case and one trial per category is the standard
default. Add cases or trials only when a known routing interaction needs coverage
or a routing error is itself costly.

Measure positive activation and negative/near-miss false activation. With a small
case set, treat percentages as smoke-test gates rather than statistically stable
estimates.

Inspect the description when routing is wrong. Inspect the body when activation
is correct but task execution is wrong. Do not rerun unchanged routing suites
after body-only or grader-only changes.

## Choose the evaluation tier

Use the standard tier for small, local, reversible skills:

- One fresh trial per behavior scenario.
- Typical and edge coverage, plus negative behavior when it is part of the value.
- A with-skill/without-skill comparison on one representative scenario.
- One isolated routing trial in each of the positive, negative, and near-miss
  categories.
- One final behavior regression after affected-case iteration.
- All critical requirements pass with no deterministic ambiguity.

Use the deep tier when failure is costly, destructive, operationally risky, or
the skill is distributed broadly to other users. Global installation alone does
not require deep evaluation:

Assess the consequence of a wrong deliverable separately from mutation authority.
A read-only review, diagnosis, or recommendation can still be high-risk when
operators rely on it for production decisions.

- At least two independent trials per critical behavior scenario.
- A no-skill baseline on representative scenarios.
- Two consecutive clear behavior iterations after behavioral changes.
- One or more holdouts kept out of the edit loop.
- Additional routing profiles or trials only when routing mistakes are costly.

## Protect validation integrity

Use a fresh executor for every measured trial. Provide only the user scenario,
the target skill path or activation context, and inputs a real user would have.
Do not provide the hidden checklist, expected answer, earlier outputs, known
failure modes, or intended fix.

For a no-skill baseline, prevent access to the target skill but keep every other
input equal. A corrective follow-up can diagnose a failure but is not an
independent trial.

## Grade outcomes

Apply a semantic rubric to every requirement. Use a broad text grader as cheap,
deterministic supporting evidence.

- Semantic fail: fail.
- Semantic pass and text pass: pass.
- Semantic pass and text miss: record a surface disagreement and pass unless
  `text.required: true` marks a literal token or artifact shape as deterministic.
- Missing or unclear semantic result: unclear.

Do not force unnatural wording to satisfy regex. Widen the text grader when the
semantic evidence is correct. Do not add a grader merely because a harmless
surface form changed.

Count a task as successful only when every critical requirement passes. Also
report total requirement achievement so partial improvements remain visible.
Qualitative unclear points and discretionary fill-ins are primary diagnostic
signals; duration and tool use are secondary cost signals.

## Capture two-sided evidence

Require the executor output to contain:

- The actual deliverable.
- Understanding, Planning, Execution, and Formatting phase status.
- Unclear points as `Issue / Cause / General Fix Rule`.
- Discretionary fill-ins.
- Retry count and reasons.
- Uncompleted work.

Store executor output, trace, semantic grade, stderr, and combined results under
`evals/results/<run-id>/`. Do not commit large or sensitive raw artifacts by
default.

## Iterate and stop

Change the smallest instruction, script, or scenario necessary to address an
observed failure. Consult the failure-pattern ledger before adding a new rule.
Rerun affected scenarios first, then one final behavior regression.

An iteration is clear when all critical behavior requirements pass, no required
deterministic result is unclear, and no previous behavior regression fails. Deep
convergence applies to behavior rather than unchanged routing suites.

Run holdouts only after convergence. If a holdout fails, fix the skill and restart
the behavior convergence count. Stop when further improvement cost is not
justified by the skill's importance; record the cutoff and residual limitation
instead of pursuing perfect routing percentages.

## Maintain the ledger

Append each iteration with the skill revision, scenario, configuration
(`with_skill` or `without_skill`), requirement evidence, failure classification,
minimal change, and next result. Key recurring failures by `General Fix Rule`.

Finish with the tier, commands, task-value and baseline results, routing smoke-test
results, residual limitations, and explicitly unrun checks.
