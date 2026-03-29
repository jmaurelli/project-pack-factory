# Project Pack Factory Build-Pack Materialization Tech Spec

## Purpose

Define a deterministic, agent-optimized workflow for materializing a new
`build_pack` from an active `template_pack` inside Project Pack Factory.

This closes the current gap between:

- template-pack authoring and validation
- manual seeded build-pack creation
- deployable build-pack lineage and registry state

## Spec Link Tags

```json
{
  "spec_id": "build-pack-materialization",
  "depends_on": [
    "directory-hierarchy"
  ],
  "integrates_with": [
    "runtime-agent-memory"
  ],
  "followed_by": [
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration"
  ]
}
```

## Problem

The factory already knows how to describe templates, track build-pack state,
validate contracts, and retire historical fixtures. It does not yet provide a
single operator workflow that creates a new build pack from a template in a
repeatable, machine-readable, evidence-preserving way.

Today the existing build packs were seeded manually. That creates three risks:

- build-pack creation is not deterministic
- lineage and copy behavior are not contract-bound
- agents cannot distinguish a canonical materialization from a hand-built
  directory copy

## Design Goals

- materialization must be deterministic and fail closed
- the new build pack must be traversable immediately after creation
- lineage must be explicit and machine-readable
- copy rules must be bounded, not ad hoc
- the operation must write evidence that later agents can inspect
- factory mutations must be sequential, per-file atomic, and reconcilable

## Scope

This spec defines:

- the operator workflow for materializing a build pack
- the copy contract from template pack to build pack
- the evidence artifact for a materialization operation
- the registry and lifecycle effects of materialization
- the JSON Schemas for the materialization request and report

This spec does not define:

- template authoring workflows
- semantic package refactors during materialization
- cloud deployment behavior
- environment promotion after materialization

## Immediate Post-Materialization Process Rule

Materialization creates a build-pack that is ready for bounded evaluation, not
yet an officially certified remote-ready working pack.

When the newly materialized build-pack is expected to become the operator's
long-lived working or daily-driver instance and may later need
promotion-compatible remote evidence, the next workflow step must be chosen
deliberately:

- either run the official fresh-pack autonomy workflow before the pack
  diverges into long-lived day-to-day use
- or accept that PackFactory's current official remote-proof workflow will
  later need a separate fresh proving-ground build-pack because it does not
  retroactively certify an already-evolving pack in place

This rule exists because the current `run_multi_hop_autonomy_rehearsal.py` and
`run_autonomy_to_promotion_workflow.py` flows begin from fresh-pack
materialization.

## Operator Interface

The canonical tool is:

- `tools/materialize_build_pack.py`

Canonical invocation:

```bash
python3 tools/materialize_build_pack.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /abs/path/materialization-request.json \
  --output json
```

The tool may also accept direct CLI flags, but the request-file contract is the
source of truth for deterministic runs.

## Preconditions

Before materialization starts:

- the source template pack must exist in `registry/templates.json`
- the source template pack must have:
  - `retirement_state = active`
  - `lifecycle_stage != retired`
- the target build-pack id must not already exist in:
  - `build-packs/<target-build-pack-id>/`
  - `registry/build-packs.json`
- the source template pack must pass `tools/validate_factory.py`
- the source template pack must expose all stable pack-local files required by
  the base PackFactory directory spec

If any precondition fails, the tool must stop before writing any build-pack
directory.

## Copy Contract

Materialization is a bounded pack-root copy plus build-pack state synthesis.

### Files And Directories Copied From The Template

The materializer must copy:

- `AGENTS.md`
- `project-context.md`
- `docs/`
- `prompts/`
- `contracts/`
- `src/`
- `tests/`
- `benchmarks/`
- `pyproject.toml`
- `uv.lock`
- `README.md`
- `Makefile` when present
- `.gitignore` when present

### Paths Never Copied From The Template

The materializer must not copy:

- `.pack-state/`
- `eval/history/`
- `eval/latest/index.json`
- `dist/exports/`
- `status/`
- any `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`,
  `*.egg-info`, `.venv/`

### Paths Synthesized For The Build Pack

The materializer must create or write:

- `pack.json`
- `lineage/source-template.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/retirement.json`
- `status/deployment.json`
- `eval/latest/index.json`
- `eval/history/<materialization_id>/materialization-report.json`
- `dist/candidates/`
- `dist/releases/`
- `.pack-state/`

The build pack must never inherit template-pack deployment state directly.

### Runtime Agent Memory Extension

When the source template enables runtime agent memory, the materializer must
preserve the subsystem through the existing bounded copy and synthesis rules.

For the current v1 runtime-memory integration, that means:

- copy runtime-memory code and CLI entrypoints through the normal `src/` and
  pack-manifest copy rules
- copy `contracts/agent-memory.schema.json` and
  `contracts/agent-memory-reader.schema.json`
- copy the runtime-memory benchmark declaration
  `agent-memory-restart-small-001`
- never copy live `.pack-state/agent-memory/` contents from the source
  template
- synthesize the inherited readiness gate
  `agent_memory_restart_small_001` in `not_run` through the existing inherited
  benchmark-gate rule

The build pack starts with runtime-memory capability but no inherited live
restart-state artifacts.

## Materialized Build-Pack State

After a successful materialization:

- `pack.json.pack_kind = build_pack`
- `status/lifecycle.json.lifecycle_stage = testing`
- `status/lifecycle.json.promotion_target = testing`
- `status/readiness.json.readiness_state = in_progress`
- `status/readiness.json.ready_for_deployment = false`
- `status/retirement.json.retirement_state = active`
- `status/deployment.json.deployment_state = not_deployed`
- `status/deployment.json.active_environment = none`
- `status/deployment.json.deployment_pointer_path = null`

The build pack starts as an active but non-deployed derivative that still
requires evaluation before promotion.

When remote-proof or promotion-proof continuity matters, operators should treat
this state as the point to schedule the fresh-pack rehearsal rather than
waiting until the pack has already become the long-lived working instance.

### Full State Synthesis Contract

The materializer must synthesize complete schema-valid documents rather than
only the highlighted fields above.

Required synthesis rules:

- `pack.json`
  - inherit from the source template:
    - `owning_team`
    - `runtime`
    - `bootstrap_read_order`
    - `entrypoints`
  - set explicitly:
    - `schema_version = pack-manifest/v2`
    - `pack_id = <target_build_pack_id>`
    - `pack_kind = build_pack`
    - `display_name = <target_display_name>`
    - `post_bootstrap_read_order` to the allowed build-pack order from the base
      PackFactory spec
    - `directory_contract` to the build-pack contract
    - `identity_source = pack.json`
    - `notes` to include the source template id and materialization id
- `status/lifecycle.json`
  - set:
    - `lifecycle_stage = testing`
    - `state_reason = <materialization_reason>`
    - `current_version = <target_version>`
    - `current_revision = <target_revision>`
    - `promotion_target = testing`
    - `updated_at = <generated_at>`
    - `updated_by = <materialized_by>`
- `status/readiness.json`
  - set:
    - `readiness_state = in_progress`
    - `ready_for_deployment = false`
    - `last_evaluated_at = <generated_at>`
    - `blocking_issues` with at least one explicit “not yet evaluated” message
    - `recommended_next_actions` with at least one evaluation action
    - `required_gates` with at least:
      - one mandatory `validate_build_pack_contract` gate in `not_run`
      - one inherited mandatory `not_run` gate per source template benchmark id
- `status/retirement.json`
  - set the full active retirement contract with `retirement_state = active`
    and all retirement-only fields null or empty
- `status/deployment.json`
  - set the full non-deployed build-pack contract with `deployment_state =
    not_deployed` and all active deployment fields null
- `eval/latest/index.json`
  - must be schema-valid immediately after creation
  - for each inherited benchmark id:
    - `status = not_run`
    - `latest_run_id = <materialization_id>`
    - `run_artifact_path = eval/history/<materialization_id>/materialization-report.json`
    - `summary_artifact_path = eval/history/<materialization_id>/materialization-report.json`

## Lineage Contract

The build pack must record lineage at:

- `lineage/source-template.json`

The lineage document must remain valid against the current
`source-template.schema.json` contract.

Required lineage fields are therefore:

- `build_pack_id`
- `source_template_id`
- `source_template_version`
- `source_template_revision`
- `derivation_mode = copied`
- `sync_state = current`
- `last_sync_at = <generated_at>`
- `last_sync_summary` including the canonical token
  `materialization_id=<materialization_id>`
- `inherited_entrypoints`
- `inherited_contracts`

Materialization-specific provenance remains authoritative in the
materialization report and the matching operation-log event.

## Registry And Operation Log Effects

On success, the materializer must:

- append a new entry to `registry/build-packs.json`
- leave `registry/templates.json` unchanged
- append `event_type = materialized` to `registry/promotion-log.json`

The build-pack registry entry must include:

- `active = true`
- `retirement_state = active`
- `retirement_file = status/retirement.json`
- `retired_at = null`
- `lifecycle_stage = testing`
- `ready_for_deployment = false`
- `deployment_state = not_deployed`
- `deployment_pointer = null`
- `latest_eval_index = build-packs/<id>/eval/latest/index.json`

The factory continues to use `registry/promotion-log.json` as the canonical
operation log for materialization even though the filename is historical.

Every `materialized` event must include:

- `materialization_id`
- `target_build_pack_id`
- `materialization_report_path`

## Evidence Contract

Every successful materialization must write:

- `build-packs/<target-build-pack-id>/eval/history/<materialization_id>/materialization-report.json`

This report is the canonical evidence artifact for the operation.

The report must be written last, after:

- the build-pack directory exists
- lineage exists
- pack-local status files exist
- the build-pack registry entry exists
- the materialized event exists in `registry/promotion-log.json`

The validator must discover materialization reports through
`registry/promotion-log.json`, not by scanning `eval/history/`.

## Required Schema Additions

This workflow adds:

- `schemas/materialization-request.schema.json`
- `schemas/materialization-report.schema.json`

This workflow extends the operation-log contract conceptually:

- `registry/promotion-log.json`
  - must accept `event_type = materialized`

## Cross-File Invariants

The factory validator must enforce:

- `lineage/source-template.json.source_template_id` equals
  `materialization-report.source_template_id`
- `lineage/source-template.json.build_pack_id` equals
  `materialization-report.target_build_pack_id`
- `materialization-report.target_build_pack_id` equals `pack.json.pack_id`
- `materialization-report.target_build_pack_root` equals the actual build-pack
  root
- `materialization-report.generated_at` equals
  `lineage/source-template.json.last_sync_at`
- `status/retirement.json.retirement_state = active`
- `status/deployment.json.deployment_state = not_deployed`
- the registry entry for the new build pack reflects the same lifecycle,
  retirement, and deployment state as the pack-local status files
- the operation log contains a matching `materialized` event whose
  `materialization_id` and `materialization_report_path` match the report
- invariants must be enforced from persisted factory state only, not from
  external request files

## Failure Model

The tool must fail before mutation when:

- the source template is retired
- the source template is missing required pack-local files
- the target build-pack id already exists
- the request references non-existent pack ids or roots

The tool writes files sequentially with per-file atomic replacement. It does
not claim cross-file transactional rollback in v1.

The materialization request may also include an optional
`personality_template_selection` object. That gives the operator three bounded
choices:

- inherit the source template default overlay when one exists
- select a different catalog personality template for this build-pack
- clear personality overlay inheritance for this one build-pack

The canonical personality template catalog lives at:

- `docs/specs/project-pack-factory/agent-personality-template-catalog.json`

If a write fails after the build-pack root has been created, the tool must:

- exit non-zero
- write a failure summary under:
  - `.pack-state/failed-operations/<materialization_id>.json`
- leave already-written files intact for later reconciliation or manual review

## Example Request

```json
{
  "schema_version": "build-pack-materialization-request/v1",
  "source_template_id": "ai-native-codex-package-template",
  "target_build_pack_id": "ai-native-codex-build-pack-v2",
  "target_display_name": "AI Native Codex Build Pack v2",
  "target_version": "0.2.0",
  "target_revision": "materialize-20260320t120000z",
  "materialized_by": "orchadmin",
  "materialization_reason": "Create a fresh active build-pack derivative from the canonical template.",
  "personality_template_selection": {
    "selection_mode": "catalog_template",
    "personality_template_id": "business-partner-concierge",
    "selection_reason": "Use the warmer operator-facing overlay for this proving-ground derivative."
  },
  "copy_mode": "copy_pack_root",
  "include_benchmark_declarations": true
}
```

## Example Report

```json
{
  "schema_version": "build-pack-materialization-report/v1",
  "materialization_id": "materialize-ai-native-codex-build-pack-v2-20260320t120000z",
  "generated_at": "2026-03-20T12:00:00Z",
  "source_template_id": "ai-native-codex-package-template",
  "target_build_pack_id": "ai-native-codex-build-pack-v2",
  "source_template_root": "templates/ai-native-codex-package-template",
  "target_build_pack_root": "build-packs/ai-native-codex-build-pack-v2",
  "materialized_by": "orchadmin",
  "target_version": "0.2.0",
  "target_revision": "materialize-20260320t120000z",
  "resolved_personality_template": {
    "template_id": "business-partner-concierge",
    "display_name": "Business Partner Concierge",
    "summary": "Warm, collaborative, outcome-aware operator posture that explains why the work matters while staying fail-closed on evidence.",
    "selection_origin": "materialization_selected",
    "selection_reason": "Use the warmer operator-facing overlay for this proving-ground derivative.",
    "catalog_path": "docs/specs/project-pack-factory/agent-personality-template-catalog.json",
    "apply_to_derived_build_packs_by_default": false
  },
  "copy_summary": {
    "copied_paths": [
      "AGENTS.md",
      "project-context.md",
      "docs/",
      "prompts/",
      "contracts/",
      "src/",
      "tests/",
      "benchmarks/"
    ],
    "skipped_paths": [
      "status/",
      "eval/history/",
      "dist/exports/",
      ".pack-state/"
    ]
  },
  "lineage_path": "build-packs/ai-native-codex-build-pack-v2/lineage/source-template.json",
  "registry_update": {
    "registry_path": "registry/build-packs.json",
    "pack_id": "ai-native-codex-build-pack-v2",
    "lifecycle_stage": "testing",
    "retirement_state": "active",
    "deployment_state": "not_deployed"
  },
  "operation_log_update": {
    "promotion_log_path": "registry/promotion-log.json",
    "event_type": "materialized",
    "materialization_id": "materialize-ai-native-codex-build-pack-v2-20260320t120000z",
    "target_build_pack_id": "ai-native-codex-build-pack-v2",
    "materialization_report_path": "eval/history/materialize-ai-native-codex-build-pack-v2-20260320t120000z/materialization-report.json"
  },
  "actions": [
    {
      "action_id": "copy_template_content",
      "status": "completed",
      "target_path": "build-packs/ai-native-codex-build-pack-v2",
      "summary": "Copied bounded template-pack content into a new build-pack root."
    },
    {
      "action_id": "write_lineage",
      "status": "completed",
      "target_path": "build-packs/ai-native-codex-build-pack-v2/lineage/source-template.json",
      "summary": "Recorded source-template provenance."
    },
    {
      "action_id": "write_materialization_report",
      "status": "completed",
      "target_path": "build-packs/ai-native-codex-build-pack-v2/eval/history/materialize-ai-native-codex-build-pack-v2-20260320t120000z/materialization-report.json",
      "summary": "Recorded terminal materialization evidence."
    }
  ],
  "evidence_paths": [
    "build-packs/ai-native-codex-build-pack-v2/pack.json",
    "build-packs/ai-native-codex-build-pack-v2/lineage/source-template.json",
    "build-packs/ai-native-codex-build-pack-v2/status/lifecycle.json",
    "build-packs/ai-native-codex-build-pack-v2/status/readiness.json",
    "build-packs/ai-native-codex-build-pack-v2/status/deployment.json"
  ]
}
```
