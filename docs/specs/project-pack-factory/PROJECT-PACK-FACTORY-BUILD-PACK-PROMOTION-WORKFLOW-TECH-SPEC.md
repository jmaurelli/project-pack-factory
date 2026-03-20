# Project Pack Factory Build-Pack Promotion Workflow Tech Spec

## Purpose

Define a deterministic, operator-driven workflow for promoting an active build
pack through the factory environments:

- `testing`
- `staging`
- `production`

This workflow is the control-plane contract for environment advancement. It is
separate from the later CI/cloud pipeline execution contract.

## Spec Link Tags

```json
{
  "spec_id": "build-pack-promotion",
  "depends_on": [
    "directory-hierarchy",
    "build-pack-materialization"
  ],
  "integrates_with": [
    "runtime-agent-memory",
    "ci-cloud-deployment-orchestration",
    "retire-workflow"
  ]
}
```

## Problem

The factory already tracks readiness, deployment state, deployment pointers, and
promotion history, but it does not yet provide a canonical promotion operation
that updates those surfaces together.

Without this workflow:

- environment transitions are ambiguous
- deployment pointers can drift from pack-local deployment state
- promotion history is incomplete
- agents cannot distinguish a real promotion from a manual file edit

## Design Goals

- promotions must be fail closed
- only active, non-retired build packs may be promoted
- promotion order must be explicit and bounded
- deployment pointers must remain a derived index rather than split-brain
  authority
- every promotion must emit machine-readable evidence
- repeated promotion to the same environment with the same release id should
  reconcile rather than duplicate state

## Scope

This spec defines:

- the operator workflow for promoting a build pack
- the environment transition rules
- the promotion evidence contract
- the deployment-pointer mutation rules
- the request and report JSON Schemas

This spec does not define:

- cloud provider API specifics
- package build mechanics
- rollback workflows

## Canonical Tool

- `tools/promote_build_pack.py`

Canonical invocation:

```bash
python3 tools/promote_build_pack.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /abs/path/promotion-request.json \
  --output json
```

## Promotion Model

Allowed target environments:

- `testing`
- `staging`
- `production`

Allowed transitions:

- `not_deployed -> testing`
- `testing -> staging`
- `staging -> production`

Direct `not_deployed -> staging` and `testing -> production` promotions are not
allowed in v1.

## Preconditions

Before promotion starts:

- the build pack must exist in `registry/build-packs.json`
- `status/retirement.json.retirement_state = active`
- `status/lifecycle.json.lifecycle_stage != retired`
- `status/readiness.json.ready_for_deployment = true`
- every mandatory gate in `status/readiness.json.required_gates` must have
  `status = pass`
- `eval/latest/index.json` must exist
- the requested `release_id` must exist under:
  - `dist/releases/<release-id>/release.json`
- for `testing`, a matching candidate artifact under:
  - `dist/candidates/<release-id>/release.json`
  should exist when the release came directly from a fresh packaging workflow

If any precondition fails, the tool must stop before mutating deployment state
or deployment pointers.

## Runtime Agent Memory Integration

Promotion does not create a separate runtime-memory decision path.

For runtime-memory-enabled packs:

- the runtime-memory benchmark contributes through the existing mandatory gate
  model
- the canonical gate id remains `agent_memory_restart_small_001`
- promotion reads the current pass or fail result from
  `status/readiness.json.required_gates`
- promotion reads the latest benchmark evidence from `eval/latest/index.json`

Runtime memory therefore affects promotion only through normal readiness, not
through a second promotion authority surface.

## Deployment State Effects

On a successful promotion:

- `status/deployment.json.deployment_state` becomes the target environment
- `status/deployment.json.active_environment` becomes the target environment
- `status/deployment.json.active_release_id` becomes the request release id
- `status/deployment.json.active_release_path` becomes:
  - `dist/releases/<release-id>`
- `status/deployment.json.deployment_pointer_path` becomes
  `deployments/<environment>/<build-pack-id>.json`
- `status/deployment.json.deployment_transaction_id` becomes the promotion id
- `status/deployment.json.last_promoted_at` becomes the report timestamp
- `status/deployment.json.last_verified_at` remains unchanged unless the request
  supplies a matching verification timestamp

Lifecycle intent should track the promotion stage:

- target `testing`:
  - `status/lifecycle.json.lifecycle_stage = testing`
  - `status/lifecycle.json.promotion_target = staging`
- target `staging`:
  - `status/lifecycle.json.lifecycle_stage = release_candidate`
  - `status/lifecycle.json.promotion_target = production`
- target `production`:
  - `status/lifecycle.json.lifecycle_stage = maintained`
  - `status/lifecycle.json.promotion_target = none`

## Deployment Pointer Rules

The deployment pointer remains a derived environment index at:

- `deployments/<environment>/<build-pack-id>.json`

Promotion must:

- write the pointer for the new active environment
- remove any stale pointer for the same build pack in the other environments
- keep only one active environment pointer per build pack

The pointer must never override pack-local deployment state.

## Registry And Operation Log Effects

On success, the promoter must:

- update the existing entry in `registry/build-packs.json`
- append `event_type = promoted` to `registry/promotion-log.json`

The registry entry must reflect:

- `deployment_state = <target-environment>`
- `deployment_pointer = deployments/<environment>/<build-pack-id>.json`
- `active_release_id = <release-id>`
- `active = true`
- `retirement_state = active`

## Reconcile Behavior

If the build pack is already active in the target environment with the same
`release_id`, the tool must return:

- `status = reconciled`

In reconcile mode the tool must:

- revalidate the deployment pointer
- revalidate pack-local deployment state
- avoid appending a duplicate `promoted` event
- allow the report to omit a new `operation_log_update`

## Evidence Contract

Every successful promotion must write:

- `build-packs/<build-pack-id>/eval/history/<promotion_id>/promotion-report.json`

This report is the canonical evidence artifact for the promotion transaction.

The report must be written last, after:

- pack-local deployment state is updated
- the environment pointer is updated
- the registry entry is updated
- the promotion log event is appended

The report path is deterministically derived before mutation begins. The
deployment pointer's existing `promotion_evidence_ref` field must point to that
reserved report path even though the report file itself is written last.

## Required Schema Additions

This workflow adds:

- `schemas/promotion-request.schema.json`
- `schemas/promotion-report.schema.json`

This workflow relies on the current pointer contract rather than extending it:

- `registry/promotion-log.json`
  - must accept `event_type = promoted`
  - promoted events must include:
    - `promotion_id`
    - `promotion_report_path`

## Cross-File Invariants

The factory validator must enforce:

- retired build packs cannot have:
  - deployment pointers
  - `deployment_state != not_deployed`
- active promoted build packs must have exactly one matching deployment pointer
- `status/deployment.json.deployment_pointer_path` equals the actual pointer path
- `promotion-report.target_environment` equals
  `status/deployment.json.active_environment`
- `promotion-report.release_id` equals
  `status/deployment.json.active_release_id`
- `promotion-report.post_promotion_state.active_release_path` equals
  `status/deployment.json.active_release_path`
- `promotion-report.post_promotion_state.lifecycle_stage` equals
  `status/lifecycle.json.lifecycle_stage`
- the registry entry and pack-local deployment state agree on environment,
  release id, and pointer path
- the operation log contains a matching `promoted` event whose `promotion_id`
  and `promotion_report_path` match the report unless the run reconciled
  existing state

## Example Request

```json
{
  "schema_version": "build-pack-promotion-request/v1",
  "build_pack_id": "ai-native-codex-build-pack-v2",
  "target_environment": "testing",
  "release_id": "release-20260320-001",
  "promoted_by": "orchadmin",
  "promotion_reason": "Promote the validated release candidate into testing.",
  "verification_timestamp": null
}
```

## Example Report

```json
{
  "schema_version": "build-pack-promotion-report/v1",
  "promotion_id": "promote-ai-native-codex-build-pack-v2-testing-20260320t130000z",
  "generated_at": "2026-03-20T13:00:00Z",
  "status": "completed",
  "build_pack_id": "ai-native-codex-build-pack-v2",
  "build_pack_root": "build-packs/ai-native-codex-build-pack-v2",
  "target_environment": "testing",
  "release_id": "release-20260320-001",
  "release_path": "dist/releases/release-20260320-001",
  "promoted_by": "orchadmin",
  "promotion_reason": "Promote the validated release candidate into testing.",
  "pre_promotion_state": {
    "lifecycle_stage": "testing",
    "deployment_state": "not_deployed",
    "active_environment": "none",
    "active_release_path": null,
    "last_verified_at": null,
    "deployment_pointer_path": null
  },
  "post_promotion_state": {
    "lifecycle_stage": "testing",
    "deployment_state": "testing",
    "active_environment": "testing",
    "active_release_path": "dist/releases/release-20260320-001",
    "last_verified_at": null,
    "deployment_pointer_path": "deployments/testing/ai-native-codex-build-pack-v2.json"
  },
  "registry_update": {
    "registry_path": "registry/build-packs.json",
    "pack_id": "ai-native-codex-build-pack-v2",
    "deployment_state": "testing",
    "deployment_pointer": "deployments/testing/ai-native-codex-build-pack-v2.json"
  },
  "operation_log_update": {
    "promotion_log_path": "registry/promotion-log.json",
    "event_type": "promoted",
    "promotion_id": "promote-ai-native-codex-build-pack-v2-testing-20260320t130000z",
    "build_pack_id": "ai-native-codex-build-pack-v2",
    "target_environment": "testing",
    "promotion_report_path": "eval/history/promote-ai-native-codex-build-pack-v2-testing-20260320t130000z/promotion-report.json"
  },
  "actions": [
    {
      "action_id": "update_deployment_state",
      "status": "completed",
      "target_path": "build-packs/ai-native-codex-build-pack-v2/status/deployment.json",
      "summary": "Activated the requested environment and release id."
    },
    {
      "action_id": "write_deployment_pointer",
      "status": "completed",
      "target_path": "deployments/testing/ai-native-codex-build-pack-v2.json",
      "summary": "Wrote the derived environment pointer."
    },
    {
      "action_id": "write_promotion_report",
      "status": "completed",
      "target_path": "build-packs/ai-native-codex-build-pack-v2/eval/history/promote-ai-native-codex-build-pack-v2-testing-20260320t130000z/promotion-report.json",
      "summary": "Recorded terminal promotion evidence."
    }
  ],
  "evidence_paths": [
    "build-packs/ai-native-codex-build-pack-v2/status/lifecycle.json",
    "build-packs/ai-native-codex-build-pack-v2/status/readiness.json",
    "build-packs/ai-native-codex-build-pack-v2/status/deployment.json",
    "deployments/testing/ai-native-codex-build-pack-v2.json"
  ]
}
```
