---
name: pi-extension-development
description: Use when creating, editing, or debugging Pi extensions, custom tools, slash commands, hooks, skills, or prompt templates. Requires behavior-level smoke tests after changes, not just import checks.
---

# Pi Extension Development

Use this skill whenever you modify Pi harness components: extensions, custom tools, commands, hooks, skills, prompt templates, or package manifests.

## Mandatory workflow

1. Read the relevant Pi docs/examples before implementing if the API surface is unfamiliar.
2. Make the smallest safe change.
3. Run a smoke test before claiming completion.
4. Report changed files and the exact smoke-test command/result.

## Smoke test requirements

For extension/tool changes, an import/load check is necessary but not sufficient.

Run both when feasible:

- **Load test**: import the extension with jiti and verify it registers expected tools/commands/hooks.
- **Behavior test**: exercise the changed behavior with a minimal mock.
  - custom tool: call `execute()` with representative params.
  - command: call `handler()` with a mock command context.
  - hook: invoke the registered handler with a representative event and mock context.
  - guard/blocking logic: test at least one allow case and one block/confirm case.

If a full behavior test is not feasible, say why and run the closest deterministic test.

## Avoid false completion claims

Do not say "動作確認済み" or "tested" unless a behavior-level smoke test actually ran. If only import/load was checked, say so explicitly.

## Harness implementation guidance

- Prefer custom extension for executable behavior: tools, hooks, guards, UI, session interaction.
- Prefer skill for reusable knowledge, workflow rules, and decision criteria.
- Prefer prompt template for one-shot repetitive requests.
- Keep CLAUDE.md / AGENTS.md minimal; move detailed procedures into skills.
- Do not auto-modify extensions from hooks. Propose changes and ask for explicit user selection.
