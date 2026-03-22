# Project Pack Factory Build-Pack Control-Plane And Dataplane Integrity Tech Spec

## Purpose

Define the PackFactory contract that keeps build-pack control-plane evidence
honest and upgrades the current `json-health-checker-build-pack` smoke
benchmark so the build-pack's primary runtime path is actually exercised before
PackFactory treats its readiness evidence as trustworthy.

This spec closes three concrete gaps observed in the current
`json-health-checker-build-pack` candidate:

- pack validation treats local scratch state as required canonical content
- readiness and eval evidence can drift from the pipeline artifacts they claim
  to summarize
- the required smoke benchmark can pass without exercising the build-pack's
  primary runtime behavior

## Spec Link Tags

```json
{
  "spec_id": "build-pack-control-plane-dataplane-integrity",
  "depends_on": [
    "directory-hierarchy",
    "build-pack-promotion"
  ],
  "integrates_with": [
    "ci-cloud-deployment-orchestration",
    "environment-assignment-consistency"
  ],
  "adjacent_work": [
    "validator hardening",
    "readiness artifact reconciliation",
    "minimal dataplane smoke coverage"
  ]
}
```

## Problem

Project Pack Factory already records machine-readable validation, benchmark,
readiness, promotion, and deployment state for build packs.

Today that control-plane can overstate confidence because it does not cleanly
separate:

- canonical pack content
- local scratch state
- execution evidence
- summarized readiness claims
- dataplane behavior that the build-pack actually performs

Without a stricter contract:

- a clean checkout can fail validation for non-canonical reasons
- readiness can point at stale or mismatched evidence
- a promoted build-pack can appear ready even when its primary runtime behavior
  is broken

## Motivating Example

The current `json-health-checker-build-pack` demonstrates all three gaps.

### Validation Gap

Its validator currently loads `pack.json.directory_contract` and treats every
string path as required content, including:

- `local_state_dir = .pack-state`

That means a fresh or sanitized checkout can fail `validate-project-pack` even
though `.pack-state` is explicitly local scratch state rather than canonical
pack content.

### Evidence Gap

Its current readiness and eval surfaces can disagree with the pipeline
artifacts they reference:

- benchmark ids can differ between `eval/latest/index.json` and the referenced
  benchmark artifact
- readiness gate ids and summaries can drift from the actual benchmark report
- validation gate evidence can point at a benchmark artifact instead of the
  validation artifact

That leaves later agents unable to trust what PackFactory says was actually
validated and benchmarked.

### Dataplane Protection Gap

Its current required smoke benchmark only checks for the presence of a few
files and does not execute the build-pack's primary runtime command path.

That means the control-plane can report:

- benchmark `pass`
- readiness `ready_for_deploy`

while the dataplane behavior exposed by `check-json` is regressed.

## Design Goals

- keep PackFactory control-plane authority explicit and fail closed
- keep local scratch state out of canonical pack validation requirements
- ensure readiness and eval summary surfaces are exact witnesses of recorded
  artifacts rather than best-effort prose
- harden PackFactory readiness decisions without creating a second readiness
  model
- fix the current candidate's smoke benchmark so it protects the runtime path
  the pack exists to expose
- keep the test delta intentionally tiny and high-signal

## Scope

This spec defines:

- the authority boundary between PackFactory control-plane state and build-pack
  dataplane behavior
- validator rules for canonical versus local-only paths
- readiness and eval artifact consistency requirements
- the minimum dataplane coverage rule for the current
  `json-health-checker-build-pack`
- the implementation posture for the `json-health-checker-build-pack` candidate

This spec does not define:

- a new general benchmark taxonomy for all build packs
- large unit-test matrices for tiny runtime helpers
- a second runtime control plane inside build packs
- non-PackFactory application deployment semantics

## Control-Plane Versus Dataplane Boundary

PackFactory control-plane state is the machine-readable authority for whether a
build-pack is:

- valid
- ready
- promoted
- assigned to an environment

Those claims live in surfaces such as:

- `pack.json`
- `status/readiness.json`
- `status/deployment.json`
- `eval/latest/index.json`
- `registry/build-packs.json`
- `registry/promotion-log.json`
- pipeline, validation, benchmark, and promotion reports under `eval/history/`

The build-pack dataplane is the runtime behavior the pack actually exposes to a
user or operator.

For `json-health-checker-build-pack`, the dataplane is the command path that:

- reads a JSON file
- validates required fields
- returns pass or fail output

PackFactory does not gain a new field called `dataplane_readiness`.

Instead, this spec tightens the existing control-plane contract behind:

- `status/readiness.json.ready_for_deployment`
- `status/readiness.json.required_gates`
- promotion and pipeline preconditions that consume those fields

## Canonical Content Versus Local Scratch State

Pack validation must distinguish canonical pack content from local working
state.

### Canonical Rule

The validator may require:

- identity files
- status files
- source files
- benchmark declarations
- pack-local evidence indexes
- other files and directories needed for deterministic traversal

The validator must not require local-only scratch paths whose absence does not
invalidate the pack.

### Local Scratch Rule

The following contract class is local-only:

- `local_state_dir`

For v1, `pack.json.directory_contract.local_state_dir` means:

- the directory name is reserved for local runtime or agent state
- the pack may create it opportunistically
- the validator must treat it as optional
- its absence in a clean checkout must not fail validation

This rule applies to both template packs and build packs.

This does not change the existing scaffold and materialization behavior that
creates `.pack-state/` up front as a convenience. It only changes the
validation meaning of that path:

- created by default
- optional when absent
- never a readiness or promotion blocker by itself

### Implementation Requirement

`validate-project-pack` must classify `directory_contract` entries into:

- canonical required paths
- optional local-only paths

The simplest compliant implementation is:

- explicitly exclude `local_state_dir` from `missing_paths`
- still include it in `checked_paths` only when it exists

PackFactory must not infer other optional classes heuristically in this change.
Only `local_state_dir` receives optional treatment in v1.

## Evidence Integrity Contract

Readiness and eval summary files are PackFactory control-plane witnesses. They
must be mechanically aligned with the artifacts they point to.

### Eval Latest Invariant

For each `benchmark_results[]` entry in `eval/latest/index.json`:

- when `status != not_run`, `run_artifact_path` must begin with:
  - `eval/history/<latest_run_id>/`
- when `status != not_run`, `summary_artifact_path` must be either:
  - `eval/history/<latest_run_id>/...`
  - or `eval/latest/...` only when another linked spec explicitly defines that
    latest-summary surface
- when `status != not_run`, the referenced run artifact must report the same:
  - `benchmark_id`
  - terminal status

Materialization-seeded `not_run` entries are explicitly valid before the first
benchmark execution. For those seeded entries:

- `latest_run_id` may equal the materialization id
- `run_artifact_path` may point at the materialization report
- `summary_artifact_path` may point at the materialization report

The stricter run-artifact consistency rule starts only after the benchmark has
executed with a status other than `not_run`.

### Readiness Gate Invariants

For each gate in `status/readiness.json.required_gates`:

- `gate_id` must match the actual gate being satisfied
- `evidence_paths` must point to the artifact type that produced the gate
  result

For v1:

- validation gates must point to validation artifacts
- benchmark gates must point to `eval/latest/index.json`
- benchmark-gate identity is then resolved through the matching
  `eval/latest/index.json.benchmark_results[]` entry for that gate id

The `summary` field remains human-facing explanatory text. It is not promoted
to a machine-parsed authority signal by this spec.

### Pipeline Report Witness Rule

If a pipeline report claims a benchmark or validation stage completed, the
artifacts referenced by readiness and `eval/latest/index.json` must be derived
from that exact run or from a later successful run of the same gate id.

PackFactory must not silently mix:

- renamed benchmark declarations
- older benchmark artifacts
- newer summary metadata

If identity drift is detected, readiness must fail closed until fresh evidence
is written.

### Readiness Integrity Precondition

This spec does not create a second readiness authority. It strengthens the
existing one.

A build pack must not be treated as ready for promotion when any of the
following is true:

- `status/readiness.json.ready_for_deployment = true` but a mandatory gate's
  referenced evidence does not resolve
- a benchmark gate points to `eval/latest/index.json` but no matching
  `benchmark_results[]` entry exists for that gate id
- a non-`not_run` benchmark result disagrees with its referenced run artifact
- a validation gate points to a non-validation artifact

That means linked specs must consume readiness as:

- `ready_for_deployment = true`
- all mandatory gates `pass`
- and evidence-integrity checks pass

not merely as:

- `ready_for_deployment = true`
- all mandatory gates `pass`
- `eval/latest/index.json` exists

### Regeneration Requirement

When a build-pack benchmark id, gate id, or readiness summary contract changes,
the corresponding evidence must be regenerated rather than patched only in the
summary surfaces.

For the current `json-health-checker-build-pack`, that means the build-pack
must not be treated as cleanly ready until:

- `benchmark-result.json`
- `validation-result.json`
- `status/readiness.json`
- `eval/latest/index.json`

all agree on build-pack identity and gate mapping.

## Json Health Checker Dataplane Benchmark Contract

This spec intentionally scopes the dataplane requirement to the current
`json-health-checker-build-pack` candidate rather than generalizing it across
all build packs in v1.

For this candidate, the runtime path that must be protected is:

- invoke the JSON checker against a small object payload
- confirm pass when all required fields are present
- confirm fail when a required field is missing

### Minimum Required Coverage

The required smoke benchmark for a build pack must:

- execute the pack's published runtime surface through the CLI command path,
  not by calling an internal helper directly
- assert one passing dataplane case
- assert one fail-closed dataplane case

The benchmark may also keep a small structural check for:

- `pack.json`
- readiness state
- benchmark declaration presence

but those checks are supplemental and cannot be the only benchmark behavior.

### Smallness Constraint

To stay within the factory testing policy, the dataplane smoke benchmark must
remain:

- text-only
- deterministic
- local
- fixture-light

For the current pack, the compliant benchmark should use inline temporary JSON
files or equivalent tiny local fixtures rather than a large test matrix.

## Json Health Checker Candidate Requirements

The current `json-health-checker-build-pack` must satisfy all of the following
before it is treated as a trustworthy primary testing candidate:

### Control-Plane Corrections

- `validate-project-pack` no longer fails when `.pack-state` is absent
- readiness validation evidence points at `validation-result.json`
- benchmark gate ids use build-pack identity consistently
- benchmark gate evidence points at `eval/latest/index.json`
- the matching `eval/latest` entry resolves to a run artifact under
  `eval/history/<latest_run_id>/`
- non-`not_run` `eval/latest` entries match the benchmark artifact they
  reference

### Dataplane Protection Corrections

- `benchmark-smoke` executes the JSON health checker runtime
- the benchmark proves one pass case and one fail case
- the benchmark returns the build-pack benchmark id, not the template-pack id

### Promotion Readiness Rule

Until the corrected evidence is regenerated, the build-pack may still exist in
the repo but should be treated as carrying stale readiness evidence.

Operators and agents should therefore distinguish:

- current deployment assignment state
- trustworthy readiness evidence

Those are related but not interchangeable control-plane claims.

This separation is intentional:

- deployment assignment records what environment currently points at
- readiness integrity determines whether the pack is eligible for future
  promotion

This spec does not require automatic eviction of an already-assigned pack just
because readiness evidence later becomes stale.

## Required Spec Corrections

This spec requires coordinated corrections in the existing family:

- promotion workflow spec:
  - require readiness evidence to be internally consistent before promotion
- CI and deployment orchestration spec:
  - require pipeline outputs and summary files to agree on benchmark identity
  - fail closed when summary metadata is patched without fresh evidence
- directory hierarchy spec:
  - clarify that `.pack-state/` is local scratch state, not canonical pack
    content even though it is scaffolded by default
  - keep benchmark-gate `evidence_paths` pointing at `eval/latest/index.json`
- testing policy:
  - no policy expansion required
  - continue to prefer replacement or strengthening of weak tests over adding
    broad new coverage

## Minimal Test Posture

Keep the test delta absolute minimum.

Required workflow-cap posture:

- `0` net-new tests in the capped materialization, promotion, and
  CI-orchestration workflow buckets

Recommended replacement plan:

- replace the weakest current CI workflow assertion-only case with an evidence
  integrity case
  - recommended replacement target:
    `test_run_deployment_pipeline_appends_pipeline_log_event`
- keep any `.pack-state` validator regression coverage outside the capped
  4/4/4 workflow budget, or satisfy it by strengthening an existing
  non-workflow validator test if one exists at implementation time

Recommended coverage:

- one small validator contract check proving `local_state_dir` is optional
- one strengthened smoke benchmark or equivalent replacement workflow test
  proving the required benchmark exercises one pass case and one fail-closed
  dataplane case

The evidence-integrity corrections should rely primarily on fail-closed
workflow validation and regenerated artifacts rather than a broad new test
matrix.

## Validation

The implemented fix should validate through:

- `validate-project-pack` passing in a clean checkout without `.pack-state`
- freshly regenerated readiness and eval files matching the written validation
  and benchmark artifacts
- one small dataplane smoke path proving both pass and fail behavior for the
  JSON checker
- whole-factory validation continuing to pass after the evidence is
  regenerated

In this section, artifact regeneration and whole-factory validation are
acceptance steps, not additional test-budget requests.

## Relationship To Existing Specs

This spec is a focused integrity layer across:

- `PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- `PROJECT-PACK-FACTORY-DIRECTORY-HIERARCHY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-CI-CLOUD-DEPLOYMENT-ORCHESTRATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-ENVIRONMENT-ASSIGNMENT-CONSISTENCY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

It should be implemented as a coordinated PackFactory control-plane hardening
change plus a tiny build-pack dataplane benchmark upgrade, not as a pure
documentation-only cleanup.
