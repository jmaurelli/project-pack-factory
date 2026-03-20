# Orchestration Rules Enforcement Options Tech Spec

## Purpose

This specification defines the enforcement options for orchestration, delegation, and documentation-role rules in template-based AI-native packages.

It exists to answer a practical question:

How do guidance documents become enforceable behavior?

This document is a companion to:

- `DELEGATION-DOCS-META-TEMPLATE.md`
- `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`
- `ORCHESTRATOR-AUTONOMY-LOOP-TECH-SPEC.md`

## Role Of This Spec

This is the enforcement-options and rollout-order spec.

It is normative for:

- enforcement layers;
- validator targets;
- result types and blocking outcomes;
- validator naming;
- minimum implementation order.

It is not the canonical source for delegation brief fields, worker return structure, documentation role boundaries, or runtime loop behavior.

Those concerns belong to:

- `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md` for the canonical contract rules;
- `ORCHESTRATOR-AUTONOMY-LOOP-TECH-SPEC.md` for runtime loop behavior and continuation policy.

## Problem Statement

Guidance alone is useful but insufficient.

Without enforcement:

- delegated task briefs drift;
- workers broaden scope silently;
- generated runtime docs lose their contract shape;
- operator and agent docs mix roles again;
- validation becomes inconsistent across packages;
- orchestrators have no objective basis for blocking bad delegation.

The template should therefore define not only the rules, but also the enforcement mechanisms available to package builders.

## Goals

- define enforcement layers from lightest to strongest;
- identify what can be enforced at each layer;
- recommend a practical rollout order;
- describe how orchestrators should block, warn, or allow work;
- provide reusable enforcement targets for future template-based packages.

## Non-Goals

- this spec does not mandate one CI platform;
- this spec does not mandate one parser library;
- this spec does not require one prompt provider or one model vendor;
- this spec does not define package-specific business logic.

## Enforcement Model

Enforcement should be layered.

Recommended layers:

1. prompt enforcement
2. file-contract enforcement
3. programmatic validation
4. CI and policy gates

Each layer adds stronger guarantees.

## Layer 1: Prompt Enforcement

## Description

Rules are embedded in:

- orchestrator prompts;
- worker prompts;
- delegation brief templates;
- runtime instructions for stop-on-scope-mismatch behavior.

## What It Can Enforce

- required task structure by instruction;
- one-objective-per-task behavior;
- stop-on-scope-mismatch policy;
- required return format;
- audience separation guidance for docs.

## Strengths

- fast to adopt;
- low engineering overhead;
- useful before validators exist.

## Weaknesses

- advisory only;
- vulnerable to prompt drift;
- hard to audit after the fact;
- not reliable as a sole control plane.

## Recommended Use

Use prompt enforcement as the first safety layer, not the final gate.

## Layer 2: File-Contract Enforcement

## Description

Rules are captured in versioned package files, such as:

- delegation brief templates;
- project-pack task lists or task graphs;
- docs-role contract files;
- generated agent README contract files;
- checklist files;
- package-local tech specs.

## What It Can Enforce

- required delegation brief headings;
- stable task brief structure;
- declared task order and lexical task identifier fields in task records;
- task-level approval requirements and approval state representation;
- required docs-role distinctions;
- required generated README section order;
- reusable micro-task templates.

## Strengths

- explicit and auditable;
- reusable across packages;
- easier to diff and review than prompt-only rules;
- can serve as input to automated validators.

## Weaknesses

- still passive unless paired with checks;
- can drift if not validated.

## Recommended Use

Treat file contracts as the canonical rule definitions that programmatic checks read from.

The canonical contract definitions themselves remain in `DELEGATION-DOCS-META-TEMPLATE.md` and `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`.

## Layer 3: Programmatic Validation

## Description

Rules are enforced by validators, linters, or preflight checks before dispatch and before completion.

## What It Can Enforce

### Task Brief Compliance

- all canonical delegation brief contract fields exist;
- exact file scope exists;
- out-of-scope section exists;
- validation commands exist;
- local evidence exists;
- required return format exists.

### Scope Discipline

- test-only tasks do not edit runtime files;
- declared file scope matches actual changed files;
- disallowed files are flagged.

### Task Ordering And Approval State

- declared task order exists for each task record;
- lexical task identifier exists for deterministic tie-break behavior;
- task-level approval requirements are declared in the project-pack task list or task graph;
- approval state is represented in machine-readable form as `approval_required`, `approval_pending`, `approval_granted`, `approval_denied`, or `approval_not_required`.

### Generated Agent README Contract

- section order is correct;
- required sections exist;
- operator-only content is absent from agent docs;
- machine-readable truth references are present.

### Documentation Role Separation

- package landing docs link to deeper docs;
- operator docs keep upload/run steps;
- agent docs keep reading semantics;
- forbidden duplicated sections are not present.

### Real Artifact Consistency

- generated docs reflect actual outputs;
- validation report paths exist;
- cross-references point to real files.

## Strengths

- objective and repeatable;
- scalable across packages;
- suitable for pre-dispatch and pre-merge enforcement;
- enables deterministic blocking rules.

## Weaknesses

- requires implementation effort;
- validators themselves must be maintained.

## Recommended Use

This should be the primary enforcement layer.

## Layer 4: CI and Policy Gates

## Description

Validators are executed as policy checks in local automation or CI.

## What It Can Enforce

- merge-blocking failures for non-compliant task briefs;
- merge-blocking failures for docs-contract violations;
- merge-blocking failures for generated README drift;
- required real-output verification for selected changes;
- required test and validator success.

## Strengths

- strongest operational enforcement;
- creates consistent package quality;
- prevents regression after initial implementation.

## Weaknesses

- slower feedback than local preflight alone;
- requires pipeline integration.

## Recommended Use

Use CI gates after prompt, contract, and validator layers are already defined.

## Enforcement Targets

The following should be considered first-class enforcement targets.

## Target A: Delegation Brief Contract

Required checks:

- `task_name` present;
- `operating_root` present;
- `project_context_reference` present;
- `source_spec_reference` present;
- `objective` present;
- `files_in_scope` present;
- `required_changes` present;
- `acceptance_criteria` present;
- `validation_commands` present;
- `out_of_scope` present;
- `local_evidence` present;
- `task_boundary_rules` present;
- `required_return_format` present.

Recommended result levels:

- `fail`
- `warn`
- `pass`

Blocking policy:

- omission of any canonical delegation brief contract field is always `fail`
- canonical-field omissions must never be downgraded to `warn` or `pass`

## Target B: File Scope Compliance

Required checks:

- every changed file is declared in task scope;
- no undeclared file is edited;
- test-only tasks do not edit `src/`;
- docs-only tasks do not edit runtime code unless explicitly approved.

Blocking policy:

- undeclared runtime file edits should be `fail`

## Target C: Generated Agent README Contract

Required checks:

- all required sections exist;
- sections appear in the correct order;
- required machine-readable truth paths are present;
- validation section is present;
- warning policy section is present.

Blocking policy:

- missing sections or bad order should be `fail`

## Target D: Operator vs Agent Role Separation

Required checks:

- operator docs retain checklist/action order;
- agent docs retain reading order and file semantics;
- agent docs do not repeat the operator checklist verbatim;
- operator docs cross-reference agent docs when semantic interpretation is needed.

Blocking policy:

- repeated upload/run checklist in agent docs should be `fail` or `warn`, depending on policy strictness

## Target E: Real-Output Verification

Required checks:

- required regeneration command executed;
- regenerated artifacts exist;
- generated runtime docs reflect the current output;
- validation reports are successful when expected.

Blocking policy:

- required real-output verification missing should be `fail` for runtime-doc and packaging changes

## Target F: Task Ordering And Approval State

Required checks:

- each task record has a declared task order or a dependency model that resolves to one deterministically;
- each task record has a stable lexical task identifier;
- each task record declares whether approval is required at task level in the project-pack task list or task graph;
- approval state is persisted in machine-readable form as `approval_required`, `approval_pending`, `approval_granted`, `approval_denied`, or `approval_not_required`;
- autonomous continuation is allowed only when approval state is `approval_not_required` or `approval_granted`.

Blocking policy:

- missing declared task order resolution should be `fail`
- missing task-level approval requirement declaration should be `fail`
- `approval_required`, `approval_pending`, or `approval_denied` should be `blocked` for autonomous dispatch

## Enforcement Outcomes

Recommended result types:

- `pass`
- `warn`
- `fail`
- `blocked`

Recommended meanings:

- `pass`: compliant
- `warn`: non-blocking but should be reviewed
- `fail`: validation failed
- `blocked`: orchestration must not proceed until the precondition is fixed

## Orchestrator Decision Rules

## Before Dispatch

The orchestrator should:

- validate the full canonical delegation brief contract before dispatch;
- confirm every canonical required field is present exactly once;
- resolve the candidate task approval state from project-pack task metadata and recorded approval responses;
- refuse dispatch when approval state is `approval_required`, `approval_pending`, or `approval_denied`;
- refuse dispatch if the brief fails contract validation.

## During Execution

The orchestrator should:

- monitor for scope mismatch;
- detect unexpected changed files;
- stop or re-brief if the worker broadens scope.

## After Execution

The orchestrator should:

- rerun validation commands;
- inspect real artifacts when required;
- compare changed files to declared scope;
- mark the slice complete only if enforcement checks pass.

## Recommended Enforcement Pipeline

Use this order:

1. author or generate the task brief from a template
2. run brief contract validation
3. resolve declared task order and approval state from the project-pack task record
4. dispatch worker only if validation passes and approval state is `approval_not_required` or `approval_granted`
5. run changed-file scope validation after worker completion
6. rerun task validation commands
7. run role and README contract validators if docs or runtime docs changed
8. run CI or local gate for final approval

## Suggested Validator Set

The template should support these validators over time:

### `validate-task-brief`

Checks:

- presence of every canonical delegation brief contract field defined in `DELEGATION-DOCS-META-TEMPLATE.md` and enforced by `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`
- rendered brief headings map to the canonical contract without omission
- missing canonical fields return `fail`, never `warn` or `pass`

### `validate-task-scope`

Checks:

- changed files vs declared scope
- test-only vs runtime edits
- docs-only vs runtime edits

### `validate-task-order-and-approval`

Checks:

- declared task order exists or dependencies resolve deterministically
- lexical task identifier exists for final tie-break behavior
- task-level approval requirement is declared in the project-pack task list or task graph
- approval state uses only `approval_required`, `approval_pending`, `approval_granted`, `approval_denied`, or `approval_not_required`

### `validate-generated-agent-readme`

Checks:

- the generated runtime agent README contract defined in `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`
- required section names
- required section order
- required field presence

### `validate-doc-role-separation`

Checks:

- package landing docs link correctly
- operator vs agent content does not blur
- runtime docs remain concise and role-correct

### `validate-real-output`

Checks:

- required output files exist
- validation reports are present
- generated docs point to real structured artifacts

## Minimum Viable Enforcement Stack

For a lightweight first version, implement:

1. versioned task brief template
2. versioned generated agent README contract file
3. brief validator
4. generated agent README validator
5. orchestrator pre-dispatch blocking on validator failure

This gives the best early leverage with relatively low complexity.

## Minimum Implementation Order

Implement the minimum viable enforcement rollout in this order:

1. `validate-task-brief`
2. pre-dispatch blocking on `validate-task-brief` failure
3. `validate-task-scope`
4. `validate-generated-agent-readme`

This order is normative for the minimum rollout because it establishes the contract gate first, then prevents bad dispatch, then verifies scope discipline, and only then expands into generated-doc structure enforcement.

## Recommended Full Enforcement Stack

For a stronger version, implement:

1. prompt rules
2. file-contract templates
3. brief validator
4. scope validator
5. generated README validator
6. docs-role separation validator
7. real-output verification check
8. CI gate

## Rollout Plan

### Phase 1

- codify rules in template docs
- add reusable templates
- implement `validate-task-brief`

### Phase 2

- add orchestrator pre-dispatch blocking on `validate-task-brief` failure

### Phase 3

- add `validate-task-scope`

### Phase 4

- add `validate-generated-agent-readme`
- add docs-role separation validation
- add CI enforcement
- require real-output verification for selected task classes

## Anti-Patterns

- relying on prompts alone;
- allowing workers to broaden scope without re-briefing;
- validating only tests but not real outputs;
- keeping role-separation rules only in prose;
- checking content count but not content usefulness;
- treating generated runtime docs as exempt from validation.

## Acceptance Criteria

This enforcement strategy is complete enough to use when:

- task briefs can be programmatically rejected before dispatch;
- changed-file scope can be checked after execution;
- generated agent READMEs can be validated for stable structure;
- operator and agent documentation roles can be checked;
- orchestrators can block completion when required checks fail.
