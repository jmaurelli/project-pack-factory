# Project Pack Factory Environment Assignment Consistency Tech Spec

## Purpose

Define the PackFactory contract that keeps canonical environments
single-assignee and prevents split-brain deployment state across:

- `deployments/`
- pack-local `status/deployment.json`
- `registry/build-packs.json`
- promotion and pipeline evidence

This spec closes the current gap where promotion and validation allow more than
one build-pack to claim the same canonical environment.

## Spec Link Tags

```json
{
  "spec_id": "environment-assignment-consistency",
  "depends_on": [
    "directory-hierarchy",
    "build-pack-promotion"
  ],
  "integrates_with": [
    "ci-cloud-deployment-orchestration",
    "retire-workflow"
  ],
  "adjacent_work": [
    "validator and tooling updates that make linked specs executable"
  ]
}
```

## Problem

Project Pack Factory currently models `deployments/` as an environment
assignment board, but the active workflow behavior does not enforce that model
consistently.

Today the factory can enter split-brain state where:

- more than one build-pack is assigned to the same environment
- pointer files remain schema-valid
- pack-local deployment state appears internally valid
- whole-factory validation still passes

That breaks the intended control-plane rule that canonical environment state
should be derived, deterministic, and single-authority.

## Observed Evidence

The current repo already demonstrates the split-brain condition.

### Live Environment Evidence

The testing environment currently contains two active assignment records:

- `deployments/testing/factory-native-smoke-build-pack.json`
- `deployments/testing/json-health-checker-build-pack.json`

Both files claim `environment = testing`.

### Registry Evidence

The current build-pack registry also shows two active build-packs with:

- `deployment_state = testing`
- distinct `deployment_pointer` values under `deployments/testing/`

That means the split-brain exists both on the environment board and in the
registry.

### Promotion-Code Evidence

The promoter currently removes stale pointers only for the pack being promoted:

- `tools/promote_build_pack.py`
- it calls `scan_deployment_pointer_paths(factory_root, pack_id)`

The helper it relies on scans only `deployments/*/<that-pack>.json`, so
promotion does not detect or evict a different build-pack that already owns the
target environment.

### Validator Evidence

The validator currently:

- does special-case retirement and template-creation checks
- schema-validates each pointer file

It does not enforce:

- one active assignee per environment
- pointer-to-registry alignment across packs
- pointer-to-pack-local deployment alignment across packs
- promotion-evidence consistency for active environment claims

### CI Evidence

The current CI/deployment pipeline also allows a deferred-promotion path where
deploy and verify can complete without changing canonical deployment state.

That is acceptable only when the run is treated as non-canonical execution
evidence. It must never be mistaken for an environment assignment in the same
authority model used by `testing`, `staging`, and `production`.

## Design Goals

- keep canonical environments single-assignee
- keep `deployments/` as a derived environment index, not a second authority
- make promotion fail closed when it would create split-brain assignment
- make validator checks catch split-brain reliably
- keep CI execution evidence distinct from canonical environment assignment
- keep test changes minimal and high-signal

## Scope

This spec defines:

- the canonical environment-assignment invariant
- promotion-time eviction behavior for a prior environment assignee
- validator invariants for environment, pointer, registry, and promotion
  evidence alignment
- the authority boundary between pipeline execution evidence and canonical
  deployment state

This spec does not define:

- a new preview-environment model
- broad cloud deployment semantics
- arbitrary multi-assignee rollout patterns
- a new deployment authority surface outside existing PackFactory state

## Authority Boundary

For canonical environments:

- `testing`
- `staging`
- `production`

the canonical deployment truth is only the tuple of:

- authoritative pack-local `status/deployment.json`
- derived pointer file in `deployments/<environment>/`
- matching registry entry in `registry/build-packs.json`
- matching `promoted` event and promotion report in
  `registry/promotion-log.json`

The authoritative record is the pack-local deployment file.

The other three surfaces are required consistency witnesses around that
authoritative record.

Execution evidence alone is not canonical environment truth.

That means:

- a pipeline report may show deploy or verify work was executed
- but that report does not create canonical environment assignment by itself
- canonical assignment exists only after the promotion contract commits the
  PackFactory deployment surfaces above

If those surfaces disagree, promotion and validation must fail closed rather
than choosing a winner heuristically.

## Canonical Invariant

For each canonical environment, there must be at most one active build-pack
assignee.

Equivalent rule:

- one environment may have zero or one active assignment
- never more than one

The factory must therefore satisfy all of the following at once:

- each build-pack may have at most one active environment pointer
- each environment may have at most one active pointer file
- any active pointer must match exactly one pack-local deployment state
- any active pointer must match exactly one registry build-pack entry
- any canonical environment claim must point to a matching promotion event and
  promotion report

## Promotion Transaction Rules

Promotion into a canonical environment must be a single bounded transaction.

Before any mutation begins, promotion must discover the current assignee for
the target environment and verify that canonical surfaces agree.

### Fail-Closed Current-Assignee Discovery

Promotion must use this order:

1. inspect `deployments/<environment>/`
2. if more than one pointer file exists there, fail immediately
3. if exactly one pointer file exists, resolve the candidate assignee from that
   pointer and verify that:
   - the candidate pack-local `status/deployment.json` matches it
   - the candidate registry entry matches it
   - the matching `promoted` event and promotion report match it
4. if no pointer file exists, ensure no build-pack registry entry and no
   pack-local deployment file claims that environment

For deterministic implementation, a no-pointer environment claim means:

- registry claim:
  - `deployment_state = <environment>`
  - or `deployment_pointer = deployments/<environment>/<pack-id>.json`
- pack-local claim:
  - `status/deployment.json.deployment_state = <environment>`
  - or `status/deployment.json.active_environment = <environment>`
  - or `status/deployment.json.deployment_pointer_path =
    deployments/<environment>/<pack-id>.json`

If any canonical surface disagrees during discovery, promotion must stop before
writing the new target pointer, registry update, or promotion-log event.

After successful discovery, promotion must:

1. discover any current assignee for the target environment
2. if the current assignee is the same build-pack, continue through reconcile
   rules
3. if the current assignee is a different build-pack, evict that prior assignee
   before writing the final promotion report

### Prior-Assignee Eviction

If build-pack `A` is being promoted into environment `E`, and build-pack `B`
is currently assigned to `E`, the promoter must:

- remove `deployments/<E>/<B>.json`
- update `B/status/deployment.json` to:
  - `deployment_state = not_deployed`
  - `active_environment = none`
  - `active_release_id = null`
  - `active_release_path = null`
  - `deployment_pointer_path = null`
  - `deployment_transaction_id = null`
  - `projection_state = not_required`
  - `last_promoted_at = null`
  - `last_verified_at = null`
- update `registry/build-packs.json` for `B` to clear:
  - `deployment_state = not_deployed`
  - `deployment_pointer = null`
  - `active_release_id = null`

To keep the change minimal, eviction should not rewrite `B` lifecycle or
readiness state unless another spec explicitly requires that later. `B`
remains an active build-pack; only its canonical environment assignment is
cleared.

### Eviction Ordering

To stay fail closed and avoid transient split-brain, promotion must use this
ordering:

1. discover and validate the current assignee state
2. write target-pack lifecycle and deployment updates in memory
3. evict the prior assignee’s pointer, pack-local deployment state, and
   registry deployment fields
4. write the target-pack deployment state
5. write the new target pointer
6. write the promoted-pack registry update
7. append the `promoted` event
8. write the final promotion report last

If any step before `write the final promotion report` fails, the promotion must
surface a failed operation and must not leave multiple active assignees for the
same environment.

### Promotion Evidence Extension

Promotion evidence must record prior-assignee eviction when it occurs.

The promotion report must preserve:

- which pack previously owned the target environment
- which deployment pointer was removed
- which pack-local deployment file was cleared
- which registry entry fields were cleared

This workflow therefore requires explicit promotion-report schema additions:

- add an optional top-level object:
  - `evicted_prior_assignment`
- require it when prior-assignee eviction occurs
- define its fields as:
  - `pack_id`
  - `environment`
  - `removed_pointer_path`
  - `cleared_deployment_file`
  - `cleared_registry_fields`

The report action enum must also include a first-class eviction action:

- `evict_prior_assignee`

## Validator Invariants

The whole-factory validator must enforce environment-assignment consistency.

### Environment-Board Invariants

For each canonical environment:

- at most one pointer file may exist under `deployments/<environment>/`

If two or more pointer files exist for the same environment, validation must
fail.

### Pointer-To-Pack Invariants

For every active pointer file:

- `pack_id` must identify an active build-pack registry entry
- `source_deployment_file` must exist
- the referenced pack’s `status/deployment.json` must match:
  - `deployment_state = <environment>`
  - `active_environment = <environment>`
  - `deployment_pointer_path = deployments/<environment>/<pack-id>.json`
  - `active_release_id` equal to the pointer release id

### Pointer-To-Registry Invariants

For every active pointer file:

- the matching build-pack registry entry must show:
  - `deployment_state = <environment>`
  - `deployment_pointer = deployments/<environment>/<pack-id>.json`
  - `active_release_id` equal to the pointer release id

If a build-pack registry entry claims a canonical environment, exactly one
matching pointer file must exist.

### Evidence Invariants

For every active pointer file:

- `promotion_evidence_ref` must point to the matching promotion report path
- a matching `promoted` event must exist in `registry/promotion-log.json`
- the matching promotion report must reference the same:
  - `build_pack_id`
  - `target_environment`
  - `release_id`
  - `post_promotion_state.deployment_pointer_path`

Any active canonical pointer without matching promotion evidence invalidates the
factory.

## CI And Pipeline Integration

This spec does not create a new preview model, but it does clarify the
authority boundary around deferred promotion.

If a pipeline runs with:

- `commit_promotion_on_success = false`

then the run may record execution evidence only.

That means:

- no canonical pointer may be created
- no pack-local canonical environment claim may be written
- no registry canonical environment claim may be written
- the pipeline report must encode that state machine-readably

This workflow therefore requires explicit pipeline-report schema support for
deferred canonical state:

- add `canonical_state_changed`
  - boolean
- add `canonical_assignment_status`
  - enum:
    - `unchanged`
    - `committed`

Required semantics:

- when `commit_promotion_on_success = false`:
  - `canonical_state_changed = false`
  - `canonical_assignment_status = unchanged`
- when a pipeline run commits canonical state through promotion:
  - `canonical_state_changed = true`
  - `canonical_assignment_status = committed`
- when the pipeline `final_status = failed`:
  - `canonical_state_changed = false`
  - `canonical_assignment_status = unchanged`
- when the pipeline `final_status = reconciled`:
  - `canonical_state_changed = false`
  - `canonical_assignment_status = committed`

If a pipeline run is intended to create canonical assignment in `testing`,
`staging`, or `production`, promotion must commit the canonical state.

## Required Spec Corrections

This spec requires coordinated corrections in the existing family:

- promotion spec:
  - add one-assignee-per-environment rule
  - add prior-assignee eviction contract
  - add promotion evidence requirements for eviction
  - add fail-closed current-assignee discovery rules
- directory hierarchy spec:
  - keep `deployments/` explicitly derived and single-assignee
  - ensure examples point `promotion_evidence_ref` at promotion reports, not
    `eval/latest/index.json`
- CI orchestration spec:
  - distinguish execution evidence from canonical state evidence when promotion
    is deferred
  - add machine-readable deferred-state fields to the pipeline report contract

## Minimal Test Posture

Keep the test delta intentionally small.

Recommended change budget:

- `2` targeted tests maximum

Recommended coverage:

- replace the weaker same-pack stale-pointer cleanup case with a cross-pack
  eviction promotion test
- add one validator contract test for duplicate environment assignment

If adding those two tests would exceed the current workflow cap, replace weaker
coverage rather than growing the suite.

## Validation

The implemented fix should validate through:

- whole-factory validation detecting split-brain assignments
- one promotion test covering cross-pack eviction
- one validator test covering duplicate environment assignment

## Relationship To Existing Specs

This spec is a focused consistency layer across:

- `PROJECT-PACK-FACTORY-DIRECTORY-HIERARCHY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-CI-CLOUD-DEPLOYMENT-ORCHESTRATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-RETIRE-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

It should be implemented as a coordinated patch to promotion, validation, and
the linked specs above rather than as a standalone behavior change in just one
tool.
