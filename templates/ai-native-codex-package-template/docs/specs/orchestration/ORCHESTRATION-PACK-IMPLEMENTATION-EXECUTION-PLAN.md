# Orchestration Pack Implementation Execution Plan

## Purpose

Turn the orchestration specification set into a sequential implementation plan with narrow, dependency-aware micro-tasks.

This plan is the execution companion to:

- `ORCHESTRATION-PACK-MODERNIZATION-IMPLEMENTATION-TECH-SPEC.md`
- `DELEGATION-DOCS-META-TEMPLATE.md`
- `DELEGATED-AGENT-COMMUNICATION-HANDOFF-PROTOCOL-TECH-SPEC.md`
- `ORCHESTRATION-DELEGATION-ENFORCEMENT-TECH-SPEC.md`
- `ORCHESTRATION-RULES-ENFORCEMENT-OPTIONS-TECH-SPEC.md`
- `ORCHESTRATOR-AUTONOMY-LOOP-TECH-SPEC.md`

## Execution Order

Implement in this order:

1. Contracts
2. Templates
3. Validators
4. Predispatch and posttask runtime gates
5. Generated agent README enforcement
6. Autonomy loop behavior

This order is mandatory because each later layer depends on the previous layer being machine-readable and enforceable.

## Phase 1: Contract Foundation

### Task P1.1: Delegation brief schema

Objective:
- create `src/ai_native_package/contracts/delegation-brief.schema.json`

Scope:
- contract file only

Acceptance:
- encodes all 13 canonical brief fields
- rejects missing required fields
- enforces ordered non-empty `files_in_scope`
- enforces ordered non-empty `validation_commands`

### Task P1.2: Worker result schema

Objective:
- create `src/ai_native_package/contracts/worker-result.schema.json`

Scope:
- contract file only

Acceptance:
- uses canonical worker result fields from the communication protocol spec
- keeps worker status separate from orchestrator task states and approval states

### Task P1.3: Task record schema

Objective:
- create `src/ai_native_package/contracts/task-record.schema.json`

Scope:
- contract file only

Acceptance:
- task record is authoritative for canonical brief rendering
- includes all canonical brief source fields
- includes `declared_order`, `approval_requirement`, and `approval_state`

### Task P1.4: Approval state and decision schemas

Objective:
- create:
  - `src/ai_native_package/contracts/approval-state.schema.json`
  - `src/ai_native_package/contracts/predispatch-decision.schema.json`
  - `src/ai_native_package/contracts/posttask-decision.schema.json`

Scope:
- contract files only

Acceptance:
- approval-state is value-shape only
- predispatch and posttask decisions are explicit machine-readable artifacts
- decision values map cleanly to runtime task states

### Task P1.5: Generated agent README contract

Objective:
- create `src/ai_native_package/contracts/generated-agent-readme.contract.json`

Scope:
- contract file only

Acceptance:
- encodes the canonical section order:
  - `mode`
  - `start_here`
  - `machine_readable_truth`
  - `read_order`
  - `primary_content_files`
  - `validation_status`
  - `warning_policy`

### Task P1.6: Policy artifacts

Objective:
- create:
  - `src/ai_native_package/policies/approval-policy.json`
  - `src/ai_native_package/policies/minimum-rollout-order.json`

Scope:
- policy files only

Acceptance:
- approval policy defines dispatchability rules
- rollout order includes:
  - `validate-task-brief`
  - `validate-task-order-and-approval`
  - pre-dispatch blocking
  - `validate-task-scope`
  - `validate-generated-agent-readme`

## Phase 2: Template Emission

### Task P2.1: Delegation brief template

Objective:
- create `src/ai_native_package/templates/delegation-brief.md`

Acceptance:
- renders all canonical brief fields from task-record inputs
- does not invent undeclared fields

### Task P2.2: Worker result template

Objective:
- create `src/ai_native_package/templates/worker-result.json`

Acceptance:
- matches `worker-result.schema.json`
- gives workers one canonical return shape

### Task P2.3: Task record template

Objective:
- create `src/ai_native_package/templates/task-record.yaml`

Acceptance:
- includes every field needed for brief rendering and approval gating

### Task P2.4: Generated agent README template

Objective:
- create `src/ai_native_package/templates/generated-agent-readme.md`

Acceptance:
- follows the canonical section order
- stays agent-facing, not operator-facing

## Phase 3: Validator Layer

### Task P3.1: Task brief validator

Objective:
- create `src/ai_native_package/validators/validate_task_brief.py`

Acceptance:
- validates against `delegation-brief.schema.json`
- validates rendered brief values against the authoritative task record
- supports deterministic CLI output:
  - `--output text|json`

### Task P3.2: Task order and approval validator

Objective:
- create `src/ai_native_package/validators/validate_task_order_and_approval.py`

Acceptance:
- validates task ordering
- validates approval-state shape
- computes dispatchability from `approval-policy.json`
- emits machine-readable decision support

### Task P3.3: Task scope validator

Objective:
- create `src/ai_native_package/validators/validate_task_scope.py`

Acceptance:
- compares changed files against declared scope
- supports strict pass/fail for out-of-scope edits

### Task P3.4: Generated agent README validator

Objective:
- create `src/ai_native_package/validators/validate_generated_agent_readme.py`

Acceptance:
- validates canonical section order
- validates machine-readable-truth references
- validates agent/operator role separation where applicable

## Phase 4: Runtime Gate Integration

### Task P4.1: Predispatch runtime

Objective:
- create `src/ai_native_package/orchestration/predispatch.py`

Acceptance:
- loads task record
- renders or validates brief
- runs:
  - `validate-task-brief`
  - `validate-task-order-and-approval`
- emits `predispatch-decision`
- blocks dispatch on failure or non-dispatchable approval state

### Task P4.2: Posttask runtime

Objective:
- create `src/ai_native_package/orchestration/posttask.py`

Acceptance:
- validates worker result against schema
- runs scope validation
- emits `posttask-decision`
- persists decision artifacts for audit and replay

### Task P4.3: CLI/runtime wiring

Objective:
- wire validators and runtime gates into the package CLI/runtime entrypoints

Scope:
- only the package runtime surfaces needed to expose contract validation and gate execution

Acceptance:
- validator commands are invokable
- output modes are deterministic
- exit behavior is stable across text and json output

## Phase 5: Generated Docs Enforcement

### Task P5.1: Runtime generated agent README emission

Objective:
- make runtime-generated agent READMEs render from the canonical template and contract

Acceptance:
- emitted docs use the canonical section order
- docs identify machine-readable source-of-truth artifacts

### Task P5.2: Operator versus agent role separation checks

Objective:
- enforce that upload/operator guidance and agent reading guidance stay separated

Acceptance:
- agent docs do not contain operator checklists
- operator docs do not duplicate agent reading rules

## Phase 6: Autonomy Loop

### Task P6.1: Task selection and continuation engine

Objective:
- implement deterministic task selection based on task records, dependency state, rollout order, and approval policy

Acceptance:
- optional scores only influence ordering when present
- stable fallback ordering is `declared_order` then `task_id`

### Task P6.2: Autonomous continuation gates

Objective:
- continue automatically only when gate decisions allow it

Acceptance:
- no continuation when approval is pending or denied
- no continuation when required validators fail

### Task P6.3: Audit and replay integration

Objective:
- persist decision artifacts and task outcomes so orchestration can replay or resume deterministically

Acceptance:
- predispatch and posttask decisions are stored
- runtime can explain why dispatch or continuation happened

## Recommended Delegation Size

Preferred worker slice size:
- one contract file
- or one validator
- or one runtime gate
- or one template family

Avoid combining:
- contracts plus runtime wiring
- validator logic plus autonomy behavior
- operator docs plus agent docs plus runtime code in one task

## Minimum Viable Implementation Sequence

If implementation must be staged tightly, use this minimum path:

1. `delegation-brief.schema.json`
2. `worker-result.schema.json`
3. `task-record.schema.json`
4. `approval-state.schema.json`
5. `approval-policy.json`
6. `minimum-rollout-order.json`
7. `delegation-brief.md`
8. `worker-result.json`
9. `task-record.yaml`
10. `validate_task_brief.py`
11. `validate_task_order_and_approval.py`
12. `predispatch.py`
13. `validate_task_scope.py`
14. `posttask.py`
15. `generated-agent-readme.contract.json`
16. `generated-agent-readme.md`
17. `validate_generated_agent_readme.py`
18. autonomy loop behavior

## Done Criteria

The implementation is complete when:

- all required contract and policy artifacts exist
- all templates emit canonical structures
- all four validators run with deterministic CLI I/O
- predispatch and posttask gates emit persisted decision artifacts
- generated agent READMEs validate against the canonical contract
- autonomous continuation obeys approval and validation gates
- package tests cover both passing and blocking paths
