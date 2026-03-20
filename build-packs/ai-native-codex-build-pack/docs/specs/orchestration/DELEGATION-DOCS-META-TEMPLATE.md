# Delegation and Agent Docs Meta Template

## Purpose

Use this document as a reusable template for:

- orchestrating implementation through narrow delegated worker tasks;
- designing human-facing, operator-facing, and agent-facing documentation surfaces;
- keeping machine-readable artifacts as the source of truth;
- preventing documentation drift through real-output validation and regression coverage.

This is a meta template.

It is intentionally project-agnostic and should be adapted to the package or workflow being built.

## Core Meta Principles

### 1. Separate Artifact Roles Early

Define the role of each artifact before implementation:

- package landing docs;
- human user guide;
- operator runbook or upload guide;
- agent guide;
- generated runtime READMEs;
- machine-readable manifests, indexes, plans, and validation reports.

Each artifact should have one primary audience and one primary job.

### 2. Machine-Readable Files Are the Source of Truth

Prose should route readers to structured artifacts.

Prefer:

- manifests;
- indexes;
- plans;
- reports;
- checksums;
- ordered inventories.

Do not let prose become the most authoritative representation of structure or state.

### 3. Generated Agent Docs Must Use a Stable Contract

Generated agent-facing runtime docs should follow one predictable section order across modes.

Recommended shared contract:

1. `mode`
2. `start_here`
3. `machine_readable_truth`
4. `read_order`
5. `primary_content_files`
6. `validation_status`
7. `warning_policy`

The prose can vary by mode.
The section order and intent should not.

### 4. Operator Actions and Agent Interpretation Must Be Separated

Operator docs explain:

- what to upload;
- what to run;
- what to click;
- what to hand off;
- in what order.

Agent docs explain:

- what files to read first;
- what files are authoritative;
- how to navigate the content;
- how to interpret warnings and validation state.

Do not duplicate upload or run checklists inside agent docs.

### 5. Real Output Validation Matters More Than Synthetic Confidence

Use synthetic fixtures for fast iteration.
Use real artifact generation for final acceptance.

Synthetic tests alone often miss:

- source-specific edge cases;
- noisy content;
- path resolution failures;
- contract drift;
- guidance drift between runtime docs and actual outputs.

## Meta Optimizations to Reuse

- classify warnings by usefulness, not just by count;
- keep transport artifacts separate from working artifacts;
- make generated summaries short and index-like;
- standardize reading order for agents;
- use exact file budgets and deterministic bundle rules when packaging content;
- validate coverage, ordering, checksum integrity, and wrapper integrity explicitly;
- prefer deterministic output names and stable key ordering;
- use runtime readmes as thin routers to the structured files;
- add regression tests after each behavior slice stabilizes.

## Delegation Strategy Template

## Delegation Rules

- Each task must have one primary objective.
- Each task must list exact files in scope.
- Each task must declare what is out of scope.
- Each task must include validation commands.
- Each task must include local evidence paths so the worker does not need to rediscover structure.
- Each task must require the worker to stop and report scope mismatch instead of silently broadening.
- Each task must require a short structured return.
- The orchestrator should independently validate after each worker completes.

## Recommended Sequencing Pattern

Use this order when possible:

1. contract and schema
2. core implementation
3. validation and QA
4. human/operator docs
5. agent docs
6. regression coverage
7. real-corpus or real-environment verification

Use smaller slices if a step is too broad.

## Normative and Explanatory Sections

For delegation brief structure, the normative sections in this document are:

- `Canonical Delegation Brief Contract`
- `Micro-Task Brief Template`

All other sections in this document are explanatory reuse guidance unless a section explicitly says otherwise.

## Canonical Delegation Brief Contract

This section is normative.

This document is the single canonical source of truth for the delegation brief contract used by this template package.

Every delegated implementation brief must contain all of the following required fields exactly once:

1. `task_name`
2. `operating_root`
3. `project_context_reference`
4. `source_spec_reference`
5. `objective`
6. `files_in_scope`
7. `required_changes`
8. `acceptance_criteria`
9. `validation_commands`
10. `out_of_scope`
11. `local_evidence`
12. `task_boundary_rules`
13. `required_return_format`

Rendered briefs may use the human-readable labels shown in the template below, but the required field set above is the canonical contract.
The `required_return_format` field should instruct the worker to return the canonical worker result schema defined in `DELEGATED-AGENT-COMMUNICATION-HANDOFF-PROTOCOL-TECH-SPEC.md` under `Canonical Worker Result Schema`.

Canonical rendering map for the header block:

- `task_name`: `# Task <ID>: <Short Name>`
- `operating_root`: `Operate only within:`
- `project_context_reference`: `Use:`
- `source_spec_reference`: `Implement exactly this task from:`

## Micro-Task Brief Template

This section is normative.

```md
# Task <ID>: <Short Name>

You are the delegated implementation worker for <project or package>.

Operate only within:
- `<repo or package root>`

Use:
- `<project-context path>`

Do not research product behavior. Use the current verified package and local artifacts already present in the repo.

Implement exactly this task from:
- `<spec path>`

Task section:

## Task <ID>: <Short Name>

### Objective
<One primary objective only>

### Files In Scope
- `<path>`
- `<path>`

### Required Changes
- `<required change>`
- `<required change>`

### Acceptance Criteria
- `<observable acceptance>`
- `<observable acceptance>`

### Validation Commands
- `<command>`
- `<command>`

### Out of Scope
- `<boundary>`
- `<boundary>`

### Local Evidence
- `<artifact path>`
- `<artifact path>`
- `<fact the worker should not rediscover>`

Task boundary rules:
- Change only the files listed in scope.
- Do not continue to the next task.
- If the task cannot be completed inside scope, stop and report the scope mismatch instead of broadening.
- Run the validation commands before you stop.

Return exactly:
- `status`
- `files_changed`
- `behavioral_change`
- `validation_results`
- `task_local_risk`
- `scope_mismatch` when the task cannot be completed inside scope
- `blocked_reason` when the task is blocked for a task-local reason
```

## Recommended Micro-Task Shapes

### Implementation Slice

Use when behavior changes are needed.

Keep scope to:

- one module or one tightly-related cluster;
- one regression surface;
- one validation outcome.

### Validation Slice

Use when structure already exists but trust is weak.

Focus on:

- required files;
- checksums;
- coverage;
- ordering;
- wrapper integrity;
- version consistency;
- cross-file invariants.

### Documentation Slice

Use when behavior is stable and docs need cleanup.

Split by audience:

- package landing docs;
- user guide;
- operator docs;
- agent docs;
- generated runtime docs.

### Regression Slice

Use after behavior and docs stabilize.

Keep it test-only when possible.

## Agent Documentation Rules Template

## Audience Roles

### Package Landing Docs

Use for:

- short overview;
- command list;
- links to deeper docs.

Do not turn the landing page into the full manual.

### Human User Guide

Use for:

- commands;
- workflows;
- examples;
- outputs;
- troubleshooting.

### Operator Guide

Use for:

- upload/run/handoff steps;
- exact order of actions;
- environment-specific operational guidance.

### Agent Guide

Use for:

- read order;
- source-of-truth file policy;
- warning interpretation;
- navigation guidance;
- anti-patterns.

### Generated Runtime Agent README

Use for:

- concise mode-specific routing;
- current validation state;
- immediate file-entry guidance;
- links to the authoritative structured files.

Do not make it a full tutorial.

## Generated Agent README Rules

- keep it concise;
- keep it mode-specific;
- use the shared section contract;
- point to machine-readable truth explicitly;
- include validation context if it affects trust;
- separate operator actions from agent semantics;
- prefer relative paths plus logical role labels where useful.

## Operator README Rules

- operator-first language;
- exact action order;
- file submission or execution order when relevant;
- concise cross-reference to the agent README for semantic interpretation;
- no duplicate agent navigation tutorial.

## Warning Policy Rules

When warnings exist:

- classify them into meaningful categories;
- identify which categories are high-signal for agent behavior;
- identify which categories are expected or low-signal;
- expose a short guidance line in runtime docs;
- keep the full details in the validation report.

## Regression Coverage Template

Add targeted tests for:

- package landing docs linking to the right deeper docs;
- stable generated agent README section order;
- separation between operator checklists and agent interpretation;
- machine-readable source-of-truth references;
- deterministic output ordering;
- failure on checksum, coverage, or missing-file regressions.

Use real artifact regeneration for final verification when feasible.

## Independent Validation Checklist

After each delegated slice, the orchestrator should verify:

- file-scope compliance;
- acceptance criteria;
- stated validation commands;
- real artifact behavior if applicable;
- no unintended scope drift;
- whether the next task is now narrower and clearer.

## Anti-Patterns

- broad multi-purpose tasks;
- silent scope expansion by the worker;
- asking the worker to rediscover structure already known locally;
- mixing operator instructions into agent docs;
- using prose as the only source of truth;
- skipping real-output verification after structural changes;
- letting generated runtime docs drift from actual artifact behavior;
- treating all warnings as equally important.

## Reusable Success Criteria

You can usually call the effort successful when:

- each doc surface has one clear audience;
- generated agent docs share one contract shape;
- operator docs and agent docs no longer duplicate each other;
- machine-readable files are clearly identified as authoritative;
- delegated work was completed through narrow, validated slices;
- regression coverage locks in the separation and structure.
