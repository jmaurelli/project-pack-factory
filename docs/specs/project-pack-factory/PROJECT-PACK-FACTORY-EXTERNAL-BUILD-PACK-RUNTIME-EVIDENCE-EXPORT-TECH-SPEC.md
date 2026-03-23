# Project Pack Factory External Build-Pack Runtime Evidence Export Tech Spec

## Purpose

Define the minimal PackFactory-native build-pack capability that lets a
build-pack running outside the factory collect its own runtime evidence and
export a bounded bundle for later review or import back into Project Pack
Factory.

This is meant to improve Project Pack Factory itself, not add arbitrary new
surface area.

The practical factory problem is simple:

- autonomous or externally run build-packs can generate useful loop data,
  memory data, and selected logs
- today that data stays local to the external run
- the factory therefore cannot learn from or audit that external execution in
  a bounded, repeatable way

This spec makes the build-pack portable without making PackFactory depend on a
remote runtime service.

## Spec Link Tags

```json
{
  "spec_id": "external-build-pack-runtime-evidence-export",
  "amends": [
    "build-pack-materialization",
    "runtime-agent-memory",
    "directory-hierarchy"
  ],
  "depends_on": [
    "runtime-agent-memory",
    "autonomous-build-pack-handoff-and-work-state",
    "autonomous-loop-and-agent-memory-measurement"
  ],
  "integrates_with": [
    "factory-validation"
  ],
  "followed_by": [
    "external-runtime-evidence-import"
  ]
}
```

## Problem

Project Pack Factory now has concrete materialization support for:

- canonical objective and backlog state
- local autonomy-run measurement under `.pack-state/autonomy-runs/`
- local runtime memory under `.pack-state/agent-memory/`

What it still cannot do is ensure that a build-pack exported from the factory
can package that local evidence for later return.

Without an explicit export contract:

- externally completed work becomes hard to audit
- PackFactory cannot compare local in-factory runs to external runs cleanly
- useful logs remain ad hoc and tool-specific
- future import behavior has no stable bundle shape to validate against

## Current Factory Evidence

### Evidence A: Current Repo Specs Define Runtime Memory As Local And Non-Remote

Current spec:

- [PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md)

Concrete evidence:

- the spec explicitly says it does not define `a remote memory service`
- the same spec says runtime memory is `runtime-local advisory state`
- the preferred PackFactory-native storage root is `.pack-state/agent-memory/`

Interpretation:

- an externally running build-pack cannot rely on a factory-hosted memory
  service
- PackFactory cannot rely on reaching back into a remote runtime

### Evidence B: Current Repo Specs Already Define Useful Local Loop Artifacts

Current spec:

- [PROJECT-PACK-FACTORY-AUTONOMOUS-LOOP-AND-AGENT-MEMORY-MEASUREMENT-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMOUS-LOOP-AND-AGENT-MEMORY-MEASUREMENT-TECH-SPEC.md)

Concrete evidence:

- the spec already defines local run artifacts under `.pack-state/autonomy-runs/`
- it already recommends:
  - `loop-events.jsonl`
  - `run-summary.json`
- it explicitly says optional exported scorecards are supplementary only

Interpretation:

- the local evidence shape is already defined at the spec level
- what is missing is a portable export bundle created by the build-pack itself

### Evidence C: A Real Build-Pack Already Produces Useful Local Loop Evidence, But It Is Not Portable As-Is

Concrete current example:

- [run-summary.json](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/.pack-state/autonomy-runs/release-evidence-summarizer-loop-002/run-summary.json)
- [loop-events.jsonl](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/.pack-state/autonomy-runs/release-evidence-summarizer-loop-002/loop-events.jsonl)

Concrete evidence:

- `run-summary.json` already records:
  - `pack_id`
  - `run_id`
  - `started_at`
  - `ended_at`
  - `stop_reason`
  - `resume_count`
  - computed metrics
- `loop-events.jsonl` already records:
  - command attempts
  - readiness transitions
  - decision source
  - memory state
- the same local run also hard-codes factory-local absolute paths and commands,
  for example:
  - `artifacts.factory_validation_command`
  - `artifacts.loop_events_path`
  - `artifacts.run_summary_path`

Interpretation:

- the build-pack already has useful local evidence
- the remaining gap is normalization plus packaging, not raw evidence creation

### Evidence D: Current Build-Pack Manifests Do Not Advertise An Export Function

Concrete current examples:

- [pack.json](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/pack.json)
- [materialize_build_pack.py](/home/orchadmin/project-pack-factory/tools/materialize_build_pack.py)

Concrete evidence:

- `entrypoints` currently contains only:
  - `cli_command`
  - `validation_command`
  - `benchmark_command`
- the current materializer copies template entrypoints directly into the new
  build-pack manifest
- no current checked-in build-pack manifest or materializer path defines
  `export_runtime_evidence_command`

Interpretation:

- even when a build-pack has useful local evidence, there is no standard
  machine-readable way to invoke export

### Evidence E: Current Build-Packs Already Have A Generic Export Area, But Not A Runtime-Evidence Contract

Concrete current example:

- [dist](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/dist)

Concrete evidence:

- the current dist tree for this example contains only release artifacts:
  - `dist/candidates/release-evidence-summarizer-v3-r1/release.json`
  - `dist/releases/release-evidence-summarizer-v3-r1/release.json`
- current materialization already creates a generic `dist/exports/` directory
- the current pack manifest schema already models generic export space through
  `template_export_dir`
- there is still no runtime-evidence-specific subdirectory, manifest field, or
  bundle schema

Interpretation:

- PackFactory already has a generic export area
- it does not yet reserve a runtime-evidence export contract for build-packs

## Design Goals

- let a build-pack export its own runtime evidence without PackFactory being
  present
- keep the export bounded and schema-valid
- make the export easy for PackFactory to import later
- keep canonical factory state unchanged during export
- avoid copying the entire `.pack-state/` tree
- keep the v1 implementation small and self-contained

## Non-Goals

This spec does not:

- define a remote telemetry service
- make external logs canonical by themselves
- allow export to update readiness, deployment, or registry state
- require every build-pack to export every possible local artifact
- require a new mandatory runtime log subsystem under `.pack-state/`
- require non-Python runtime support in v1

## V1 Scope

V1 applies to newly materialized PackFactory-native Python build-packs.

Existing build-packs may adopt the exporter manually later, but the required
factory behavior in v1 is:

- seed the export capability into newly materialized Python build-packs
- give those build-packs a stable output location and bundle schema

## Canonical Build-Pack Export Surface

### Manifest Contract

`pack.json.entrypoints` gains a new optional field for build-packs:

- `export_runtime_evidence_command`

This spec also amends:

- `docs/specs/project-pack-factory/schemas/pack.schema.json`
- the build-pack branch of the directory contract
- the build-pack dist layout in the directory hierarchy spec

For `pack_kind = build_pack` and `runtime = python`, the field must be present
after materialization.

For all other packs in v1, it may be omitted.

`pack.json.directory_contract` gains a new optional field:

- `runtime_evidence_export_dir`

For newly materialized Python build-packs, it must be:

- `dist/exports/runtime-evidence`

For build-packs, `template_export_dir` remains `null`.

`runtime_evidence_export_dir` declares only the reserved export root.

The existence or contents of any `<export_id>/` bundle under that root:

- are not canonical pack state
- must not affect validation, readiness, promotion, or deployment decisions
- must be ignored by release packaging workflows in v1

### Pack-Local Helper

The materializer must seed a pack-local helper script at:

- `src/pack_export_runtime_evidence.py`

This helper is part of the build-pack artifact itself so it still works when
the build-pack is copied or run outside the factory repo.

The helper must not depend on:

- `../../tools/...`
- factory registries
- deployment pointers
- the pack still living inside the original factory checkout

### Canonical Invocation

The seeded entrypoint should invoke the helper in this shape:

```bash
python3 src/pack_export_runtime_evidence.py \
  --pack-root . \
  --run-id <run-id> \
  --exported-by <actor> \
  --output-dir dist/exports/runtime-evidence \
  --output json
```

The helper may accept additional `--include-log` flags, but the core invocation
above is the required v1 path.

## Export Preconditions

The exporter must fail closed unless:

- `pack.json.pack_kind = build_pack`
- `pack.json` is present and readable
- `--pack-root` resolves to the build-pack root
- the requested `run_id` exists under `.pack-state/autonomy-runs/<run_id>/`
- `.pack-state/autonomy-runs/<run_id>/run-summary.json` validates and reports:
  - `pack_id == pack.json.pack_id`
  - `run_id == <requested run_id>`
- every explicitly included file exists under the allowed local runtime roots
- if `loop-events.jsonl` is included, every included event reports the same
  `run_id`

The exporter must reject:

- paths that escape the pack root
- directory copies
- any include outside `.pack-state/autonomy-runs/<run_id>/`
- whole-tree `.pack-state/` export requests
- includes under:
  - `status/`
  - `eval/`
  - `registry/`
  - `deployments/`
  - `dist/candidates/`
  - `dist/releases/`
  - `lineage/`
  - `tasks/`
  - `contracts/`
  - pack-root files such as `pack.json`, `AGENTS.md`, and `project-context.md`
- any attempt to include runtime-memory files under `.pack-state/agent-memory/`
  in v1
- run-id mismatches between the selected run root and its included artifacts

## Required V1 Bundle Shape

The exporter writes a self-contained bundle under:

- `dist/exports/runtime-evidence/<export_id>/`

Required files:

- `dist/exports/runtime-evidence/<export_id>/bundle.json`
- `dist/exports/runtime-evidence/<export_id>/artifacts/run-summary.json`

Conditionally required files:

- `dist/exports/runtime-evidence/<export_id>/artifacts/loop-events.jsonl`
  when present for the selected `run_id`
- `dist/exports/runtime-evidence/<export_id>/artifacts/logs/<name>`
  for each explicit `--include-log`

This spec must also land:

- `docs/specs/project-pack-factory/schemas/external-runtime-evidence-bundle.schema.json`

The exporter may validate against a pack-local copy or generate to that schema
contract without depending on `../../tools`.

### `bundle.json` Required Fields

The canonical bundle manifest must include at least:

- `schema_version = external-runtime-evidence-bundle/v1`
- `export_id`
- `generated_at`
- `pack_id`
- `pack_kind`
- `run_id`
- `exported_by`
- `bundle_root`
- `source_runtime_roots`
- `authority_class = supplementary_runtime_evidence`
- `control_plane_mutations`
- `artifact_manifest`
- `summary`

`control_plane_mutations` must report all v1 flags as false:

- `readiness_updated`
- `work_state_updated`
- `eval_latest_updated`
- `deployment_updated`
- `registry_updated`
- `release_artifacts_updated`

### `summary` Required Fields

The bundle summary must include at least:

- `stop_reason`
- `started_at`
- `ended_at`
- `resume_count`
- `escalation_count`
- `task_completion_rate`
- `readiness_state_in_selected_run`
- `ready_for_deployment_in_selected_run`

When a field is not available from the selected local evidence, the exporter
must set it to `null` rather than inventing a value.

These summary fields must be derived only from the selected run's local
evidence, such as `run-summary.json` or included loop-event snapshots.

The exporter must not read current:

- `status/readiness.json`
- `status/work-state.json`
- `eval/latest/index.json`

to populate `summary` in v1.

### `artifact_manifest` Required Fields

Each bundled artifact record must include at least:

- `bundle_path`
- `source_pack_path`
- `sha256`
- `media_type`
- `required`

## Export Selection Rules

The exporter must always attempt to include:

- the selected run's `run-summary.json`

The exporter should include when present:

- the selected run's `loop-events.jsonl`

The exporter may include only by explicit operator request:

- extra log files

Explicit includes may resolve only under:

- `.pack-state/autonomy-runs/<run_id>/`

The exporter must never include automatically:

- `registry/*.json`
- `deployments/*`
- `status/deployment.json`
- `status/readiness.json`
- the entire `.pack-state/` tree

The exporter must never include in v1:

- files under `.pack-state/agent-memory/`
- canonical control-plane files from `status/`, `eval/`, `registry/`,
  `deployments/`, `tasks/`, `contracts/`, or `lineage/`
- pack-root files such as `pack.json`, `AGENTS.md`, `project-context.md`,
  `README.md`, or `pyproject.toml`

Those files may still be inspected locally by an operator, but they are not
part of the default v1 external runtime-evidence export.

## Materialization Changes

To improve PackFactory itself, newly materialized Python build-packs must gain
this capability automatically.

That means `tools/materialize_build_pack.py` must:

- preserve inherited template entrypoints and append
  `pack.json.entrypoints.export_runtime_evidence_command` for newly
  materialized Python build-packs
- set `pack.json.directory_contract.runtime_evidence_export_dir` to
  `dist/exports/runtime-evidence` for newly materialized Python build-packs
- create `dist/exports/runtime-evidence/` in addition to `dist/candidates/`
  and `dist/releases/`
- synthesize `src/pack_export_runtime_evidence.py` as a standalone helper;
  this does not change package module layout or pyproject entry points
- keep `template_export_dir = null` for build-packs
- not add `export_runtime_evidence_command` to
  `lineage/source-template.json.inherited_entrypoints`, because it is
  materializer-generated rather than source-template-inherited

This keeps the export function with the build-pack rather than leaving it as a
factory-only tool.

## Authority And Integrity Rules

The exporter is a data-plane packaging tool.

It must not:

- edit `status/readiness.json`
- edit `status/work-state.json`
- edit `eval/latest/index.json`
- edit `registry/*.json`
- edit `deployments/*`
- create release artifacts under `dist/releases/`

Its job is only to package bounded runtime evidence for later transport.

Consumers must not treat:

- `bundle.json`
- `summary`
- bundled artifacts

as current PackFactory control-plane state.

## Minimal Validation Plan

This spec should keep tests extremely small.

Preferred implementation validation:

- extend only
  [test_materialize_build_pack_happy_path_creates_pack_and_registry](/home/orchadmin/project-pack-factory/tests/test_materialize_build_pack.py)
- add assertions for:
  - `entrypoints.export_runtime_evidence_command`
  - `directory_contract.runtime_evidence_export_dir`
  - existence of `dist/exports/runtime-evidence/`
  - existence of `src/pack_export_runtime_evidence.py`
- do not add a dedicated export-only test case or test file in v1

End-to-end exporter behavior, if exercised in v1, is covered only by the
single paired export/import smoke test.
