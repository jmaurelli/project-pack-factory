# Orchestrator Autonomy Loop Tech Spec

## Purpose

This specification defines how a template-based orchestration agent can operate in a semi-autonomous or autonomous loop using project-pack specifications as the control surface.

It is intentionally template-level.

It defines:

- what the orchestrator is allowed to do automatically;
- what must be specified in the project pack before autonomy is allowed;
- what gates must pass before the orchestrator continues;
- what conditions require the orchestrator to stop, escalate, or ask the user.

This document does not implement the runtime loop.
It defines the contract that a runtime orchestrator should follow.

## Role Of This Spec

This is the runtime loop spec.

It is normative for:

- autonomous and semi-autonomous loop behavior;
- task selection rules;
- continuation, retry, stop, and escalation rules;
- approval-state handling;
- required runtime state tracking.

It is not the canonical source for delegation brief fields, worker return fields, or validator rollout order.

Those concerns belong to:

- `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md` for contract rules;
- `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md` for validator definitions, blocking policy, and rollout order.

## Problem Statement

A project pack may contain:

- specs;
- delegation templates;
- validation rules;
- documentation contracts;
- rollout guidance.

But that alone does not make orchestration autonomous.

Without a defined autonomy loop:

- the orchestrator may stop too early;
- the orchestrator may continue too far without approval;
- task sequencing may become inconsistent;
- workers may be delegated before prerequisites are satisfied;
- validation failures may not block further delegation;
- human approval boundaries may be unclear.

The template therefore needs a reusable specification for autonomy behavior.

## Goals

- define a deterministic orchestration loop driven by project-pack specs;
- define the minimum required project-pack inputs for autonomous execution;
- define safe continuation, retry, stop, and escalation rules;
- separate template-level autonomy policy from runtime implementation;
- support repeatable delegated execution across future packages.

## Non-Goals

- this spec does not define business-domain logic;
- this spec does not require a specific scheduler or job runner;
- this spec does not require one model vendor;
- this spec does not replace package-specific implementation specs;
- this spec does not authorize destructive actions by default.

## Boundary Clarification

This work crosses a real boundary.

Template layer defines:

- the autonomy policy;
- the allowed task shapes;
- the validation contracts;
- the stopping and escalation rules.

Runtime layer implements:

- the actual loop;
- task dispatch;
- task state tracking;
- worker monitoring;
- validation execution;
- retries;
- approval handling.

This is expected and acceptable.

The template should define the rules.
The runtime should execute them.

## Required Inputs for Autonomous Orchestration

Autonomy should not start unless the project pack provides:

1. a project-level spec or task sequence
2. reusable delegation brief templates
3. validation rules for task completion
4. stop-on-scope-mismatch policy
5. acceptance criteria per task
6. declared task order or an explicit dependency model with stable task identifiers
7. task-level approval requirements declared in machine-readable task metadata
8. a way to determine when the project is complete

Recommended additional inputs:

- task dependency model
- optional `dependency unlock` score declared per task
- optional `risk reduction` score declared per task
- task class labels such as implementation, docs, validation, regression
- escalation policy
- approval policy for risky operations

## Autonomy Modes

The template should support at least these modes.

### Mode 1: Assisted

The orchestrator may:

- propose the next task;
- generate the worker brief;
- wait for user confirmation before dispatch.

### Mode 2: Semi-Autonomous

The orchestrator may:

- select the next task automatically;
- dispatch workers automatically;
- validate automatically;
- continue automatically only while all gates pass and no escalation rule is triggered.

### Mode 3: Autonomous

The orchestrator may:

- repeatedly select, delegate, validate, and continue until completion;
- stop only on defined escalation, approval, or failure conditions.

The template may choose to make Semi-Autonomous the default and Autonomous opt-in.

## Core Loop

The runtime orchestrator should conceptually execute this loop:

1. load project-pack specs and contracts
2. build a task graph or ordered task list
3. select the next eligible task
4. generate a deterministic worker brief
5. validate the brief before dispatch
6. dispatch the worker
7. monitor worker execution
8. validate worker outputs
9. decide:
   - continue
   - retry
   - escalate
   - stop as complete
10. persist state and repeat

## Deterministic Task Metadata

Autonomous task selection must use only declared task metadata and persisted runtime state.

Each task record in the project pack task list or task graph should declare:

- stable task identifier
- prerequisite task identifiers or explicit dependency edges
- declared task order
- per-task acceptance criteria
- per-task validation commands
- task-level approval requirement

Optional task metadata may also declare:

- `dependency unlock` score
- `risk reduction` score

The orchestrator must not infer missing scores from prose, severity language, or hidden judgment.

## Task Selection Rules

The next task may be selected automatically only when:

- all prerequisite tasks are complete;
- no blocking validation failure remains;
- no unresolved scope mismatch remains;
- the task approval state is `approval_not_required` or `approval_granted`;
- the task is fully specified enough to produce a compliant brief.

Selection priority must be deterministic and must use only declared inputs plus persisted runtime state.

Selection order:

1. keep only tasks whose prerequisites are satisfied and whose approval state is `approval_not_required` or `approval_granted`
2. if every remaining candidate declares a `dependency unlock` score, keep only candidates with the highest declared score
3. if a tie remains and every tied candidate declares a `risk reduction` score, keep only candidates with the highest declared score
4. if optional scoring fields are absent for any remaining candidate, skip that scoring dimension for that selection pass
5. prefer the lowest declared task order
6. apply lexical task identifier ordering as the final tie-break

Fallback behavior when optional scoring fields are absent:

- if `dependency unlock` is not explicitly declared for every remaining candidate, skip that dimension
- if `risk reduction` is not explicitly declared for every tied candidate, skip that dimension
- the orchestrator must then fall back to declared task order and lexical task identifier without inventing replacement rankings

## Delegation Brief Generation Rules

Autonomy may only dispatch a task if the generated brief passes contract validation.

Required generated brief properties:

- the canonical delegation brief contract is complete
- the brief satisfies the deterministic task-shape rules defined in `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`

If any are missing, the orchestrator must not dispatch.

## Validation Gates

The orchestrator may continue to the next task only when all required gates pass.

### Gate A: Brief Compliance

Checks:

- `validate-task-brief` passes

### Gate B: Worker Completion Contract

Checks:

- worker returned the required summary fields
- worker did not silently broaden scope
- required commands were run

### Gate C: Output Validation

Checks:

- task-specific validation commands passed
- required outputs exist
- required reports are updated

### Gate D: Scope Compliance

Checks:

- `validate-task-scope` passes

### Gate E: Real-Output Validation

Required when the task affects:

- generated artifacts
- packaging
- export outputs
- runtime documentation
- end-to-end behavior

## Continuation Rules

The orchestrator may continue automatically when:

- all required gates pass;
- no escalation rule is triggered;
- the next task approval state is `approval_not_required` or `approval_granted`;
- max-iteration and max-failure thresholds are not exceeded.

## Retry Rules

The orchestrator may retry automatically only for bounded, non-destructive failures.

Examples:

- flaky validation execution
- transient network failure during a required fetch
- worker formatting or contract miss that can be corrected with a smaller re-brief

Recommended retry limits:

- max 1 or 2 automatic retries per task
- retries must preserve or reduce scope

If retry budget is exhausted, escalate.

## Stop Conditions

The orchestrator must stop and report when:

- the project completion condition is satisfied;
- no eligible task remains;
- a blocking validation failure remains unresolved;
- a scope mismatch cannot be resolved within the task boundary;
- the next task approval state is `approval_required`, `approval_pending`, or `approval_denied`;
- a retry limit is exceeded;
- a destructive or high-risk action would be required and the task approval state is not `approval_granted`.

## Escalation Conditions

The orchestrator must escalate to the user when:

- the next task has non-obvious consequences;
- multiple valid next paths exist with materially different outcomes;
- scope expansion is required;
- network, credentials, or external system access changes risk materially;
- a destructive action would be needed;
- validation reveals ambiguous or contradictory results;
- the project pack itself is underspecified.

## Approval Policy

Autonomy must never imply blanket permission for risky actions.

Project packs must declare task-level approval requirements in the machine-readable task list or task graph entry for each task.
The declaration point is the task record itself, alongside the task identifier and declared task order.

The minimal approval state model is:

- `approval_required`
- `approval_pending`
- `approval_granted`
- `approval_denied`
- `approval_not_required`

Approval state meanings:

- `approval_required`: the project pack declares approval is required, but no approval request has been issued yet
- `approval_pending`: approval has been requested and no response has been recorded yet
- `approval_granted`: approval was required and was granted for the current task scope
- `approval_denied`: approval was required and was explicitly denied for the current task scope
- `approval_not_required`: the project pack declares that the task may proceed without approval

Minimum approval state transitions:

- tasks declared as requiring approval start in `approval_required`
- tasks declared as not requiring approval start in `approval_not_required`
- an issued approval request moves the task to `approval_pending`
- an approving response moves the task to `approval_granted`
- a denying response moves the task to `approval_denied`

Autonomous continuation may proceed only when the current task approval state is `approval_not_required` or `approval_granted`.

Typical cases that should map a task to `approval_required` are:

- destructive commands;
- privileged environment changes;
- pushes, merges, or releases unless already explicitly requested;
- network access when policy requires explicit approval;
- changes outside declared writable or owned scope;
- broad scope expansion beyond the current task.

## State Tracking Requirements

The runtime should persist at least:

- current autonomy mode
- ordered task list or task graph
- declared task order per task
- task status:
  - pending
  - in_progress
  - completed
  - blocked
  - failed
  - escalated
- approval state per task
- validation results per task
- retry count per task
- changed files per task
- evidence links or artifact paths

Recommended additional state:

- reason for task selection
- reason for stop/escalation
- approval request or response evidence

## Project Completion Rules

The template should require a project pack to define what “complete” means.

Recommended completion definition:

- all required tasks complete;
- all required validations pass;
- all required real-output checks pass;
- no blocking warnings remain in the defined policy class;
- documentation and runtime artifacts are aligned.

If completion rules are undefined, autonomy should not run in full autonomous mode.

## Required Project-Pack Sections for Autonomy

To support autonomy safely, a project pack should define:

- task list or task graph
- task IDs
- dependency or order rules
- declared task order
- per-task acceptance criteria
- per-task validation commands
- per-task approval requirement declaration
- escalation guidance
- completion criteria

Recommended additional sections:

- optional per-task `dependency unlock` scores
- optional per-task `risk reduction` scores
- risky-operation policy
- retry policy
- real-output verification policy
- docs-role policy

## Recommended Supporting Templates

The template package should eventually provide:

- autonomy policy template
- task graph template
- per-task brief template
- per-task validation result template
- escalation report template
- completion checklist template

## Enforcement Expectations

Autonomous orchestration should be paired with the enforcement stack defined in:

- `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`
- `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md`

At minimum:

- `validate-task-brief` before dispatch
- pre-dispatch blocking on `validate-task-brief` failure
- `validate-task-scope` after execution
- `validate-generated-agent-readme` when relevant
- real-output validation when relevant

## Suggested Runtime State Machine

Recommended high-level states:

- `idle`
- `planning`
- `ready_to_dispatch`
- `dispatching`
- `monitoring`
- `validating`
- `retry_pending`
- `blocked`
- `escalated`
- `complete`

Allowed transitions should be deterministic and auditable.

## Observability Requirements

The runtime should expose enough telemetry to explain:

- why a task was selected;
- why a task was retried;
- why a task was blocked;
- why the loop continued;
- why the loop stopped.

Recommended outputs:

- task event log
- task snapshot
- evidence manifest
- validation summaries

## Anti-Patterns

- autonomous continuation without explicit stop rules;
- worker dispatch without brief validation;
- continuing after failed validation just because tests partially passed;
- silent scope expansion during autonomous loops;
- using autonomy to bypass required approvals;
- treating approval knowledge as implied context instead of explicit approval state;
- defining completion as “the worker stopped talking”;
- allowing the orchestrator to guess missing task order from weak context when the spec should define it.

## Recommended Rollout

### Phase 1

- define autonomy policy in the template
- add required project-pack sections

### Phase 2

- adopt the minimum implementation order from `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md`
- add task status persistence

### Phase 3

- implement semi-autonomous loop
- require explicit approval for autonomous mode

### Phase 4

- add retry policy
- add completion and escalation reporting
- add CI or local gates for autonomy support

## Acceptance Criteria

This template-level autonomy spec is good enough to implement when:

- the required project-pack inputs are clearly defined;
- the orchestrator’s continuation rules are explicit;
- stop and escalation conditions are explicit;
- approval boundaries are explicit and represented as approval state;
- task selection and completion rules are deterministic enough to implement;
- the autonomy loop can be built without inventing hidden policy at runtime.
