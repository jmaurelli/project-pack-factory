# Orchestration Delegation Enforcement Tech Spec

## Purpose

This specification defines how the template package should support deterministic, enforceable orchestration of delegated implementation work.

It turns documentation and delegation guidance into a reusable technical contract for:

- orchestration agents that prepare and dispatch worker tasks;
- delegated worker agents that execute narrow implementation slices;
- validators that check task briefs, generated runtime docs, and task outcomes for compliance.

This spec is intentionally generic and is meant to be reused across future packages created from this template.

## Role Of This Spec

This is the canonical contract spec for delegated orchestration work.

It is the normative source for:

- delegation brief enforcement requirements;
- deterministic task-shape rules for delegated work;
- required worker return structure;
- documentation role boundaries;
- generated runtime agent README contract requirements.

It does not define validator rollout strategy or the runtime orchestration loop.

Those concerns belong to:

- `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md` for enforcement options and rollout order;
- `ORCHESTRATOR-AUTONOMY-LOOP-TECH-SPEC.md` for runtime loop behavior and continuation rules.

## Problem Statement

Orchestrated delegation often fails in predictable ways:

- worker tasks are too broad;
- file scope is not explicit;
- validation commands are omitted;
- workers re-research known local context;
- scope expands silently;
- operator and agent documentation roles blur;
- generated runtime docs drift away from actual artifact behavior;
- synthetic tests pass while real outputs remain weak.

The template should provide a deterministic structure that reduces these failures before implementation begins.

## Goals

- make delegated task briefs deterministic and machine-checkable;
- standardize the minimum required sections for worker briefs;
- standardize generated agent-facing runtime README structure;
- enforce separation between human, operator, and agent documentation roles;
- require validation evidence for each delegated slice;
- support independent orchestrator verification after worker completion;
- make these rules reusable in future template-based packages.

## Non-Goals

- this spec does not define one project’s business logic;
- this spec does not define a specific transport or network backend;
- this spec does not require one specific test framework;
- this spec does not replace package-specific implementation specs.

## Required Deliverables

The template package should contain reusable artifacts for:

- delegation brief templates;
- documentation-role rules;
- generated agent README contract rules;
- validation checklists;
- optional validators or lint-style checkers.

Recommended package-local files:

```text
docs/specs/orchestration/
  DELEGATION-DOCS-META-TEMPLATE.md
  ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md
src/<module>/
  delegation_templates/
    task-brief-template.md
    docs-task-template.md
    validation-task-template.md
    regression-task-template.md
  enforcement/
    brief_contract.md
    docs_contract.md
    generated_agent_readme_contract.md
```

Exact filenames may vary by package, but the template must provide equivalent content.

## Normative and Explanatory Sections

For delegation brief requirements, the normative sections in this document are:

- `Delegation Contract Enforcement`
- `Deterministic Task Rules`
- `Required Return Contract`
- `Documentation Role Enforcement`
- `Generated Agent README Contract`

Examples, recommended package-local files, and suggested next steps are explanatory unless a section explicitly says otherwise.

## Delegation Contract Enforcement

This section is normative.

The canonical delegation brief contract is defined only in `DELEGATION-DOCS-META-TEMPLATE.md` under `Canonical Delegation Brief Contract`.

This enforcement spec inherits that canonical contract by reference and must not redefine a divergent required-field list.

Every delegated task brief must contain every canonical required field from that source of truth. If any canonical field is missing, the brief is non-compliant.

Canonical-field omissions are contract failures, not recommendations. This includes omissions of `operating_root`, `project_context_reference`, `source_spec_reference`, and `required_return_format`.

## Deterministic Task Rules

### One Primary Objective

Each delegated task must have one primary objective only.

Examples:

- add export validation
- refine package landing docs
- add regression coverage

Non-compliant example:

- implement export validation, improve docs, and rewrite tests

### Exact File Scope

Each task must list the exact files that the worker may edit.

Rules:

- file paths must be explicit;
- directories alone are not sufficient unless the task is explicitly directory-scoped;
- if the task is test-only, `src/` files must be out of scope;
- if a worker needs a file outside scope, the worker must stop and report the mismatch.

### Explicit Out-of-Scope Boundaries

Each task must declare concrete exclusions.

Examples:

- no schema changes
- no CLI changes
- no new feature work
- no runtime behavior changes

### Validation Commands Required

Every task must include the exact commands needed to validate the slice.

Rules:

- commands must be copyable;
- commands should reflect real local paths;
- when real-corpus validation matters, include it explicitly;
- if network may be required, that must be acknowledged at orchestration time.

### Local Evidence Required

Each task must include local evidence so the worker does not rediscover known facts.

Examples:

- current artifact paths
- known counts
- known warning categories
- known output layout
- already-completed phases

### Stop-On-Scope-Mismatch Rule

If the worker discovers that the task cannot be completed inside scope, the worker must stop and report:

- the missing file or boundary;
- why it is required;
- the smallest possible scope expansion.

Silent scope expansion is non-compliant.

## Required Return Contract

This section is normative.

The canonical `required_return_format` field in every worker brief must require this exact return structure:

- files changed
- behavioral change
- validation commands run and results
- any task-local risk

If the `required_return_format` field is omitted, the brief is non-compliant even if other completion guidance is present.

This makes completion review deterministic for the orchestrator.

## Documentation Role Enforcement

The template must distinguish these roles:

### Package Landing Docs

Purpose:

- package overview;
- command inventory;
- links to deeper docs.

Must not become the full user guide.

### Human User Guide

Purpose:

- command usage;
- workflows;
- examples;
- outputs;
- troubleshooting.

### Operator Guide

Purpose:

- exact action order;
- execution steps;
- upload steps;
- handoff guidance.

### Agent Guide

Purpose:

- read order;
- source-of-truth files;
- warning interpretation;
- navigation guidance;
- anti-patterns.

### Generated Runtime Agent README

Purpose:

- concise mode-specific runtime orientation;
- current validation state;
- file-entry guidance;
- machine-readable truth pointers.

Rules:

- concise;
- mode-specific;
- no broad tutorial prose;
- no duplicated operator checklist.

## Generated Agent README Contract

This section is normative.

All generated runtime agent READMEs must use the same logical section order:

1. `mode`
2. `start_here`
3. `machine_readable_truth`
4. `read_order`
5. `primary_content_files`
6. `validation_status`
7. `warning_policy`

Rules:

- section order must be stable;
- headings may be rendered in markdown, JSON-backed markdown, or equivalent text form;
- the prose may vary by mode;
- the section intent may not vary by mode.

## Operator vs Agent Separation Rules

Operator docs may include:

- exact upload order;
- exact execution sequence;
- handoff steps;
- environment actions.

Agent docs may include:

- source-of-truth file references;
- read order;
- validation interpretation;
- content-file orientation;
- warning guidance.

Operator docs may point to agent docs.
Agent docs may point to operator docs.

Operator docs must not become the main semantic reading guide.
Agent docs must not duplicate operator checklists.

## Validation and QA Enforcement

Every implementation track should include these phases when applicable:

1. fixture validation
2. scoped task validation
3. real-corpus or real-output regeneration
4. independent orchestrator verification
5. regression coverage

## Required Validation Dimensions

Depending on the feature, validators should be able to check:

- required files exist;
- structured payloads load correctly;
- checksums match;
- coverage is complete;
- ordering is deterministic;
- wrapper or delimiter integrity holds;
- version and identity remain consistent;
- generated docs match the intended role;
- generated agent README section order is correct.

## Warning Classification Rule

Warnings should be classified by usefulness, not only counted.

Recommended categories:

- navigation-relevant
- expected text-only loss
- source-content issue
- external issue
- operator-only warning

Generated runtime docs should summarize what warning classes matter.
Full detail belongs in the machine-readable validation report.

## Orchestrator Responsibilities

The orchestration agent should:

- prepare the task brief from a spec;
- include local evidence to avoid worker rediscovery;
- dispatch only one micro-task objective at a time;
- monitor the worker;
- detect scope mismatch or boundary violations;
- independently rerun validation commands;
- inspect real generated artifacts when the task affects outputs;
- decide whether the next task is now narrower and clearer.

Validator naming, blocking behavior, and rollout order are defined in `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md`.

## Worker Responsibilities

The delegated worker should:

- stay inside scope;
- avoid unnecessary research;
- implement only the requested slice;
- stop on scope mismatch;
- run the required validation commands;
- return the required structured completion summary.

## Recommended Micro-Task Sequence

Use this sequence when practical:

1. contract and schema
2. core implementation
3. validator and QA hardening
4. user/operator docs
5. generated agent docs
6. regression coverage
7. real-corpus verification

## Enforcement Mechanisms

The template should support at least one of these enforcement methods:

### Prompt-Level Enforcement

- task brief template with mandatory headings;
- orchestrator prompts that refuse incomplete briefs;
- worker prompts that require stop-on-scope-mismatch behavior.

### File-Level Enforcement

- reusable markdown templates for tasks;
- reusable docs-role contract docs;
- reusable generated agent README contract docs.

### Programmatic Enforcement

Optional but recommended:

- validators or lint checks for task brief completeness;
- checks that generated agent READMEs follow required section order;
- checks that test-only tasks did not change runtime files;
- checks that operator docs and agent docs do not duplicate forbidden sections.

## Recommended Reusable Templates

The template package should provide:

- task brief template
- docs-task template
- validation-task template
- regression-task template
- real-output verification checklist
- generated agent README contract checklist

## Acceptance Criteria

This template-level effort is complete when:

- delegated task briefs can be produced from a stable contract;
- generated runtime agent docs can be checked against a stable section order;
- documentation surfaces are separated by audience role;
- workers can be instructed without rediscovering known local facts;
- orchestrators can independently validate each delegated slice;
- regression coverage protects the documentation-role separation and task-brief contract.

## Anti-Patterns

- broad multi-purpose worker tasks;
- hidden scope expansion;
- vague file scope such as “edit whatever is needed”;
- missing validation commands;
- duplicated operator checklist inside agent docs;
- duplicated agent reading semantics across unrelated docs without one canonical contract;
- prose that competes with machine-readable truth;
- skipping real-output verification after changing generated docs.

## Suggested Next Implementation Steps

For a package adopting this spec:

1. add reusable task brief templates;
2. add reusable docs-role contract docs;
3. add generated agent README contract checks;
4. add a brief validator or lint step;
5. wire these checks into orchestration before dispatch.
