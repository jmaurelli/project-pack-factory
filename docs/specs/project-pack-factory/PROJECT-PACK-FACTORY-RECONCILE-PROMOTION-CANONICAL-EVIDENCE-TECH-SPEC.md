# Project Pack Factory Reconcile Promotion Canonical Evidence Tech Spec

## Purpose

Define the minimal remediation required to make reconcile-mode build-pack
promotion preserve factory-valid canonical deployment evidence.

The goal is not to redesign promotion semantics.

The goal is to keep reconcile behavior idempotent while avoiding control-plane
drift that makes the factory invalid.

## Spec Link Tags

```json
{
  "spec_id": "reconcile-promotion-canonical-evidence",
  "depends_on": [
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration",
    "environment-assignment-consistency"
  ],
  "integrates_with": [
    "factory-validation",
    "json-health-checker-workflow-evaluation"
  ],
  "adjacent_work": [
    "reconcile-mode promotion",
    "deployment pointer evidence integrity",
    "workflow idempotency"
  ]
}
```

## Problem

The live JSON Health Checker workflow successfully reached production, but a
follow-up reconcile run exposed a PackFactory self-consistency bug.

When `tools/promote_build_pack.py` enters reconcile mode for a build pack that
is already active in the requested environment with the same release:

- it generates a fresh `promotion_id`
- it rewrites the active deployment pointer to reference a new reconcile report
- it does not append a matching `promoted` event
- it leaves pack-local `status/deployment.json` transaction metadata unchanged

This creates a split-brain control-plane state:

- the active pointer now references non-canonical reconcile evidence
- the promotion log still reflects the last real promotion transaction
- pack-local deployment state and active pointer no longer agree on
  `deployment_transaction_id`

The factory validator then rejects the factory even though no real deployment
change occurred.

## Evidence

Evidence was collected on 2026-03-22 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: The Reconcile Attempt Leaves The Factory Invalid

Command:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory
```

Observed result:

- `INVALID: 1 errors`
- `/home/orchadmin/project-pack-factory/registry/promotion-log.json: active pointer `deployments/production/json-health-checker-build-pack.json` is missing a matching promoted event`

Interpretation:

- the factory becomes invalid immediately after reconcile-mode promotion writes
  new active-pointer evidence
- the failure is tied to promotion evidence integrity, not to the JSON checker
  runtime itself

### Evidence B: Reconcile Mode Rewrites The Active Pointer To New Evidence

Current active pointer contents in
`deployments/production/json-health-checker-build-pack.json`:

- `deployment_transaction_id = promote-json-health-checker-build-pack-production-20260322t165250z`
- `promotion_evidence_ref = eval/history/promote-json-health-checker-build-pack-production-20260322t165250z/promotion-report.json`
- `updated_at = 2026-03-22T16:52:50Z`

Interpretation:

- reconcile mode currently changes the canonical active pointer even though the
  active release remains `json-health-checker-r3`
- the pointer now names a reconcile transaction that was never promoted into
  the operation log

### Evidence C: Pack-Local Deployment State Still Points At The Prior Promotion

Current pack-local deployment state in
`build-packs/json-health-checker-build-pack/status/deployment.json`:

- `deployment_transaction_id = promote-json-health-checker-build-pack-production-20260322t162927z`
- `last_promoted_at = 2026-03-22T16:29:27Z`
- `active_release_id = json-health-checker-r3`
- `deployment_pointer_path = deployments/production/json-health-checker-build-pack.json`

Interpretation:

- reconcile mode did not update pack-local transaction metadata to match the
  rewritten pointer
- the factory now contains disagreeing control-plane records for the same
  active production assignment

### Evidence D: The Reconcile Report Is Explicitly Non-Promotion Evidence

Current reconcile report:

- path:
  `build-packs/json-health-checker-build-pack/eval/history/promote-json-health-checker-build-pack-production-20260322t165250z/promotion-report.json`
- `status = reconciled`
- `operation_log_update = null`
- `registry_update = null`

Interpretation:

- the reconcile report is intentionally non-promotional
- treating it as the canonical active-pointer evidence conflicts with the
  existing promotion-log contract

### Evidence E: Current Reconcile Code Rewrites The Pointer But Skips The Log

Relevant code in
`tools/promote_build_pack.py` lines `268-342`:

- enters reconcile mode when environment and release already match
- generates a new `promotion_id`
- builds a new pointer payload using that new `promotion_id`
- writes the pointer to `deployments/<environment>/<pack-id>.json`
- writes a reconcile report
- returns without updating `registry/promotion-log.json`

Interpretation:

- the current implementation directly causes the broken evidence chain

### Evidence F: The Promotion Spec Requires Reconcile To Avoid Duplicate Events

Relevant spec text in
`PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md`:

- reconcile mode must return `status = reconciled`
- reconcile mode must avoid appending a duplicate `promoted` event
- reconcile mode may omit a new `operation_log_update`

Interpretation:

- the correct fix is not to append a new duplicate `promoted` event
- the reconcile path should preserve the prior canonical promotion evidence
  instead of minting a new canonical pointer target

### Evidence G: The Validator Treats The Pointer-Referenced Report As Promotion Evidence

Relevant code in `tools/validate_factory.py` lines `454-493`:

- reads `promotion_evidence_ref` from the active pointer
- validates the referenced report
- requires a matching `promoted` event whose `promotion_report_path` equals
  that same report path

Interpretation:

- the validator already treats the pointer-referenced report as promotion
  evidence that must be backed by a matching `promoted` event
- reconcile mode currently violates that rule

### Evidence H: Canonical Promotion Evidence Already Has A Stronger Matching Helper

Relevant code in `tools/factory_ops.py` lines `305-331`:

- `_find_matching_promotion_event(...)` requires exactly one `promoted` event
- the match keys are `promotion_id`, `build_pack_id`, `target_environment`, and
  `promotion_report_path`

Interpretation:

- the factory already has a stronger notion of canonical promotion evidence
  available to reconcile-mode logic
- reconcile repair should align with that stronger helper rather than relying on
  looser path-only matching

## Design Goals

- keep the remediation tightly scoped to reconcile-mode promotion
- preserve existing promotion semantics for non-reconcile paths
- preserve the spec requirement that reconcile mode avoids duplicate promoted
  events
- keep workflow testing minimal and limited to existing validation and workflow
  surfaces
- restore full-factory validity after a reconcile run

## Non-Goals

- changing the normal success-path promotion workflow
- broadening deployment pipeline coverage
- adding new benchmarks or new test cases
- redefining reconcile mode as a new promotion event type

## Contract Narrowing

This spec narrows the promotion evidence contract for reconcile runs only.

The current promotion workflow spec says every successful promotion report is
the canonical evidence artifact and that the deployment pointer's
`promotion_evidence_ref` points at that reserved report path.

That remains true for non-reconcile promotion runs.

For reconcile runs only, this spec defines a different evidence role split:

- the active deployment pointer must continue to reference the last canonical
  promotion report already backed by a matching `promoted` event
- the new reconcile report is revalidation history, not canonical promotion
  evidence for the active pointer

This is a narrow clarification for reconcile mode, not a broad rewrite of the
promotion workflow contract.

## Required Behavior

### Canonical Pointer Preservation

If promotion enters reconcile mode because the requested environment and
`release_id` already match the active deployment, the tool must not replace the
active deployment pointer's canonical promotion transaction metadata with a new
reconcile transaction id or a new reconcile report path.

The active pointer must continue to reference the last canonical promoted
transaction already reflected in:

- `status/deployment.json.deployment_transaction_id`
- `registry/promotion-log.json`
- the existing canonical promotion report

If the active pointer is already corrupt, reconcile mode must repair it to the
last canonical promoted transaction instead of preserving the corrupt value.

The canonical transaction source must be derived from factory-controlled
promotion evidence, not from whichever pointer payload happens to exist.

### Reconcile Evidence Recording

Reconcile mode may still write a new reconcile report under
`eval/history/<promotion_id>/promotion-report.json`.

That reconcile report is historical evidence of the revalidation action, not
the canonical promotion evidence for the active pointer.

Because reconcile mode is not a new promotion transaction:

- `operation_log_update` may remain `null`
- `registry_update` may remain `null`
- no new `promoted` event should be appended

### Pack-Local State Consistency

Reconcile mode must keep pack-local deployment state internally consistent with
the active pointer.

At minimum, after reconcile completes successfully:

- `status/deployment.json.deployment_pointer_path` must still equal the
  canonical pointer path
- `status/deployment.json.deployment_transaction_id` must continue to match the
  active pointer's `deployment_transaction_id`
- `active_release_id` and `active_release_path` must remain unchanged

### Reconcile Preflight And Fail-Closed Rules

Before writing reconcile evidence, the tool must revalidate that:

- the requested build pack is still the canonical assignee for the target
  environment
- there is exactly one canonical deployment pointer for that build pack across
  environments
- there is exactly one matching canonical `promoted` event for the active
  assignment
- the canonical promotion report referenced by that event still exists

If those conditions are not true, reconcile mode must fail closed rather than
blessing ambiguous or multi-pointer drift.

### Report Semantics

The reconcile report must clearly describe reconcile behavior without claiming
that a new promotion transaction became canonical.

It may use a fresh `promotion_id` for its own evidence file naming, but that id
must not become the active pointer's deployment transaction id unless a matching
promoted event is also created, which reconcile mode explicitly avoids.

The reconcile report must not imply that the canonical pointer was rewritten if
no pointer rewrite occurred.

In particular, reconcile evidence should not:

- record `write_deployment_pointer` as a completed mutation when the canonical
  pointer payload was intentionally preserved or repaired in place
- include the active deployment pointer in `evidence_paths` as though it were
  new reconcile evidence
- describe the reconcile report itself as the canonical promotion evidence for
  the active assignment

## Minimal Implementation Shape

`tools/promote_build_pack.py` reconcile mode should:

1. identify the canonical promoted transaction by using pack-local deployment
   state plus a matching `promoted` event and report, or fail closed if that
   canonical chain cannot be proven
2. verify there is no stale same-pack assignment in another environment
3. repair the active pointer to the canonical promoted transaction if it has
   drifted
4. align `status/deployment.json.deployment_transaction_id` with that canonical
   transaction if needed
5. leave `registry/promotion-log.json` unchanged
6. write a separate reconcile report for the new revalidation action with
   non-canonical semantics
7. return `status = reconciled`

This spec does not require introducing a new schema or event type.

## Acceptance Criteria

The remediation is complete when all of the following are true:

1. A reconcile-mode promotion for the already-production JSON Health Checker
   build pack returns `status = reconciled`.
2. After that reconcile run, `python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory`
   returns a valid result.
3. The active pointer at
   `deployments/production/json-health-checker-build-pack.json` still points to
   the canonical promotion report already backed by exactly one matching
   `promoted` event.
4. The reconcile run writes its own report under the pack's `eval/history/`
   directory without becoming the pointer-referenced promotion evidence.
5. No duplicate `promoted` event is appended to `registry/promotion-log.json`.
6. The reconcile report does not falsely claim that the active deployment
   pointer was rewritten when canonical pointer metadata was preserved or
   repaired.

## Validation Plan

Use existing workflow surfaces only:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory
python3 tools/promote_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <reconcile-request.json> --output json
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory
```

If desired, a pipeline reconcile run may be used later as secondary evidence,
but it is not required for this remediation spec.

No new tests are required by this spec.
