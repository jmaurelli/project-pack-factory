# Project Pack Factory Reconcile Canonical Promotion Evidence Refresh Tech Spec

## Purpose

Define the smallest explicit PackFactory change that allows an already-live
build-pack to refresh its canonical promotion evidence for the same
environment and the same `release_id`.

This is not a request to broaden reconcile generally.

This is a narrow amendment to same-release reconcile behavior when the
operator explicitly asks the factory to replace the current canonical
promotion witness with newer same-release evidence.

## Spec Link Tags

```json
{
  "spec_id": "reconcile-canonical-promotion-evidence-refresh",
  "amends": [
    "build-pack-promotion",
    "reconcile-promotion-canonical-evidence",
    "pipeline-reconcile-release-immutability"
  ],
  "depends_on": [
    "environment-assignment-consistency"
  ],
  "integrates_with": [
    "factory-validation"
  ],
  "adjacent_work": [
    "promotion evidence refresh",
    "reconcile-mode canonical state",
    "workflow idempotency"
  ]
}
```

## Problem

Today PackFactory intentionally separates:

- mutable current-state evidence such as `status/readiness.json` and
  `eval/latest/index.json`
- canonical promotion evidence such as the deployment pointer, pack-local
  deployment transaction id, and matching `promoted` event

That current contract is valid and validator-friendly.

The gap is narrower than an invalid state bug:

- the live assignment can remain correct
- whole-factory validation can still pass
- newer same-release reconcile evidence can exist
- but the active canonical promotion witness can remain anchored to an older
  promotion record

The current Config Drift Checker production state shows that exact case after
the standalone rename pass. The repo evidence supports the claim that later
same-release reconcile evidence is newer and aligned with the current manifest
entrypoints. The repo evidence does not prove the earlier promotion evidence is
incorrect. This spec exists to make canonical evidence refresh possible as an
explicit operator action, not to reclassify the current state as invalid.

## Evidence

Evidence was collected on 2026-03-22 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: The Live Production Pointer Still Targets The Earlier Promotion Transaction

Current production pointer:

- file:
  `deployments/production/config-drift-checker-build-pack.json`
- `deployment_transaction_id = promote-config-drift-checker-build-pack-production-20260322t222933z`
- `promotion_evidence_ref = eval/history/promote-config-drift-checker-build-pack-production-20260322t222933z/promotion-report.json`

Interpretation:

- the live canonical production pointer still names the original production
  promotion transaction from `2026-03-22T22:29:33Z`

### Evidence B: The Original Canonical Promotion Is Tied To Pre-Rename Pipeline Evidence

Current original production promotion report:

- file:
  `build-packs/config-drift-checker-build-pack/eval/history/promote-config-drift-checker-build-pack-production-20260322t222933z/promotion-report.json`
- `promotion_reason = Finalized by pipeline pipeline-config-drift-checker-build-pack-production-20260322t222930z`

That linked pipeline records the old module path in:

- `build-packs/config-drift-checker-build-pack/eval/history/pipeline-config-drift-checker-build-pack-production-20260322t222930z/validation-result.json`
- `build-packs/config-drift-checker-build-pack/eval/history/pipeline-config-drift-checker-build-pack-production-20260322t222930z/benchmark-result.json`
- `build-packs/config-drift-checker-build-pack/eval/history/pipeline-config-drift-checker-build-pack-production-20260322t222930z/verification-result.json`

Interpretation:

- the current canonical promotion chain still points at the earlier promotion
  record and its linked pipeline evidence

### Evidence C: Pack-Local Current-State Surfaces Now Point At Later Reconcile Evidence

Current pack-local surfaces:

- `build-packs/config-drift-checker-build-pack/pack.json`
  uses `config_drift_checker_build_pack` for validation and benchmark
  entrypoints
- `build-packs/config-drift-checker-build-pack/status/readiness.json`
  points validation evidence at:
  `eval/history/pipeline-config-drift-checker-build-pack-production-20260322t224056z/validation-result.json`
- `build-packs/config-drift-checker-build-pack/eval/latest/index.json`
  points benchmark evidence at:
  `eval/history/pipeline-config-drift-checker-build-pack-production-20260322t224056z/benchmark-result.json`

Interpretation:

- mutable current-state evidence has already moved to the later reconcile run
- the active canonical promotion witness did not move with it

### Evidence D: The Later Reconcile Pipeline Matches The Current Manifest Entry Points

Current reconcile pipeline evidence:

- `build-packs/config-drift-checker-build-pack/eval/history/pipeline-config-drift-checker-build-pack-production-20260322t224056z/validation-result.json`
- `build-packs/config-drift-checker-build-pack/eval/history/pipeline-config-drift-checker-build-pack-production-20260322t224056z/benchmark-result.json`
- `build-packs/config-drift-checker-build-pack/eval/history/pipeline-config-drift-checker-build-pack-production-20260322t224056z/verification-result.json`

Observed commands use:

- `python3 -m config_drift_checker_build_pack validate-project-pack`
- `python3 -m config_drift_checker_build_pack benchmark-smoke`

Interpretation:

- the later reconcile pipeline is newer and aligned with the current manifest
  entrypoints for the live pack

### Evidence E: Reconcile Promotion Explicitly Preserved The Earlier Canonical Pointer

Current reconcile promotion report:

- file:
  `build-packs/config-drift-checker-build-pack/eval/history/promote-config-drift-checker-build-pack-production-20260322t224059z/promotion-report.json`
- `status = reconciled`
- `write_deployment_pointer.status = reconciled`
- `summary = Revalidated the canonical deployment pointer without rewriting it.`

Interpretation:

- the current same-release reconcile contract intentionally preserved the
  earlier canonical promotion witness

### Evidence F: Whole-Factory Validation Still Passes

Command:

```bash
python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```

Observed result on 2026-03-22:

- `valid = true`
- `error_count = 0`

Interpretation:

- the current repo state is valid today
- this spec addresses an optional canonical evidence refresh path, not a
  validator repair

## Design Goals

- keep the change tightly scoped to same-pack, same-environment, same-release
  reconcile
- preserve release immutability
- preserve single-assignee environment rules
- preserve the current default reconcile path when refresh is not explicitly
  requested
- make the refresh trigger machine-readable
- make refresh outcome machine-readable in both promotion and pipeline reports
- keep the resulting control-plane state deterministic and validator-friendly
- keep tests small and high-signal

## Non-Goals

- changing normal non-reconcile promotion behavior
- turning every reconcile run into a canonical refresh
- redefining `pipeline_executed` as canonical deployment truth by itself
- refreshing canonical evidence while changing `release_id`
- refreshing canonical evidence while changing environment
- bulk repair of historical promotion chains
- loosening any current fail-closed environment assignment rules

## Supersession Boundary

This spec intentionally amends the current same-release reconcile contract in
the promotion workflow and reconcile canonical evidence specs.

The amended rule is narrow:

- plain same-release reconcile remains `revalidated only`
- same-release reconcile with explicit refresh request may commit a fresh
  canonical promotion witness

Without an explicit refresh request, existing reconcile semantics remain in
force:

- no new canonical `promoted` event
- no new canonical deployment transaction id
- no canonical pointer refresh

## Request Contract

Canonical evidence refresh must be opt-in.

The feature is requested through two explicit machine-readable booleans:

- `promotion-request.schema.json`
  adds `refresh_canonical_evidence`
- `deployment-pipeline-request.schema.json`
  adds `refresh_canonical_evidence_on_reconcile`

Required request behavior:

- both new fields default to `false`
- `run_deployment_pipeline.py` must pass the pipeline field through to the
  promotion request field
- if the direct promotion interface is used, only
  `refresh_canonical_evidence = true` may request refresh
- if neither field is set, current behavior remains unchanged

This spec does not allow an implicit or automatic refresh path.

## Eligibility Contract

Refresh is allowed only when all of the following are true:

- the requested build-pack is already active in the requested environment
- the requested `release_id` already matches the active deployed release
- the pack-local deployment file shows the expected environment, release path,
  and deployment pointer path for that live assignment
- the registry entry shows the same active environment pointer and
  `active_release_id`
- there is exactly one pointer for the target environment
- there is exactly one deployment pointer for the target pack across
  environments
- the current canonical pointer references exactly one matching `promoted`
  event in `registry/promotion-log.json`
- that matching `promoted` event references an existing promotion report for
  the same pack, environment, and `release_id`
- the build-pack lifecycle stage still matches the target environment's
  maintained state
- the refresh request is tied to a same-release reconcile verification set in
  which validation, benchmark, and verification all passed

For pipeline-driven refresh, the evidence set must come from the current
pipeline run being finalized. Older passing runs cannot be reused to justify a
new refresh.

## Fail-Closed Behavior

If refresh is requested and any eligibility condition fails:

- the command must return an error
- the factory must not silently downgrade to plain reconcile
- the factory must not fall through to normal promotion behavior
- the active pointer, registry entry, and pack-local deployment transaction id
  must remain unchanged
- no new `promoted` event may be appended

Refresh is therefore opt-in and fail-closed.

## Idempotency Rule

If refresh is requested and the active canonical promotion witness already
records the same evidence source that the request is trying to refresh to:

- the operation must return `reconciled`
- the operation must not mint another `promotion_id`
- the operation must not append another `promoted` event

This prevents duplicate same-evidence refresh spam in the promotion log.

## Required Behavior

### Refresh Outcome Semantics

If reconcile enters canonical evidence refresh mode and commits the refresh:

- promotion report `status` must be `completed`
- pipeline report `final_status` must be `completed`
- pipeline report `canonical_state_changed` must be `true`
- pipeline report `canonical_assignment_status` must be `refreshed`

Plain reconcile without refresh keeps current semantics:

- promotion report `status = reconciled`
- pipeline report `final_status = reconciled`
- pipeline report `canonical_state_changed = false`
- pipeline report `canonical_assignment_status = unchanged`

### Fresh Canonical Promotion Event

On successful refresh, the promoter must:

- create a new `promotion_id`
- write a new promotion report
- append a new `promoted` event to `registry/promotion-log.json`
- update the deployment pointer to reference that new promotion report
- update pack-local `status/deployment.json.deployment_transaction_id`
- update pack-local `status/deployment.json.last_promoted_at`
- update the registry entry's `active_release_id` and `deployment_pointer`
  witnesses

This is a fresh canonical promotion event for the same live release. It is not
an environment transition and it is not a release change.

### Explicit Structured Refresh Metadata

The promotion report for this mode must carry a structured
`reconcile_refresh` object.

Required fields:

- `requested = true`
- `performed = true`
- `mode = canonical_evidence_refresh`
- `environment_unchanged = true`
- `release_id_unchanged = true`
- `evidence_source_pipeline_id = <current-pipeline-id>` when invoked from the
  deployment pipeline

If refresh was requested but found already-current under the idempotency rule,
the report must still carry `reconcile_refresh`, but with:

- `requested = true`
- `performed = false`
- `mode = already_current`

Free-text `promotion_reason` remains allowed, but it is not sufficient by
itself for this feature.

### Witness Fields That Must Agree After Refresh

After refresh completes, these active canonical witnesses must agree on the
same new promotion transaction:

- `deployments/<environment>/<pack-id>.json.deployment_transaction_id`
- `deployments/<environment>/<pack-id>.json.promotion_evidence_ref`
- `build-packs/<pack-id>/status/deployment.json.deployment_transaction_id`
- `build-packs/<pack-id>/status/deployment.json.active_release_id`
- `build-packs/<pack-id>/status/deployment.json.active_release_path`
- `registry/build-packs.json` entry `deployment_pointer`
- `registry/build-packs.json` entry `active_release_id`
- the new `promoted` event in `registry/promotion-log.json`
- the new promotion report path

The old promotion report remains historical evidence, but it is no longer the
active canonical promotion witness.

### No Release Artifact Mutation

This mode must not rewrite:

- `dist/releases/<release-id>/release.json`

It may continue to update mutable evidence surfaces such as:

- `status/readiness.json`
- `eval/latest/index.json`
- `eval/history/<run-id>/...`
- `status/deployment.json.last_verified_at`

### Partial-Write Safety

All eligibility checks must complete before any canonical witness is mutated.

If a write fails after the new promotion report is written but before the
pointer, registry, deployment state, and promotion log all agree on the new
promotion id:

- the command must return an error
- the new report file is treated as inert historical evidence only
- the implementation must not claim refresh success

This spec does not require transactional filesystem writes. It does require
that failed refresh attempts do not present partially refreshed canonical truth
as successful.

## Schema Changes Required

This spec requires explicit schema updates. The feature is not real without
them.

Required schema changes:

- `promotion-request.schema.json`
  adds `refresh_canonical_evidence: boolean`
- `deployment-pipeline-request.schema.json`
  adds `refresh_canonical_evidence_on_reconcile: boolean`
- `promotion-report.schema.json`
  adds `reconcile_refresh`
- `deployment-pipeline-report.schema.json`
  extends `canonical_assignment_status` to include `refreshed`

No schema may accept free-form extra properties as a substitute for these
additions.

## Validator Expectations

The factory validator should continue to enforce:

- active pointer references a report backed by a matching `promoted` event
- active pointer, registry, and pack-local deployment state agree
- single-assignee environment rules remain fail-closed

No validator relaxation is needed for this spec.

## Minimal Tooling Shape

The minimal implementation shape is:

1. extend reconcile-mode promotion logic in
   `tools/promote_build_pack.py`
2. add explicit refresh request handling
3. add the narrow same-release refresh branch behind that request
4. update `tools/run_deployment_pipeline.py` to pass through the pipeline
   refresh flag and report `canonical_assignment_status = refreshed`
5. preserve current plain reconcile behavior when refresh is not requested

## Recommended Scope Boundary

To keep the change focused, the first implementation supports refresh only
for:

- same pack
- same environment
- same `release_id`
- already-active canonical assignment
- current pipeline evidence only

It does not support:

- refresh while changing environment
- refresh while changing `release_id`
- refresh without passing validation, benchmark, and verification
- refresh from stale historical pipeline evidence
- repair of older historical promotion chains

## Acceptance Criteria

This spec is satisfied when all of the following are true:

1. A same-release production pipeline run for
   `config-drift-checker-build-pack` with
   `refresh_canonical_evidence_on_reconcile = true` can produce a fresh
   canonical promotion record for `config-drift-checker-r3`.
2. The active production pointer references that fresh promotion report.
3. `status/deployment.json.deployment_transaction_id` matches that fresh
   promotion id.
4. `status/deployment.json.last_promoted_at` advances to the new canonical
   promotion timestamp.
5. `registry/promotion-log.json` contains a matching new `promoted` event.
6. The promotion report carries the structured `reconcile_refresh` object.
7. The pipeline report records:
   `final_status = completed`,
   `canonical_state_changed = true`,
   and `canonical_assignment_status = refreshed`.
8. Whole-factory validation still passes.
9. The active release remains `config-drift-checker-r3`.
10. `dist/releases/config-drift-checker-r3/release.json` is not rewritten.
11. A same-release reconcile request without the refresh flag still preserves
    current behavior and does not append a new `promoted` event.
12. A refresh request with mismatched environment, mismatched release, or
    ambiguous assignment fails closed and does not mutate the current
    canonical witnesses.

## Commands

Verification commands for this spec stay small:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory --output json
python3 tools/run_deployment_pipeline.py --factory-root /home/orchadmin/project-pack-factory --request-file <same-release-production-reconcile-refresh-request.json> --output json
```

The second request file must explicitly set:

- `commit_promotion_on_success = true`
- `refresh_canonical_evidence_on_reconcile = true`

