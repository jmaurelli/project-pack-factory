# Goal-Driven Build Loop Tech Spec

## Purpose

Define a lightweight, agent-first feedback loop for template-generated projects so an AI agent can keep working toward a declared project goal until the goal-linked validation passes.

This spec intentionally avoids heavyweight human-style TDD ceremony. It defines a narrow repo-native loop that makes project goals explicit, validation deterministic, and completion machine-checkable while reusing existing package contracts and validator patterns.

## Scope

This spec applies to the local template at:

- `/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template`

It extends and reuses these existing template surfaces:

- [AGENTS.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/AGENTS.md)
- [project-context.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/project-context.md)
- [task-record.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/contracts/task-record.schema.json)
- [task-record.yaml](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/templates/task-record.yaml)
- [validate_task_brief.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/validators/validate_task_brief.py)
- [validate_project_pack.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/validators/validate_project_pack.py)
- [Makefile](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/Makefile)

## Design Goals

- keep the project reasonably deterministic rather than fully rigid
- reduce agent effort by making the repo tell the agent how to validate progress
- make project goals explicit in one machine-readable source
- keep completion tied to passing goal-linked validation
- preserve a light testing model with minimal, high-signal checks

## Authority Model

The goal-driven loop uses the existing `task-record` as the source of truth for a small build objective.

Authority order:

1. `task-record` machine-readable goal contract
2. package-local `AGENTS.md` operating rules
3. package-local `project-context.md` support context
4. broader package docs

## Goal Contract

The existing `task-record` remains the canonical goal contract. This spec does not add a separate goal file.

The minimum goal-driving fields are:

- `task_name`
- `objective`
- `acceptance_criteria`
- `task_boundary_rules`
- `validation_commands`
- `files_in_scope`
- `goal_validation`

These fields serve the following roles:

- `objective`: the single goal statement
- `acceptance_criteria`: what observable behavior counts as correct
- `task_boundary_rules`: what the agent must not expand into
- `validation_commands`: the deterministic proof path
- `files_in_scope`: the allowed change area
- `goal_validation`: explicit stage metadata for the goal loop

`goal_validation` should be added to the task-record shape as a machine-readable object with:

- `primary_goal_command`
- `safety_check_commands`
- `completion_rule`

The initial allowed `completion_rule` value is:

- `all_declared_commands_must_pass`

## Validation Loop Contract

The validation loop is intentionally simple.

Rules:

1. `goal_validation.primary_goal_command` is the primary goal gate.
2. `goal_validation.safety_check_commands` are broader safety checks.
3. `validation_commands` remains the compatibility list for existing validators and brief rendering.
4. `validation_commands` should contain the same commands declared in `goal_validation`, in execution order.
5. The agent should implement the smallest step that could make the primary goal gate pass.
6. If the primary goal gate fails, the agent should continue working rather than stopping.
7. Once the primary goal gate passes, the agent should run the broader safety checks.
8. A task is not complete until the primary goal gate passes and the broader package validation passes.

Recommended command ordering:

1. focused goal test or behavior check
2. optional secondary focused check
3. package-wide validation such as `make validate`

The loop command must not require `make validate` specifically. It should use the declared task-record commands in order.

## Existing Package Contract Integration

The goal-driven loop does not replace current package validation surfaces.

It must integrate with:

- `validate-doc-update-record`
- `validate-doc-updates` when a changed-files artifact exists
- `validate-project-pack`
- package-local `AGENTS.md`
- package-local `project-context.md`

Implementation must update package-local docs and doc-update artifacts when the new goal-loop commands change package behavior or guidance.

The new loop commands are helpers for agent execution. They are not a replacement for `make validate`.

## CLI Surface

Add one new validator-style command:

- `validate-task-goal`

Purpose:

- validate that a task record is usable as a lightweight goal contract
- report the primary goal gate and broader validation commands deterministically
- fail when the task record lacks the minimum goal-driving fields

Pattern requirements:

- follow the current validator module style under `src/ai_native_package/validators/`
- accept `--task-record`
- support `--output text|json`
- load YAML or JSON task-record inputs using the same fallback pattern used by current validators

Add one new execution command:

- `run-task-goal-loop`

Purpose:

- load the task record
- run `validation_commands` in order from `operating_root`
- stop on first failure
- emit machine-readable status that tells the agent whether to keep working or the goal has passed

Pattern requirements:

- exposed through the existing Click CLI
- implemented in a small dedicated module rather than inline in `cli.py`
- machine-readable JSON output should match the current thin CLI style
- command execution should use explicit task-record commands only

## Execution Envelope

`run-task-goal-loop` should remain intentionally narrow.

Rules:

- input commands are trusted local task-record command strings, not interactive prompts
- commands run from `operating_root`
- commands execute in declared order: primary goal command first, then safety checks
- command execution uses shell command strings because the existing task-record contract already stores validation commands as strings
- stdout and stderr should be captured and truncated in the result payload rather than streamed as an uncontrolled transcript
- each command should use a deterministic timeout
- package code should report command outcomes in machine-readable form

Initial implementation defaults:

- shell command strings executed with the host shell
- per-command timeout: `120` seconds
- stdout tail: last `20` lines
- stderr tail: last `20` lines

## Output Contract

`validate-task-goal` should emit:

- validator name
- result
- parsed goal summary
- primary goal command
- broader validation commands
- structured errors

`run-task-goal-loop` should emit:

- command name
- result
- continue_working
- primary_goal_passed
- completed
- operating_root
- command_results

`command_results` should preserve:

- command
- exit_code
- passed
- stage
- timed_out
- stdout_tail
- stderr_tail

## Failure Semantics

`validate-task-goal` fails when:

- the task-record cannot be loaded
- required goal-driving fields are missing or empty
- `validation_commands` is empty
- `files_in_scope` is empty
- `operating_root` is missing or not absolute
- `goal_validation` is missing or inconsistent with `validation_commands`

`run-task-goal-loop` fails closed when:

- the task-record is invalid for goal-loop use
- `operating_root` is missing
- a validation command exits non-zero

The command should return:

- exit code `0` when all declared validation commands pass
- exit code `2` when the goal loop is incomplete, the task-record is invalid, or execution setup fails

When the primary goal command fails:

- `continue_working = true`
- `primary_goal_passed = false`
- `completed = false`

When all validation commands pass:

- `continue_working = false`
- `primary_goal_passed = true`
- `completed = true`

## Project-Pack Contract Updates

The project-pack contract should add a lightweight goal-loop policy that requires:

- package guidance mentioning goal-driven iteration
- `task-record.yaml` carrying explicit goal and validation fields
- `task-record.schema.json` carrying explicit goal-loop metadata
- a validator command for goal-contract checks
- a declared integration with package-wide validation rather than replacement of package-wide validation
- reuse of existing validator/result conventions

This policy should remain light and should not require a large test suite.

## Agent Guidance Updates

`AGENTS.md` and `project-context.md` should explicitly tell agents:

1. read the task record as the goal contract
2. implement the smallest step toward the objective
3. run the primary goal gate first
4. keep iterating if it fails
5. run broader validation after the goal gate passes
6. stop only when the declared validation path passes

## Template Impact

Implementation should update:

- task-record guidance
- task-record schema
- project-pack validation guidance
- CLI command surface
- minimal focused tests for the new validator and loop runner
- package reference docs where the CLI command inventory is described
- docs-with-code guidance for the new command surfaces

Implementation should not:

- require broad integration suites
- require human-facing docs at project start
- create a second competing goal-definition file
- force goal-loop execution into the default `make validate` path when no task-record is present

## Minimal Test Plan

Add focused tests for:

1. valid task record produces a passing `validate-task-goal` result
2. missing or inconsistent `goal_validation` fails validation
3. empty `validation_commands` fails validation
4. `run-task-goal-loop` reports `continue_working = true` when the primary goal command fails
5. `run-task-goal-loop` reports `completed = true` when all commands pass
6. `run-task-goal-loop` captures truncated stdout and stderr tails deterministically
7. click CLI wrappers emit deterministic JSON for both commands

## Implementation Notes

- prefer existing task-record loading patterns used by current validators
- prefer deterministic JSON/text output matching current CLI style
- keep shell execution local to explicit validation commands from the task record
- preserve the current light repo contract: thin CLI, small modules, minimal high-signal tests
- keep the command runner narrow and machine-readable
- preserve existing package-wide validation authority: `make validate` remains the broader package gate
