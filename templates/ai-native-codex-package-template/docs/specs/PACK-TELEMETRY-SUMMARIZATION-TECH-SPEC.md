# Pack Telemetry Summarization Tech Spec

## Purpose

Define one bounded local summary artifact for reusable project packs that
aggregates multiple `task-goal-telemetry.json` files without changing canonical
eval schemas or compare-report behavior.

The goal is simple:

- let a pack summarize repeated local task-goal attempts
- keep the summary useful for both agents and humans
- preserve the repo's authority split between local pack evidence and canonical
  benchmark artifacts

This spec is intentionally narrow. It covers local pack telemetry
summarization only. It does not redefine `external-measurements.json`,
`metrics.json`, `summary-report.json`, or `compare-report.json`.

It also depends on a stable persisted telemetry contract. If the linked
task-goal loop and persisted telemetry schema disagree about result semantics,
summary work must pause until that drift is resolved.

## Linked Surfaces

- [PACK-TELEMETRY-AND-LEARNING-LOOP-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/PACK-TELEMETRY-AND-LEARNING-LOOP-TECH-SPEC.md)
- [EXTERNAL-MEASUREMENTS-ARTIFACT-TECH-SPEC.md](/home/orchadmin/ai-orchestrator-lab/orchestration/template-pack-eval/EXTERNAL-MEASUREMENTS-ARTIFACT-TECH-SPEC.md)
- [write_compare_report.py](/home/orchadmin/ai-orchestrator-lab/orchestration/template-pack-eval/src/template_pack_eval/write_compare_report.py)
- [task_goal_telemetry.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/task_goal_telemetry.py)
- [task-goal-telemetry.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/contracts/task-goal-telemetry.schema.json)
- [cli.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/cli.py)
- [test_task_goal.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/tests/test_task_goal.py)

## Why This Exists

The pack already has one-at-a-time local telemetry:

- one `task-goal-telemetry.json` per task-goal loop attempt

That is enough for one run, but not enough to quickly answer local pack
questions such as:

- which goal gates fail most often
- which stages usually fail first
- how often tasks stop in `continue_working` versus complete
- which task names recur and succeed consistently
- whether local pack changes are reducing friction over time

The missing piece is a local summary artifact that can consume many telemetry
files and report bounded aggregates without pretending to be a canonical eval
artifact.

## Prerequisite

Before this summary surface is implemented, the pack must have a stable
persisted telemetry vocabulary.

That means:
- the persisted telemetry artifact must remain a valid serialization of the
  linked task-goal loop result
- the persisted telemetry schema must allow the result values the loop can
  actually emit
- summarization must not normalize or guess around result-vocabulary drift

If those conditions are not true, the summarizer must not be implemented on
top of that mismatch.

## Scope

This spec defines:

- one local-only pack summary artifact
- the authority split for that artifact
- the minimum required aggregate fields
- how the summary consumes multiple `task-goal-telemetry.json` artifacts
- how it stays separate from canonical eval and compare reports
- one small phased implementation slice

This spec does not define:

- changes to canonical eval schemas
- changes to `write_compare_report.py`
- changes to canonical compare report semantics
- a control-plane aggregation service
- a streaming or live telemetry system
- benchmark-wide comparisons across unrelated tasks

## Authority Split

Authority must remain explicit.

`task-goal-telemetry.json`

- authoritative for one local task-goal loop attempt
- still the source of truth for attempt-level outcome, stage order, and
  command-level evidence

`pack telemetry summary`

- authoritative only for derived local aggregates computed from a declared set
  of telemetry inputs
- not authoritative for canonical benchmark identity or compare-safe metrics
- not a replacement for any source telemetry artifact

`template-pack-eval` run artifacts

- authoritative for canonical run-level benchmark history
- still own `run.json`, `metrics.json`, `summary-report.json`, and
  `compare-report.json`

`external-measurements.json`

- authoritative for target-native measurements attached to canonical eval runs
- still run-scoped, not pack-summary-scoped

The summary artifact must not be ingested as a canonical eval artifact by
default.

## Separation From Canonical Compare Reports

This local summary should follow the same separation discipline already used by
the external-measurements spec and by
[write_compare_report.py](/home/orchadmin/ai-orchestrator-lab/orchestration/template-pack-eval/src/template_pack_eval/write_compare_report.py).

That means:

- canonical compare reports remain benchmark-native and identity-bound
- local pack summaries remain pack-native and telemetry-bound
- local summaries may reference canonical run ids when they are present in
  `run_correlation`, but they must not redefine benchmark outcome classes
- local summaries must not try to replace `compare-report.json`

Short version:

- pack summary = local learning artifact
- compare report = canonical benchmark comparison artifact

## Local Summary Artifact

### Artifact Name

`task-goal-telemetry-summary.json`

### Schema Placement

The summary artifact must be schema-backed.

For the local template family, the schema file should live at:

`src/ai_native_package/contracts/task-goal-telemetry-summary.schema.json`

The first schema version should be:
- `task-goal-telemetry-summary/v1`

### Default Placement

For the local template family, the default output path should live beside the
existing pack-local telemetry directory:

`<project_root>/.ai-native-codex-package-template/task-goal-telemetry/task-goal-telemetry-summary.json`

Generated packs should derive the hidden root the same way
[task_goal_telemetry.py](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/src/ai_native_package/task_goal_telemetry.py)
derives per-attempt telemetry placement.

### Write Policy

- summary writing is local-only
- summary writing is explicit, not automatic in the first slice
- summary writing must fail closed when no input telemetry files are provided or
  discovered
- summary writing must not mutate source telemetry files

## Input Model

The summary consumes multiple per-attempt telemetry artifacts from the pack's
telemetry directory, such as:

`<project_root>/.ai-native-codex-package-template/task-goal-telemetry/<task_name>.json`

Allowed input modes in the first slice:

1. repeated explicit telemetry paths
2. one explicit telemetry directory scan over the pack-scoped telemetry
   directory

The summary writer must record which source files it used.

The summary writer must ignore unrelated JSON files outside the declared
telemetry directory scan.

Inside the declared telemetry directory scan, it must only consider files that
validate against the telemetry schema.

The summary writer must reject malformed telemetry inputs instead of silently
counting partial data.

## Required Summary Fields

Every summary artifact must include:

- `schema_version`
- `generated_at`
- `producer`
- `summary_scope`
- `source_artifacts`
- `aggregate_counts`
- `result_breakdown`
- `stage_breakdown`
- `task_breakdown`
- `correlation_summary`
- `summary_notes`

## Required Field Meaning

`summary_scope`

- declares what was summarized
- minimum required fields:
  - `project_root`
  - `telemetry_artifact_count`

`source_artifacts`

- ordered list of telemetry artifact descriptors
- each descriptor must include:
  - `path`
  - `task_name`
  - `generated_at`

`aggregate_counts`

- minimum required fields:
  - `total_attempts`
  - `completed_count`
  - `continue_working_count`
  - `failed_count`
  - `primary_goal_passed_count`

`result_breakdown`

- counts grouped by telemetry `result`
- must preserve local vocabulary from `task-goal-telemetry.json`
- must not invent canonical benchmark classes

`stage_breakdown`

- counts grouped by first failing stage
- minimum stage buckets:
  - `primary_goal_gate`
  - `broader_validation`
  - `none`

`task_breakdown`

- ordered per-`task_name` aggregates
- each entry must include:
  - `task_name`
  - `attempt_count`
  - `completed_count`
  - `continue_working_count`
  - `failed_count`

`correlation_summary`

- local bridge to broader evidence when telemetry contains `run_correlation`
- minimum required fields:
  - `run_ids`
  - `build_run_manifest_paths`
- informational only
- deduplicated and sorted
- not a benchmark identity, compare-safe grouping key, or substitute for
  canonical run indexes

`summary_notes`

- plain-language observations for humans
- short and readable
- should explain the summary without requiring canonical eval vocabulary

## Minimum Useful Aggregate Fields

The first implementation must compute at least these aggregates:

- total telemetry artifacts summarized
- count of completed attempts
- count of continue-working attempts
- count of failed attempts
- count of attempts where the primary goal gate passed
- count of attempts whose first failure was `primary_goal_gate`
- count of attempts whose first failure was `broader_validation`
- per-task attempt counts

This is enough to support local pack learning without creating a heavyweight
analytics system.

## Derivation Rules

The summary must derive values from source telemetry using stable rules.

Rules:

1. one source telemetry file equals one attempt
2. `completed = true` increments `completed_count`
3. `continue_working = true` increments `continue_working_count`
4. `result = fail` with `continue_working = false` increments `failed_count`
5. `primary_goal_passed = true` increments `primary_goal_passed_count`
6. first failed command stage determines the stage bucket
7. if no command failed, stage bucket is `none`

If a telemetry artifact is schema-valid but missing expected command-stage
detail, the summary must preserve that as local summary uncertainty in
`summary_notes` rather than guessing.

If a telemetry artifact fails schema validation, the summary write must fail
closed instead of skipping that artifact silently.

## Summary Output Constraints

The summary artifact should be:

- machine-readable first
- human-plain in wording
- deterministic in ordering

Ordering rules:

- `source_artifacts` sorted by `generated_at`, then `path`
- `task_breakdown` sorted by descending `attempt_count`, then `task_name`
- `run_ids` and `build_run_manifest_paths` sorted lexically

## Relationship To External Measurements

The local summary may be useful later when selecting fields for
`external-measurements.json`, but it is not an external-measurements artifact.

The key distinction is:

- `external-measurements.json` attaches target-native measurements to one
  canonical eval run
- `task-goal-telemetry-summary.json` summarizes many local telemetry attempts
  for one pack workspace

No canonical eval writer should consume the local summary by default in the
first implementation slice.

## Relationship To Compare Report Patterns

[write_compare_report.py](/home/orchadmin/ai-orchestrator-lab/orchestration/template-pack-eval/src/template_pack_eval/write_compare_report.py)
only writes compare artifacts when all compared runs share the same benchmark
identity fields.

The local summary must not copy that contract.

Instead, the local summary groups local telemetry attempts inside one pack
workspace and reports local counts. It may include correlated run ids, but it
must not act as a benchmark identity or compare-safe report.

## Canonical Boundary Rule

If a future slice wants canonical comparison of task-goal behavior, that
projection must start from raw run-scoped evidence or an explicit control-plane
adapter.

It must not start from the many-attempt local summary artifact.

## CLI Shape

The first implementation should stay small:

- one pack-local command such as `summarize-task-goal-telemetry`
- support repeated `--telemetry-path`
- support one `--telemetry-dir`
- support optional explicit `--output-path`
- support `--output text|json`

The text output should remain brief. The JSON artifact remains the source of
truth.

## Phased Implementation Slice

### Phase 1

- add one schema-backed summary writer in the local pack
- consume explicit telemetry paths only
- write `task-goal-telemetry-summary.json`
- compute the minimum aggregate fields from this spec
- add focused tests for:
  - multiple passing attempts
  - mixed `continue_working` and completed attempts
  - first-failure stage counting
  - malformed telemetry input rejection

### Phase 2

- add directory scanning for telemetry artifacts
- add brief text output
- add optional local drill-down links to correlated build-run manifests

### Phase 3

- evaluate whether recurring patterns should inform future pack tuning reports
  or an explicit raw-evidence adapter
- do not change canonical eval schemas unless there is a clear compare-safe
  need backed by repeated use
- do not project from the many-attempt local summary artifact into canonical
  eval surfaces

## Implementation Boundaries

The implementation should:

- stay inside the local project-pack template
- reuse the existing telemetry artifact as the source input
- preserve canonical eval boundaries
- use plain language in summary notes
- validate source telemetry and the written summary against schemas

The implementation should not:

- rewrite or extend canonical compare reports
- create a second benchmark identity model
- aggregate across unrelated pack roots by default
- replace source telemetry artifacts with only a summary
