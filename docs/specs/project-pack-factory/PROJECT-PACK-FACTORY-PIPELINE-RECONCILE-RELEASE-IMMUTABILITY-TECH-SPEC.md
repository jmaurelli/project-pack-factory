# Project Pack Factory Pipeline Reconcile Release Immutability Tech Spec

## Purpose

Define the minimal remediation required to keep reconcile-mode deployment
pipeline runs from mutating an already-promoted release artifact.

The goal is not to redesign the deployment pipeline.

The goal is to preserve release identity while still allowing fresh validation,
benchmark, verification, and reconcile evidence to be recorded.

## Spec Link Tags

```json
{
  "spec_id": "pipeline-reconcile-release-immutability",
  "depends_on": [
    "directory-hierarchy",
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration",
    "reconcile-promotion-canonical-evidence"
  ],
  "integrates_with": [
    "factory-validation",
    "environment-assignment-consistency",
    "json-health-checker-workflow-evaluation"
  ],
  "adjacent_work": [
    "release artifact identity",
    "pipeline idempotency",
    "reconcile-mode deployment verification"
  ]
}
```

## Problem

The live JSON Health Checker production pipeline now reconciles cleanly at the
control-plane level, but the pipeline still mutates the release document for
the already-active release id.

During a reconcile run where:

- the target environment is already active
- the requested `release_id` already matches the active deployed release
- final promotion resolves as `reconciled`

the current pipeline still executes `package_release` by rewriting:

- `dist/candidates/<release-id>/release.json`
- `dist/releases/<release-id>/release.json`

with a fresh `built_at` timestamp.

That behavior conflicts with the factory's own directory contract that
`dist/releases/` contains immutable promoted releases.

It also weakens auditability, because the same release id can now point to
different release document contents at different times even when the canonical
deployment assignment did not change.

## Evidence

Evidence was collected on 2026-03-22 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: The Live Production Reconcile Pipeline Reports No Canonical Assignment Change

Command:

```bash
python3 tools/run_deployment_pipeline.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file <production-reconcile-request.json> \
  --output json
```

Observed result:

- `pipeline_id = pipeline-json-health-checker-build-pack-production-20260322t181431z`
- `status = reconciled`

Observed report in
`build-packs/json-health-checker-build-pack/eval/history/pipeline-json-health-checker-build-pack-production-20260322t181431z/pipeline-report.json`:

- `final_status = reconciled`
- `canonical_state_changed = false`
- `canonical_assignment_status = committed`

Interpretation:

- the run is explicitly framed as a revalidation of existing production state,
  not as a new canonical release assignment

### Evidence B: The Same Reconcile Report Still Says `package_release` Wrote Release Artifacts

In the same pipeline report:

- `stage_results[3].stage_id = package_release`
- `stage_results[3].status = completed`
- `stage_results[3].summary = Created candidate and release artifacts.`
- `evidence_paths` includes:
  - `build-packs/json-health-checker-build-pack/dist/candidates/json-health-checker-r3/release.json`
  - `build-packs/json-health-checker-build-pack/dist/releases/json-health-checker-r3/release.json`

Interpretation:

- the pipeline report currently claims fresh artifact creation for an
  already-active release id
- whether those artifacts were actually rewritten is established by the code
  path and worktree evidence below

### Evidence C: The Pipeline Implementation Rewrites The Release Document Unconditionally

Relevant code in `tools/run_deployment_pipeline.py`:

- computes `release_document` using `built_at = generated_at`
- assigns:
  - `candidate_path = pack_root / "dist/candidates" / release_id / "release.json"`
  - `release_path = pack_root / "dist/releases" / release_id / "release.json"`
- calls:
  - `write_json(candidate_path, release_document)`
  - `write_json(release_path, release_document)`

Interpretation:

- the current implementation has no guard for:
  - existing release artifacts
  - active deployment already pointing to the same release
  - reconcile-mode finalization

### Evidence D: Current Reconcile Activity Shows Release-Artifact Drift For The Same `release_id`

Observed current worktree diff against `HEAD` after reconcile activity on
2026-03-22, including the latest observed reconcile pipeline at
`2026-03-22T18:14:31Z`:

- `build-packs/json-health-checker-build-pack/dist/releases/json-health-checker-r3/release.json`
  changed:
  - `built_at: 2026-03-22T16:29:26Z`
  - to `built_at: 2026-03-22T18:14:31Z`
- `build-packs/json-health-checker-build-pack/dist/candidates/json-health-checker-r3/release.json`
  changed the same way

Interpretation:

- the release id `json-health-checker-r3` no longer names one stable release
  document
- the pipeline is refreshing release identity metadata, not just writing new
  evaluation evidence

### Evidence E: Fresh Verification Evidence Was Also Recorded Separately

Observed git diff after the same reconcile run:

- `build-packs/json-health-checker-build-pack/status/readiness.json`
  advanced `last_evaluated_at` and pointed validation evidence at
  `pipeline-json-health-checker-build-pack-production-20260322t181431z`
- `build-packs/json-health-checker-build-pack/eval/latest/index.json`
  advanced `updated_at` to `2026-03-22T18:14:31Z` and updated
  `benchmark_results[0].latest_run_id`,
  `benchmark_results[0].run_artifact_path`, and
  `benchmark_results[0].summary_artifact_path` to reference
  `pipeline-json-health-checker-build-pack-production-20260322t181431z`
- `build-packs/json-health-checker-build-pack/status/deployment.json`
  advanced `last_verified_at` to `2026-03-22T18:14:31Z`
- `registry/promotion-log.json`
  appended a new `pipeline_executed` event with `status = reconciled`

Interpretation:

- the factory already has appropriate mutable surfaces for fresh revalidation
  evidence
- mutating the release document is not required to record a successful
  reconcile run

### Evidence F: The Directory Contract Already Says Promoted Releases Are Immutable

Relevant text in
`PROJECT-PACK-FACTORY-DIRECTORY-HIERARCHY-TECH-SPEC.md`:

- deployment notes example says production points to an immutable release
  directory
- operational rules say:
  - keep immutable evidence in `eval/history/`
  - keep immutable promoted releases under `dist/releases/`

Interpretation:

- the current pipeline behavior is narrower than the factory's own declared
  storage contract

### Evidence G: The CI/Deployment Spec Requires Release Artifacts But Does Not Yet Distinguish Reuse From Rewrite

Relevant text in
`PROJECT-PACK-FACTORY-CI-CLOUD-DEPLOYMENT-ORCHESTRATION-TECH-SPEC.md`:

- `package_release` must produce:
  - `dist/candidates/<release-id>/release.json`
  - `dist/releases/<release-id>/release.json`
- the release document must include `built_at` or `created_at`

Interpretation:

- the existing pipeline spec says the artifacts must exist
- it does not yet say what must happen when the same promoted release id is
  revalidated via reconcile

### Evidence H: Promotion Reconcile Already Distinguishes Revalidation From Canonical Mutation

Relevant text in
`PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md` and
`PROJECT-PACK-FACTORY-RECONCILE-PROMOTION-CANONICAL-EVIDENCE-TECH-SPEC.md`:

- reconcile returns `status = reconciled`
- reconcile revalidates existing state
- reconcile avoids duplicate canonical promotion mutation

Interpretation:

- the promotion side of the factory already separates
  "revalidate current assignment" from "create a new canonical transaction"
- the deployment pipeline should preserve the same distinction for release
  artifacts

## Design Goals

- keep the remediation tightly scoped to reconcile-mode pipeline behavior
- preserve fresh validation, benchmark, verification, and reconcile evidence
- preserve the existing release artifact schema
- preserve the existing pipeline stage order
- align pipeline behavior with the declared immutability of `dist/releases/`
- keep verification and tests intentionally small under the testing policy

## Non-Goals

- redesigning release packaging for new promotions
- changing build-pack promotion semantics outside reconcile-linked pipeline runs
- adding benchmark scenarios
- broadening workflow test matrices
- inventing a second latest-evidence surface

## Contract Clarification

This spec narrows the `package_release` contract for the specific case where
the pipeline is revalidating an already-active release id.

The normal rule remains:

- new promotion-targeted pipeline runs create release artifacts for the
  requested `release_id`

The reconcile-linked rule becomes:

- if the target environment already points at the same `release_id` and the
  pipeline is revalidating that same release, the pipeline must reuse the
  existing release artifacts instead of rewriting them

This is not a broad change to packaging semantics. It is an idempotency rule
for an already-canonical release.

## Required Behavior

### Immutable Release Reuse

If all of the following are true before `package_release` begins:

- `status/deployment.json.active_environment` equals the requested target
  environment
- `status/deployment.json.active_release_id` equals the requested `release_id`
- `status/deployment.json.active_release_path` equals
  `dist/releases/<release-id>`
- `dist/releases/<release-id>/release.json` already exists

then `package_release` must not rewrite:

- `dist/releases/<release-id>/release.json`
- `dist/candidates/<release-id>/release.json` when that candidate artifact
  already exists for the same release id

The pipeline may still reference those existing paths in `evidence_paths`.

### Stage Semantics For Reused Release Artifacts

In the immutable-reuse case, the `package_release` stage should report:

- `stage_id = package_release`
- `status = reconciled`

with a summary that makes it explicit that:

- existing release artifacts were reused
- no release artifact contents were mutated

This keeps the report aligned with actual behavior instead of claiming fresh
artifact creation.

### Fail-Closed Rules

If the pipeline appears to be reconciling an already-active release id but the
release artifact state is incomplete or contradictory, the tool must fail
closed rather than silently synthesizing a replacement immutable release.

Fail-closed examples include:

- `status/deployment.json` claims `dist/releases/<release-id>` is active but
  `dist/releases/<release-id>/release.json` is missing
- the active release id matches but the active release path does not
  match `dist/releases/<release-id>`
- the pack is already active in the environment but the request attempts to
  "reconcile" a different release path shape under the same `release_id`

The correct recovery path for such corruption is explicit repair or a new
release id, not silent mutation of the old release identity.

### Mutable Evidence Still Allowed

The immutable-reuse rule does not block normal mutable evidence updates.

The pipeline may still update:

- `eval/history/<pipeline-id>/pipeline-report.json`
- `eval/history/<pipeline-id>/validation-result.json`
- `eval/history/<pipeline-id>/benchmark-result.json`
- `eval/history/<pipeline-id>/verification-result.json`
- `eval/latest/index.json`
- `status/readiness.json`
- `status/deployment.json.last_verified_at`
- `registry/promotion-log.json` with a new `pipeline_executed` event
- reconcile-mode promotion history under `eval/history/<promotion-id>/`

This preserves freshness of operational evidence while keeping release identity
stable.

### Release Identity Rule

For a release id already active in an environment, the contents of
`dist/releases/<release-id>/release.json` must remain byte-stable across
reconcile-only pipeline reruns.

In particular, a reconcile-only rerun must not refresh:

- `built_at`
- `created_at`
- `release_state`
- lineage-derived release identity fields

unless the operator is creating a new release id instead of reconciling the
existing one.

## Minimal Test Posture

This remediation should stay within the testing policy's intentionally small
surface.

Explicit limits:

- this spec does not authorize adding, modifying, or strengthening tests
- if implementation later receives explicit operator approval for test changes,
  prefer replacing a weaker existing pipeline test instead of growing the
  current CI/deployment orchestration surface
- do not add new benchmark scenarios
- do not add a broad environment matrix
- prefer exercising existing workflow surfaces over new helper-level tests
- keep automated verification local, deterministic, and text-only by preferring
  the existing copied-factory harness pattern in
  `tests/test_run_deployment_pipeline.py`

Operational live-pack evidence may still be collected secondarily, but it
should not replace the smaller local verification surface.

## Acceptance Criteria

1. A reconcile-linked production pipeline rerun for
   `json-health-checker-build-pack` and `json-health-checker-r3` returns
   `final_status = reconciled`.
2. The resulting pipeline report records `package_release` as artifact reuse,
   not fresh artifact creation.
3. Before and after that reconcile run,
   `build-packs/json-health-checker-build-pack/dist/releases/json-health-checker-r3/release.json`
   is byte-identical.
4. If
   `build-packs/json-health-checker-build-pack/dist/candidates/json-health-checker-r3/release.json`
   already exists before the run, it is also byte-identical after the run.
5. Fresh mutable evidence still advances:
   - `status/readiness.json.last_evaluated_at`
   - `eval/latest/index.json.updated_at`
   - `eval/latest/index.json.benchmark_results[0].latest_run_id`
   - `status/deployment.json.last_verified_at`
   - `registry/promotion-log.json.updated_at`
6. `python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory`
   still reports a valid factory after the reconcile run.
7. Primary automated verification remains a local copied-factory workflow
   surface; any live JSON Health Checker reconcile run is secondary operational
   evidence, not the only verification path.

## Verification Commands

Primary verification should stay bounded to the smallest existing factory
surfaces:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory --output json
python3 tools/run_deployment_pipeline.py --factory-root /home/orchadmin/project-pack-factory --request-file <reconcile-request.json> --output json
```

If deeper confirmation is needed during implementation, use file-content
comparison on the existing release artifact before and after the reconcile run
rather than expanding the workflow suite.

If broader workflow confidence is desired later, `run_workflow_eval.py` may be
used as secondary evidence after the narrow pipeline verification passes, not
as the primary verification surface for this change.
