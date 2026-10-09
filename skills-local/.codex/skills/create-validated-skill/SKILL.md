---
name: create-validated-skill
description: Create or substantially revise Codex skills with outcome-first fresh-agent evaluation, with-skill/without-skill comparison, structural validation, and proportionate trigger smoke tests. Use when adding a new SKILL.md, making a behaviorally meaningful workflow or trigger change, deciding whether reusable guidance belongs in a skill, or evaluating whether a skill is ready to use. Do not use for spelling, link, comment, or formatting-only edits that leave behavior and activation unchanged. This workflow owns skill completion when another skill-creation guide also applies.
---

# Create Validated Skill

Create skills only when a reusable, selectively triggered workflow is the right
mechanism. Treat implementation and evaluation as one task: do not call a skill
complete after structural validation alone.

## Apply the completion rule

Use this workflow as the completion authority whenever creating a skill or making
a behaviorally meaningful change to one. Other skill-creation guidance may supply
format conventions or utilities, but it does not replace the validation gates
below.

Classify edits before starting:

- **New skill:** run the full workflow.
- **Behavioral update:** rerun affected scenarios and all critical requirements;
  rerun trigger tests when the description or routing environment changed.
- **Non-behavioral edit:** for spelling, links, or comments only, run static
  validation and explain why behavioral evaluation is unaffected.

If a fresh isolated executor cannot be used, report the skill as **not behaviorally
validated**. Do not describe it as complete.

## 1. Decide whether a skill is warranted

Search the installed and repository-local skills before creating another one.
Compare the proposed scope, triggers, and workflow with existing skills.

Choose the narrowest durable mechanism:

- Use a **skill** for a reusable workflow or specialized knowledge that should
  activate only for identifiable tasks.
- Use `AGENTS.md` for short rules that should apply broadly in a directory or
  globally.
- Use a deterministic script, linter, test, or hook when the requirement can be
  enforced mechanically.
- Use ordinary project documentation for human-facing reference material that
  does not need agent activation.

Extend an existing skill when the proposed behavior shares its trigger contract
and workflow. Reject or redirect the request when a skill would only duplicate an
existing mechanism.

Record this decision in the evaluation ledger.

## 2. Define the outcome contract before implementation

Write down:

1. The user problem and intended deliverable.
2. Inputs, outputs, constraints, and external side effects.
3. Observable critical requirements, each marked `[critical]`.
4. Two or three realistic task scenarios: one typical and one or two edge,
   non-applicability, or refusal cases.
5. Positive, negative, and near-miss trigger examples.

Make task scenarios concrete enough to judge the deliverable without requiring a
fixture repository when the skill produces advice, analysis, plans, designs, or
other narrative artifacts. State the hypothetical system, current state, actors,
constraints, recurring changes, protected contracts, and non-goals. Use a real or
fixture repository only when files, commands, diffs, or tests are themselves part
of the promised outcome.

Make the frontmatter `description` the routing contract. State both what the skill
does and when it should activate. Make the body consistent with that contract.
Avoid vague claims such as "helps with workflows."

For a new skill, initialize it with:

```bash
python3 scripts/init_skill.py <skill-name> --path <skills-directory>
```

Use the bundled evaluator template as the starting point. Do not silently
overwrite an existing skill.

## 3. Implement for progressive disclosure

Keep `SKILL.md` focused on decisions and procedure. Move detailed methods into
`references/`, deterministic operations into `scripts/`, and files intended to be
copied into outputs into `assets/`.

Follow these constraints:

- Use lowercase kebab-case for the directory and skill name.
- Keep frontmatter to `name` and `description`.
- Use imperative instructions.
- Link every supporting file from `SKILL.md` and say when to read or run it.
- Avoid auxiliary README, changelog, installation guide, or process diary files.
- Prefer deterministic scripts for repeatable checks.
- Test every added script directly.

## 4. Run static validation

Run the system skill validator when available, then the stricter bundled validator:

```bash
python3 <system-skill-creator>/scripts/quick_validate.py <skill-directory>
python3 scripts/validate_skill.py <skill-directory>
```

Resolve every error. Static success proves only that the package is internally
well formed; it does not prove that the instructions work.

## 5. Run outcome-first fresh-agent evaluation

Read [evaluation-method.md](references/evaluation-method.md) before designing or
changing evaluation scenarios. Read
[executor-contract.md](references/executor-contract.md) before dispatching fresh
executors.

Run the fixed scenarios from the target skill's `evals/eval.yaml` with a fresh,
blank-slate executor for every trial. Give the executor the scenario, available
inputs, and path to the skill. Do not include the expected answer, checklist, prior
failures, or previous output.

Evaluate in this order:

1. Run one typical and one edge scenario and cover every `[critical]`
   requirement. Add a negative, refusal, or non-applicability behavior scenario
   when avoiding unnecessary work is part of the skill's value.
2. Run a representative scenario both with and without the skill, keeping the
   prompt and available inputs identical. Compare requirement achievement,
   critical success, unclear points, retries, tool use, and duration. If the
   baseline is equally good, simplify the skill or record the concrete
   consistency or constraint-preservation value that still justifies it.
3. Only after the skill demonstrates task value, run positive, negative, and
   near-miss routing smoke tests. Routing is an access check, not the primary
   quality measure.
4. Run a holdout after the edit loop when overfitting is a material risk.

Do not substitute rereading the skill yourself for a fresh execution.

Run behavior and baseline before automatic routing:

```bash
uv run --with pyyaml python scripts/run_eval.py <skill-directory> \
  --mode behavior
uv run --with pyyaml python scripts/run_eval.py <skill-directory> \
  --mode behavior --baseline --case <representative-task-id>
uv run --with pyyaml python scripts/run_eval.py <skill-directory> \
  --mode routing --profile isolated
```

Use one trial per case by default. Use the normal routing profile only for a
small set of cases where installed sibling skills or global instructions could
plausibly change selection. Do not run every case in both profiles merely because
the skill is installed globally. Rerun routing only when the description,
installation, or a known routing interaction changed.

In the isolated routing profile, expose the target skill through a temporary
`CODEX_HOME` without global `AGENTS.md`; do not mention the skill name or path in
the user prompt. In the normal profile, retain the real global environment. Count
activation only when the execution trace shows that the target `SKILL.md` was
read. A claim that the skill was used is not evidence by itself.

For behavior trials, save the executor output and JSONL trace. Require the
executor to report phase status, unclear points using `Issue / Cause / General Fix
Rule`, discretionary fill-ins, retries, and uncompleted work. Grade every
requirement with a semantic judge and use a broad deterministic text grader as
supporting evidence. A semantic pass with a text miss is a surface disagreement,
not automatically a skill failure. Make text matching a hard gate only for truly
deterministic literals or artifact shapes by setting `text.required: true`.

Use the deep tier only when failure is costly, destructive, operationally risky,
or the skill is broadly distributed to other users. Global installation alone is
not sufficient:

Before choosing a tier, record the consequence of an incorrect deliverable, the
authority and reversibility of side effects, operational reliance, and
distribution. Do not equate read-only with low risk: a review or diagnostic skill
that can provide false assurance for a production decision may require deep
behavior evaluation even though it cannot mutate the system.

- Run at least two independent trials for critical behavior scenarios.
- Compare performance with and without the skill on representative scenarios.
- Require two consecutive clear behavior iterations after behavioral changes.
- Keep at least one holdout scenario out of the edit loop until final validation.
- Deepen routing trials only when false activation or missed activation is itself
  costly.

## 6. Iterate against evidence

Append results to `evals/ledger.yaml`. Record the scenario, trial, observable
result, failed requirement, ambiguity, change made, and next result.

Change the smallest instruction, description, script, or scenario necessary to
address observed failures. Do not rewrite the whole skill unless the evidence
shows that its structure is wrong. Rerun the affected scenarios after each
change, then one final behavior regression. Do not rerun unchanged routing suites
after body-only or grader-only changes.

Treat unclear deterministic output as a failure. Do not explain away executor
mistakes that the skill was intended to prevent.

## 7. Complete only after all gates pass

Declare a skill ready only when:

- The need and non-duplication decision is recorded.
- Structural validation passes.
- Added scripts pass direct tests.
- Description and body agree.
- Representative tasks produce usable deliverables and satisfy all critical
  outcome requirements.
- The with-skill result improves on the no-skill baseline, or the ledger records
  a concrete repeatability, constraint-preservation, or error-prevention benefit
  that the baseline lacks.
- Typical and edge scenarios satisfy every critical requirement.
- Negative and near-miss cases do not cause unnecessary activation or work.
- The declared routing smoke-test profiles meet their activation and
  false-activation thresholds.
- No deterministic ambiguity remains.
- Required risk-proportional trials, baseline, convergence, and holdout checks
  pass.
- The ledger contains the final evidence and any residual limitations.

Report which commands and behavioral scenarios were run. Distinguish unrun checks
from passed checks.

## Resources

- [evaluation-method.md](references/evaluation-method.md): scenario design,
  evaluation tiers, metrics, convergence, and contamination controls.
- [executor-contract.md](references/executor-contract.md): prompt and response
  contract for isolated executors.
- [evaluation-schema.md](references/evaluation-schema.md): manifest, requirement,
  routing-case, grader, and artifact schemas.
- `scripts/init_skill.py`: create a skill with a local evaluation scaffold.
- `scripts/validate_skill.py`: validate package and evaluation structure.
- `scripts/run_eval.py`: execute automatic routing, structured behavioral trials,
  paired graders, artifact capture, and ledger updates.
- `assets/executor-output.schema.json` and
  `assets/semantic-grade.schema.json`: structured Codex output contracts.
- `assets/evals-template/`: copyable evaluator files for manual recovery or
  customization.
