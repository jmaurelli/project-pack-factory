# Agent Telemetry Reader Tech Spec

## Purpose

Define one read-only package-local helper that lets an AI agent consume the
most relevant local build evidence without guessing paths or confusing local
pack state with canonical benchmark artifacts.

The reader is agent-first:

- deterministic input
- deterministic read order
- local evidence only by default
- machine-readable output
- fail-closed on malformed local artifacts

## Linked Specs And Code

- [GOAL-DRIVEN-BUILD-LOOP-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/GOAL-DRIVEN-BUILD-LOOP-TECH-SPEC.md)
- [PACK-TELEMETRY-AND-LEARNING-LOOP-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/PACK-TELEMETRY-AND-LEARNING-LOOP-TECH-SPEC.md)
- [PACK-TELEMETRY-SUMMARIZATION-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/PACK-TELEMETRY-SUMMARIZATION-TECH-SPEC.md)
- [task_goal_telemetry.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/task_goal_telemetry.py)
- [task_goal_telemetry_summary.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/task_goal_telemetry_summary.py)
- [run_manifest.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/run_manifest.py)
- [agent_telemetry_reader.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/agent_telemetry_reader.py)
- [agent-telemetry-reader.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/contracts/agent-telemetry-reader.schema.json)

## Why This Exists

The package already writes local evidence:

- task-goal telemetry
- task-goal telemetry summary
- build-run manifests

Without a reader, an agent still has to:

- remember pack-scoped hidden directories
- exclude the summary file from per-attempt telemetry
- choose the latest local telemetry artifact
- decide whether any local build-run manifest exists
- avoid accidentally treating canonical eval artifacts as local state

The reader removes that repeated path-stitching work.

## Scope

This spec defines:

- one package-local reader module
- one stable snapshot payload
- deterministic path resolution for local evidence
- deterministic latest-artifact selection
- one optional CLI command for JSON output

This spec does not define:

- canonical eval ingestion
- compare report behavior
- cross-project search
- remote host scanning
- artifact writes

## Authority Split

Authority must remain explicit.

`task record`

- authoritative for the task goal and declared validation path

`task-goal telemetry`

- authoritative for one saved loop attempt

`task-goal telemetry summary`

- authoritative only for local aggregates derived from saved telemetry

`build-run manifest`

- authoritative for one broader local benchmark run record

`agent telemetry snapshot`

- authoritative only as a read-only view over existing local artifacts

`template-pack-eval` and `control-plane-data`

- authoritative for canonical benchmark history, normalization, and comparison

The reader must default to local evidence only. It must not read canonical eval
artifacts.

## Default Read Order

When an agent needs project-local evidence, the reader should expose this read
order:

1. task record path from the latest task-goal telemetry, when available
2. latest matching task-goal telemetry
3. task-goal telemetry summary, when available
4. latest local build-run manifest, when available

Why this order matters:

- the task record points at the live goal contract
- the latest telemetry says what just happened
- the summary says whether the latest result is part of a pattern
- the build-run manifest gives broader local benchmark context

## Path Policy

The reader must fail closed on path ambiguity.

Required rules:

- `project_root` must be absolute
- per-attempt telemetry must live only under:
  - `<project_root>/.ai-native-codex-package-template/task-goal-telemetry/`
- the summary path must be only:
  - `<project_root>/.ai-native-codex-package-template/task-goal-telemetry/task-goal-telemetry-summary.json`
- build-run manifests must live only under:
  - `<project_root>/.ai-native-codex-package-template/run-manifests/`
- the summary file must never be counted as a per-attempt telemetry file

Missing local artifacts are allowed. Malformed local artifacts are not.

## Reader Responsibilities

The implementation must provide:

- `discover_task_goal_telemetry_paths(project_root, task_name=None)`
- `load_task_goal_telemetry(path)`
- `load_task_goal_telemetry_summary(project_root)`
- `discover_build_run_manifest_paths(project_root)`
- `load_build_run_manifest(path)`
- `read_agent_telemetry(project_root, task_name=None)`

## Required Snapshot Payload

The reader must return one stable snapshot payload with:

- `schema_version`
- `reader`
- `project_root`
- `task_name_filter`
- `recommended_read_order`
- `task_record`
- `latest_task_goal_telemetry`
- `task_goal_telemetry_summary`
- `latest_build_run_manifest`
- `local_artifact_counts`
- `status_summary`
- `notes`

### Required Field Meaning

`schema_version`

- `agent-telemetry-reader/v1`

`reader`

- `agent-telemetry-reader`

`task_record`

- object with:
  - `path`
  - `present`

`latest_task_goal_telemetry`

- object with:
  - `path`
  - `present`
  - `payload`

`task_goal_telemetry_summary`

- object with:
  - `path`
  - `present`
  - `payload`

`latest_build_run_manifest`

- object with:
  - `path`
  - `present`
  - `payload`

`local_artifact_counts`

- object with:
  - `task_goal_telemetry_count`
  - `build_run_manifest_count`

`status_summary`

- object with:
  - `latest_result`
  - `latest_completed`
  - `latest_continue_working`
  - `latest_primary_goal_passed`

`notes`

- plain-language guidance about what local evidence exists and what is missing

## Validation Rules

The reader must validate:

- task-goal telemetry against
  [task-goal-telemetry.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/contracts/task-goal-telemetry.schema.json)
- task-goal telemetry summary against
  [task-goal-telemetry-summary.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/contracts/task-goal-telemetry-summary.schema.json)
- the combined snapshot against
  [agent-telemetry-reader.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/contracts/agent-telemetry-reader.schema.json)

The build-run manifest may use a bounded local shape check instead of importing
canonical eval schemas into the package. That check must require at least:

- `schema_version = build-run-manifest/v1`
- non-empty `run_id`
- non-empty `generated_at`
- non-empty `task_name`
- object `outcome`

The reader must reject malformed local telemetry, summary, or manifest files
instead of silently returning partial or guessed data.

## Selection Rules

The implementation must use deterministic latest-artifact selection.

Per-attempt telemetry selection:

- use only files under the pack-local telemetry directory
- exclude `task-goal-telemetry-summary.json`
- if `task_name` is provided, only accept telemetry whose payload `task_name`
  matches exactly
- select the latest artifact by:
  1. `generated_at`
  2. resolved path as a tie-breaker

Build-run manifest selection:

- use only files under the pack-local run-manifest directory
- select the latest artifact by:
  1. `generated_at`
  2. resolved path as a tie-breaker

## CLI Surface

The first implementation should add:

`read-agent-telemetry`

Required options:

- `--project-root`
- `--task-name` optional
- `--output text|json`

Behavior:

- JSON output returns the full snapshot payload
- text output returns a short plain-language local summary
- valid missing-artifact states still return exit code `0`
- malformed local artifacts fail closed

## Tests

Tests must stay minimal and focused.

Required coverage:

- one focused API test for latest telemetry selection
- one focused API test for task-name filtering
- one focused API test for summary inclusion
- one focused fail-closed test for malformed summary telemetry
- one focused fail-closed test for malformed per-attempt telemetry
- one focused CLI smoke test for JSON output

The tests must use local temporary directories only and must not touch
canonical eval paths.

## Implementation Notes

The reader lives in:

`src/ai_native_package/agent_telemetry_reader.py`

The snapshot schema lives in:

`src/ai_native_package/contracts/agent-telemetry-reader.schema.json`

CLI wiring lives in:

`src/ai_native_package/cli.py`

Public exports are added through:

- [api.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/api.py)
- [__init__.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/__init__.py)

## Future Work

Possible later additions:

- task-record loading when no telemetry exists yet
- explicit adapters from local snapshots to canonical benchmark tooling
- broader local evidence readers beyond the pack scope

Those are intentionally out of scope for the first slice.
