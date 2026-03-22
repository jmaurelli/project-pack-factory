# Project Pack Factory Workflow Eval Evidence Integrity Tech Spec

## Purpose

Define the minimal remediation required to make
`tools/run_workflow_eval.py` produce factory-valid evaluation fixtures instead
of placeholder-ready state that the factory's own validator rejects.

The goal is not to expand the workflow evaluation suite.

The goal is to make the existing small workflow evaluation consistent with the
current PackFactory evidence-integrity rules.

## Spec Link Tags

```json
{
  "spec_id": "workflow-eval-evidence-integrity",
  "depends_on": [
    "build-pack-materialization",
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration",
    "runtime-agent-memory"
  ],
  "integrates_with": [
    "testing-policy",
    "root-test-harness"
  ],
  "adjacent_work": [
    "workflow evaluator fixture preparation",
    "factory evidence integrity validation",
    "minimal workflow verification"
  ]
}
```

## Problem

The live factory workflows are currently healthy when exercised directly, but
the factory's own workflow evaluator is not.

`tools/run_workflow_eval.py` currently manufactures build-pack readiness by
stamping pass state and placeholder evidence into copied factories instead of
producing real validation and benchmark evidence.

The factory validator rejects that synthetic state, which causes:

- promotion workflow evaluation to fail before promotion can begin
- deployment pipeline evaluation to fail at `validate_factory_state`
- the workflow evaluator to report false-negative factory failures

This is not a broad workflow regression in the live PackFactory.

It is a self-consistency bug in the evaluator fixture-preparation path.

## Evidence

Evidence was collected on 2026-03-22 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: Live Factory State Is Valid

Command:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory
```

Observed result:

- `VALID: 8 packs and 21 schemas passed`

Interpretation:

- the active factory state is valid before workflow-eval remediation
- this command alone does not explain live workflow success or failure

### Evidence A2: Direct JSON Checker Workflow Execution Succeeds

Observed factory operation log entries in
`registry/promotion-log.json` for `json-health-checker-build-pack`:

- testing pipeline and promotion completed
- staging pipeline and promotion completed
- production pipeline and promotion completed

Representative event indexes from the current log:

- `11`
- `12`
- `13`
- `14`
- `15`
- `16`

Interpretation:

- the live PackFactory workflow surfaces can complete successfully
- the workflow-eval failures are not sufficient evidence of a broad live
  workflow regression

### Evidence B: Workflow Eval Fails In Three Cases

Command:

```bash
python3 tools/run_workflow_eval.py --factory-root /home/orchadmin/project-pack-factory --output json
```

Observed result:

- workflow eval status: `failed`
- case count: `5`
- passed: `2`
- failed: `3`

Failing cases:

- `promote_success_testing`
- `pipeline_success_without_commit`
- `pipeline_success_with_commit`

Representative error from the failed promotion case:

- `readiness evidence integrity failed: ... materialization-report.json: benchmark run artifact does not report benchmark_id 'agent-memory-restart-small-001'`

Interpretation:

- the failures begin before the tested workflow can prove its own happy path
- the failure is tied to evidence integrity, not to promotion transition rules
  themselves

### Evidence C: The Copied Eval Factories Are Internally Invalid

Commands:

```bash
python3 tools/validate_factory.py --factory-root /tmp/ppf-workflow-eval-promote-qbub03uu/factory --output json
python3 tools/validate_factory.py --factory-root /tmp/ppf-workflow-eval-pipeline-no-commit-t8vv1kzb/factory --output json
python3 tools/validate_factory.py --factory-root /tmp/ppf-workflow-eval-pipeline-commit-5fd2toxz/factory --output json
```

Observed result in each copied factory:

- invalid factory with `3` errors

Shared errors:

- materialization report does not report benchmark id
  `agent-memory-restart-small-001`
- readiness validation gate `validate_build_pack_contract` must point to
  `validation-result.json`
- readiness benchmark gate `agent_memory_restart_small_001` must point to
  `eval/latest/index.json`

Interpretation:

- the workflow evaluator prepares invalid copied factories before the tested
  promotion or pipeline path executes
- the pipeline failures are downstream of invalid pre-seeded evidence

### Evidence D: Evaluator Code Writes Placeholder Pass Evidence

Relevant code:

- [run_workflow_eval.py](/home/orchadmin/project-pack-factory/tools/run_workflow_eval.py#L145)
- [run_workflow_eval.py](/home/orchadmin/project-pack-factory/tools/run_workflow_eval.py#L193)

Observed behavior in `_prepare_ready_build_pack()`:

- marks readiness state as `ready_for_deploy`
- marks every gate as `pass`
- points every gate at `eval/history/bootstrap/pass.json`
- flips `eval/latest/index.json` benchmark status to `pass`
- does not generate real `validation-result.json`
- does not generate real benchmark run artifacts

Observed behavior in `_configure_pipeline_commands()`:

- replaces the validation command with `print('ok')`
- replaces the benchmark command with `print('bench')`

Interpretation:

- the evaluator creates state that cannot satisfy the current factory
  validator's evidence contract
- the pipeline benchmark command override is also incompatible with the
  deployment pipeline's JSON benchmark parsing contract

### Evidence E: Validator And Pipeline Contracts Require Real Evidence

Relevant code:

- [validate_factory.py](/home/orchadmin/project-pack-factory/tools/validate_factory.py#L142)
- [validate_factory.py](/home/orchadmin/project-pack-factory/tools/validate_factory.py#L239)
- [run_deployment_pipeline.py](/home/orchadmin/project-pack-factory/tools/run_deployment_pipeline.py#L204)
- [run_deployment_pipeline.py](/home/orchadmin/project-pack-factory/tools/run_deployment_pipeline.py#L235)

Observed contract requirements:

- non-`not_run` benchmark entries in `eval/latest/index.json` must reference a
  real run artifact under `eval/history/<run_id>/`
- the run artifact must actually report the expected benchmark id
- validation readiness evidence must point to `validation-result.json`
- benchmark readiness evidence must point to `eval/latest/index.json`
- pipeline benchmark commands must emit JSON with `benchmark_id` or
  `benchmark_results`

Interpretation:

- the current validator and pipeline behavior are internally consistent
- remediation should make the evaluator comply with those contracts rather than
  loosening the validator

## Design Goals

- keep the remediation tightly scoped to workflow evaluation support code
- preserve the existing workflow-eval case count
- generate real evidence using existing pack commands wherever possible
- avoid adding new benchmark scenarios or broader fixture matrices
- keep the workflow verification aligned with the testing policy
- avoid weakening validator integrity rules to accommodate fake evaluator state

## Scope

This spec defines:

- the required remediation to `tools/run_workflow_eval.py`
- the minimum evidence shape the evaluator must generate before promotion and
  pipeline evaluation
- the verification commands for proving the evaluator is self-consistent

This spec does not define:

- a new workflow-eval case
- broader PackFactory benchmark coverage
- changes to live JSON checker pack behavior
- changes to the live validator integrity contract
- retrofitting runtime agent memory into non-memory packs

## Current Failure Mode

The workflow evaluator currently uses a shortcut:

1. materialize a copied build pack from the memory-first template
2. mark readiness gates as `pass`
3. seed placeholder evidence paths
4. optionally write a release artifact
5. call promotion or pipeline tooling

That shortcut was once sufficient for looser workflow assumptions, but it is no
longer valid under the current evidence-integrity rules.

Under current rules, a build pack cannot be treated as ready by merely editing:

- `status/readiness.json`
- `eval/latest/index.json`

The referenced evidence artifacts must also exist and match those status files.

## Required Remediation

### 1. Replace Placeholder Readiness Seeding With Integrity-Aligned Evidence

`_prepare_ready_build_pack()` in
[run_workflow_eval.py](/home/orchadmin/project-pack-factory/tools/run_workflow_eval.py#L145)
must stop manufacturing pass state through:

- `eval/history/bootstrap/pass.json`
- synthetic gate pass markers without matching artifacts

Instead, it must produce integrity-aligned evidence that satisfies the current
validator contract.

The compliant minimal implementation may use either of these approaches:

- synthesize small evidence artifacts that match the current readiness and
  `eval/latest/index.json` integrity rules
- execute or wrap pack commands when that is the smallest clean way to produce
  compliant artifacts

This spec does not require proof that inherited pack entrypoints were executed.

What it requires is that the evaluator stop writing malformed pass evidence.

The evaluator must then update:

- `status/readiness.json`
- `eval/latest/index.json`

using the same evidence-shape rules already enforced by the current validator
and pipeline:

- validation gate evidence points to a real `validation-result.json`
- benchmark gate evidence points to `eval/latest/index.json`
- `eval/latest/index.json` points to a real benchmark artifact under
  `eval/history/<run_id>/`

The preferred minimal evidence shape is the same small shape already used by
the maintained happy-path workflow tests under:

- [test_promote_build_pack.py](/home/orchadmin/project-pack-factory/tests/test_promote_build_pack.py)
- [test_run_deployment_pipeline.py](/home/orchadmin/project-pack-factory/tests/test_run_deployment_pipeline.py)

### 2. Keep Release Preparation Separate From Readiness Preparation

`_prepare_release()` may continue to synthesize minimal release artifacts for
the evaluator, but that release preparation must remain separate from evidence
generation.

The evaluator must not treat release creation as a substitute for:

- validation evidence
- benchmark evidence
- readiness integrity

### 3. Stop Overriding The Benchmark Command With Non-Compliant Output

`_configure_pipeline_commands()` in
[run_workflow_eval.py](/home/orchadmin/project-pack-factory/tools/run_workflow_eval.py#L193)
must not replace the benchmark command with:

- `print('bench')`

Those overrides are incompatible with the deployment pipeline contract because:

- the benchmark stage expects JSON benchmark output

The validation override is not itself proven invalid by the collected evidence,
because the pipeline validation stage only requires a zero exit code before it
writes `validation-result.json`.

The compliant minimal implementation is:

- remove the benchmark override entirely, or
- replace it only with another JSON-emitting benchmark-compatible command

If the evaluator keeps an override for the benchmark command, that override
must emit JSON whose benchmark ids match `eval/latest/index.json`.

The preferred implementation is:

- do not override the benchmark command when the selected fixture already emits
  pipeline-compatible JSON

### 4. Preserve Minimal Workflow Coverage

This remediation must not add new workflow-eval cases.

The maintained case set remains:

- materialization fail-closed baseline
- materialization success after template reactivation
- promotion success into testing
- pipeline success without commit
- pipeline success with commit

The fix is about making those five cases valid and trustworthy.

### 5. Fixture Selection Boundary

This spec does not require preserving the retired
`agent-memory-first-template-pack` as the long-term workflow-eval source.

This spec also does not require changing workflow-eval to a different fixture
as part of the minimal remediation.

The immediate requirement is narrower:

- whichever fixture the evaluator currently uses, it must generate compliant
  evidence for that fixture's benchmark contract

If the team later wants workflow-eval to stop depending on a retired fixture,
that should be handled as a separate fixture-selection remediation rather than
bundled into this evidence-integrity fix.

## Test And Verification Policy

This remediation must stay minimal.

Preferred verification order:

- run `validate_factory.py` first
- run `run_workflow_eval.py` second
- inspect the failing copied factory only when a workflow-eval case fails

### Test Budget Rule

The implementation should prefer:

- zero new tests if the existing workflow evaluator command can prove the fix

This spec does not authorize any new or modified automated tests.

If a future implementation proposes test changes, that must be approved
separately under the testing policy.

The remediation should not add:

- new benchmark declarations
- new evaluator cases
- a broader matrix of template fixtures

## Acceptance Criteria

The remediation is complete when all of the following are true:

1. `python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory`
   still succeeds.
2. `python3 tools/run_workflow_eval.py --factory-root /home/orchadmin/project-pack-factory --output json`
   returns status `completed`.
3. The promotion workflow-eval case reports `completed`.
4. The pipeline workflow-eval case without commit reports `completed`.
5. The pipeline workflow-eval case with commit reports `completed`.
6. The copied promotion and pipeline eval factories each pass
   `validate_factory.py` after evaluator readiness preparation and before the
   tested promotion or pipeline workflow is invoked.
7. The workflow-eval case count remains `5`.
8. The remediation does not weaken validator evidence-integrity rules to accept
   malformed evaluator-generated pass state.

## Verification

Required verification:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory
python3 tools/run_workflow_eval.py --factory-root /home/orchadmin/project-pack-factory --output json
```

Required implementation-level verification during remediation:

- run `validate_factory.py` against the copied promotion eval factory after
  readiness preparation
- run `validate_factory.py` against the copied pipeline eval factory after
  readiness preparation

Optional diagnostic verification when the workflow eval still fails:

```bash
python3 tools/validate_factory.py --factory-root <copied-workflow-eval-factory> --output json
```

Expected outcomes after remediation:

- the live factory remains valid
- workflow eval completes successfully
- copied workflow-eval factories no longer fail because of self-inflicted
  placeholder evidence mismatches
