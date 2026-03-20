# Orchestration Pack Modernization Implementation Tech Spec

## Purpose

Modernize the `ai-native-codex-package-template` project pack so orchestration agents and delegated worker agents operate from enforceable, machine-readable contracts instead of relying primarily on prose guidance.

The goal is agent-optimized software delivery:

- deterministic task selection
- deterministic delegation briefs
- deterministic worker return payloads
- deterministic approval handling
- deterministic generated agent README structure
- pre-dispatch and post-execution validation gates

This specification defines the implementation work needed to convert the current template-pack orchestration specs into operational scaffolding, contracts, validators, and runtime integration points.

## Problem Statement

The template pack now has strong orchestration policy and delegation rules in prose, but they are still primarily Markdown specifications. That is useful for humans, but not sufficient for reliable autonomous or semi-autonomous execution.

Current limitations:

- brief and worker-result rules are documented, but not enforced through schemas
- templates are not yet guaranteed to emit the canonical contract fields
- validator names and rollout order are defined, but not implemented as first-class package assets
- the orchestration runtime does not yet consume machine-readable task records and approval state by default
- generated agent docs are governed by specs, but not yet backed by a formal contract file

## Desired End State

The project pack should provide:

- machine-readable contracts for orchestration and delegation artifacts
- template files that emit those contracts by default
- validators that enforce those contracts
- runtime/orchestration entrypoints that call those validators before dispatch and after worker completion
- a minimum rollout policy that can be adopted incrementally without implementing the full autonomy stack at once

## Design Principles

### 1. Machine-Readable First

Normative orchestration rules must be encoded as machine-readable artifacts wherever feasible.

Preferred precedence order:

1. machine-readable contract
2. validator result
3. generated template
4. prose specification

### 2. One Source Of Truth Per Concern

Each concern should have one authoritative machine-readable artifact:

- delegation brief structure and rendering rules
- worker result structure
- task record structure and per-task brief source values
- approval state value shape
- approval transitions and dispatch policy
- generated agent README structure
- rollout order policy

### 3. Prose Specs Remain Normative For Humans

The Markdown tech specs remain the human-readable explanation layer. They should describe the rules, but runtime enforcement must read the contract files and validator outputs.

### 4. Determinism Over Heuristics

If a runtime decision affects delegation, continuation, or generated documentation structure, it must be based on declared fields and validator outcomes rather than inferred intent.

## Repository Additions

Add the following package assets:

```text
src/ai_native_package/
  contracts/
    delegation-brief.schema.json
    worker-result.schema.json
    task-record.schema.json
    approval-state.schema.json
    predispatch-decision.schema.json
    posttask-decision.schema.json
    generated-agent-readme.contract.json
  policies/
    approval-policy.json
    minimum-rollout-order.json
  templates/
    delegation-brief.md
    worker-result.json
    task-record.yaml
    generated-agent-readme.md
  validators/
    validate_task_brief.py
    validate_task_scope.py
    validate_task_order_and_approval.py
    validate_generated_agent_readme.py
  orchestration/
    predispatch.py
    posttask.py
```

Exact filenames may vary if they remain consistent with package naming, but equivalent content is required.

## Contract Definitions

### 1. Delegation Brief Contract

File:

- `src/ai_native_package/contracts/delegation-brief.schema.json`

Must encode the canonical brief contract already defined in the template specs.

Required fields:

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

Additional constraints:

- `files_in_scope` must be a non-empty ordered list
- `validation_commands` must be a non-empty ordered list
- `objective` must be a single primary objective string, not an array of unrelated goals
- `required_return_format` must reference the canonical worker result schema fields, not ad hoc prose

### 2. Worker Result Contract

File:

- `src/ai_native_package/contracts/worker-result.schema.json`

Required fields:

- `status`
- `files_changed`
- `behavioral_change`
- `validation_results`
- `task_local_risk`

Optional fields:

- `scope_mismatch`
- `blocked_reason`
- `artifacts_updated`
- `notes_for_next_task`

Status enum must be:

- `success`
- `blocked`
- `failed`
- `scope_mismatch`
- `partial`

Additional constraints:

- `status` must not reuse orchestrator task states
- `status` must not reuse approval states
- `validation_results` must contain structured command/result records, not raw unparsed transcript text only

### 3. Task Record Contract

File:

- `src/ai_native_package/contracts/task-record.schema.json`

Authority and role:

- the task record is the authoritative machine-readable source for task orchestration metadata and all per-task values required to render the canonical delegation brief
- the delegation brief is a rendered handoff artifact derived from the task record plus `delegation-brief.schema.json`; it is not an independent authority for task content
- if a stored delegation brief is loaded, every canonical brief field must match the authoritative task record or pre-dispatch validation fails

Required fields:

- `task_id`
- `task_name`
- `operating_root`
- `project_context_reference`
- `objective`
- `source_spec_reference`
- `required_changes`
- `acceptance_criteria`
- `out_of_scope`
- `local_evidence`
- `task_boundary_rules`
- `required_return_format`
- `declared_order`
- `files_in_scope`
- `validation_commands`
- `approval_requirement`
- `approval_state`

Optional fields:

- `dependencies`
- `dependency_unlock_score`
- `risk_reduction_score`
- `task_group`
- `notes`

Additional constraints:

- `task_id` must be stable and unique
- `declared_order` must be deterministic
- `dependencies` must reference valid `task_id` values
- no canonical delegation brief field may be omitted from the task record and later inferred from prose-only guidance, operator memory, or repository conventions
- `operating_root` and `project_context_reference` must be explicit task-record fields even when a batch shares common defaults
- `required_return_format` must explicitly reference the canonical worker result schema defined in `DELEGATED-AGENT-COMMUNICATION-HANDOFF-PROTOCOL-TECH-SPEC.md`
- `approval_requirement` and `approval_state` are authoritative for dispatch eligibility metadata, but they are not canonical delegation brief fields unless separately mirrored outside the canonical brief contract
- optional scoring fields are only usable if explicitly present

Canonical delegation brief field sources:

- `task_name`: from `task_record.task_name`; the rendered header may prepend `task_record.task_id` for protocol labeling, but the brief field value comes from `task_name`
- `operating_root`: from `task_record.operating_root`
- `project_context_reference`: from `task_record.project_context_reference`
- `source_spec_reference`: from `task_record.source_spec_reference`
- `objective`: from `task_record.objective`
- `files_in_scope`: from `task_record.files_in_scope`
- `required_changes`: from `task_record.required_changes`
- `acceptance_criteria`: from `task_record.acceptance_criteria`
- `validation_commands`: from `task_record.validation_commands`
- `out_of_scope`: from `task_record.out_of_scope`
- `local_evidence`: from `task_record.local_evidence`
- `task_boundary_rules`: from `task_record.task_boundary_rules`
- `required_return_format`: from `task_record.required_return_format`

Runtime rule:

- a runtime may either render the canonical delegation brief directly from the authoritative task record or load a previously rendered brief and validate it against the task record field-for-field

### 4. Approval State Contract

File:

- `src/ai_native_package/contracts/approval-state.schema.json`

This schema is a pure value-shape contract for the `approval_state` field carried by task metadata and runtime decisions.
It defines only the legal state values and must not encode transition rules, dispatch rules, or continuation policy.

Enum values:

- `approval_required`
- `approval_pending`
- `approval_granted`
- `approval_denied`
- `approval_not_required`

Separate approval policy artifact:

- `src/ai_native_package/policies/approval-policy.json`

This policy artifact should define:

- allowed transitions between approval states
- which approval states are dispatchable for autonomous continuation
- the blocking outcome to emit when the current approval state is not dispatchable

Dispatchability policy:

- autonomous dispatch is allowed only for `approval_not_required` and `approval_granted`

Policy consumers:

- `validate-task-order-and-approval` must validate `approval_state` against `approval-state.schema.json` and compute dispatchability from `approval-policy.json`
- `src/ai_native_package/orchestration/predispatch.py` must consume the validator outcome as the runtime gate for autonomous dispatch rather than redefining approval transitions inline

### 5. Predispatch Decision Contract

File:

- `src/ai_native_package/contracts/predispatch-decision.schema.json`

Purpose:

- define the canonical machine-readable output of the pre-dispatch runtime gate
- make dispatch authorization, blocking, and escalation outcomes auditable and replayable from persisted inputs

Required fields:

- `task_id`
- `decision`
- `resulting_task_state`
- `task_record_reference`
- `delegation_brief_reference`
- `approval_state`
- `validator_results`
- `persisted_artifacts`

Optional fields:

- `blocking_reasons`
- `escalation_reason`
- `dispatch_attempt`
- `emitted_at`

Decision enum must be:

- `dispatch`
- `blocked`
- `escalate`

Mapping to orchestrator task states:

- `dispatch` maps to `ready_to_dispatch` as the gate output state; a runtime may transition to `in_progress` only after worker launch succeeds
- `blocked` maps to `blocked`
- `escalate` maps to `escalated`

Additional constraints:

- `validator_results` must include structured results for both `validate-task-brief` and `validate-task-order-and-approval`
- `resulting_task_state` must match the declared `decision`
- `task_record_reference` and `delegation_brief_reference` must identify the exact artifacts used to compute the decision
- `blocking_reasons` must be non-empty when `decision` is `blocked`
- `escalation_reason` must be present when `decision` is `escalate`
- the decision must be derivable only from persisted task metadata, brief content, approval policy, and validator outcomes

Persisted artifacts for audit and replay:

- persist one `predispatch-decision` artifact for every dispatch attempt, even when dispatch is blocked
- persist or reference the exact task record, delegation brief, approval policy version, and validator-result artifacts used to compute the decision
- persist enough stable references or content digests for a replay runner to recompute the same decision without relying on prose logs or operator memory

### 6. Post-Task Decision Contract

File:

- `src/ai_native_package/contracts/posttask-decision.schema.json`

Purpose:

- define the canonical machine-readable output of the post-task runtime gate
- make completion, retry, blocking, and escalation outcomes auditable and replayable from persisted worker outputs and validator evidence

Required fields:

- `task_id`
- `decision`
- `resulting_task_state`
- `worker_result_reference`
- `worker_result_status`
- `validator_results`
- `persisted_artifacts`

Optional fields:

- `blocking_reasons`
- `retry_reason`
- `escalation_reason`
- `emitted_at`

Decision enum must be:

- `complete`
- `blocked`
- `retry`
- `escalate`

Mapping to orchestrator task states:

- `complete` maps to `completed`
- `blocked` maps to `blocked`
- `retry` maps to `retry_pending`
- `escalate` maps to `escalated`

Additional constraints:

- `validator_results` must include the worker-result contract validation outcome and any executed post-task validators
- `resulting_task_state` must match the declared `decision`
- `worker_result_reference` must identify the exact worker-result artifact that was evaluated
- `blocking_reasons` must be non-empty when `decision` is `blocked`
- `retry_reason` must be present when `decision` is `retry`
- `escalation_reason` must be present when `decision` is `escalate`
- the decision must be derivable only from the persisted worker result, rerun validation outputs, and declared runtime policy inputs

Persisted artifacts for audit and replay:

- persist one `posttask-decision` artifact for every completed worker attempt, including retries and escalations
- persist or reference the evaluated worker result, task-scope validator output, rerun validation-command results, and generated-agent-readme validation output when applicable
- persist enough stable references or content digests for a replay runner to recompute the same post-task decision without relying on prose summaries alone

### 7. Generated Agent README Contract

File:

- `src/ai_native_package/contracts/generated-agent-readme.contract.json`

Required ordered sections:

1. `mode`
2. `start_here`
3. `machine_readable_truth`
4. `read_order`
5. `primary_content_files`
6. `validation_status`
7. `warning_policy`

Additional constraints:

- section order is fixed
- section names are exact
- the contract must support both `in-repo` and `portable-bundle` modes
- the `mode` section must use one of those exact canonical identifiers
- operator-only instructions must not appear in agent-only generated docs

### 8. Minimum Rollout Order Policy

File:

- `src/ai_native_package/policies/minimum-rollout-order.json`

Required rollout sequence:

1. `validate-task-brief`
2. `validate-task-order-and-approval`
3. pre-dispatch blocking on `validate-task-brief` failure or `validate-task-order-and-approval` failure/non-dispatchable outcome
4. `validate-task-scope`
5. `validate-generated-agent-readme`

This order is normative for the minimum rollout and maps to implementation phases as follows:

- Phase 1 provides the contract and template foundation required before rollout begins
- Phase 2 delivers steps 1 through 3 and is not complete until both pre-dispatch validators feed the dispatch gate
- Phase 3 delivers step 4
- Phase 4 delivers step 5

The policy file must define:

- sequence order
- blocking semantics
- validator dependencies required before each blocking stage is considered implemented
- minimum required implementation state for each stage

## Template Definitions

### Delegation Brief Template

File:

- `src/ai_native_package/templates/delegation-brief.md`

Must render every field required by `delegation-brief.schema.json`.

The template must:

- preserve canonical field naming at least in machine-readable markers or mapping metadata
- render the human-readable sections in the same order every time
- include explicit out-of-scope and validation sections

### Worker Result Template

File:

- `src/ai_native_package/templates/worker-result.json`

Must mirror `worker-result.schema.json` and provide:

- canonical field names
- placeholder validation result entries
- optional fields present only where appropriate

### Task Record Template

File:

- `src/ai_native_package/templates/task-record.yaml`

Must emit:

- stable `task_id`
- all canonical delegation brief source fields
- declared task order
- dependency list
- approval requirement and approval state
- scope and validation commands
- enough structured task metadata to render a canonical delegation brief without inventing missing fields during dispatch

### Generated Agent README Template

File:

- `src/ai_native_package/templates/generated-agent-readme.md`

Must render the ordered sections defined in `generated-agent-readme.contract.json`.

It must support:

- `in-repo` mode for artifacts consumed directly from the working tree
- `portable-bundle` mode for artifacts consumed from a transferred package bundle

## Validator Definitions

### 1. `validate-task-brief`

File:

- `src/ai_native_package/validators/validate_task_brief.py`

Must check:

- schema compliance with `delegation-brief.schema.json`
- presence of all canonical fields
- when a task record is supplied by the runtime, field-for-field agreement between the rendered delegation brief and the authoritative task-record brief-source values
- no missing `required_return_format`
- no missing validation commands
- no empty file scope

Result levels:

- `pass`
- `warn`
- `fail`

Blocking rule:

- any missing canonical field is `fail`
- any mismatch between a loaded delegation brief and the authoritative task record is `fail`

### 2. `validate-task-scope`

File:

- `src/ai_native_package/validators/validate_task_scope.py`

Must check:

- changed files vs declared scope
- no undeclared file edits
- docs-only tasks vs runtime edits
- test-only tasks vs runtime edits

Blocking rule:

- undeclared changed files are `fail`

### 3. `validate-task-order-and-approval`

File:

- `src/ai_native_package/validators/validate_task_order_and_approval.py`

Must check:

- task order exists or dependency resolution is deterministic
- lexical task identifier exists
- approval requirement exists
- approval state is valid against `approval-state.schema.json`
- dispatch eligibility can be computed from `approval-policy.json` for the current approval state

Blocking rule:

- missing approval requirement is `fail`
- unresolved order is `fail`
- non-dispatchable approval state is `blocked`

### 4. `validate-generated-agent-readme`

File:

- `src/ai_native_package/validators/validate_generated_agent_readme.py`

Must check:

- exact section names
- exact section order
- required field presence in the rendered README
- mode compatibility using the canonical `in-repo|portable-bundle` identifiers
- no operator-only checklist duplication in agent-only mode

Blocking rule:

- required section/order drift is `fail`

## Orchestration Runtime Integration

### Pre-Dispatch Gate

File:

- `src/ai_native_package/orchestration/predispatch.py`

Must:

- load the authoritative task record
- derive the canonical delegation brief input set from the task record
- render the delegation brief from that input set when a persisted brief is not supplied
- when a persisted brief is supplied, treat it as a derived artifact and fail if any canonical field disagrees with the task record
- run `validate-task-brief`
- run `validate-task-order-and-approval`
- emit a machine-readable decision artifact that validates against `predispatch-decision.schema.json`
- map the decision artifact to orchestrator runtime state using the declared `decision` to `resulting_task_state` contract mapping
- persist the decision artifact and its referenced inputs for audit and replay before any worker dispatch attempt begins
- block dispatch if either validator returns `fail`
- block autonomous dispatch if `validate-task-order-and-approval` reports the current approval state as non-dispatchable under `approval-policy.json`

### Post-Task Gate

File:

- `src/ai_native_package/orchestration/posttask.py`

Must:

- validate the worker result against `worker-result.schema.json`
- run `validate-task-scope`
- rerun task validation commands if configured
- run `validate-generated-agent-readme` when generated runtime docs changed
- emit a machine-readable decision artifact that validates against `posttask-decision.schema.json`
- support only these post-task decisions:
  - `complete`
  - `blocked`
  - `retry`
  - `escalate`
- map the decision artifact to orchestrator runtime state using the declared `decision` to `resulting_task_state` contract mapping
- persist the decision artifact and its referenced validator outputs for audit and replay

## CLI And Package Surface

The package should expose validator and orchestration commands through the CLI.

Canonical validator input formats:

- `--brief`: UTF-8 Markdown with LF line endings rendered from `delegation-brief.md`; this is the canonical on-disk format for delegation briefs consumed by validators and orchestration commands
- `--task-record`: UTF-8 YAML with LF line endings; this is the canonical on-disk format for task records consumed by validator and orchestration commands
- `--worker-result`: UTF-8 JSON object with LF line endings; this is the canonical on-disk format for worker-result payloads
- `--readme`: UTF-8 Markdown with LF line endings rendered from `generated-agent-readme.md`; this is the canonical on-disk format for generated agent README validation
- `--changed-files`: UTF-8 JSON array of repo-relative POSIX-style path strings sorted lexically with no duplicates; newline-delimited text and JSONL are not canonical for this interface

Canonical validator output modes:

- every validator command must support both `human-readable` and `machine-readable` output
- the CLI flag surface for validator output must be `--output text|json`
- `text` is the default mode and must emit a deterministic human-readable summary in stable check order
- `json` must emit a deterministic machine-readable UTF-8 JSON object to stdout with stable key ordering and, at minimum, `validator`, `result`, `errors`, `warnings`, and `inputs` fields
- validator exit codes must not vary by output mode
- validators must not define additional ad hoc output modes

Recommended command surface:

- `ai-native-package validate-task-brief --brief <path> [--output text|json]`
- `ai-native-package validate-task-scope --brief <path> --changed-files <path> [--output text|json]`
- `ai-native-package validate-task-order-and-approval --task-record <path> [--output text|json]`
- `ai-native-package validate-generated-agent-readme --readme <path> --mode <in-repo|portable-bundle> [--output text|json]`
- `ai-native-package predispatch --task-record <path> --brief <path>`
- `ai-native-package posttask --task-record <path> --brief <path> --worker-result <path>`

## Implementation Phases

### Phase 1: Contract And Template Foundation

Build:

- contract files
- template files
- basic schema loading utilities

Acceptance:

- templates render contract-compliant skeleton artifacts

### Phase 2: Brief, Approval, And Predispatch Gates

Build:

- `validate-task-brief`
- `validate-task-order-and-approval`
- pre-dispatch gate

Acceptance:

- pre-dispatch blocking runs only after both `validate-task-brief` and `validate-task-order-and-approval` execute
- bad briefs are blocked before dispatch
- unresolved task order or missing approval metadata blocks dispatch
- approval policy blocks autonomous dispatch when appropriate

### Phase 3: Scope And Result Enforcement

Build:

- `worker-result.schema.json`
- worker-result template
- `validate-task-scope`
- post-task gate

Acceptance:

- worker completions are structured and scope-checked

### Phase 4: Generated Agent README Enforcement

Build:

- generated README contract
- generated agent README template
- `validate-generated-agent-readme`

Acceptance:

- generated agent READMEs are structurally stable and machine-checkable

### Phase 5: Runtime Adoption

Build:

- CLI integration
- orchestration helpers
- end-to-end tests

Acceptance:

- the project pack can drive agent-oriented orchestration with validator-backed decisions

## Testing Requirements

Add tests for:

- valid delegation brief acceptance
- loaded delegation brief rejection when any canonical field disagrees with the authoritative task record
- missing canonical field rejection
- invalid approval state rejection
- blocked dispatch when approval is pending or denied
- scope validator failure on undeclared edits
- generated agent README section-order failure
- worker result schema validation
- predispatch decision schema validation and decision-to-state mapping
- posttask decision schema validation and decision-to-state mapping
- persisted decision artifacts include replayable references to gate inputs and validator outputs

## Success Criteria

This modernization is complete when:

- the project pack emits machine-readable contracts for all core orchestration artifacts
- templates default to those contracts
- validators enforce them
- pre-dispatch and post-task gates consume validator results
- pre-dispatch and post-task gates emit persisted decision artifacts that can be validated and replayed
- the rollout order is machine-readable and explicit
- orchestration and delegated work can be governed by contracts instead of prose alone

## Non-Goals

This implementation spec does not require:

- a full autonomous orchestration engine in one step
- external workflow backends
- network-based orchestration services
- replacing the human-readable tech specs

The focus is enabling deterministic, agent-optimized orchestration from the existing template pack.
