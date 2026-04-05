# ADF adf-dev remote autonomy continuity evaluation - 2026-03-28

## Purpose

Run the first bounded remote autonomy evaluation on `adf-dev` against the
current real ADF trajectory and judge whether the PackFactory-managed remote
loop can hand back a useful checkpoint without manual shell babysitting.

## Control path

- local PackFactory root
- staged build-pack copy on `adf-dev`
- official PackFactory remote loop wrapper:
  `tools/run_remote_autonomy_loop.py`

## Intended evaluation target

- current autonomy-facing task: `evaluate_adf_dev_remote_autonomy_continuity`
- current real-task candidate for unattended continuation:
  `deepen_dependency_aware_playbooks`

## What happened

- The remote loop initialized correctly and wrote a `run_started` event on
  `adf-dev`.
- The remote Codex process stayed alive until it was manually stopped to let
  the wrapper finalize and reveal the actual result.
- The returned official wrapper result was:
  - `status = stopped`
  - `terminal_outcome = boundary_violation`
  - `terminal_reason = unauthorized_writable_surface`
  - `export_status = not_attempted`

## Useful failure signal

This first real remote autonomy evaluation failed in a useful fail-closed way.
It exposed two concrete problems in the current remote loop contract.

### 1. Prompt scope mismatch

The generated remote invocation prompt still said:

- `Scope: starter backlog only`

That does not match the real current ADF task we were trying to evaluate. The
run was supposed to judge continuity on live pack work, not only starter
backlog behavior.

### 2. Writable-surface mismatch

The returned boundary-violation result named these unauthorized writes:

- `dist/candidates/benchmark-smoke-baseline/runtime-evidence.json`
- `dist/candidates/benchmark-smoke-baseline/service-inventory.json`
- `dist/candidates/benchmark-smoke-baseline/support-baseline.html`
- `dist/candidates/benchmark-smoke-baseline/support-baseline.json`

That means the remote loop's writable-surface allowlist is currently too
narrow for a real ADF run that legitimately uses the existing smoke benchmark
surface.

## Why this is still progress

This evaluation answered the question we actually cared about:

- can `adf-dev` continue a real current ADF task unattended through the
  official PackFactory remote path?

Current answer:

- not yet, because the current remote prompt and writable-surface contract are
  still shaped for starter-backlog proof work, not for real current ADF pack
  work.

That is a strong next-step result, not wasted effort.

## Preserved evidence

- official wrapper result from `tools/run_remote_autonomy_loop.py`
- remote run summary:
  `.pack-state/autonomy-runs/algosec-diagnostic-framework-build-pack-v1-split-host-smoke-run-v1/run-summary.json`
- remote loop events:
  `.pack-state/autonomy-runs/algosec-diagnostic-framework-build-pack-v1-split-host-smoke-run-v1/loop-events.jsonl`
- remote execution manifest:
  `.packfactory-remote/execution-manifest.json`

## Conclusion

The first real `adf-dev` continuity evaluation is complete and preserved.

The next move is not to rerun the same loop unchanged. The next move is to
tighten the remote autonomy contract for real ADF tasks:

- align the remote prompt with real current-task continuation instead of
  starter-backlog-only scope
- allow the bounded benchmark-generated `dist/candidates` artifacts that a
  legitimate ADF run needs
- rerun the same evaluation and confirm that the next result returns a usable
  export bundle and restart-quality checkpoint
