# Pack Telemetry And Learning Loop Tech Spec

## Purpose

Define one bounded telemetry slice for reusable project packs so they are not only build templates, but also structured evidence producers.

The goal is to let a pack record what happened during a real task-goal loop in a way that is:
- easy for an agent to emit
- easy for a human to read in plain language
- compatible with the repo's existing benchmark and control-plane data model
- useful later when we compare runs and design new project packs

This spec is intentionally narrow. It covers task-goal-loop telemetry only. It does not replace broader benchmark records, compare reports, or control-plane task state.

The telemetry payload in v1 must be a strict persisted superset of the existing `run-task-goal-loop` result. It must not invent a second competing outcome model.

## Linked Specs

- [GOAL-DRIVEN-BUILD-LOOP-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/GOAL-DRIVEN-BUILD-LOOP-TECH-SPEC.md)
- [BUILD-RUN-MANIFEST-INGESTION-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/orchestration/template-pack-eval/BUILD-RUN-MANIFEST-INGESTION-TECH-SPEC.md)
- [ORCHADMIN-DETERMINISTIC-DATA-AND-TASK-STATE-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/orchestration/control-plane-data/ORCHADMIN-DETERMINISTIC-DATA-AND-TASK-STATE-TECH-SPEC.md)
- [run_manifest.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/run_manifest.py)
- [task_goal.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/task_goal.py)

## Why This Matters

Today the pack already emits useful artifacts:
- task-goal validation and loop results
- docs-with-code records
- local build-run manifests
- canonical eval artifacts after ingestion

That is enough to benchmark one run, but not enough to learn systematically from many runs.

A dedicated pack telemetry artifact makes it easier to answer:
- which goal gates fail most often
- which validation stage catches real defects
- how many correction cycles a task usually needs
- which pack defaults reduce agent effort
- which feature patterns should become future template capabilities

This is the beginning of a learning loop for pack design, not just one more log file.

## Scope

This spec defines:
- one machine-readable telemetry artifact for `run-task-goal-loop`
- the minimum required fields that every pack should record
- optional fields that packs may add later without changing the core meaning
- how this telemetry coexists with docs-with-code, build-run manifests, and canonical eval artifacts

This spec does not define:
- a live telemetry streaming system
- cross-run dashboards
- benchmark declaration structure
- changes to canonical eval schemas
- a new control-plane status model

## Authority Model

Authority must remain split cleanly:

`task-record`
- authoritative for the task goal, scope, validation commands, and approval state

`run-task-goal-loop` result
- authoritative for the immediate execution outcome of one task-goal attempt

`task-goal telemetry artifact`
- authoritative only as the persisted saved copy of one loop attempt
- not authoritative for outcome semantics beyond the underlying `run-task-goal-loop` payload it serializes

`build-run-manifest`
- authoritative for project-local benchmark evidence at the broader run level

`template-pack-eval` and `control-plane-data`
- authoritative for canonical cross-run normalization, comparison, and reporting

The telemetry artifact must not replace the task record, doc-update record, project-pack contract, or build-run manifest.

## Compatibility With Existing Package Validation

The local template already treats these surfaces as active package policy:
- docs-with-code validation
- project-pack contract validation
- task-goal validation
- package `make validate`

Telemetry must fit inside that model, not bypass it.

That means:
- CLI changes that add telemetry options still require docs-with-code updates
- telemetry output must not weaken project-pack validation
- telemetry writing must not redefine validator exit semantics
- telemetry files must be optional outputs, not mandatory blockers for package bootstrap

## Telemetry Artifact

### Artifact Name

`task-goal-telemetry.json`

### Default Location

When `run-task-goal-loop` is given a project root or a task record with an absolute `operating_root`, the default path should be pack-scoped and should match the existing hidden-artifact family used by local run manifests.

For the local template, the default path should be:

`<project_root>/.ai-native-codex-package-template/task-goal-telemetry/<task_name>.json`

Generated packs should derive the hidden root from the pack identity the same way [run_manifest.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/run_manifest.py) derives its pack-local manifest directory.

If the user passes an explicit output path, that path wins.

If no deterministic project root can be resolved, telemetry writing must fail closed instead of guessing a path.

### Write Policy

- telemetry writing is opt-in in the first implementation slice
- a loop may still run without writing telemetry
- when telemetry writing is requested and the write fails, the command must report that failure clearly

## Required Telemetry Fields

Every telemetry artifact must include:
- `schema_version`
- `task_name`
- `generated_at`
- `producer`
- `operating_root`
- `task_record_path`
- `inputs`
- `result`
- `completed`
- `continue_working`
- `primary_goal_passed`
- `command_results`
- `errors`
- `attempt_summary`

In v1, `task_id` is optional. The current linked goal-loop implementation does not guarantee that `task_id` is present in the emitted loop payload, so the first telemetry slice must not depend on it as a required join key.

### Required Meaning

`result`
- `pass` or `fail`

`completed`
- `true` only when the declared goal gate and broader validation commands all pass

`continue_working`
- `true` only when the task is still incomplete but the outcome is an expected work-in-progress state rather than a malformed input/setup failure

`command_results`
- ordered per-command records from the loop
- must preserve stage meaning such as `primary_goal_gate` and `broader_validation`

`attempt_summary`
- plain-language summary for humans
- concise and readable
- should explain what happened without assuming repo-specific jargon

## Strict Payload Mapping

The telemetry artifact must persist the existing `run-task-goal-loop` payload without reinterpretation.

Required direct carry-through fields:
- `result`
- `completed`
- `continue_working`
- `primary_goal_passed`
- `command_results`
- `errors`
- `operating_root`
- `inputs`

Required added persistence fields:
- `schema_version`
- `generated_at`
- `producer`
- `task_record_path`
- `attempt_summary`
- `run_correlation`

The telemetry writer must not derive a new pass/fail vocabulary or collapse the ordered command results into a lossy summary.

## Allowed Optional Fields

The first implementation may optionally include:
- `artifact_paths`
- `files_in_scope`
- `validation_command_count`
- `failed_stage`
- `failure_count`
- `notes`
- `task_id`

These optional fields are useful, but they must not be required for a valid first implementation.

## Minimum Useful Telemetry

For pack learning, the minimum useful derived signals are:
- whether the primary goal gate passed
- whether broader validation passed
- how many commands were attempted
- which stage failed first
- whether the run ended as complete or still-in-progress

This gives future pack analysis enough signal to learn from friction without forcing a heavyweight event model.

## Relationship To Build Run Manifests

Task-goal telemetry and build-run manifests solve different problems.

Task-goal telemetry:
- one task loop attempt
- local, narrow, execution-focused
- useful for agent iteration analysis

Build-run manifest:
- one broader benchmark run
- local, project-level evidence
- useful for ingestion into canonical eval artifacts

The telemetry artifact may later help populate build-run metrics, but it is not a replacement for the build-run manifest.

## Correlation Contract

The telemetry artifact must carry one stable bridge back to broader local run evidence whenever that evidence exists.

V1 required shape:
- `run_correlation`

V1 allowed `run_correlation` fields:
- `build_run_manifest_path`
- `build_run_manifest_run_id`
- `run_id`

V1 rules:
- if the caller provides a local build-run manifest path or run id, the telemetry artifact must record it
- if no broader local run record exists yet, `run_correlation` may be present with null values
- the writer must not invent a run id

This keeps telemetry joinable to [run_manifest.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/run_manifest.py) and later ingestion flows without creating a new canonical run surface.

## Relationship To Future Pack Generation

Pack telemetry becomes useful when many runs are compared.

Examples:
- repeated failures in docs-with-code stages suggest a better default doc-update workflow
- repeated lint-only failures suggest the pack should narrow code patterns or add scaffold helpers
- repeated primary-goal failures before validation starts suggest the task-record examples or command templates are too loose
- repeated success with certain feature shapes suggests those capabilities should graduate into reusable pack modules

This is the core learning-loop idea:
- build
- validate
- record structured friction
- compare runs
- improve the template
- generate better future packs from that evidence

## Canonical Bridge

V1 telemetry remains local-only.

That means:
- it is not ingested directly into canonical eval artifacts
- it does not create a new control-plane schema
- any later cross-run normalization should flow through existing local run evidence and the build-run-manifest ingestion path

If a future slice wants canonical comparison of task-goal telemetry, that slice must define how telemetry projects into `external-measurements.json` or another explicitly approved canonical surface. It must not create a parallel canonical write path by accident.

## Fail-Closed Rules

Telemetry writing must fail closed when:
- `task_id` cannot be resolved
- `operating_root` is missing or not absolute
- the output path would be ambiguous
- the payload cannot be serialized deterministically

Telemetry writing must not:
- invent a project root
- silently drop required fields
- rewrite canonical eval artifacts
- override package-wide validation outcomes

## Execution And Exit Semantics

This telemetry slice must stay compatible with the existing package behavior.

That means:
- `run-task-goal-loop` keeps its existing result payload semantics
- telemetry is a side effect of the loop, not a new validator class
- telemetry does not introduce a new success/fail vocabulary beyond the existing loop result model

If telemetry writing is requested and the loop succeeds but the telemetry write fails, the command should report that explicitly in JSON output and exit nonzero.

## Human Wording Rule

The artifact and docs should stay agent-first in structure and human-plain in language.

That means:
- structured fields for agents
- short plain-language summaries for humans
- no unexplained internal jargon in the human summary

## First Implementation Slice

The first implementation should stay small.

### Add

- one schema file for task-goal telemetry
- one helper module to build and write telemetry payloads
- one optional `run-task-goal-loop` telemetry output flag
- one optional correlation input for an existing local run id or build-run manifest path
- one or two focused tests

### Reuse

- existing loop payload from [task_goal.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/task_goal.py)
- existing package metadata and project-root handling patterns
- existing pack-scoped hidden artifact naming patterns from [run_manifest.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/run_manifest.py)
- existing docs-with-code workflow

### Avoid In V1

- background aggregation
- automatic canonical eval ingestion
- multiple telemetry artifact variants
- new control-plane schemas

## Suggested File Surfaces

Likely local template surfaces:
- `src/ai_native_package/contracts/task-goal-telemetry.schema.json`
- `src/ai_native_package/task_goal_telemetry.py`
- `src/ai_native_package/task_goal.py`
- `src/ai_native_package/cli.py`
- focused tests under `tests/`

## Validation Expectations

The first implementation is complete when:
- a passing goal loop can optionally write one telemetry artifact
- a failing or incomplete loop can optionally write one telemetry artifact
- the artifact is deterministic and schema-valid
- the persisted payload remains a strict superset of the loop result payload
- a provided local run id or build-run manifest reference is preserved in `run_correlation`
- the package validation surface still passes

## Longer-Term Follow-On

After the first slice proves stable, a later spec can define:
- how task-goal telemetry aggregates across runs
- how it projects into benchmark comparisons
- how it informs automatic generation of novel project-pack variants

That later work should build on this artifact, not replace it.
