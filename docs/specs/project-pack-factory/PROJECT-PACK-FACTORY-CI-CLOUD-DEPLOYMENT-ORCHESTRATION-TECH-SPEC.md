# Project Pack Factory CI And Cloud Deployment Orchestration Tech Spec

## Purpose

Define a provider-neutral orchestration contract for running CI validation,
artifact packaging, cloud deployment, and post-deploy verification for a build
pack.

This spec sits above the promotion workflow:

- the promotion workflow is the state transition contract
- the CI/cloud orchestration workflow is the execution contract that can produce
  the evidence needed for promotion

This spec assumes the promotion workflow exists as a contract, but does not
assume it is already implemented in the current factory codebase.

## Spec Link Tags

```json
{
  "spec_id": "ci-cloud-deployment-orchestration",
  "depends_on": [
    "directory-hierarchy",
    "build-pack-materialization",
    "build-pack-promotion"
  ],
  "integrates_with": [
    "runtime-agent-memory"
  ],
  "adjacent_work": [
    "provider adapters and CI execution tooling"
  ]
}
```

## Problem

The factory currently tracks readiness, deployment state, and promotion
evidence, but it does not yet provide a concrete orchestration contract for
running:

- validation commands
- benchmark suites
- release packaging
- provider deployment
- post-deploy verification

Without a bounded orchestration contract:

- CI systems and agents will invent incompatible stage models
- deployment evidence will be fragmented
- cloud deploy behavior will not be explainable to later agents
- promotion will depend on unverifiable out-of-band execution

## Design Goals

- orchestration must be provider neutral and agent-readable
- pipeline stages must be explicit and ordered
- secrets and credentials must remain external to factory state
- all execution evidence must be machine-readable
- final deployment state must still flow through the promotion workflow
- the pipeline must fail closed if any required stage fails

## Scope

This spec defines:

- the canonical orchestration tool contract
- the pipeline stage model
- the provider adapter response contract
- the pipeline evidence artifact
- the request and report JSON Schemas

This spec does not define:

- a specific CI vendor
- a specific cloud provider
- secret-management implementation
- rollback execution

## Canonical Tool

- `tools/run_deployment_pipeline.py`

Canonical invocation:

```bash
python3 tools/run_deployment_pipeline.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /abs/path/deployment-pipeline-request.json \
  --output json
```

## Pipeline Model

The pipeline executes these stages in order:

1. `validate_factory_state`
2. `validate_build_pack`
3. `run_required_benchmarks`
4. `package_release`
5. `deploy_release`
6. `verify_deployment`
7. `finalize_promotion`

Every stage is required in v1.

If any stage fails:

- later stages must not run
- no promotion to the target environment may be recorded
- the pipeline report must still be written with terminal failure evidence

## Request Contract

The request must declare:

- the target build pack
- the target environment
- the cloud adapter id
- the release id
- the structured references used to derive validation and benchmark execution
- whether final promotion should be committed on success

Secrets must not be written into the request file. The request may only reference
environment-variable names or external secret handles.

Validation and benchmark execution must default to current pack-local control
surfaces rather than opaque request-provided shell commands:

- validation must derive from `pack.json.entrypoints.validation_command`
- benchmark execution must derive from:
  - `pack.json.entrypoints.benchmark_command`
  - mandatory readiness gates in `status/readiness.json`

The request may still provide explicit post-deploy `verification_commands`.

## Runtime Agent Memory Integration

For runtime-memory-enabled packs, the pipeline must treat the runtime-memory
benchmark as an ordinary required benchmark rather than a side-channel runtime
operation.

In the current v1 model this means:

- the active benchmark declaration is `agent-memory-restart-small-001`
- the benchmark stage publishes `agent-memory-scorecard.json` and
  `agent-memory-snapshot.json` into `eval/history/<run-id>/`
- `eval/latest/index.json` remains the canonical latest index for that
  benchmark result
- readiness continues to read the gate state from
  `status/readiness.json.required_gates`

The pipeline must not invent a second runtime-memory "latest summary" surface.

## Provider Adapter Contract

The pipeline does not call cloud APIs directly. It calls an adapter boundary.

The adapter contract must produce:

- `adapter_id`
- `provider`
- `deployment_handle`
- `deployment_url`
- `status`
- `artifacts`
- `logs`

Allowed adapter statuses:

- `completed`
- `failed`
- `reconciled`

The adapter result becomes part of the pipeline report.

## Release Artifact Contract

The `package_release` stage must produce:

- `dist/candidates/<release-id>/release.json`
- `dist/releases/<release-id>/release.json`

The current deployment contracts require active deployed releases to be
referenced through pack-relative `dist/releases/<release-id>`. Candidate
artifacts remain pre-promotion evidence only.

The release document must match the current factory release artifact shape and
include:

- `release_id`
- `build_pack_id`
- `source_template_id`
- `source_template_revision`
- `built_at` or `created_at`
- `artifact_paths`
- a release-state field matching the current artifact format

## Finalization Rules

If `commit_promotion_on_success = true`:

- the pipeline must invoke the promotion workflow after successful verification
- `finalize_promotion` must write the same environment state that a direct
  promotion would have written

If `commit_promotion_on_success = false`:

- the pipeline may package, deploy, and verify
- the pipeline must not mutate:
  - `status/deployment.json`
  - `deployments/<environment>/<build-pack-id>.json`
  - `registry/build-packs.json`

This distinction keeps the pipeline usable for dry-run or pre-promotion
verification.

## Evidence Contract

Every pipeline run must write:

- `build-packs/<build-pack-id>/eval/history/<pipeline_id>/pipeline-report.json`

The report must be written even when the pipeline fails.

Required evidence paths include:

- pipeline-stage logs or summaries
- validation command outputs
- benchmark scorecards when benchmarks run
- release artifact paths
- provider adapter result
- post-deploy verification result

The factory validator must discover pipeline reports through
`registry/promotion-log.json` `pipeline_executed` events rather than by scanning
`eval/history/`.

## Operation Log Effects

Every pipeline run must append:

- `event_type = pipeline_executed`

to:

- `registry/promotion-log.json`

If the pipeline committed promotion successfully, the standard `promoted` event
must also be present.

Every `pipeline_executed` event must include:

- `pipeline_id`
- `build_pack_id`
- `pipeline_report_path`

## Required Schema Additions

This workflow adds:

- `schemas/deployment-pipeline-request.schema.json`
- `schemas/deployment-pipeline-report.schema.json`

This workflow conceptually extends:

- `registry/promotion-log.json`
  - must accept `event_type = pipeline_executed`

## Cross-File Invariants

The factory validator must enforce:

- `pipeline-report.build_pack_id` equals the build-pack root used by the run
- `pipeline-report.target_environment` matches the request
- `pipeline-report.stage_results` contains all seven required stages in order
- `pipeline-report.final_status = completed` only if every required stage is
  `completed` or `reconciled`
- when `commit_promotion_on_success = true` and `final_status = completed`:
  - a matching `promoted` event exists
  - `status/deployment.json.active_environment` equals the target environment
- a matching `pipeline_executed` event exists whose `pipeline_id` and
  `pipeline_report_path` match the report
- when `commit_promotion_on_success = false`:
  - the pipeline must not create or mutate deployment pointers
- when `pipeline-report.adapter_result` is not `null`, its `status` must be
  `completed` or `reconciled` before `verify_deployment` may complete

## Example Request

```json
{
  "schema_version": "deployment-pipeline-request/v1",
  "build_pack_id": "ai-native-codex-build-pack-v2",
  "target_environment": "testing",
  "release_id": "release-20260320-001",
  "cloud_adapter_id": "local-k8s-adapter",
  "invoked_by": "orchadmin",
  "commit_promotion_on_success": true,
  "validation_command_ref": "pack.json.entrypoints.validation_command",
  "benchmark_source": "status/readiness.json.required_gates",
  "verification_commands": [
    "curl -fsS https://testing.example.invalid/healthz"
  ],
  "secret_refs": [
    "KUBECONFIG_PATH",
    "TESTING_DEPLOY_TOKEN"
  ]
}
```

## Example Report

```json
{
  "schema_version": "deployment-pipeline-report/v1",
  "pipeline_id": "pipeline-ai-native-codex-build-pack-v2-testing-20260320t140000z",
  "generated_at": "2026-03-20T14:00:00Z",
  "build_pack_id": "ai-native-codex-build-pack-v2",
  "build_pack_root": "build-packs/ai-native-codex-build-pack-v2",
  "target_environment": "testing",
  "release_id": "release-20260320-001",
  "cloud_adapter_id": "local-k8s-adapter",
  "invoked_by": "orchadmin",
  "commit_promotion_on_success": true,
  "final_status": "completed",
  "operation_log_update": {
    "promotion_log_path": "registry/promotion-log.json",
    "event_type": "pipeline_executed",
    "pipeline_id": "pipeline-ai-native-codex-build-pack-v2-testing-20260320t140000z",
    "build_pack_id": "ai-native-codex-build-pack-v2",
    "pipeline_report_path": "eval/history/pipeline-ai-native-codex-build-pack-v2-testing-20260320t140000z/pipeline-report.json"
  },
  "stage_results": [
    {
      "stage_id": "validate_factory_state",
      "status": "completed",
      "summary": "Factory-wide validation passed."
    },
    {
      "stage_id": "validate_build_pack",
      "status": "completed",
      "summary": "Build-pack validation and tests passed."
    },
    {
      "stage_id": "run_required_benchmarks",
      "status": "completed",
      "summary": "Required benchmarks passed."
    },
    {
      "stage_id": "package_release",
      "status": "completed",
      "summary": "Release artifacts written to dist/candidates and dist/releases."
    },
    {
      "stage_id": "deploy_release",
      "status": "completed",
      "summary": "Cloud adapter deployed the release."
    },
    {
      "stage_id": "verify_deployment",
      "status": "completed",
      "summary": "Post-deploy verification passed."
    },
    {
      "stage_id": "finalize_promotion",
      "status": "completed",
      "summary": "Promotion state committed."
    }
  ],
  "adapter_result": {
    "adapter_id": "local-k8s-adapter",
    "provider": "kubernetes",
    "deployment_handle": "testing/ai-native-codex-build-pack-v2",
    "deployment_url": "https://testing.example.invalid",
    "status": "completed",
    "artifacts": [
      "dist/candidates/release-20260320-001/release.json",
      "dist/releases/release-20260320-001/release.json"
    ],
    "logs": [
      "eval/history/pipeline-ai-native-codex-build-pack-v2-testing-20260320t140000z/deploy.log"
    ]
  },
  "evidence_paths": [
    "build-packs/ai-native-codex-build-pack-v2/eval/history/pipeline-ai-native-codex-build-pack-v2-testing-20260320t140000z/pipeline-report.json",
    "build-packs/ai-native-codex-build-pack-v2/dist/candidates/release-20260320-001/release.json",
    "build-packs/ai-native-codex-build-pack-v2/dist/releases/release-20260320-001/release.json"
  ]
}
```
