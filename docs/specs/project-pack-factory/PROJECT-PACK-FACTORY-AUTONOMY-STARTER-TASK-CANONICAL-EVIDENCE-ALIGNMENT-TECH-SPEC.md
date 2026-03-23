# Project Pack Factory Autonomy Starter Task Canonical Evidence Alignment Tech Spec

## Purpose

Define the smallest PackFactory change needed so newly materialized
build-packs that carry the autonomy handoff files can make honest forward
progress from their seeded starter tasks.

The immediate problem is specific and concrete:

- the seeded starter task `run_build_pack_validation` currently asks the agent
  to produce canonical readiness evidence
- but the task only points at the raw pack-local validation command
- that raw command can pass without updating `status/readiness.json` or
  `eval/latest/index.json`
- the autonomous loop therefore stops correctly, but cannot complete the task

This spec closes that gap without expanding into deployment, promotion, or
broader autonomous planning.

## Spec Link Tags

```json
{
  "spec_id": "autonomy-starter-task-canonical-evidence-alignment",
  "depends_on": [
    "autonomous-build-pack-handoff-and-work-state",
    "autonomous-loop-and-agent-memory-measurement",
    "workflow-eval-evidence-integrity"
  ],
  "integrates_with": [
    "build-pack-materialization",
    "readiness",
    "eval-latest-index",
    "factory-validation"
  ]
}
```

## Problem

PackFactory now materializes build-packs with:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

That gives the autonomous loop a clean starting point.

But the first real measured loop on a fresh handoff-carrying build-pack showed
that the seeded starter task contract is internally inconsistent.

The agent can run the declared command successfully, but still cannot satisfy
the task's own acceptance criteria because no bounded evidence-writing surface
is attached to that task.

That means:

- the loop can prove runtime health
- the loop can prove correct stop and resume behavior
- the loop cannot honestly mark the validation task complete
- the loop cannot advance to the benchmark task

This is a handoff contract problem, not an agent behavior problem.

## Current Factory Evidence

### Evidence A: The Fresh Build-Pack Seeds A Validation Task That Requires Canonical Evidence

Concrete pack:

- `build-packs/release-evidence-summarizer-build-pack-v2`

Concrete evidence:

- `build-packs/release-evidence-summarizer-build-pack-v2/tasks/active-backlog.json`
  currently seeds:
  - `task_id = run_build_pack_validation`
  - `status = in_progress`
  - `acceptance_criteria` includes:
    - `The validation command exits successfully.`
    - `The validation gate records passing evidence in status/readiness.json.`
  - `completion_signals` includes:
    - `validate_build_pack_contract reaches pass state.`
    - `Validation evidence is recorded under eval/history and linked from status/readiness.json.`
  - `validation_commands` contains only:
    - `PYTHONPATH=src python3 -m release_evidence_summarizer_template_pack validate-project-pack --project-root . --output json`

Interpretation:

- the task explicitly requires canonical readiness evidence
- the seeded command surface only proves pack-local runtime success

### Evidence B: The Same Pack Starts With No Validation Evidence

Concrete evidence before the loop:

- `build-packs/release-evidence-summarizer-build-pack-v2/status/readiness.json`
  declared:
  - `readiness_state = in_progress`
  - gate `validate_build_pack_contract.status = not_run`
  - gate `validate_build_pack_contract.last_run_at = null`
  - gate `validate_build_pack_contract.evidence_paths = []`
- `build-packs/release-evidence-summarizer-build-pack-v2/eval/latest/index.json`
  declared:
  - benchmark status `release-evidence-summarizer-template-pack-smoke-small-001 = not_run`
  - `updated_at = 2026-03-23T02:13:54Z`

Interpretation:

- the pack is correctly initialized in a pre-evidence state
- forward progress requires a bounded evidence-writing step, not only command
  exit success

### Evidence C: The Measured Loop Reached A Successful Runtime Validation Step

Concrete command run from the pack root:

```bash
PYTHONPATH=src python3 -m release_evidence_summarizer_template_pack validate-project-pack --project-root . --output json
```

Concrete loop evidence:

- `build-packs/release-evidence-summarizer-build-pack-v2/.pack-state/autonomy-runs/release-evidence-summarizer-loop-001/loop-events.jsonl`
  records:
  - a `command_completed` event for
    `PYTHONPATH=src python3 -m release_evidence_summarizer_template_pack validate-project-pack --project-root . --output json`
  - `outcome = pass`
  - note:
    `Validation command exited successfully.`
- `build-packs/release-evidence-summarizer-build-pack-v2/.pack-state/autonomy-runs/release-evidence-summarizer-loop-001/run-summary.json`
  declares:
  - `failed_command_count = 0`
  - `canonical_state_integrity.status = pass`
  - `stop_reason = seeded_task_cannot_record_canonical_evidence`

Interpretation:

- runtime validation succeeded
- the loop did not fail due to code or packaging breakage
- the stopping condition came from the handoff contract itself

### Evidence D: Canonical Evidence Did Not Advance After The Validation Command

Concrete evidence after the loop:

- `build-packs/release-evidence-summarizer-build-pack-v2/status/readiness.json`
  still declares:
  - `validate_build_pack_contract.status = not_run`
  - `validate_build_pack_contract.last_run_at = null`
  - `validate_build_pack_contract.evidence_paths = []`
- `build-packs/release-evidence-summarizer-build-pack-v2/eval/latest/index.json`
  still declares:
  - `release-evidence-summarizer-template-pack-smoke-small-001.status = not_run`

Concrete measured result:

- `build-packs/release-evidence-summarizer-build-pack-v2/.pack-state/autonomy-runs/release-evidence-summarizer-loop-001/run-summary.json`
  declares:
  - `validation_evidence_gain = false`
  - `benchmark_evidence_gain = false`
  - `readiness_change_summary.state_advanced = false`
  - `resume_count = 2`
  - `escalation_count = 1`

Interpretation:

- the loop resumed to the same canonical next task
- the loop escalated after evidence failed to advance
- the loop could not complete the starter task because no canonical evidence
  path was available

### Evidence E: The Materializer Seeds The Inconsistency Directly

Concrete code:

- `tools/materialize_build_pack.py`

Current behavior:

- seeds the validation task summary as:
  - `Run the build-pack validation command and capture readiness evidence.`
- seeds `acceptance_criteria` and `completion_signals` that require canonical
  evidence
- seeds `validation_commands` with only the raw
  `pack.json.entrypoints.validation_command`
- seeds the benchmark task in the same pattern using only the raw
  `pack.json.entrypoints.benchmark_command`

Interpretation:

- this is a factory-side synthesis issue
- individual agents are not expected to guess an unstated evidence-writing
  workflow

### Evidence F: PackFactory Already Has A Canonical Evidence-Writing Pattern

Concrete code:

- `tools/run_deployment_pipeline.py`

Observed behavior:

- runs the raw validation command
- writes `eval/history/<pipeline-id>/validation-result.json`
- runs the raw benchmark command
- writes `eval/history/<pipeline-id>/benchmark-result.json`
- updates `eval/latest/index.json`
- updates `status/readiness.json`

Interpretation:

- PackFactory already knows how to transform raw command execution into
  canonical readiness evidence
- the missing piece is a smaller non-deployment evaluation surface for starter
  autonomy tasks

## Design Goals

- keep the fix tightly scoped to starter autonomy tasks
- let a single agent complete seeded validation and benchmark tasks honestly
- reuse existing PackFactory evidence contracts
- avoid coupling starter autonomy tasks to deployment or promotion
- keep testing absolute minimal

## Non-Goals

This spec does not:

- change deployment or promotion workflows
- require a new remote service or long-running orchestrator
- redesign runtime agent memory
- broaden validator scope beyond what this fix needs
- add broad new autonomous task planning logic
- solve standalone exported build-pack execution outside PackFactory in v1

## Proposed Contract

### New Minimal Evaluation Surface

Introduce one new bounded PackFactory tool:

- `tools/run_build_pack_readiness_eval.py`

Its purpose is narrow:

- run one bounded readiness-evaluation phase at a time
- write canonical evaluation evidence for that phase
- update `status/readiness.json`
- update `eval/latest/index.json` only when benchmark evidence is written
- stop before release packaging, cloud verification, promotion, or deployment

This tool is the non-deployment counterpart to the evidence-writing slice that
already exists inside `tools/run_deployment_pipeline.py`.

### Scope Selector

For this spec, a build-pack is in scope only when its `pack.json` declares all
three autonomy handoff files in `directory_contract`:

- `project_objective_file`
- `task_backlog_file`
- `work_state_file`

Under the current materializer, newly materialized build-packs receive those
files by default. This is the operational meaning of “handoff-carrying
build-pack” in this spec.

### Input Contract

The tool should accept:

- `pack_root`
- `mode`
- `invoked_by`
- optional `eval_run_id`

Where:

- `pack_root` is the current build-pack root and may be `.` when the command is
  run from that directory
- `mode` is required and must be one of:
  - `validation-only`
  - `benchmark-only`

The tool must discover `factory_root` from `pack_root` by walking upward to the
PackFactory root.

No deployment environment, release id, cloud adapter, or promotion flags are
required in v1.

### Seeded Command Shape

Because starter task commands are stored today as raw shell strings in
`tasks/active-backlog.json`, the seeded command shape must be explicit.

Materialization must seed:

- `run_build_pack_validation.validation_commands[0]` as:
  - `python3 ../../tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop`
- `run_inherited_benchmarks.validation_commands[0]` as:
  - `python3 ../../tools/run_build_pack_readiness_eval.py --pack-root . --mode benchmark-only --invoked-by autonomous-loop`

These commands are intended to run from the build-pack root.

The raw pack-local runtime commands remain unchanged in `pack.json.entrypoints`.

### Output Contract

The tool reuses the evidence payload shapes already written by
`tools/run_deployment_pipeline.py` for:

- `validation-result.json`
- `benchmark-result.json`

V1 does not require a separate request-file schema or report-file schema for
this starter-task tool. It is a direct CLI surface with explicit flags, and its
canonical evidence artifacts must match the existing PackFactory evidence
contract.

#### `validation-only` Mode

On success, `validation-only` mode must:

- run only the raw build-pack validation command from `pack.json.entrypoints`
- create `eval/history/<eval-run-id>/validation-result.json`
- update `status/readiness.json`
  - `validate_build_pack_contract.status = pass`
  - validation gate `last_run_at` updates
  - validation gate `evidence_paths` points at the new
    `validation-result.json`
- leave inherited benchmark gate statuses unchanged
- leave `eval/latest/index.json` benchmark statuses unchanged
- keep `ready_for_deployment = false`
- keep deployment, release packaging, registry, and promotion state untouched

On failure, `validation-only` mode must fail closed:

- do not mark `validate_build_pack_contract = pass` unless the validation
  command succeeded and `validation-result.json` was written
- do not mutate inherited benchmark gate state
- do not mutate `eval/latest/index.json`

#### `benchmark-only` Mode

`benchmark-only` mode must enforce this precondition before running:

- `validate_build_pack_contract.status = pass`
- the validation gate `evidence_paths` includes a real
  `validation-result.json` path

If that precondition is not met, `benchmark-only` mode must fail closed without
writing benchmark evidence.

On success, `benchmark-only` mode must:

- run only the raw benchmark command from `pack.json.entrypoints`
- create `eval/history/<eval-run-id>/benchmark-result.json`
- update `eval/latest/index.json` to point at the new benchmark run artifact
- update mandatory inherited benchmark gates in `status/readiness.json`
  to `pass` or `waived` according to the benchmark output
- update `last_evaluated_at`
- set `ready_for_deployment = true` only when:
  - the validation gate is already canonically passed
  - all mandatory inherited benchmark gates are `pass` or `waived`

On failure, `benchmark-only` mode must fail closed:

- do not write benchmark pass state before validating benchmark identity and
  benchmark status
- do not set `ready_for_deployment = true` unless both validation and required
  benchmark gates are satisfied
- do not write any deployment pointer, release artifact, or promotion log entry

### Explicit Non-Ownership

`tools/run_build_pack_readiness_eval.py` must never edit:

- `tasks/active-backlog.json`
- `status/work-state.json`

Those files remain owned by the autonomous loop or orchestrator after it
observes canonical readiness/eval evidence.

## Materialization Changes

### Starter Task Command Semantics

`tasks/active-backlog.json.tasks[*].validation_commands` should remain the
existing machine-readable command list.

V1 does not require a new backlog field.

Instead, materialization should seed starter tasks with bounded
evidence-producing commands, not just the raw pack-local runtime commands.

### Required Seeded Task Changes

For newly materialized handoff-carrying build-packs:

- `run_build_pack_validation.validation_commands[0]` must use the exact
  `validation-only` command shape defined above
- `run_inherited_benchmarks.validation_commands[0]` must use the exact
  `benchmark-only` command shape defined above

The raw pack-local commands remain in `pack.json.entrypoints`.

The new starter task commands become the bounded canonical path that an
autonomous agent can execute to satisfy the task's own acceptance criteria.

### Task Summary Alignment

The starter task summaries and completion signals must be rewritten to match
the new bounded evidence-writing path explicitly.

For example:

- validation task summary must say it runs the validation evaluation workflow,
  not only the raw validation command
- benchmark task summary must say it runs the benchmark evaluation workflow,
  not only the raw benchmark command

## Work-State Expectations

When the validation-only command succeeds and canonical evidence is written:

- the autonomous loop must be able to mark `run_build_pack_validation`
  `completed`
- the autonomous loop must be able to advance
  `next_recommended_task_id` to `run_inherited_benchmarks`
- the readiness-evaluation tool itself still must not edit
  `tasks/active-backlog.json` or `status/work-state.json`

When validation succeeds but no evidence can be written:

- the task must remain incomplete
- the loop should stop or escalate, exactly as the measured loop did

This preserves the honest-stop behavior already proven by
`release-evidence-summarizer-loop-001`.

## Acceptance Criteria

This spec is satisfied when all of the following are true for a newly
materialized handoff-carrying build-pack:

1. Running the seeded validation task through its declared command changes
   `validate_build_pack_contract` from `not_run` to `pass`.
2. The validation gate points at a real `validation-result.json` artifact.
3. Running the seeded benchmark task before criterion 1 is satisfied fails
   closed without writing benchmark pass evidence.
4. Running the seeded benchmark task after criterion 1 is satisfied changes the
   inherited benchmark entry in `eval/latest/index.json` from `not_run` to
   `pass`.
5. Mandatory inherited benchmark gates point at `eval/latest/index.json`.
6. After criterion 1 succeeds, the autonomous loop can advance from the
   validation task to the benchmark task without
   requiring an operator to invent a missing workflow.
7. No deployment pointer, promotion record, or release packaging artifact is
   created by this starter-task evaluation path.

## Minimal Validation Plan

Keep verification absolute minimal and aligned with
`PROJECT-PACK-FACTORY-TESTING-POLICY.md`.

The current workflow-suite count already exceeds the stated hard-cap guidance,
so this spec must not assume unconstrained net-new workflow tests.

V1 verification should be folded into existing coverage:

1. Update the existing materialization coverage in
   `tests/test_materialize_build_pack.py`:
   - prove that newly materialized handoff-carrying build-packs seed the exact
     starter-task command strings defined in this spec.
2. Add or replace one small orchestration-level check in the closest existing
   evidence-writing suite:
   - prefer folding into `tests/test_run_deployment_pipeline.py` style helpers
     or replacing a weaker overlapping happy-path assertion rather than opening
     a broader new matrix
   - assert only the few state files that matter:
     - `status/readiness.json`
     - `eval/latest/index.json`
     - `eval/history/<run-id>/validation-result.json`
     - `eval/history/<run-id>/benchmark-result.json`
   - assert one critical ordering invariant:
     - `benchmark-only` fails closed before canonical validation pass exists
   - assert that no deployment pointer or release artifact was created

If the current test budget cannot absorb even that narrow change without
raising suite size, the implementation should replace weaker overlapping
coverage rather than expand the workflow suite further.

## Rollout Boundary

V1 rollout should be limited to newly materialized handoff-carrying build-packs
as defined in this spec.

V1 does not require:

- migration of historical build-packs
- retrofitting existing loop run summaries
- standalone exported build-pack support outside PackFactory
- changes to deployment pipeline behavior

## Why This Matters

The measured loop already proved something important:

- the agent can follow canonical work-state
- the agent can stop honestly
- the agent can resume honestly

What it still cannot do is finish the very first seeded task without an
evidence-writing bridge.

Fixing that bridge is the smallest change that moves PackFactory from
autonomy-shaped handoff to an autonomy-capable starter loop.
