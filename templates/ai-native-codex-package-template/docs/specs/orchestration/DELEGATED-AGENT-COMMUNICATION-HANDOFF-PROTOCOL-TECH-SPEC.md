# Delegated Agent Communication And Handoff Protocol Tech Spec

## Purpose

This specification defines a reusable, agent-optimized communication and handoff protocol between:

- an orchestration agent; and
- a delegated implementation worker agent.

It is intended for template-based AI-native packages that use delegated execution and validation loops.

This spec defines:

- the communication model;
- handoff boundaries;
- required inputs to workers;
- required outputs from workers;
- monitoring and state tracking expectations;
- protocol options from lightweight to strongly typed.

This is a template-level contract, not a project-specific implementation.

## Problem Statement

Most delegated agent systems have communication, but not a single explicit protocol.

Communication is often spread across:

- prompt files;
- wrapper JSON;
- logs;
- validation reports;
- changed-file inspection;
- ad hoc orchestrator notes.

This creates predictable weaknesses:

- handoff boundaries are implicit;
- scope mismatch handling is inconsistent;
- monitoring is fragmented;
- completion is inferred instead of declared;
- continuation logic depends on the orchestrator’s memory rather than a stable contract.

The template should therefore define a reusable protocol for agent-to-agent task handoff and monitoring.

## Goals

- make orchestrator-to-worker handoff explicit and deterministic;
- make worker-to-orchestrator completion and risk reporting explicit;
- support monitoring through machine-readable state and evidence;
- support autonomous and semi-autonomous orchestration loops;
- separate communication layers from implementation details.

## Non-Goals

- this spec does not define one transport mechanism only;
- this spec does not require conversational back-and-forth chat;
- this spec does not replace task briefs, specs, or validation rules;
- this spec does not define business-domain payload schemas.

## Normative and Explanatory Sections

For protocol payload requirements, the normative sections in this document are:

- `Minimum Handoff Contract`
- `Canonical Worker Result Schema`
- `Scope Mismatch Protocol`
- `Validation Result Protocol`

Protocol options, monitoring guidance, and example payloads are explanatory unless a section explicitly says otherwise.

## Current Communication Model

In many delegated systems, communication already exists in partially structured form:

- orchestrator sends:
  - task brief
  - file scope
  - validation commands
  - local evidence
- worker returns:
  - changed files
  - behavior summary
  - validation results
  - risk notes
- wrapper/runtime provides:
  - preflight evidence
  - policy decision
  - execution metadata
- tracking system provides:
  - event ledger
  - state snapshot
  - evidence manifest

This is useful, but fragmented.

The goal of this spec is to unify those pieces into a clearer handoff contract.

## Communication Layers

The protocol should be understood in layers.

### Layer 1: Task Brief Layer

The orchestrator hands the worker:

- objective;
- scope;
- constraints;
- validation commands;
- local evidence;
- return contract.

### Layer 2: Execution Control Layer

The runtime wrapper or dispatch layer provides:

- preflight validation;
- execution mode;
- sandbox or policy decision;
- required evidence binding;
- fail-closed behavior for invalid dispatch.

### Layer 3: Worker Result Layer

The worker returns:

- status;
- files changed;
- validation results;
- scope mismatch or block reason;
- task-local risk.

### Layer 4: Monitoring Layer

The tracking system persists:

- task events;
- task status;
- evidence refs;
- validation summaries;
- lineage or retry metadata.

## Boundary Model

The protocol should enforce a clear separation of responsibilities.

### Orchestrator Responsibilities

- select the task;
- prepare the brief;
- include local evidence;
- validate the brief before dispatch;
- dispatch the worker;
- monitor progress;
- rerun validation;
- decide whether to continue, retry, escalate, or stop.

### Delegated Worker Responsibilities

- stay within scope;
- implement the requested slice;
- stop on scope mismatch;
- run the required validation commands;
- return a structured completion summary.

### Wrapper or Dispatch Runtime Responsibilities

- validate the dispatch request;
- enforce contract and policy gates;
- bind execution to preflight evidence when required;
- emit deterministic execution metadata.

### Tracking Layer Responsibilities

- persist events;
- render task state;
- preserve evidence lineage;
- support audit and replay.

## Minimum Handoff Contract

This section is normative.

Every worker handoff must include the canonical delegation brief contract defined in `DELEGATION-DOCS-META-TEMPLATE.md` under `Canonical Delegation Brief Contract`.

Required canonical brief fields:

- `task_name`
- `operating_root`
- `project_context_reference`
- `source_spec_reference`
- `objective`
- `files_in_scope`
- `required_changes`
- `acceptance_criteria`
- `validation_commands`
- `out_of_scope`
- `local_evidence`
- `task_boundary_rules`
- `required_return_format`

Required protocol field:

- `task_id`

`task_id` is protocol metadata. It is required for the handoff protocol, but it is not part of the canonical delegation brief contract itself.

If any canonical brief field or required protocol field is missing, the handoff is incomplete.

## Canonical Worker Result Schema

This section is normative.

This section defines the only canonical worker result schema in this document.
Later payload snippets and JSON examples are illustrative only and must not be treated as alternate schemas.

Every worker completion response must contain these required top-level fields:

- `status`
- `files_changed`
- `behavioral_change`
- `validation_results`
- `task_local_risk`

Allowed optional top-level fields:

- `scope_mismatch`
- `blocked_reason`
- `artifacts_updated`
- `notes_for_next_task`

Field semantics:

- `status`: required protocol outcome for the delegated task result
- `files_changed`: required list of files changed within declared scope; use an empty list when no file changes were made
- `behavioral_change`: required concise summary of the implemented behavior change or explicit statement that no behavior changed
- `validation_results`: required list of structured validation command results defined in `Validation Result Protocol`
- `task_local_risk`: required concise statement of residual task-local risk, or an explicit statement that no task-local risk remains
- `scope_mismatch`: optional structured scope-expansion request; present only when `status` is `scope_mismatch`
- `blocked_reason`: optional blocking explanation; present when `status` is `blocked`
- `artifacts_updated`: optional list of generated or supporting artifacts updated by the task
- `notes_for_next_task`: optional concise handoff note for the orchestrator or next delegated worker

## Status Model

This section is normative for worker result `status` values and explanatory for orchestrator task states.

Allowed worker result `status` values:

- `success`
- `blocked`
- `scope_mismatch`

Worker result `status` must not reuse orchestrator task states such as `pending`, `in_progress`, `completed`, `failed`, or `escalated`.
Worker result `status` must not reuse approval states such as `approval_required` or `approval_granted`.

Status meanings for the canonical worker result schema:

- `success`: the worker completed the requested task within scope and returned the required schema fields
- `blocked`: the worker could not complete the task within the current task boundary and must explain the stop condition through `blocked_reason` and `validation_results` as applicable
- `scope_mismatch`: the worker determined that completion would require a file, artifact, or task expansion outside the declared scope and must populate `scope_mismatch`

Recommended orchestrator task states:

- `pending`
- `brief_ready`
- `dispatched`
- `in_progress`
- `validation_pending`
- `completed`
- `blocked`
- `failed`
- `escalated`

## Protocol Options

The template should support multiple protocol styles.

## Option 1: Brief-And-Summary Protocol

### Description

Input:

- markdown or text brief

Output:

- short structured completion summary

### Strengths

- easiest to adopt;
- human-readable;
- good for manual orchestration.

### Weaknesses

- harder to validate mechanically;
- more reliant on orchestrator interpretation.

## Option 2: Wrapper-Evidence Protocol

### Description

Input:

- task brief plus validated preflight evidence

Output:

- wrapper execution metadata plus worker result

### Strengths

- strong dispatch safety;
- deterministic policy enforcement;
- good for fail-closed execution.

### Weaknesses

- still not a complete project-level state protocol by itself.

## Option 3: Ledger-Backed Protocol

### Description

Each dispatch and completion is reflected in:

- event ledger
- snapshot state
- evidence manifest

### Strengths

- auditable;
- recoverable;
- strong for long-running orchestration.

### Weaknesses

- requires tracking infrastructure;
- more moving pieces.

## Option 4: Typed State-Machine Protocol

### Description

All agent communication is mapped to typed state transitions and structured payloads.

### Strengths

- strongest for autonomous loops;
- easiest to automate continuation logic;
- easiest to gate on validation and policy.

### Weaknesses

- highest implementation effort.

## Recommended Default

Use a hybrid of:

- brief-and-summary
- wrapper evidence
- ledger-backed tracking

Then evolve toward typed state-machine protocol if full autonomy is needed.

## Required Monitoring Signals

The orchestrator should be able to observe:

- worker dispatch started
- worker active or silent
- changed files detected
- validation started
- validation passed or failed
- scope mismatch reported
- completion summary received

Recommended monitoring sources:

- wrapper execution result
- local changed-file inspection
- task event ledger
- task snapshot
- evidence manifest
- validation report files

## Handoff Rules

### Handoff In

The orchestrator must provide:

- exact file scope;
- exact validation commands;
- local evidence;
- explicit stop-on-scope-mismatch rule.

### Handoff Out

The worker must provide:

- exact changed files;
- exact validation command results;
- any risk or mismatch;
- explicit statement of completion or block.

### Handoff Quality Rule

A handoff is complete only when both:

- the worker return contract is satisfied; and
- the orchestrator independently validates the result.

## Scope Mismatch Protocol

If the worker discovers a needed file outside scope, the worker should return:

- `status: scope_mismatch`
- `required_file`
- `why_needed`
- `smallest_scope_expansion`

The orchestrator should then:

- stop current task continuation;
- review whether to expand scope or create a new task;
- avoid silent broadening.

## Validation Result Protocol

This section is normative for the record shape used inside `validation_results`.

Validation results should be represented in a structured form whenever possible.

Each validation result record must contain:

- `command`
- `status`
- `exit_code`
- `summary`
- `artifacts_produced`

This allows the orchestrator to reason about:

- what was run;
- what passed;
- what failed;
- whether real-output verification occurred.

## Evidence Protocol

Local evidence included in the brief should be treated as authoritative context for the worker.

Recommended evidence types:

- current artifact paths
- known counts
- current warning categories
- current generated output paths
- already-completed tasks
- required section order or contract expectations

Workers should not re-research facts already included as local evidence unless needed to verify the work itself.

## Escalation Protocol

The worker should explicitly escalate through structured return states when:

- scope mismatch occurs;
- validation cannot be completed;
- a required artifact is missing;
- the task is underspecified;
- user approval would be required.

Recommended fields:

- `status`
- `blocked_reason`
- `required_input`
- `recommended_next_step`

## Agent-Optimized Monitoring Patterns

The most effective monitoring patterns are:

- compare changed files to declared scope;
- compare actual outputs to required artifacts;
- compare validation results to required commands;
- inspect generated runtime docs directly when documentation tasks are involved;
- use snapshots and ledgers for continuity across long sessions.

## Recommended Handoff Templates

The template package should eventually include reusable communication templates for:

- task brief
- worker completion summary
- scope mismatch report
- validation result record
- escalation report
- final verification report

## Suggested Future Structured Payload

This section is explanatory.

The following payload is an illustrative example of the canonical worker result schema above.
It is not a second schema and does not change the required or optional fields defined in `Canonical Worker Result Schema`.

Example worker result payload:

```json
{
  "task_id": "D-002",
  "status": "success",
  "files_changed": [
    "src/example.py",
    "tests/test_example.py"
  ],
  "behavioral_change": "Added validation and updated output formatting.",
  "validation_results": [
    {
      "command": "pytest -q tests/test_example.py",
      "status": "pass",
      "exit_code": 0,
      "summary": "12 passed"
    }
  ],
  "task_local_risk": "No known blocking risk."
}
```

This is illustrative only.

## Recommended Enforcement Hooks

This protocol works best when paired with:

- brief contract validation before dispatch;
- scope validation after worker completion;
- generated-doc contract validation;
- real-output verification gates.

See also:

- `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`
- `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md`
- `ORCHESTRATOR-AUTONOMY-LOOP-TECH-SPEC.md`

## Anti-Patterns

- inferring task completion from silence;
- using logs as the only handoff contract;
- allowing workers to return free-form completion without structure;
- letting the orchestrator rely only on memory of prior steps;
- skipping changed-file scope checks;
- treating validation as optional narrative instead of a protocol output.

## Acceptance Criteria

This protocol spec is good enough to implement when:

- orchestrator and worker responsibilities are clearly separated;
- the minimum handoff contract is explicit;
- the minimum worker return contract is explicit;
- monitoring signals are identified;
- scope mismatch handling is defined;
- the protocol options are clear enough for a project to choose an implementation path.
