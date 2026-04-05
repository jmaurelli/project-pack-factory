# Project Pack Factory Remote Autonomy End-To-End Roundtrip Tech Spec

## Purpose

Define the reusable factory-level workflow that proves PackFactory can:

1. materialize a build-pack locally
2. stage it to a remote target
3. let a remote agent complete the pack-local backlog
4. export remote runtime evidence
5. pull that bundle back
6. import it as supplementary factory evidence

This is the end-to-end test of the source-target control-plane split.

## Spec Link Tags

```json
{
  "spec_id": "remote-autonomy-end-to-end-roundtrip",
  "part_of": [
    "remote-autonomy-spec-family-overview"
  ],
  "depends_on": [
    "remote-autonomy-target-workspace-and-staging",
    "portable-build-pack-autonomy-runtime-helpers",
    "remote-autonomous-build-pack-execution",
    "external-runtime-evidence-import"
  ],
  "integrates_with": [
    "factory-validation",
    "build-pack-control-plane-dataplane-integrity"
  ]
}
```

## Relationship To Remote Autonomy Spec Family

This is the fourth and top-level workflow spec in the remote-autonomy family.

It does not replace the lower-level specs.

Instead, it composes them:

- staging prepares the remote target
- portable helpers make the staged build-pack self-sufficient
- remote execution runs the bounded autonomy loop
- this spec closes the roundtrip by pulling and importing the exported runtime
  evidence

This spec flows directly from the family overview and from the first three
family specs:

- the family overview defines this as the bounded end-to-end proof layer
- the staging spec defines the staged payload identity and target manifest
- the helper spec defines the portable helper manifest the staged pack carries
- the execution spec defines the execution manifest, terminal outcome, and
  same-run export requirements that this spec must preserve through pullback
  and import

Success here proves only bounded end-to-end roundtrip composition across those
layers.

It does not by itself prove:

- promotion readiness as canonical local truth
- deployment assignment
- direct local readiness mutation beyond supplementary evidence import

Read it after:

- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md)

Its relationship to the broader project is:

- it is the reusable proof of the PackFactory source-target split
- it keeps imported remote evidence supplementary rather than turning the
  remote target into a second control plane

## Problem

The repo can already prove important pieces in isolation:

- local autonomous completion of a bounded starter backlog
- pack-local runtime evidence export
- local factory import of external runtime evidence

What it does not yet define is the reusable roundtrip that joins those pieces
into one auditable end-to-end workflow.

Without this spec:

- the remote test remains a manual sequence
- bundle pullback paths drift between operators
- import intent becomes under-specified
- future roundtrip runs become harder to compare

## Design Goals

- keep the whole roundtrip request-driven and reusable
- keep the remote side outside local control-plane authority
- keep bundle retrieval deterministic
- keep import explicit and auditable
- prove the PackFactory source versus remote target split end to end

## Non-Goals

This spec does not:

- auto-promote a build-pack after imported evidence arrives
- make imported evidence canonical readiness by itself
- require a specific remote host name or alias
- require the remote target to host the whole factory

## Proposed Reusable Scripts

V1 should add:

- `tools/pull_remote_runtime_evidence.py`
- `tools/run_remote_autonomy_test.py`

The wrapper script should orchestrate:

1. remote target preparation
2. remote pack staging
3. remote autonomy execution
4. runtime evidence pullback
5. local import request creation
6. local import invocation

Each lower-level step must remain reusable on its own.

## Wrapper Request Contract

V1 should add:

- `docs/specs/project-pack-factory/schemas/remote-autonomy-test-request.schema.json`

At minimum it should include:

- `schema_version = remote-autonomy-test-request/v1`
- `remote_run_request_path`
- `local_bundle_staging_dir`
- `pull_bundle`
- `import_bundle`
- `imported_by`
- `import_reason`
- `test_reason`

This wrapper request is the source of truth for the end-to-end run intent.

The remote run request remains the source of truth for remote coordinates and
pack identity.

The wrapper request stays intentionally small in v1.

To keep the end-to-end proof deterministic without widening the wrapper
request, the wrapper must derive and verify from the referenced remote run
request:

- `source_build_pack_id`
- `run_id`
- `remote_target_label`
- the expected staged remote export directory

If later roundtrip evidence disagrees with those derived identities, the
wrapper must fail closed before import.

## Roundtrip Manifest Contract

V1 should add:

- `docs/specs/project-pack-factory/schemas/remote-roundtrip-manifest.schema.json`

The wrapper should write a local orchestration manifest under the local bundle
staging root, for example:

- `roundtrip-manifest.json`

At minimum it should include:

- `schema_version`
- `wrapper_request_sha256`
- `remote_run_request_sha256`
- `source_build_pack_id`
- `run_id`
- `remote_target_label`
- `target_manifest_sha256`
- `execution_manifest_sha256`
- `portable_helper_manifest_sha256` when the build-pack declares one
- `pulled_bundle_path`
- `pulled_bundle_sha256`
- `pulled_at`
- `generated_import_request_path`
- `generated_import_request_sha256`

This manifest is the roundtrip-layer audit record that proves the pulled and
imported bundle is the same run that was staged and executed.

## Local Bundle Staging Contract

The pull step should default to a deterministic local staging root such as:

- `.pack-state/remote-autonomy-roundtrips/<remote_target_label>/<build_pack_id>/<run_id>/incoming`

The pulled bundle itself should remain immutable once retrieved.

To make that immutability auditable, the pull step must record at least:

- the pulled bundle path
- the pulled bundle digest
- the retrieved-at timestamp
- the originating `run_id`

The later import request must reference that exact staged bundle artifact, not
an independently rediscovered bundle path.

The local staging root is orchestration state only.

It must not:

- become canonical PackFactory readiness state
- replace imported history under the target build-pack

For the transient local scratch-root design, this local staging root should be
treated as scratch workspace. If PackFactory needs to preserve operator-facing
artifacts such as generated import requests or roundtrip manifests, it must
write or copy them to a durable path outside scratch before cleanup runs.

## Import Contract

If `import_bundle = true`, the wrapper must create an explicit import request
for:

- `tools/import_external_runtime_evidence.py`

The wrapper must not copy bundle artifacts directly into `eval/history/`
without going through the existing bounded importer.

Before creating the import request, the wrapper must verify linkage across:

- the wrapper request
- the referenced remote run request
- `.packfactory-remote/target-manifest.json`
- `.packfactory-remote/execution-manifest.json`
- the pulled bundle

At minimum it must verify:

- matching `source_build_pack_id`
- matching `run_id`
- matching `remote_target_label` where recorded
- a pulled bundle digest that matches the locally staged artifact selected for
  import
- execution-manifest linkage to the same staged target manifest and same
  request lineage
- bundle contents that match the terminal execution outcome recorded by the
  execution layer

If any of those identities disagree, the wrapper must fail closed before
invoking the importer.

## Re-Entry Boundary

The only allowed canonical re-entry path in this spec is the existing bounded
external runtime evidence importer.

The wrapper may write only:

- local orchestration scratch under the local bundle staging root
- the roundtrip manifest
- the generated import request
- any importer-owned supplementary history written by the bounded importer

The wrapper must not directly update:

- local `registry/*.json`
- local `deployments/`
- local promotion history
- local `status/readiness.json`
- local `status/work-state.json`
- local `eval/latest/index.json`
- local release artifacts

Imported remote evidence remains supplementary only.

It must not be treated by the wrapper as canonical readiness, deployment, or
promotion truth.

## Control-Plane Boundary

The wrapper and its lower-level helpers must never update:

- local `registry/*.json`
- local `deployments/`
- local promotion history
- local `status/readiness.json`
- local `status/work-state.json`
- local `eval/latest/index.json`
- local release artifacts

unless a later explicit promotion workflow is invoked separately after evidence
review.

The wrapper may only:

- stage and run the remote pack
- retrieve the exported bundle
- import the bundle through the bounded importer

## End-To-End Success Criteria

This spec is satisfied when all of the following are true:

1. A build-pack is staged from PackFactory to a remote target through reusable
   scripts.
2. The remote agent completes the pack-local backlog or reaches a declared stop
   condition.
3. The remote run exports a schema-valid runtime evidence bundle for the same
   `run_id` recorded by the execution manifest.
4. The pulled bundle matches the same `run_id`, matching autonomy artifacts,
   and an export timestamp later than the terminal execution event.
5. The bundle is pulled back to a deterministic local staging directory with a
   recorded local digest and pull-time manifest linkage.
6. The bundle is imported through the bounded importer and preserved under
   canonical pack history as supplementary evidence.
7. No local factory registry, deployment pointer, readiness file, work-state
   file, or latest-eval index is mutated directly by the remote roundtrip
   workflow.

## Interpretation Of Success

When the end-to-end roundtrip succeeds, PackFactory has proven:

- it can produce a portable autonomous work packet
- it can let a remote agent execute that packet to its pack-local completion
  boundary
- it can recover that remote runtime evidence without surrendering control of
  local factory truth

That is the practical proof of the source-target separation model.

## Minimal Validation Plan

Verification for this spec must follow the PackFactory testing policy:

- keep verification intentionally small
- prefer contract checks over host, transport, or provider matrices
- protect only the few behaviors that would materially break bounded
  roundtrip proof

V1 verification should stay absolute minimal and focus on:

- one happy-path roundtrip smoke check from wrapper request through pullback
  through bounded import
- one fail-closed linkage or re-entry check, such as mismatched `run_id`,
  mismatched pulled-bundle digest, or an attempted direct canonical-state
  update outside the importer
- one supplementary-evidence assertion that imported runtime evidence is
  preserved as history only and does not become canonical readiness or latest
  eval truth

Do not add:

- broad host or cloud matrices
- transport/provider permutation matrices
- deep pull/import scenario forests
- multi-run comparison suites in v1
