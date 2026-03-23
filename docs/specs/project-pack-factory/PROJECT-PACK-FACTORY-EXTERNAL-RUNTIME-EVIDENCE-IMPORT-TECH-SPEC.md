# Project Pack Factory External Runtime Evidence Import Tech Spec

## Purpose

Define the minimal PackFactory-native import workflow that lets Project Pack
Factory ingest a bounded runtime-evidence bundle produced by an externally run
build-pack and preserve that evidence under the pack's canonical history.

This is meant to improve PackFactory operations directly:

- it gives the factory a reliable way to learn from external autonomous runs
- it keeps external evidence auditable
- it avoids turning raw remote logs into uncontrolled control-plane state

## Spec Link Tags

```json
{
  "spec_id": "external-runtime-evidence-import",
  "depends_on": [
    "external-build-pack-runtime-evidence-export",
    "runtime-agent-memory",
    "autonomous-loop-and-agent-memory-measurement"
  ],
  "integrates_with": [
    "factory-validation",
    "build-pack-control-plane-and-dataplane-integrity"
  ]
}
```

## Problem

Current repo specs and tools already define strong rules for canonical
evidence:

- readiness points at artifacts
- pipeline and promotion runs write immutable reports under `eval/history/`
- runtime memory stays local and advisory

But there is still no bounded import path for runtime evidence produced outside
the factory repo.

Without an explicit import workflow:

- externally completed work stays disconnected from factory history
- operators cannot review external loop evidence beside local factory evidence
- ad hoc copying risks contaminating control-plane state
- future promotion decisions get less context than the build-pack actually
  produced

## Current Repo Evidence

### Evidence A: Current Spec Authority Boundaries Are Already Explicit

Current spec:

- [PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md)

Concrete evidence:

- canonical PackFactory authority remains:
  - `pack.json`
  - `status/*`
  - `benchmarks/active-set.json`
  - `eval/latest/index.json`
  - `eval/history/*`
  - factory registries and deployment pointers
- runtime memory is explicitly advisory only

Interpretation:

- imported external evidence must remain subordinate to canonical PackFactory
  state
- import must preserve the control-plane/data-plane split

### Evidence B: Current Spec Measurement Artifacts Are Already Defined As Supplementary

Current spec:

- [PROJECT-PACK-FACTORY-AUTONOMOUS-LOOP-AND-AGENT-MEMORY-MEASUREMENT-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMOUS-LOOP-AND-AGENT-MEMORY-MEASUREMENT-TECH-SPEC.md)

Concrete evidence:

- optional exported scorecards may be written under `eval/history/<run-id>/`
- the same spec explicitly says those exported scorecards:
  - must not satisfy readiness gates by themselves
  - must not update `eval/latest/index.json`
  - must not become a new control-plane authority

Interpretation:

- import must preserve external runtime evidence as supplementary history, not
  as a new promotion shortcut

### Evidence C: Current Factory Tools Write Canonical Evidence Only Through Bounded Paths

Current code:

- [run_build_pack_readiness_eval.py](/home/orchadmin/project-pack-factory/tools/run_build_pack_readiness_eval.py)
- [run_deployment_pipeline.py](/home/orchadmin/project-pack-factory/tools/run_deployment_pipeline.py)

Concrete evidence:

- these tools write canonical artifacts under `eval/history/<run-id>/`
- they update readiness and eval state only through explicit bounded logic

Interpretation:

- external evidence import should follow the same evidence-first pattern
- it should not bypass readiness, deployment, or promotion workflows

### Evidence D: Current Repo Tooling Does Not Offer A Remote Evidence Ingest Path

Current code:

- [validate_factory.py](/home/orchadmin/project-pack-factory/tools/validate_factory.py)

Concrete evidence:

- the validator checks canonical files and cross-file invariants
- it does not define a schema or workflow for importing external runtime
  bundles
- there is currently no `tools/import_external_runtime_evidence.py`
- `docs/specs/project-pack-factory/schemas/` currently contains no external
  runtime evidence import request or report schema files

Interpretation:

- v1 import needs a dedicated tool and bundle schema
- it should avoid widening whole-factory validation requirements

### Evidence E: A Real Build-Pack Already Has Both Canonical History And Local Runtime Evidence

Concrete current example:

- canonical history:
  [eval/history](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/eval/history)
- local runtime evidence:
  [run-summary.json](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/.pack-state/autonomy-runs/release-evidence-summarizer-loop-002/run-summary.json)

Interpretation:

- PackFactory already has a useful place to preserve imported evidence
- what is missing is the import contract, not a storage location

## Design Goals

- ingest external runtime evidence deterministically
- verify bundle identity and hashes before writing history
- preserve imported evidence under the target build-pack's `eval/history/`
- avoid mutating readiness, deployment, registry, or latest-eval state in v1
- keep the implementation and tests small

## Non-Goals

This spec does not:

- define remote agent control
- auto-promote a build-pack based on imported evidence
- treat imported logs as readiness gates
- rewrite `status/readiness.json`
- rewrite `status/work-state.json`
- rewrite `eval/latest/index.json`
- mirror an external build-pack's whole `.pack-state/` tree into the factory

## Proposed V1 Import Tool

The v1 implementation should add:

- `tools/import_external_runtime_evidence.py`

Proposed invocation:

```bash
python3 tools/import_external_runtime_evidence.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /abs/path/import-request.json \
  --output json
```

The request-file contract is the source of truth for deterministic imports.

This spec also lands:

- `docs/specs/project-pack-factory/schemas/external-runtime-evidence-import-request.schema.json`
- `docs/specs/project-pack-factory/schemas/external-runtime-evidence-import-report.schema.json`

The importer must validate `--request-file` against the request schema before
reading bundle contents, and must validate `import-report.json` against the
report schema before returning success.

## Request Contract

The proposed v1 import request must include at least:

- `schema_version = external-runtime-evidence-import-request/v1`
- `build_pack_id`
- `bundle_manifest_path`
- `import_reason`
- `imported_by`

The request file is the source of truth only for operator intent:

- `build_pack_id`
- `bundle_manifest_path`
- `import_reason`
- `imported_by`

Canonical pack identity, bundle authority class, and allowed mutation scope
are validated from `pack.json`, `bundle.json`, and this spec.

Request-file values must not override those surfaces.

## Import Preconditions

The tool must fail closed unless:

- the target build-pack exists under `build-packs/<build_pack_id>/`
- the target pack's `pack.json.pack_kind = build_pack`
- the bundle manifest validates against `external-runtime-evidence-bundle.schema.json`
  once that schema lands
- `bundle.json.schema_version = external-runtime-evidence-bundle/v1`
- `bundle.json.pack_id` matches the target build-pack id
- `bundle.json.pack_kind = build_pack`
- `bundle.json.authority_class = supplementary_runtime_evidence`
- every `bundle.json.control_plane_mutations.* = false`
- every artifact declared in the bundle exists within the bundle root
- each `artifact_manifest[].bundle_path` resolves within `bundle_root`
- each `artifact_manifest[].sha256` matches the file copied from
  `bundle_root / bundle_path`
- `external-runtime-evidence/artifacts/run-summary.json` validates and reports:
  - `pack_id == bundle.json.pack_id`
  - `run_id == bundle.json.run_id`

The importer must reject:

- bundle paths that escape the provided bundle root
- a bundle that targets a different pack id
- missing required artifacts
- hash mismatches
- any bundled artifact outside the v1 allowlist of:
  - `run-summary.json`
  - optional `loop-events.jsonl`
  - explicit `logs/*`
- any bundle containing `external-runtime-evidence/artifacts/memory/`

## Canonical Imported Evidence Layout

On success, the importer writes a new immutable import run under:

- `build-packs/<pack-id>/eval/history/import-external-runtime-evidence-<timestamp>/`

Required files:

- `build-packs/<pack-id>/eval/history/import-external-runtime-evidence-<timestamp>/import-report.json`
- `build-packs/<pack-id>/eval/history/import-external-runtime-evidence-<timestamp>/external-runtime-evidence/bundle.json`

Required copied artifacts:

- `external-runtime-evidence/artifacts/run-summary.json`

Conditionally copied artifacts:

- `external-runtime-evidence/artifacts/loop-events.jsonl`
- `external-runtime-evidence/artifacts/logs/*`

The importer may preserve artifact filenames, but it must preserve the bundle's
relative structure under `external-runtime-evidence/`.

In v1, the importer copies exactly the files declared in
`bundle.json.artifact_manifest`, preserving each
`artifact_manifest[].bundle_path` under `external-runtime-evidence/`.

Imported runs under `eval/history/import-external-runtime-evidence-<timestamp>/`
are audit-only preservation records.

They are not:

- readiness-eval runs
- deployment-pipeline runs
- promotion reports
- canonical benchmark runs

## Import Report Contract

The proposed v1 `import-report.json` must include at least:

- `schema_version = external-runtime-evidence-import-report/v1`
- `import_id`
- `generated_at`
- `status`
- `build_pack_id`
- `build_pack_root`
- `bundle_manifest_path`
- `import_reason`
- `imported_by`
- `hash_verification_status`
- `copied_artifact_paths`
- `warnings`
- `control_plane_mutations`

For v1, `control_plane_mutations` must explicitly report:

- `eval_history_written = true`
- `readiness_updated = false`
- `work_state_updated = false`
- `eval_latest_updated = false`
- `deployment_updated = false`
- `registry_updated = false`
- `release_artifacts_updated = false`

## Authority Rules

Imported external runtime evidence is supplementary evidence only.

V1 import is allowed to write only:

- the import run directory under `eval/history/`

In v1:

- `status/readiness.json.required_gates[].evidence_paths` must never point at
  imported runtime-evidence files
- `eval/latest/index.json` must never be updated to reference an imported run
- readiness, promotion, deployment, and registry workflows must ignore
  imported run directories unless a separate canonicalization workflow
  explicitly says otherwise

If imported bundle claims disagree with current:

- `pack.json`
- `status/*`
- `eval/latest/index.json`
- `registry/*.json`
- `deployments/*`

canonical PackFactory state wins.

The importer must record the disagreement as a warning and must not reconcile,
rewrite, or refresh control-plane state.

`tools/import_external_runtime_evidence.py` must never edit:

- `status/readiness.json`
- `status/work-state.json`
- `eval/latest/index.json`
- `status/deployment.json`
- `registry/*.json`
- `deployments/*`
- `dist/candidates/*`
- `dist/releases/*`

This keeps imported external evidence available for operators and later
workflows without silently changing the current factory decision state.

V1 does not extend `tools/validate_factory.py` to scan imported `eval/history`
runs.

Validator impact is limited to linting any newly added schema files.

## Optional Follow-On Work

If PackFactory later wants imported external runtime evidence to affect
readiness or promotion, that must be specified separately through a bounded
canonicalization workflow.

That is not part of this spec.

## Minimal Validation Plan

This spec should stay within an extremely small test budget.

Preferred implementation validation:

- extend the existing export-side materialization assertions once
- add at most one dedicated export/import smoke test that covers:
  - exporting a small bounded bundle
  - importing it into a target build-pack
  - confirming the bundle lands under `eval/history/.../external-runtime-evidence/`
  - confirming `status/readiness.json`, `status/work-state.json`,
    `eval/latest/index.json`, `registry/*.json`, and `deployments/*` are not
    mutated
  - confirming one fail-closed rejection before any `eval/history/` write for:
    - `authority_class` drift
    - or an `artifacts/memory/...` bundle

Do not add:

- dedicated export-only tests
- importer failure-matrix tests
- validate_factory-specific tests

in v1.
