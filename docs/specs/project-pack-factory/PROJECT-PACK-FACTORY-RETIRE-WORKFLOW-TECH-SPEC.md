# Project Pack Factory Retire Workflow Tech Spec

## Purpose

Define an agent-optimized retirement workflow for Project Pack Factory so
stopped migrations, superseded experiments, and no-longer-deployable build
packs can be preserved as historical evidence without remaining active factory
targets.

This extension keeps PackFactory fail-closed while preserving restart context,
evaluation history, lineage, and retirement rationale for future agents.

## Spec Link Tags

```json
{
  "spec_id": "retire-workflow",
  "depends_on": [
    "directory-hierarchy"
  ],
  "integrates_with": [
    "build-pack-materialization",
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration",
    "runtime-agent-memory"
  ],
  "historical_fixtures": [
    "build-packs/agent-memory-first-build-pack"
  ]
}
```

## Problem

The current factory can represent packs that are under test, ready, deployed,
deprecated, or non-deployable, but it does not have a first-class workflow for
declaring a pack permanently inactive while preserving its evidence.

That gap creates three agent-level problems:

- agents cannot tell whether a pack is intentionally frozen or merely stale
- deployment and registry state can continue to imply activity for superseded
  build packs
- experiments such as stopped migrations remain mixed with canonical targets
  instead of becoming explicit historical fixtures

## Design Goals

- retirement must be machine-readable and fail closed
- retired packs must remain traversable for historical context
- retired build packs must never remain active deployment candidates
- retirement must preserve evidence, not delete it
- agents must be able to detect retirement early in traversal
- retirement must be executable through a deterministic operator tool

## Scope

This spec defines:

- the `status/retirement.json` contract
- the retirement evidence artifact contract
- lifecycle, readiness, deployment, registry, and promotion-log effects
- the operator workflow for retiring a pack
- the required cross-file invariants for retirement

This spec does not define:

- physical deletion of pack directories
- long-term archival storage outside the factory root
- restoration or unretire workflows

## Retirement Model

Retirement is distinct from deprecation.

- `deprecated`
  - pack remains visible and intentionally discouraged
  - future promotion or deployment may still exist after repair or review
- `retired`
  - pack is frozen historical state
  - the factory must treat it as permanently inactive
  - deployment and promotion eligibility are removed

## Agent Traversal Contract

Retirement is part of the stable pack-local state surface.

Every pack must expose:

- `status/retirement.json`

The post-bootstrap read order becomes:

- template pack:
  - `status/lifecycle.json`
  - `status/readiness.json`
  - `status/retirement.json`
  - `status/deployment.json`
  - `benchmarks/active-set.json`
  - `eval/latest/index.json`
- build pack:
  - `status/lifecycle.json`
  - `status/readiness.json`
  - `status/retirement.json`
  - `status/deployment.json`
  - `lineage/source-template.json`
  - `benchmarks/active-set.json`
  - `eval/latest/index.json`

Agents must interpret retirement as an early-stop decision for active factory
operations:

- do not promote retired packs
- do not deploy retired build packs
- do not use retired packs as canonical sources unless the task explicitly asks
  for historical inspection

## Required Pack-Local Contract

Every pack must add:

- `status/retirement.json`

The pack manifest directory contract must add:

- `retirement_file: "status/retirement.json"`

Active packs must still carry this file with:

- `retirement_state = active`

## Runtime Agent Memory Integration

Retirement preserves runtime-memory evidence without leaving the pack eligible
for active factory workflows.

When a retired pack contains runtime-memory artifacts or runtime-memory eval
history:

- `eval/history/` runtime-memory evidence remains readable
- `.pack-state/agent-memory/` may remain in place when the pack is intentionally
  preserved as a historical fixture
- retirement does not create a second runtime-memory retirement state

The retired `agent-memory-first-build-pack` remains a concrete example of this
historical-fixture behavior.

## Retirement State Contract

`status/retirement.json` is the authority for retirement state.

Retirement states:

- `active`
- `retired`

Required semantics:

- `active`
  - pack remains eligible for normal factory workflows subject to its other
    state files
- `retired`
  - pack is historical only
  - pack must not be promoted
  - pack must not be used as an active deployment target
  - build-pack deployment pointers must not remain active

## Retirement Evidence Contract

Every retirement operation must emit a machine-readable report at:

- `eval/history/<retirement_id>/retirement-report.json`

This report is the evidence artifact for the retirement transaction.

For template packs, the report must use the existing template deployment state
surface from `status/deployment.json`:

- `deployment_state = not_deployed`
- `active_environment = none`
- `deployment_pointer_path = null`

It captures:

- who retired the pack
- why it was retired
- what the pre-retirement lifecycle/readiness/deployment state was
- what mutations were performed
- which deployment pointers were removed
- which registry entries were updated
- which promotion-log event was appended

## Lifecycle, Readiness, And Deployment Effects

When a pack is retired:

- `status/lifecycle.json.lifecycle_stage` must become `retired`
- `status/lifecycle.json.promotion_target` must become `none`
- `status/readiness.json.readiness_state` must become `retired`
- `status/readiness.json.ready_for_deployment` must become `false`

When a build pack is retired:

- `status/deployment.json.deployment_state` must become `not_deployed`
- `status/deployment.json.active_environment` must become `none`
- `status/deployment.json.active_release_id` must become `null`
- `status/deployment.json.active_release_path` must become `null`
- `status/deployment.json.deployment_pointer_path` must become `null`
- `status/deployment.json.deployment_transaction_id` must become `null`
- `status/deployment.json.projection_state` must become `not_required`
- `status/deployment.json.last_promoted_at` must become `null`
- `status/deployment.json.last_verified_at` must become `null`
- the matching `deployments/<environment>/<build-pack-id>.json` file must be
  removed or multiple stale pointers must be removed if discovered

If the build pack has no active deployment pointer at retirement time:

- the tool must not fail
- `removed_deployment_pointer_paths` remains empty
- the retirement report must record the pointer action as `skipped`

## Registry And Promotion Log Effects

Retirement must be reflected in the factory indexes.

### Registry Entry Extensions

Template and build-pack registry entries gain:

- `active`
- `retirement_state`
- `retirement_file`
- `retired_at`

Required semantics:

- `active` is `false` when `retirement_state = retired`
- `retirement_file` points to `status/retirement.json`
- `retired_at` is `null` for active packs and a timestamp for retired packs
- retired template registry entries must also set:
  - `lifecycle_stage = retired`
  - `ready_for_deployment = false`
- retired build-pack registry entries must also set:
  - `lifecycle_stage = retired`
  - `ready_for_deployment = false`
  - `deployment_state = not_deployed`
  - `active_release_id = null`
  - `deployment_pointer = null`

### Promotion Log Extensions

The promotion log must accept `event_type = retired`.

Retirement events must include:

- `retired_pack_id`
- `retired_pack_kind`
- `retirement_reason`
- `retirement_report_path`

Retirement remains historical evidence even when a pack was never promoted to
staging or production.

## Required Schema Updates

This workflow extends the existing PackFactory contracts:

- `pack.schema.json`
  - add `directory_contract.retirement_file`
  - add `status/retirement.json` to the allowed post-bootstrap read order
- `lifecycle.schema.json`
  - add `retired` as a valid lifecycle stage
  - require `promotion_target = none` for retired packs
- `readiness.schema.json`
  - add `retired` as a valid readiness state
  - require `ready_for_deployment = false` for retired packs
- new `retirement.schema.json`
- new `retirement-report.schema.json`
- update the base directory-hierarchy spec so retired packs are not classified as
  “under testing”

## Cross-File Invariants

The factory validator must enforce these retirement invariants:

- `status/retirement.json.pack_id` equals `pack.json.pack_id`
- `status/retirement.json.pack_kind` equals `pack.json.pack_kind`
- when `status/retirement.json.retirement_state = retired`:
  - `status/lifecycle.json.lifecycle_stage = retired`
  - `status/lifecycle.json.promotion_target = none`
  - `status/readiness.json.readiness_state = retired`
  - `status/readiness.json.ready_for_deployment = false`
  - `status/retirement.json.retirement_report_path` exists
  - `status/retirement.json.retired_at` equals `retirement-report.generated_at`
  - `retirement-report.pack_id` equals `pack.json.pack_id`
  - `retirement-report.pack_kind` equals `pack.json.pack_kind`
  - `retirement-report.pack_root` equals the actual pack root
  - `retirement-report.post_retirement_state.lifecycle_stage = retired`
  - `retirement-report.post_retirement_state.readiness_state = retired`
- when the retired pack is a build pack:
  - `status/deployment.json.deployment_state = not_deployed`
  - `status/deployment.json.active_environment = none`
  - `status/deployment.json.deployment_pointer_path = null`
  - `status/deployment.json.last_promoted_at = null`
  - `status/deployment.json.last_verified_at = null`
  - every `removed_deployment_pointer_paths[]` entry must end with
    `/<pack-id>.json`
  - no active deployment pointer file may exist for that pack
  - the build-pack registry entry must show `active = false`
  - the build-pack registry entry must show `retirement_state = retired`
  - the build-pack registry entry must show
    `retirement_file = status/retirement.json`
  - the build-pack registry entry must show `retired_at` equal to
    `status/retirement.json.retired_at`
  - the build-pack registry entry must show `deployment_state = not_deployed`
  - the build-pack registry entry must show `deployment_pointer = null`
  - the build-pack registry entry must show `active_release_id = null`
- when the retired pack is a template pack:
  - the template registry entry must show `active = false`
  - the template registry entry must show `retirement_state = retired`
  - the template registry entry must show `lifecycle_stage = retired`
  - the template registry entry must show
    `retirement_file = status/retirement.json`
  - the template registry entry must show `retired_at` equal to
    `status/retirement.json.retired_at`
- when `status/retirement.json.retirement_state = active`:
  - `retired_at`, `retired_by`, `retirement_reason`,
    `retirement_report_path` must be `null`
  - `removed_deployment_pointer_paths` must be empty
- when `status/retirement.json.superseded_by_pack_id` is not `null`:
  - the referenced pack must exist
  - the referenced pack id must not equal the retired pack id

## Operator Tool Contract

The factory must expose a deterministic operator tool:

- `tools/retire_pack.py`

The factory must also expose a validator:

- `tools/validate_factory.py`

Required CLI:

```text
python3 tools/retire_pack.py \
  --factory-root /abs/path/to/project-pack-factory \
  --pack-id <pack-id> \
  --retired-by <operator> \
  --retirement-reason <reason> \
  [--superseded-by-pack-id <pack-id>] \
  [--output json]
```

Required behavior:

1. discover the target pack and kind from factory state
2. fail closed if the pack does not exist
3. if the pack is already retired, enter reconcile mode and repair any missing
   retirement side effects instead of failing
4. capture pre-retirement state
5. update pack-local lifecycle, readiness, retirement, and deployment state
6. remove any matching deployment pointers for retired build packs
7. update the relevant registry entry
8. append a `retired` event to the promotion log
9. write the final retirement report evidence last
10. emit a machine-readable summary to stdout

The validator must fail closed when:

- a retired pack is still deployment-addressable
- a retired build pack still has an environment pointer
- `status/retirement.json` disagrees with lifecycle or readiness
- the retirement report is missing
- the retirement report is inconsistent with the retired pack identity or
  terminal state

## Evidence Retention Rules

Retirement preserves evidence by default.

- evaluation history must remain on disk
- release artifacts may remain on disk
- lineage must remain on disk for build packs
- latest indexes may continue to point at the last successful evidence, but the
  retirement state becomes the first active decision surface for agents

## Example Retirement State

```json
{
  "schema_version": "pack-retirement/v1",
  "pack_id": "agent-memory-first-build-pack",
  "pack_kind": "build_pack",
  "retirement_state": "retired",
  "retired_at": "2026-03-20T00:00:00Z",
  "retired_by": "orchadmin",
  "retirement_reason": "Experimental isolated memory build-pack superseded by runtime-integrated memory design.",
  "superseded_by_pack_id": null,
  "retirement_report_path": "eval/history/retire-agent-memory-first-build-pack-20260320t000000z/retirement-report.json",
  "removed_deployment_pointer_paths": [
    "deployments/testing/agent-memory-first-build-pack.json"
  ],
  "retained_artifacts": {
    "eval_history": true,
    "release_artifacts": true,
    "lineage": true
  },
  "operator_notes": [
    "Preserved as a PackFactory retirement fixture."
  ]
}
```

## Example Retirement Report

```json
{
  "schema_version": "pack-retirement-report/v1",
  "retirement_id": "retire-agent-memory-first-build-pack-20260320t000000z",
  "generated_at": "2026-03-20T00:00:00Z",
  "pack_id": "agent-memory-first-build-pack",
  "pack_kind": "build_pack",
  "pack_root": "build-packs/agent-memory-first-build-pack",
  "retired_by": "orchadmin",
  "retirement_reason": "Experimental isolated memory build-pack superseded by runtime-integrated memory design.",
  "superseded_by_pack_id": null,
  "pre_retirement_state": {
    "lifecycle_stage": "testing",
    "readiness_state": "in_progress",
    "deployment_state": "testing",
    "active_environment": "testing",
    "deployment_pointer_path": "deployments/testing/agent-memory-first-build-pack.json"
  },
  "post_retirement_state": {
    "lifecycle_stage": "retired",
    "readiness_state": "retired",
    "deployment_state": "not_deployed",
    "active_environment": "none",
    "deployment_pointer_path": null,
    "retirement_state": "retired"
  },
  "registry_updates": [
    {
      "registry_path": "registry/build-packs.json",
      "pack_id": "agent-memory-first-build-pack",
      "pack_kind": "build_pack",
      "retirement_state": "retired",
      "active": false,
      "retired_at": "2026-03-20T00:00:00Z"
    }
  ],
  "promotion_log_update": {
    "promotion_log_path": "registry/promotion-log.json",
    "event_type": "retired",
    "retired_pack_id": "agent-memory-first-build-pack",
    "retired_pack_kind": "build_pack",
    "retirement_report_path": "eval/history/retire-agent-memory-first-build-pack-20260320t000000z/retirement-report.json",
    "retired_at": "2026-03-20T00:00:00Z"
  },
  "actions": [
    {
      "action_id": "write_retirement_state",
      "status": "completed",
      "target_path": "build-packs/agent-memory-first-build-pack/status/retirement.json",
      "summary": "Recorded terminal retirement state."
    },
    {
      "action_id": "update_registry_entry",
      "status": "completed",
      "target_path": "registry/build-packs.json",
      "summary": "Marked the build-pack registry entry inactive and retired."
    },
    {
      "action_id": "append_promotion_log",
      "status": "completed",
      "target_path": "registry/promotion-log.json",
      "summary": "Appended a retired event with evidence path."
    },
    {
      "action_id": "remove_deployment_pointer",
      "status": "completed",
      "target_path": "deployments/testing/agent-memory-first-build-pack.json",
      "summary": "Removed active testing deployment pointer."
    }
  ],
  "evidence_paths": [
    "build-packs/agent-memory-first-build-pack/status/lifecycle.json",
    "build-packs/agent-memory-first-build-pack/status/readiness.json",
    "build-packs/agent-memory-first-build-pack/status/deployment.json",
    "build-packs/agent-memory-first-build-pack/eval/latest/index.json"
  ]
}
```

## Initial Factory Fixtures

The first retirement fixtures should be the two existing build packs that no
longer represent the desired canonical path:

- `ai-native-codex-build-pack`
  - stopped migration fixture
- `agent-memory-first-build-pack`
  - isolated subsystem experiment fixture

Their retirement evidence should be preserved as PackFactory validation cases.
