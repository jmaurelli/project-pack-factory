# ADF Remote Autonomy Testing Workflow V1

## Purpose

This note records how ADF should test automation and autonomy on `adf-dev`
without drifting into open-ended remote-session babysitting.

The goal is to prove that the staged ADF build-pack on `adf-dev` can run a
bounded real task, emit the right checkpoint artifacts, and resume cleanly
through the PackFactory control plane with minimal human supervision.

This workflow is intentionally small and subject to change. If it does not
help us make ADF more autonomous in a grounded way, we should revise it
quickly instead of scaling it up.

## Core Question

Can Codex on `adf-dev`, driven through the official PackFactory remote path,
continue a real ADF task without us manually watching the shell the whole
time?

## Principles

- Use the existing PackFactory remote control plane, not ad hoc SSH loops.
- Test with a real current ADF task, not only synthetic rehearsal work.
- Keep each run bounded, reviewable, and easy to stop.
- Judge success by continuity quality and useful returned evidence, not by
  runtime length or log volume.
- Preserve local PackFactory state as the current source of truth unless a
  checkpoint bundle explicitly proposes accepted changes.

## Required Control Path

Use the PackFactory-managed path already documented in:

- `docs/specs/adf-remote-runtime-decoupling-plan-v1.md`
- `docs/specs/adf-remote-codex-invocation-notes-v1.md`

That means:

1. prepare or reuse the named remote request for `adf-dev`
2. push the accepted local build-pack state to `adf-dev`
3. launch the bounded remote run through the PackFactory workflow
4. pull checkpoint or completion artifacts back to PackFactory root
5. evaluate the returned state and preserve only accepted changes

## Task Contract Guardrail

Treat `remote active-task continuity` as a completion-oriented workflow, not as
a generic remote progress probe.

That means:

- only use `run_remote_active_task_continuity_test.py` when the current task's
  `validation_commands` are a real completion boundary for that task
- do not use it on broad checkpoint-series tasks whose `validation_commands`
  only prove the pack still validates
- for those broader tasks, prefer the bounded remote autonomy loop plus
  checkpoint review and import, because that keeps the task in progress instead
  of auto-completing it

Current ADF implication:

- `deepen_dependency_aware_playbooks` is a checkpoint-series task, not a
  single-pass completion task
- it should be exercised through bounded remote slices that return accepted
  checkpoint evidence
- a completion-oriented active-task continuity run will naturally mark it done
  after validation commands and branch to the next eligible task, which is not
  the behavior we want for this current content track

## First Test Shape

The first autonomy evaluation should be a bounded remote active-task slice on
`adf-dev` against the current real ADF task, not a synthetic proving-ground
task.

Current recommended candidate for a bounded remote slice:

- `deepen_dependency_aware_playbooks`

Why this is the right first remote-slice test:

- it is a real current pack task
- it already sits behind a clearer shallow support model
- it should be deep enough to need continuity but bounded enough to review

Current caution:

- do not treat it as the right candidate for a completion-oriented
  `active-task continuity` run unless we first split out a smaller task with a
  true completion boundary
- do not treat the raw bounded remote loop as already suitable for this task's
  authoring slices under the current writable-surface contract; the recovered
  March 28 bounded slice still ended with `boundary_violation /
  unauthorized_writable_surface` and returned no export bundle
- use raw bounded remote loops here only when the slice is narrowed enough to
  stay inside the current writable-surface contract, or after a reviewed
  contract change explicitly allows the needed source-authoring surfaces

## Current Contract-Safe Slice Rule

Under the current raw bounded loop contract, the safe remote slice types for
ADF are narrower than general playbook authoring.

Treat the following as contract-safe slice shapes:

- state-only checkpointing in the declared backlog, work-state, readiness, or
  eval latest surfaces
- evidence and checkpoint writing under `eval/history/`
- memory and checkpoint-bundle writing under `.pack-state/`
- candidate or runtime-evidence generation inside the declared output
  directories

Treat the following as contract-change work, not as safe default raw-loop work:

- source edits under `src/`
- note or planning edits under `docs/`
- any broader authoring pass that needs to change operator-facing playbook text
  outside the declared writable surfaces

Current ADF implication:

- for `deepen_dependency_aware_playbooks`, the next raw remote slice should be
  a review, scoring, or checkpoint-writing pass that stays inside those allowed
  surfaces
- if we want the remote loop to author the next playbook checkpoint directly in
  `src/` or `docs/`, we should first review and explicitly widen the contract
  instead of retrying the same bounded raw loop
- if the local controller times out first, do one short delayed pullback retry
  before classifying the run as failed; the remote side may still finish,
  publish `execution-manifest.json`, and export a usable bundle shortly after
- PackFactory now encodes that rule directly in the wrapper path:
  `tools/run_remote_autonomy_test.py` and
  `tools/run_remote_active_task_continuity_test.py` sleep briefly and attempt
  one pullback when `run_remote_autonomy_loop.py` times out at the controller
  layer
- if that first delayed pullback still misses a bundle, the pullback helper now
  gives recovered bundle discovery a bounded extra window before it settles on
  a no-bundle stopped result
- use `PACKFACTORY_REMOTE_EXECUTION_TIMEOUT_SECONDS` when the main remote run
  needs a longer bounded wait than bootstrap, and treat 600 seconds as the
  current reviewed floor for `adf-dev` evidence-only slices

## Test Sequence

### 1. Bounded Remote Slice

Run one bounded remote slice on `adf-dev` for the named current task and
confirm that the remote Codex loop can:

- load the current canonical local state
- continue the named task without manual shell babysitting
- emit a run summary and loop events
- emit feedback memory
- emit or reference an `adf-remote-checkpoint-bundle.json`

### 2. Checkpoint Review

Pull the checkpoint back to PackFactory root and judge whether the returned
bundle is useful enough to resume from without rereading the whole remote run.

Minimum evidence to review:

- run summary
- loop events
- feedback memory
- checkpoint bundle
- any proposed source or state changes

Current caution:

- a run can export a bundle that still lacks the intended
  `adf-remote-checkpoint-bundle.json` handoff artifact even when the remote loop
  stayed inside the writable-surface contract and stopped cleanly
- after the generic checkpoint-writer/export fix, the next quality gap is
  checkpoint usefulness: a returned bundle can now contain the checkpoint
  artifact while still stopping at a meta measurement boundary instead of a
  support-useful evidence boundary

### 3. Restart Continuity

Relaunch or continue from the accepted checkpoint and confirm that the next
run resumes the same trajectory instead of branching into unrelated work.

### 4. Improvement Capture

Record what made the remote run autonomous versus what still required human
intervention. The point is not only to get work done, but to improve the
unattended workflow itself.

## Success Criteria

Treat the test as effective when it does all of the following:

- stays on the named current ADF task
- uses the official PackFactory remote path end to end
- produces a usable checkpoint bundle and restart memory
- returns enough evidence to decide the next step without rereading raw shell
  output
- resumes cleanly after a checkpoint
- gives one plain-language judgment about what should be improved next

## Failure Criteria

Treat the test as a useful failure when any of the following happens and the
reason is preserved clearly:

- the remote run requires manual shell watching to stay on task
- the checkpoint bundle is missing or too weak to support restart
- the remote run returns artifacts but not enough state to judge progress
- restart continuity drifts away from the original task
- the remote run produces raw logs without a supportable next-step judgment

## Evaluation Questions

After each run, answer these questions plainly:

1. Did `adf-dev` continue the intended task with bounded supervision?
2. Did the returned checkpoint make the next decision easier?
3. Could a fresh agent restart from the returned memory and state without
   reconstructing the whole run?
4. What is the highest-value improvement before the next unattended run?

## Current Direction

The current autonomy direction for ADF is:

- keep PackFactory root as orchestrator and canonical state owner
- use `adf-dev` as the normal remote Codex execution home
- test autonomy on real ADF work, one bounded slice at a time
- improve checkpoint, memory, and resume quality after each run
