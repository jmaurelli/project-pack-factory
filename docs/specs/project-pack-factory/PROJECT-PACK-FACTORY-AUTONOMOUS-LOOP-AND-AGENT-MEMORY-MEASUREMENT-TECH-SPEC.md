# Project Pack Factory Autonomous Loop And Agent Memory Measurement Tech Spec

## Purpose

Define how Project Pack Factory should measure:

- whether the autonomous loop moves a build-pack forward deterministically
- whether the resulting build-pack state is actually better
- whether agent memory improves restart and resume quality when the target pack
  actually has runtime-memory surfaces enabled

This spec is about measurement, not implementation autonomy by itself.

The goal is to answer a narrow operating question:

- did the memory system and loop help the agent complete the build-pack with
  less ambiguity, fewer restarts, and better evidence

## Spec Link Tags

```json
{
  "spec_id": "autonomous-loop-and-agent-memory-measurement",
  "depends_on": [
    "runtime-agent-memory",
    "autonomous-build-pack-handoff-and-work-state"
  ],
  "integrates_with": [
    "readiness",
    "factory-validation",
    "build-pack-materialization",
    "workflow-eval-evidence-integrity"
  ],
  "historical_idea_sources": [
    "templates/agent-memory-first-template-pack",
    "build-packs/agent-memory-first-build-pack"
  ]
}
```

## Problem

Project Pack Factory now has a PackFactory-native handoff model for newly
materialized build-packs:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

It also already has a runtime-memory model under `.pack-state/agent-memory/`.

What it does not yet have is a PackFactory-native way to measure whether those
layers are actually helping an agent complete work.

Important current limitation:

- newly materialized autonomy-enabled build-packs such as
  `release-evidence-summarizer-build-pack-v2` are strong baselines for
  autonomous-loop measurement
- they are not yet runtime-memory-enabled baselines by default
- memory-quality metrics therefore become fully measurable only for
  runtime-memory-enabled packs or after a target pack adds runtime-memory
  surfaces

Without a measurement contract:

- restart quality is anecdotal
- loop progress is hard to compare between runs
- stale memory can look useful until it causes divergence
- readiness improvements cannot be cleanly attributed to the loop
- future autonomy work risks optimizing for activity rather than completion

## Current Factory Evidence

### Evidence A: Newly Materialized Build-Packs Now Carry Canonical Objective, Backlog, And Work-State

Concrete current example:

- `build-packs/release-evidence-summarizer-build-pack-v2`

Concrete evidence:

- `build-packs/release-evidence-summarizer-build-pack-v2/contracts/project-objective.json`
  exists and declares:
  - `objective_id`
  - `objective_summary`
  - `metrics`
  - `promotion_readiness_requirements`
- `build-packs/release-evidence-summarizer-build-pack-v2/tasks/active-backlog.json`
  exists and declares two starter tasks:
  - `run_build_pack_validation`
  - `run_inherited_benchmarks`
- `build-packs/release-evidence-summarizer-build-pack-v2/status/work-state.json`
  exists and currently declares:
  - `autonomy_state = actively_building`
  - `active_task_id = run_build_pack_validation`
  - `next_recommended_task_id = run_build_pack_validation`

Interpretation:

- PackFactory now has a canonical starting point for loop measurement
- the loop no longer has to infer the initial objective and next task from
  prose alone

### Evidence B: Readiness Remains The Human-Readable Shadow Of Machine State

Concrete evidence:

- `build-packs/release-evidence-summarizer-build-pack-v2/status/readiness.json`
  currently declares:
  - `readiness_state = in_progress`
  - `ready_for_deployment = false`
  - `recommended_next_actions` that shadow the backlog:
    - start with validation
    - then run the inherited benchmark

Interpretation:

- readiness already exposes high-level progress signals
- but it does not expose loop quality, memory correctness, or restart quality

### Evidence C: Eval State Already Captures Readiness Evidence, Not Loop Telemetry

Concrete evidence:

- `build-packs/release-evidence-summarizer-build-pack-v2/eval/latest/index.json`
  currently shows inherited benchmark state only
- the current benchmark result for this freshly materialized pack is still
  `not_run`

Interpretation:

- current eval state is the right source for validation and benchmark outcome
- it is not the right place for every per-iteration loop event

### Evidence D: Runtime Memory Is Already Explicitly Advisory And Local

Concrete evidence:

- `PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md` says:
  - runtime memory is advisory local state
  - canonical PackFactory state wins on disagreement
  - PackFactory-native local runtime-memory storage is
    `.pack-state/agent-memory/`
- the same spec explicitly forbids runtime-memory artifacts from becoming a
  second control plane under `status/`, `registry/`, or `deployments/`

Interpretation:

- measurement must not accidentally promote runtime-memory logs into canonical
  PackFactory authority
- loop telemetry belongs in local mutable state first

### Evidence E: Validator Scope Is Intentionally Minimal For The New Handoff

Concrete evidence:

- `tools/validate_factory.py` now validates the new autonomy files only when a
  build-pack declares them
- current validator checks are intentionally narrow:
  - schema validity
  - `active_task_id` resolves to a real task when autonomy is active
  - `next_recommended_task_id` resolves to a real non-final non-blocked task
  - blocked tasks are not also active

Interpretation:

- the measurement spec should preserve PackFactory's minimal-test discipline
- v1 measurement should not require a broad new contradiction suite

### Evidence F: The Existing Agent-Memory Line Shows A Historical Example Of Bounded Measurement Artifacts

Current evidence source, used here only as an idea bank:

- `templates/agent-memory-first-template-pack`
- `build-packs/agent-memory-first-build-pack`

Concrete evidence:

- the runtime-memory line already emits bounded evidence artifacts such as:
  - `agent-memory-scorecard.json`
  - `agent-memory-snapshot.json`
- these are benchmark-linked evidence outputs, not new control-plane files

Interpretation:

- PackFactory already has a historical example of bounded scorecard-style
  measurement artifacts
- the new autonomy measurement layer should borrow that pattern cautiously
  without importing the retired line as direct authority

## Design Goals

- measure restart quality separately from output quality
- keep canonical PackFactory authority unchanged
- make run quality comparable between autonomous runs
- keep per-iteration telemetry local and mutable
- produce a compact scorecard that operators can review quickly
- stay compatible with PackFactory's minimal-test policy

## Non-Goals

This spec does not:

- create a new PackFactory authority file under `status/`
- require every build-pack to support autonomous runs immediately
- require remote telemetry infrastructure
- redefine readiness or eval artifacts as loop telemetry stores
- require broad new workflow tests in v1

## Authority Model

The measurement model has three layers.

### 1. Canonical PackFactory State

This remains authoritative:

- `pack.json`
- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`
- `eval/latest/index.json`
- `eval/history/*`
- factory registries and deployment pointers

### 2. Runtime Memory

This remains advisory:

- `.pack-state/agent-memory/`

If runtime memory disagrees with canonical PackFactory state:

- canonical PackFactory state wins
- the disagreement counts as stale-memory evidence for measurement

### 3. Measurement Artifacts

These are measurement outputs, not control-plane state.

V1 measurement artifacts should live under:

- `.pack-state/autonomy-runs/`

Optional exported scorecards may also be written under:

- `eval/history/<run-id>/`

but only when an explicit benchmark, operator review, or workflow step chooses
to preserve them as evidence.

Exported scorecards remain supplementary evidence only.

They must not:

- satisfy readiness gates by themselves
- update `eval/latest/index.json`
- override `status/work-state.json.next_recommended_task_id`
- become a new control-plane authority

## V1 Measurement Surfaces

### Local Run Log

Each autonomous run should have a local mutable run root:

- `.pack-state/autonomy-runs/<run_id>/`

Recommended files:

- `.pack-state/autonomy-runs/<run_id>/loop-events.jsonl`
- `.pack-state/autonomy-runs/<run_id>/run-summary.json`

These local runtime files are local-consumer contracts only.

They must not:

- be added to `pack.json.directory_contract` as required paths
- become required inputs to `tools/validate_factory.py`
- fail whole-factory validation when absent

### Optional Exported Scorecard

When a run needs stable operator-facing evidence, PackFactory may export:

- `eval/history/<run_id>/autonomy-loop-scorecard.json`

V1 does not require factory-wide validator support for this exported scorecard.

## Required Event Fields For `loop-events.jsonl`

Each event record should contain at least:

- `schema_version`
- `run_id`
- `recorded_at`
- `step_index`
- `event_type`
- `active_task_id`
- `next_recommended_task_id`
- `decision_source`
- `memory_state`
- `commands_attempted`
- `outcome`
- `readiness_state_before`
- `readiness_state_after`
- `notes`

Required value meanings:

- `decision_source`:
  - `canonical_only`
  - `canonical_plus_memory`
  - `memory_only`
- `memory_state`:
  - `not_used`
  - `used_and_consistent`
  - `used_and_stale`
  - `used_and_incomplete`
- `event_type`:
  - `run_started`
  - `task_selected`
  - `command_completed`
  - `state_updated`
  - `escalation_raised`
  - `run_stopped`
  - `run_completed`

## Required Fields For `run-summary.json`

Each run summary should contain at least:

- `schema_version`
- `run_id`
- `pack_id`
- `started_at`
- `ended_at`
- `baseline_snapshot`
- `step_count`
- `resume_count`
- `completed_task_ids`
- `failed_command_count`
- `escalation_count`
- `stop_reason`
- `metrics`

The `metrics` object should carry the score outputs defined below.

The `baseline_snapshot` object should capture the run-start baseline from
canonical state at minimum:

- `active_task_id`
- `next_recommended_task_id`
- `readiness_state`
- `ready_for_deployment`
- `gate_statuses`
- `eval_result_statuses`

## Core Measurement Families

V1 measurement should score three families:

- memory quality
- loop quality
- outcome quality

## Metric Computability Rules

V1 must distinguish between:

- metrics that are computable from current loop telemetry plus canonical pack
  state
- richer metrics that require stronger runtime instrumentation or
  runtime-memory-enabled packs

The required v1 scorecard therefore uses a smaller mandatory core.

Memory-specific metrics are optional unless the target pack actually has
runtime-memory surfaces enabled for the measured run.

## Memory Quality Metrics

These metrics are only required when the measured pack or measured run
explicitly uses runtime-memory surfaces.

### Resume Event Rule

For this spec, a resume event means:

- a `task_selected` event that occurs after `run_started`
- for a run whose `resume_count` is greater than zero

The comparison baseline for that resume event is the pre-resume canonical
`next_recommended_task_id` captured in the prior run’s terminal summary or in
the current run’s `baseline_snapshot`.

### 1. `resume_correctness`

Question:

- after a restart or resume, did the agent continue from the task canonical
  state already recommended

Definition:

- numerator:
  resume events where the first post-resume `active_task_id` equals the
  canonical `next_recommended_task_id` from pre-resume work-state
- denominator:
  all resume events

Primary evidence:

- pre-resume and post-resume snapshots of `status/work-state.json`
- `loop-events.jsonl`

### 2. `stale_memory_rate`

Question:

- how often did runtime memory disagree with canonical state

Definition:

- numerator:
  loop events where `memory_state = used_and_stale`
- denominator:
  loop events where runtime memory was used

Primary evidence:

- `loop-events.jsonl`
- `.pack-state/agent-memory/`
- canonical `tasks/active-backlog.json`
- canonical `status/work-state.json`

Classification rule:

- `used_and_stale` means the memory-derived task, blocker, or next-action
  claim conflicts with the canonical `status/work-state.json` or
  `tasks/active-backlog.json` state available at task-selection time

### 3. `consistent_memory_use_rate`

Question:

- when memory was used, how often was it used without conflicting with current
  canonical state

Definition:

- numerator:
  loop events where `decision_source = canonical_plus_memory` and
  `memory_state = used_and_consistent`
- denominator:
  loop events where runtime memory was used

Primary evidence:

- `loop-events.jsonl`

### 4. `boundary_compliance`

Question:

- did runtime memory ever push the loop toward illegal control-plane edits

Definition:

- this is a follow-on metric, not part of the mandatory v1 scorecard
- it becomes computable only when loop events include structured command target
  data or explicit transcript references

Primary evidence:

- `loop-events.jsonl`
- any command transcripts referenced there

## Loop Quality Metrics

### 5. `task_completion_rate`

Question:

- how much of the declared backlog did the loop complete

Definition:

- numerator:
  tasks with final `status = completed`
- denominator:
  total declared tasks in `tasks/active-backlog.json`

Primary evidence:

- `tasks/active-backlog.json`

### 6. `iterations_to_first_evidence`

Question:

- how long did it take before the loop produced the first real validation or
  benchmark evidence

Definition:

- the smallest `step_index` where:
  - `status/readiness.json.required_gates[*].status` changes from `not_run`, or
  - `eval/latest/index.json` changes from the materialized baseline

Primary evidence:

- `loop-events.jsonl`
- `status/readiness.json`
- `eval/latest/index.json`

### 7. `iterations_to_readiness_change`

Question:

- how long did it take before readiness moved beyond the materialized baseline

Definition:

- the smallest `step_index` where either:
  - `readiness_state` changes from the materialized starting state, or
  - `ready_for_deployment` changes from `false`

Primary evidence:

- `status/readiness.json`
- `loop-events.jsonl`

### 8. `blocked_recovery_rate`

Question:

- when the loop became blocked, how often did it recover and complete the task

Definition:

- numerator:
  tasks that entered `blocked` and later became `completed`
- denominator:
  tasks that entered `blocked`

Primary evidence:

- `tasks/active-backlog.json`
- `status/work-state.json`
- `loop-events.jsonl`

### 9. `escalation_precision`

Question:

- were escalations raised only when the declared stop or escalation conditions
  actually required them

Definition:

- numerator:
  escalations whose reason matches a task `escalation_condition` or
  work-state `stop_condition`
- denominator:
  all escalations raised

Primary evidence:

- `loop-events.jsonl`
- `tasks/active-backlog.json`
- `status/work-state.json`

### 10. `stop_condition_accuracy`

Question:

- if the loop stopped, did it stop for a declared valid reason

Definition:

- pass if the terminal `stop_reason` matches one declared in:
  - `status/work-state.json.stop_conditions`, or
  - the current task’s `escalation_conditions`

Primary evidence:

- `run-summary.json`
- `status/work-state.json`
- `tasks/active-backlog.json`

## Outcome Quality Metrics

### 11. `readiness_change_summary`

Question:

- did the loop leave the pack in a better readiness state than where it began

Definition:

- record the following tuple relative to `baseline_snapshot`:
  - `state_advanced`
  - `deployability_changed`
  - `gates_advanced_count`

Primary evidence:

- initial materialization state
- final `status/readiness.json`

### 12. `validation_evidence_gain`

Question:

- did the loop turn missing validation evidence into recorded evidence

Definition:

- pass if the validation gate moved from `not_run` to one of:
  - `pass`
  - `fail`
  - `waived`

Primary evidence:

- `status/readiness.json`
- referenced validation artifacts

### 13. `benchmark_evidence_gain`

Question:

- did the loop turn missing benchmark evidence into recorded benchmark results

Definition:

- pass if any required benchmark result moved from `not_run` to a terminal
  state and is indexed in `eval/latest/index.json`

Primary evidence:

- `benchmarks/active-set.json`
- `status/readiness.json`
- `eval/latest/index.json`

### 14. `canonical_state_integrity`

Question:

- did the loop preserve PackFactory cross-file invariants

Definition:

- this is a validity gate, not a scored quality dimension
- pass if whole-factory validation still passes after the run

Primary evidence:

- `tools/validate_factory.py --factory-root ... --output json`

## V1 Scorecard Contract

### Required V1 Core

The compact scorecard must summarize:

- `task_completion_rate`
- `iterations_to_first_evidence`
- `iterations_to_readiness_change`
- `readiness_change_summary`
- `validation_evidence_gain`
- `benchmark_evidence_gain`
- `canonical_state_integrity`

### Optional V1 Memory Add-On

When the measured run actually uses runtime-memory surfaces, the scorecard
should also summarize:

- `resume_correctness`
- `stale_memory_rate`
- `consistent_memory_use_rate`

### Follow-On Metrics

The following remain useful but are not required in the first scorecard:

- `boundary_compliance`
- `blocked_recovery_rate`
- `escalation_precision`
- `stop_condition_accuracy`

The scorecard should also include:

- `operator_summary`
- `highest_risk_observation`
- `recommended_next_action`

Each narrative field must cite one or more:

- metric ids
- artifact paths

## Initial Loop Measurement Baseline For `release-evidence-summarizer-build-pack-v2`

This build-pack is the first PackFactory-native loop baseline for this spec
because it is freshly materialized with the new handoff surfaces and has not
yet run its declared validation or benchmark commands.

It is not yet a runtime-memory-enabled baseline.

Current baseline evidence:

- `contracts/project-objective.json` declares the intended release-evidence
  objective
- `tasks/active-backlog.json` declares:
  - `run_build_pack_validation` as the active first task
  - `run_inherited_benchmarks` as the dependent second task
- `status/work-state.json` declares:
  - `autonomy_state = actively_building`
  - `active_task_id = run_build_pack_validation`
  - `next_recommended_task_id = run_build_pack_validation`
- `status/readiness.json` declares:
  - both required gates are still `not_run`
- `eval/latest/index.json` declares:
  - the inherited benchmark result is still `not_run`

Interpretation:

- this pack gives PackFactory a usable pre-evidence autonomy baseline
- its inherited benchmark metadata is still template-shaped, so it is not a
  fully normalized benchmark-identity baseline yet
- it is well-suited for measuring:
  - iterations to first evidence
  - readiness delta
  - validation evidence gain
  - benchmark evidence gain
- memory-quality metrics only become measurable here after runtime-memory
  surfaces are added or explicitly used

## Minimal Verification Boundary

This spec should follow PackFactory's minimal-test policy.

V1 measurement support should prefer:

- local runtime logs under `.pack-state/autonomy-runs/`
- a compact scorecard
- comparison against existing canonical pack state

V1 should not require:

- broad new validator suites
- full autonomous-loop simulation harnesses
- template-creation expansion
- new workflow tests unless a concrete measurement exporter is actually
  implemented

## Acceptance Criteria

This spec is satisfied when all of the following are true:

1. PackFactory has an explicit measurement model that separates:
   - canonical pack state
   - advisory runtime memory
   - loop and memory measurement artifacts
2. The measurement model defines concrete formulas and evidence sources for:
   - memory quality
   - loop quality
   - outcome quality
3. The measurement model is grounded in a current PackFactory-native build-pack
   baseline, specifically `release-evidence-summarizer-build-pack-v2`.
4. The measurement model preserves the current PackFactory authority boundary.
5. The measurement model remains compatible with PackFactory's minimal-test
   policy.

## Recommended Next Step

The next implementation step after this spec is to define two local runtime
schemas:

- `autonomy-loop-event.schema.json`
- `autonomy-run-summary.schema.json`

and add a minimal runtime recorder that writes:

- `.pack-state/autonomy-runs/<run_id>/loop-events.jsonl`
- `.pack-state/autonomy-runs/<run_id>/run-summary.json`

The first implementation should stay local-state-first and should not add new
canonical `status/` files.

The first implementation should also keep the mandatory scorecard to the v1
core set rather than attempting the full follow-on metric set immediately.
