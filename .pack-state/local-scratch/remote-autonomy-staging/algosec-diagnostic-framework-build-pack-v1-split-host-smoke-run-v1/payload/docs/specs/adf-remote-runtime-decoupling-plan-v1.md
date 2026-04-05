# ADF Remote Runtime Decoupling Plan V1

## Purpose

This note defines the current split-host runtime model for ADF.

The goal is to stop assuming that the ADF build-pack runtime must live on the
same Rocky host as the target application.

Runtime host model:
PackFactory root orchestrates a separate Ubuntu 24.04 LTS remote Codex host.
That remote Codex host carries the staged ADF build-pack workspace and runs
the ADF agent runtime. The Rocky target application host remains a separate
system that the remote ADF runtime reaches over the network only when the
named ADF task needs target-backed evidence, browser investigation, or
read-only diagnostic commands.

Current remote Codex host:
Use `adf-dev` as the named remote Codex host for this model. PackFactory root
already has SSH key authentication to `adf-dev`, so that keyed SSH path is the
default control connection for staging, launch, export, pull, and reconcile
work.

Preferred protocol:
Use the PackFactory-managed remote request, staging, execution, export, pull,
import, and reconcile workflow between PackFactory root and the remote Codex
host. Treat SSH plus staged files and exported evidence bundles as the primary
control protocol for the PackFactory root to remote Codex hop. Treat the
remote Codex host to target application hop as task-scoped outbound access
only, using bounded read-only protocols such as SSH, HTTPS, browser
automation, and service-specific diagnostic requests when the current ADF task
requires them.

PackFactory control-plane impact:
PackFactory root stays the owner of orchestration, autonomy memory, evidence
import, readiness, and promotion semantics. The remote Codex host becomes the
live mutable ADF execution workspace. The Rocky target host is never the
PackFactory control-plane primary for ADF state; it is an observed system that
produces runtime evidence through the remote ADF runtime.

## Existing ADF Surfaces To Reuse

The decoupled model should reuse the ADF surfaces that already exist instead
of inventing a second remote-runtime protocol.

Use these existing surfaces first:

- `pack.json.entrypoints.export_runtime_evidence_command`
  as the canonical remote-build-pack export surface
- `src/pack_export_runtime_evidence.py`
  as the bounded exporter for remote run summaries, loop events, and feedback
  memory
- `.pack-state/autonomy-runs/<run-id>/run-summary.json`
  as the primary remote run summary artifact
- `.pack-state/autonomy-runs/<run-id>/loop-events.jsonl`
  as the loop continuity and checkpoint event stream
- `.pack-state/agent-memory/autonomy-feedback-<run-id>.json`
  as the pack-local feedback-memory artifact when a run records one
- `docs/specs/adf-remote-codex-invocation-notes-v1.md`
  as the launcher and remote-session hygiene note for the remote Codex host
- `eval/history/adf-root-build-pack-remote-reconciliation-plan-20260326.md`
  as the current checkpointed-sync model between `Root`, `ADF Build Pack`, and
  `ADF Remote`

The important design choice is:

- keep the loop and target communication close to `ADF Remote`
- keep PackFactory root as the consumer of bounded exported artifacts
- avoid turning PackFactory root into a live socket-level proxy between the
  ADF runtime and the target application host

## Existing PackFactory Remote Communication To Reuse

The split-host ADF design should reuse the PackFactory remote-autonomy control
plane that already exists at the factory root.

Use these factory-level tools and contracts first:

- `tools/prepare_remote_autonomy_target.py`
  validates `remote-autonomy-run-request/v1`, creates the canonical remote
  parent, pack, run, and export directories, and writes
  `.packfactory-remote/request.json`
- `tools/push_build_pack_to_remote.py`
  stages the bounded build-pack payload to the remote host and records the
  PackFactory target manifest for that staged payload
- `tools/run_remote_autonomy_loop.py`
  launches the remote build-pack run inside the staged workspace and records
  the execution-side manifest
- `tools/pull_remote_runtime_evidence.py`
  pulls the staged runtime-evidence bundle and the matching remote manifests
  back to PackFactory root
- `tools/import_external_runtime_evidence.py`
  imports the returned runtime-evidence bundle through the bounded factory
  importer
- `tools/reconcile_imported_runtime_state.py`
  reconciles accepted imported runtime state back into local canonical
  pack-local state

Existing higher-level wrappers already compose those lower-level steps:

- `tools/run_remote_autonomy_test.py`
- `tools/run_multi_hop_autonomy_rehearsal.py`
- `tools/run_autonomy_to_promotion_workflow.py`

This means the current ADF task is not to invent a second transport or a new
remote-session control plane.

The ADF-specific work is narrower:

- define how ADF uses the existing PackFactory request, staging, execution,
  pull, import, and reconcile path
- define what extra ADF review metadata must ride along with that path
- keep the target-facing loop behavior close to `ADF Remote`

In plain language:

- PackFactory already knows how to talk to a remote Codex host
- ADF needs to plug into that path cleanly
- the new ADF checkpoint bundle is extra review metadata, not a replacement
  for PackFactory transport or evidence manifests

## Current `adf-dev` Request Profile

The concrete current request surfaces for the split-host model live under:

- `docs/remote-targets/adf-dev/README.md`
- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `docs/remote-targets/adf-dev/remote-autonomy-test-request.json`

Current field mapping:

- `remote_host = adf-dev`
  names the remote Codex runtime host
- `remote_target_label = adf-dev`
  names the PackFactory remote-runtime side of the roundtrip and drives the
  canonical remote staging path
- downstream AlgoSec appliance identity stays separate from the PackFactory
  run request and remains task context inside ADF docs and runtime behavior

In plain language:

- the PackFactory remote request talks about where Codex runs
- ADF task context still talks about which appliance the remote runtime is
  investigating

## Topology

The split is now:

1. `Root`
   PackFactory control plane and canonical accepted pack state.
2. `ADF Remote`
   remote Ubuntu Codex host that runs the staged ADF build pack.
3. `ADF Target`
   separate Rocky application server that the remote ADF runtime inspects.

In plain language:

- `Root` talks to `ADF Remote`.
- `ADF Remote` hosts the ADF build-pack runtime.
- `ADF Remote` talks to `ADF Target` when the task needs real appliance-backed
  evidence.
- `Root` does not need to run the ADF build-pack runtime on `ADF Target`.
- `ADF Remote` currently means the keyed SSH host `adf-dev`.

## Current Precedence Rule

The current source-of-truth precedence is explicit:

- the local ADF build pack in PackFactory takes precedence over the remote ADF
  build-pack copy on `adf-dev`
- the remote ADF build-pack copy on `adf-dev` is the live execution workspace,
  not the current canonical build-pack home

In plain language:

- `adf-dev` is where the runtime runs
- PackFactory root is still where accepted build-pack truth lives today

That means:

- if the local PackFactory build pack and the remote `adf-dev` build pack
  disagree, the local PackFactory copy wins until a later explicit canonical
  mode change says otherwise
- remote task progress, remote file edits, or remote generated artifacts do not
  outrank the local build-pack copy only because they were produced on
  `adf-dev`
- PackFactory root may consume remote evidence and accepted remote progress,
  but it still decides what becomes canonical

## Ownership Model

### Root Owns

`Root` remains the authority for:

- PackFactory request, staging, execution, export, pull, import, and reconcile
  workflows
- autonomy-memory semantics and activation
- readiness and promotion control-plane decisions
- accepted checkpoint state in local `status/work-state.json`,
  `tasks/active-backlog.json`, and related PackFactory surfaces
- preserved evidence and audit trails after import

### ADF Remote Owns

`ADF Remote` becomes the live ADF working copy for:

- active Codex execution
- mutable pack-local source and docs work during a remote run
- local launcher scripts, prompt files, result files, and intermediate logs
- target-facing investigation steps that need proximity to the target network
  or target browser path
- temporary generated artifacts before they are accepted and pulled back
- the local web server that publishes generated human-facing content from the
  staged build-pack workspace

### ADF Target Owns

`ADF Target` owns only target runtime reality:

- application state
- service behavior
- logs and browser-visible behavior
- runtime evidence gathered during a task

`ADF Target` does not become canonical for:

- backlog state
- PackFactory memory state
- readiness state
- promotion state
- accepted ADF source truth

## Communication Contract

### Root To ADF Remote

Use the PackFactory-root remote workflow as the only supported control path.

That path should:

- prepare `ADF Remote` through `tools/prepare_remote_autonomy_target.py`
- restage the accepted build-pack workspace through
  `tools/push_build_pack_to_remote.py`
- launch remote Codex from the staged workspace through
  `tools/run_remote_autonomy_loop.py` or a higher-level PackFactory wrapper
- collect the PackFactory target manifest, execution manifest, exported
  runtime-evidence bundle, and returned artifacts
- pull accepted changes or evidence back through
  `tools/pull_remote_runtime_evidence.py`
- import and reconcile returned runtime state through
  `tools/import_external_runtime_evidence.py` and
  `tools/reconcile_imported_runtime_state.py`
- update local canonical state only after bounded review or import

### ADF Remote To ADF Target

Treat the ADF runtime on `ADF Remote` as the primary agent that talks directly
to `ADF Target` during this model.

That hop is allowed to:

- open SSH sessions for read-only diagnostics
- run browser-backed checks against the target UI
- collect target logs and runtime evidence
- generate target-backed candidate artifacts inside the remote staged pack

That hop should not:

- mutate PackFactory root state directly
- bypass the accepted ADF task boundary
- assume the target host is also the persistent build-pack working copy

Direct `adf-dev -> target` access remains the default path. A secondary
delegated path may use target-local Codex on `ADF Target`, but only under the
bounded rules below.

### ADF Remote Runtime Contract

The ADF runtime on `adf-dev` should treat the staged build-pack root as the
live working packet for one remote execution slice.

That runtime may:

- run pack-local baseline generation commands
- run pack-local Starlight generation commands
- write generated artifacts under `dist/candidates/`
- write loop state and checkpoint artifacts under `.pack-state/`
- serve generated human-facing content from the staged build-pack root
- open task-scoped outbound connections from `adf-dev` to `ADF Target`

That runtime should not:

- mutate PackFactory registry or deployment state
- treat `ADF Target` as the working copy for the build pack
- bypass the PackFactory pull, import, and reconcile path
- assume the current bounded starter-backlog runner already authorizes all ADF
  source-authoring tasks

### Generated Content Service Contract

As part of the staged build pack on `adf-dev`, ADF should serve the human-facing
content it generates.

Preferred local serving rule:

- first preference: serve a built static site from
  `dist/candidates/<target>/starlight-site/dist/` when it exists
- fallback: serve the selected candidate artifact root directly
- when serving the candidate artifact root without an `index.html`, route `/`
  to `support-baseline.html`

Preferred command surface:

- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack serve-generated-content ...`

Default bind:

- `host = 0.0.0.0`
- `port = 18082`

Why this matters:

- the remote ADF runtime can publish operator-facing content from `adf-dev`
  immediately after generation
- PackFactory does not need to proxy the generated site itself
- the content server stays close to the generated artifact root and the
  target-backed evidence used to create it

### `ADF Remote` To `ADF Target` Connection Contract

The `adf-dev` runtime is the component that keeps target-facing connectivity
alive during a run.

Use this contract:

- maintain SSH, HTTPS, browser, and service-specific target sessions on
  `adf-dev`, not on `Root`
- prefer the existing key-based SSH path from `adf-dev` to `ADF Target`;
  do not invent password prompts or store secrets in PackFactory state
- keep target access read-only by default
- preserve target-backed generated artifacts under `dist/candidates/`
- record target communication failures, retries, and recovery points in
  `loop-events.jsonl`
- keep the generated content server independent from the target session so the
  current operator view can stay reachable even if the target later degrades

Target shell nuance:

- the current AlgoSec appliance can drop into an interactive menu on login
- target-facing shell commands should prefer a non-login shell pattern such as
  `env -i ... /bin/bash --noprofile --norc`
- if a task needs a multi-step target-side shell action, prefer a small
  bounded launcher script over long inline SSH quoting
- treat those menu-bypass rules as part of the normal `adf-dev -> target`
  execution contract, not as one-off debugging trivia

Current pack-local helper surfaces for that hop:

- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-preflight ...`
- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-heartbeat ...`
- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-shell-command ...`

Current default profile:

- `docs/remote-targets/algosec-lab/target-connection-profile.json`

### Target-Local Codex Delegation Mode

Use target-local Codex only as a secondary execution mode when direct
`adf-dev -> target` crawling is too slow, too noisy, or too awkward for a task
slice that needs many local reads on the appliance.

This mode is useful when:

- the task needs many local file, log, service, or process inspections
- direct SSH command fan-out from `adf-dev` would create too much transport
  overhead
- the target-side Codex installation can gather evidence more naturally than a
  long sequence of remote shell calls

This mode does not change the primary split-host rule:

- `adf-dev` still owns the ADF runtime
- `adf-dev` still hosts the generated-content server
- `adf-dev` still owns checkpoints, review, and pullback to PackFactory root
- `ADF Target` still does not become the canonical build-pack home

Use this fail-closed boundary:

- `adf-dev` decides when a bounded task slice is delegated
- target-local Codex may gather evidence and synthesize task results for that
  slice
- target-local Codex must return its results to `adf-dev`
- `adf-dev` reviews, checkpoints, and exports the returned evidence before
  anything flows back to PackFactory root

Target-local Codex should not:

- act as the primary long-running ADF loop owner
- host the ADF web server
- mutate PackFactory root state
- become the only copy of task progress or loop state
- silently widen its task scope beyond the delegated slice

Preferred first-pass return shape:

- target-local Codex writes bounded result artifacts for the delegated slice
- `adf-dev` pulls those artifacts back over the existing SSH-based path
- `adf-dev` records the delegation event, returned evidence paths, and review
  outcome in the local checkpoint bundle

### Delegation Tiers

Because `ADF Target` is a disposable lab environment under operator control,
the delegated mode can support both observation and bounded experimentation.

Use these tiers:

- `observe_only`
- `guided_change_lab`

#### `observe_only`

Use `observe_only` when the delegated slice needs local inspection on the
target but should not intentionally change target state.

Allowed behavior:

- read files, logs, configs, service state, and process state
- run local shell commands for diagnostics
- inspect browser or HTTP-visible state when needed
- synthesize findings and collect bounded evidence artifacts

Not allowed:

- intentional config edits
- intentional package or binary changes
- intentional service restarts except when a read-only status command implies
  a harmless refresh

#### `guided_change_lab`

Use `guided_change_lab` only because the target is a lab appliance and the
operator can redeploy it quickly.

Allowed behavior:

- make bounded local changes needed for a delegated experiment
- restart services
- rerun checks after the change
- compare before and after evidence
- leave explicit rollback or redeploy notes when the slice does not restore the
  original state

Required guardrails:

- the delegated request must say that mutation is allowed for this slice
- the delegated result must declare every intentional target mutation
- `adf-dev` must treat the returned result as lab evidence, not silent baseline
  truth
- if the slice leaves the target in a changed state, that must be called out in
  the checkpoint bundle and operator-facing summary

In plain language:

- `observe_only` is the safe default
- `guided_change_lab` is the faster lab-only experiment mode
- both still report back to `adf-dev`

### Delegated Result Bundle Contract

The first delegated return path should stay simple and auditable.

Preferred remote bundle root on `ADF Target`:

- `.pack-state/delegated-codex-runs/<delegation-run-id>/`

Preferred bundle contents:

- `delegated-task-request.json`
- `delegated-task-result.json`
- `commands.jsonl`
- `findings.md`
- `artifacts/`
- `candidate-diffs/` only when the delegated tier explicitly allows changes to
  staged files or generated content

Minimum `delegated-task-request.json` fields:

- `delegation_run_id`
- `task_id`
- `delegation_tier`
- `scope_summary`
- `allowed_targets`
- `expected_outputs`
- `time_budget_seconds`

Minimum `delegated-task-result.json` fields:

- `delegation_run_id`
- `task_id`
- `delegation_tier`
- `status`
- `summary`
- `returned_artifact_paths`
- `intentional_mutations`
- `follow_up_recommendations`

Default review rule:

- `adf-dev` pulls the whole delegated bundle back over the existing SSH path
- `adf-dev` validates the expected bundle shape before trusting the contents
- `adf-dev` records the delegated run id, tier, result status, and artifact
  paths in `adf-remote-checkpoint-bundle.json`
- a missing command log, missing result file, or undeclared mutation should
  fail the delegated slice closed

In plain language:

- direct SSH from `adf-dev` stays the baseline
- target-local Codex is the helper when target-local crawling is the better
  way to inspect the system
- `adf-dev` stays in charge

### Checkpoint And Return Contract

When a remote slice on `adf-dev` reaches a named checkpoint, it should return
all of these through the existing PackFactory control plane:

- run-summary and loop-events evidence
- the ADF checkpoint bundle
- candidate source or docs changes, if any
- candidate generated artifacts under `dist/candidates/`
- generated-content serving metadata for the current slice

The serving metadata should identify at least:

- the selected serving root
- the serving mode
- the host and port
- the default entry path

That serving metadata may live inside the ADF checkpoint bundle as
supplementary review metadata.

When target-local Codex delegation is used, the checkpoint bundle should also
record:

- `delegation_run_id`
- `delegation_tier`
- `delegated_result_status`
- `delegated_bundle_root`
- `delegated_bundle_review_outcome`
- `intentional_mutations`

### Evidence Return Path

The return path is:

1. gather target-backed evidence on `ADF Remote`
2. preserve it in the staged ADF workspace or export bundle on `ADF Remote`
3. use PackFactory-root pull and import workflows to move accepted evidence
   back to `Root`
4. reconcile local canonical state only after the accepted checkpoint boundary
   is chosen

When target-local Codex is used for one delegated slice, insert this bounded
subpath inside step 1:

1. `adf-dev` writes the delegated task request
2. target-local Codex performs the bounded slice on `ADF Target`
3. target-local Codex writes the delegated result bundle on `ADF Target`
4. `adf-dev` pulls that bundle back, reviews it, and records the result in the
   checkpoint bundle

## Local To `adf-dev` Checkpoint Contract

This section defines the exact current sync rule between the local PackFactory
build-pack copy and the remote runtime workspace on `adf-dev`.

### Current Authority Rule

Until a later explicit remote-canonical mode change is recorded:

- local PackFactory is the canonical accepted build-pack copy
- `adf-dev` is the live runtime workspace
- `adf-dev` does not overwrite local PackFactory state automatically

### Push To `adf-dev`

Use a bounded restage from local PackFactory to `adf-dev` before a remote run
when one of these is true:

- accepted local source changed
- accepted local docs changed
- accepted local task instructions changed
- the remote workspace needs to be reset to a known local checkpoint

The local-to-remote push should normally carry:

- accepted ADF source under `src/`
- accepted ADF docs under `docs/`
- accepted prompts and pack metadata needed for execution
- accepted `contracts/project-objective.json`
- accepted `tasks/active-backlog.json`
- accepted `status/work-state.json`
- PackFactory-owned runtime helper surfaces that ship with the build pack

The local-to-remote push should not blindly carry:

- `status/readiness.json`
- `eval/latest/index.json`
- `.pack-state/agent-memory/latest-memory.json`
- imported runtime-evidence artifacts that are only local audit records
- local-only experimental generated outputs that were not selected for the
  remote run

In plain language:

- push accepted local logic and instructions to `adf-dev`
- do not push generated control-plane leftovers just because they exist locally

### What `adf-dev` Produces

During a run, `adf-dev` is expected to produce:

- mutable remote source or docs changes when the task is an authoring task
- target-backed generated artifacts
- `.pack-state/autonomy-runs/<run-id>/run-summary.json`
- `.pack-state/autonomy-runs/<run-id>/loop-events.jsonl`
- optional `.pack-state/agent-memory/autonomy-feedback-<run-id>.json`
- optional exported runtime-evidence bundles under
  `dist/exports/runtime-evidence/`

Those outputs are candidates for acceptance, not automatic truth.

### Pull Back From `adf-dev`

Use a bounded pull from `adf-dev` to local PackFactory only at a named
checkpoint.

Named checkpoints are:

- remote run paused for operator review
- remote run completed a bounded task slice
- remote run produced target-backed evidence worth preserving
- remote run hit a blocked boundary that must be recorded locally
- local PackFactory needs a recovery snapshot from the live remote workspace

The default pull order is:

1. pull exported runtime evidence or the raw run summary and loop artifacts
2. review whether the remote run changed accepted ADF source or docs
3. review whether any remote-generated artifact should be preserved as accepted
   output
4. update local canonical state only after the accepted checkpoint bundle is
   explicit

### Safe Pull Categories

These are normally safe to pull and review first:

- exported runtime-evidence bundles
- `run-summary.json`
- `loop-events.jsonl`
- feedback-memory artifacts
- target-backed generated artifacts selected for review

These are pull-with-review surfaces:

- `src/`
- `docs/`
- `tasks/active-backlog.json`
- `status/work-state.json`

These are regenerate-or-import surfaces, not blind copy surfaces:

- `status/readiness.json`
- `.pack-state/agent-memory/latest-memory.json`
- `eval/latest/index.json`

### Acceptance Rule

Remote output from `adf-dev` becomes locally accepted only when the checkpoint
bundle names all of these:

- accepted run or checkpoint id
- accepted `status/work-state.json` boundary
- accepted `tasks/active-backlog.json` boundary when it changed
- accepted remote source/docs changes, if any
- accepted target-backed artifact provenance, if any
- which generated control-plane files must be regenerated locally afterward

If that bundle is missing, local PackFactory keeps precedence and the pulled
remote material stays review evidence rather than accepted truth.

### Checkpoint Bundle Format V1

The checkpoint bundle should be one explicit machine-readable manifest that
describes what `adf-dev` is proposing back to local PackFactory.

Recommended manifest name:

- `adf-remote-checkpoint-bundle.json`

Recommended current remote location:

- `.pack-state/autonomy-runs/<run-id>/adf-remote-checkpoint-bundle.json`

Recommended exported copy location when a runtime-evidence bundle is emitted:

- `dist/exports/runtime-evidence/<export-id>/artifacts/adf-remote-checkpoint-bundle.json`

Recommended authority:

- this manifest is review metadata
- it does not become canonical control-plane truth by itself
- it tells PackFactory root what the remote run is asking to preserve or accept

Recommended v1 shape:

- `schema_version = adf-remote-checkpoint-bundle/v1`
- `pack_id`
- `remote_host`
- `remote_target_label`
- `remote_build_pack_root`
- `checkpoint_id`
- `run_id`
- `checkpoint_reason`
- `generated_at`
- `generated_by`
- `source_of_truth_mode`
- `local_precedence = true | false`
- `export_bundle`
- `run_artifacts`
- `candidate_changes`
- `proposed_acceptance`
- `local_regeneration_required`

#### Required Top-Level Meaning

- `pack_id`
  the target build-pack id
- `remote_host`
  the current remote runtime host, which is `adf-dev` in the current phase
- `remote_target_label`
  the named downstream target environment for the run
- `remote_build_pack_root`
  the remote staged build-pack root used by the run
- `checkpoint_id`
  a unique id for this proposed checkpoint
- `run_id`
  the associated remote loop run id
- `checkpoint_reason`
  for example:
  `paused_for_review | task_slice_complete | evidence_ready | blocked_boundary | recovery_snapshot`
- `source_of_truth_mode`
  for example:
  `local_precedence_split_host`
- `local_precedence`
  whether local PackFactory still wins by default for this checkpoint

#### `export_bundle`

This object points to the bounded exported runtime-evidence bundle when one
exists.

Recommended fields:

- `present`
- `bundle_manifest_path`
- `bundle_sha256`
- `authority_class`
- `import_ready`

In the current phase:

- `authority_class` should remain supplementary runtime evidence
- `import_ready` should be `true` only when the exported bundle already matches
  the PackFactory import contract

#### `run_artifacts`

This object names the direct remote run artifacts that explain the loop
boundary.

Recommended fields:

- `run_summary_path`
- `loop_events_path`
- `feedback_memory_path`
- `result_log_paths`
- `target_artifact_paths`

These are evidence references first, not acceptance decisions.

#### `candidate_changes`

This object lists the remote state that changed and is being proposed for
review.

Recommended fields:

- `source_paths`
- `doc_paths`
- `prompt_paths`
- `work_state_fields`
- `backlog_task_updates`
- `artifact_paths`

The key distinction is:

- `source_paths`, `doc_paths`, and `artifact_paths` point to concrete changed
  files
- `work_state_fields` and `backlog_task_updates` are field-level proposals, not
  a whole-file replacement request

Recommended `work_state_fields` shape:

- list of objects with:
  - `field_path`
  - `remote_value_summary`
  - `acceptance_reason`

Recommended `backlog_task_updates` shape:

- list of objects with:
  - `task_id`
  - `current_local_status`
  - `proposed_remote_status`
  - `acceptance_reason`

#### Emission Location And Timing

The remote loop on `adf-dev` should write the checkpoint manifest into the run
root first.

Current write target:

- `.pack-state/autonomy-runs/<run-id>/adf-remote-checkpoint-bundle.json`

Reason:

- this keeps the checkpoint manifest beside `run-summary.json` and
  `loop-events.jsonl`
- the remote loop can update it without needing an export step to complete
- PackFactory root can still pull the raw run-root checkpoint if export fails

When the run also emits a runtime-evidence export bundle, that same checkpoint
manifest should be copied into the exported bundle under:

- `artifacts/adf-remote-checkpoint-bundle.json`

This keeps the exported bundle self-describing for later review.

#### Required Emit Events

For the current phase, the remote loop should emit or refresh the checkpoint
manifest whenever one of these events happens:

- `paused_for_review`
- `task_slice_complete`
- `evidence_ready`
- `blocked_boundary`
- `recovery_snapshot`

These event names should also be used as the allowed v1 values for
`checkpoint_reason`.

#### Optional Refresh Events

The loop may also refresh the checkpoint manifest on lower-level internal
progress points, but those refreshes are advisory only and do not by
themselves justify a pull.

Examples:

- target connection recovered after a transient failure
- browser session was re-established
- a long-running target investigation crossed an internal milestone

Those advisory refreshes should still preserve the latest named checkpoint
reason that justifies the current pull boundary.

#### Emit-Minimum Rule

Every required checkpoint emission should include at least:

- the current `run_id`
- the current `checkpoint_id`
- the required `checkpoint_reason`
- the current `run_summary_path`
- the current `loop_events_path`
- the current local-precedence mode fields
- the current candidate-change lists, even if they are empty
- the current proposed-acceptance lists, even if they are empty

That rule keeps the manifest usable even when the run stopped because of a
boundary or remote-target failure rather than a clean task completion.

#### `proposed_acceptance`

This object is the remote run's explicit ask to local PackFactory.

Recommended fields:

- `accept_source_paths`
- `accept_doc_paths`
- `accept_artifact_paths`
- `accept_work_state_fields`
- `accept_backlog_task_updates`
- `defer_paths`
- `defer_fields`
- `notes`

This section should make it easy for local PackFactory to say:

- accept these parts
- defer these parts
- regenerate these parts locally

#### `local_regeneration_required`

This object lists the generated local surfaces that should be refreshed after
acceptance.

Recommended fields:

- `readiness`
- `latest_memory_pointer`
- `eval_latest_index`
- `other_generated_surfaces`

This keeps generated control-plane files from being copied blindly from
`adf-dev`.

### Relationship To Existing PackFactory Manifests

The ADF checkpoint bundle does not replace the PackFactory manifests that
already govern the remote roundtrip.

It supplements them.

The existing PackFactory truth surfaces for the remote roundtrip are still:

- `remote-autonomy-run-request/v1`
  for the requested remote coordinates, run id, and source build-pack identity
- the remote target manifest written by PackFactory staging
  for the exact staged payload identity
- `remote-execution-manifest/v1`
  for remote execution status and same-run export linkage
- the exported runtime-evidence bundle manifest
  for the bounded returned artifact set
- the external-runtime-evidence import report
  for the local import audit record
- the imported-runtime-state reconcile report
  for accepted local canonical-state updates

The ADF-specific `adf-remote-checkpoint-bundle.json` should be treated as:

- review metadata that explains what the ADF run wants local PackFactory to
  accept
- a map from ADF loop state to the existing PackFactory roundtrip artifacts
- supplementary evidence that must agree with the existing PackFactory
  manifests rather than override them

If the ADF checkpoint bundle and the PackFactory manifests disagree, fail
closed and keep the existing PackFactory manifests as the stronger transport
and audit record.

### Current V1 Review Rule

For the current phase, local PackFactory should accept a checkpoint bundle only
if all of these are true:

- `remote_host = adf-dev`
- `source_of_truth_mode = local_precedence_split_host`
- `local_precedence = true`
- the bundle was emitted at one of the required checkpoint reasons
- the run artifacts match the associated remote run id
- any exported bundle still passes the existing runtime-evidence import rules
- any proposed work-state or backlog update is field-level and explicit

If one of those conditions is missing, the checkpoint bundle is still useful as
review evidence, but it is not enough to justify local acceptance by itself.

### Conflict Rule

If local PackFactory and `adf-dev` disagree at checkpoint time:

- local PackFactory still wins by default
- remote state is reviewed as candidate evidence
- only the explicitly accepted fields or artifacts may replace local state

Do not:

- copy remote `status/work-state.json` wholesale over local
- copy remote `tasks/active-backlog.json` wholesale over local
- let a remote-generated pointer file replace a local canonical pointer without
  a named acceptance decision

### Remote Failure Recovery Rule

If `adf-dev` drifts, disconnects, or loses the working copy:

- local PackFactory remains the recovery baseline
- restage from the last accepted local checkpoint
- then re-import or preserve any remote evidence artifacts that were exported
  before failure

This is one reason local precedence remains in place for the current phase.

## Connection Consistency Requirements

The remote-build-pack to target-host hop needs to be stable enough for guided
loops, not just one-off command launches.

Use these consistency rules:

- keep the long-running ADF loop on `ADF Remote`, not on `Root`
- let `ADF Remote` hold the target-facing session state, browser state, and
  task-local retries
- treat `Root` as orchestration and consumption, not as the component that
  keeps the target session alive step by step
- checkpoint loop progress into `run-summary.json`, `loop-events.jsonl`, and
  feedback memory on `ADF Remote`
- export those artifacts through the existing runtime-evidence export path when
  the run reaches a bounded checkpoint, pause point, or end state

In plain language:

- the loop should survive normal target communication noise without forcing the
  whole PackFactory root workflow to stay attached continuously
- the remote build pack should do the target talking
- PackFactory root should consume the remote results

### Connection Stability Specification V1

For the current split-host phase, `adf-dev -> ADF Target` must be designed as
a stable loop transport rather than as a one-shot operator shell.

The stability target is:

- no interactive auth prompts during a normal loop
- no dependency on one fragile long-lived login shell to keep the run alive
- no silent hang at the target-menu boundary
- bounded detection of loss, recovery, and degraded target reachability
- clear checkpoint and retry behavior when the target becomes unstable

#### Stability Rules

Use these rules for the `adf-dev -> target` hop:

- authentication must be key-based and non-interactive
- target commands must fail closed rather than waiting forever for prompts,
  passphrases, or menu input
- target shell work must prefer non-login shell launch patterns over login
  shells
- each target interaction must run under a bounded timeout
- retries must happen on `adf-dev`, not by asking `Root` to restage for every
  transient issue
- the loop should rely on short-lived recoverable target actions more than one
  monolithic shell session
- the generated-content server on `adf-dev` must remain independent from the
  current target session so the operator view does not disappear when target
  connectivity degrades

#### No-Hang Rule

The runtime should treat hanging target access as a contract failure, not as a
normal waiting state.

Specifically:

- no target-facing SSH command should depend on a login shell that can fall
  into the interactive appliance menu
- no target-facing command should wait indefinitely for stdin
- no browser wait should depend on `networkidle` when the target UI is known to
  keep background activity alive
- no loop slice should stay uncheckpointed while waiting forever on one target
  action

If the target reaches a non-progress state, `adf-dev` should:

- stop the affected action with a bounded timeout
- record the failure in `loop-events.jsonl`
- classify it as transient retry, blocked boundary, or recovery snapshot
- keep the larger remote loop alive when the failure is recoverable

#### Preflight Requirements

Before a loop slice starts, `adf-dev` should confirm all of these:

- SSH key authentication to the target works without an interactive prompt
- the target shell can be reached through the non-login shell pattern
- the target identity used for the slice matches the intended appliance
- the task's first required protocol is reachable from `adf-dev`
- the local export and checkpoint paths on `adf-dev` are writable
- the generated-content serving root is still available if the slice depends on
  previously generated content

#### Heartbeat And Reachability Rules

While the loop is active, `adf-dev` should keep one lightweight reachability
signal separate from the heavier investigation steps.

Preferred shape:

- a small SSH or HTTPS reachability check before a new target-heavy step
- a fresh reachability check after a transient failure before resuming
- a recorded loop event whenever target reachability changes state

The goal is:

- do not assume the target is healthy only because a prior step succeeded
- do not rerun a full investigative slice just to learn that the target is
  still unreachable

#### Timeout And Retry Rules

Use bounded retry rather than indefinite persistence.

Current v1 expectation:

- each target action has an explicit timeout
- transient failures may be retried from `adf-dev` a small bounded number of
  times
- if the same failure persists past the bounded retry window, stop at a named
  boundary and checkpoint the state
- recovery should resume from the latest valid checkpoint rather than replaying
  the full loop blindly

In plain language:

- retry a little
- checkpoint quickly
- stop clearly when the target is still unhealthy

#### Session Ownership Rules

To keep the connection solid enough for loops:

- `adf-dev` owns SSH session setup, bounded retries, browser session state, and
  target command timing
- `Root` owns orchestration, pullback, import, and acceptance
- `ADF Target` should never be the only place where loop state lives

That means the loop can lose one target session without losing the whole run.

#### Browser Stability Rules

For browser-backed target investigation:

- hold browser state on `adf-dev`
- use fresh browser contexts when a prior context becomes suspect
- prefer visible-shell success markers over `networkidle` on known noisy pages
- treat browser-session recovery as a normal recoverable event and record it in
  loop evidence

#### Checkpoint Expectations For Connection Events

The connection contract should produce checkpoints for connection-state changes,
not only for task completion.

At minimum, emit or refresh checkpoint state when:

- target reachability is lost
- target reachability is restored after a transient failure
- a bounded retry budget is exhausted
- a browser session is re-established
- the loop chooses a blocked boundary because stable target access is not
  available

Those events should still map back to the existing named checkpoint reasons in
the current ADF checkpoint bundle contract.

### Minimum Reliable Loop Contract

Before a remote loop starts, `ADF Remote` should confirm:

- the staged build-pack workspace is present and writable
- the target host identity and connection material are present
- the chosen target protocol for the task is reachable
- the export path for bounded runtime evidence is still available

During the loop, `ADF Remote` should:

- record meaningful loop events when the target becomes unreachable, recovers,
  or forces a bounded stop
- prefer bounded retry and resume on `ADF Remote` over relaunching from
  `Root` for every transient target issue
- keep task-level target access read-only unless a later ADF task explicitly
  approves a controlled lab mutation
- keep target command execution bounded so a single hanging call does not stall
  the whole loop indefinitely

After the loop, `Root` should:

- consume the exported run summary, loop events, and feedback memory
- import or reconcile accepted runtime evidence through PackFactory workflows
- update canonical local state only after the accepted checkpoint is clear

## Final Target Mode

This decoupling plan now has an explicit long-horizon target mode.

The final target is:

- the remote build pack becomes the canonical ADF runtime home
- PackFactory root becomes the remote orchestrator and agent-runtime consumer
- `Root` consumes exported remote runtime evidence, loop summaries, memory
  artifacts, and accepted checkpoint decisions instead of trying to behave like
  a minute-by-minute live twin

That future mode is stronger than the current checkpointed-sync baseline.

For now:

- `Root` still holds canonical accepted control-plane state
- `ADF Remote` is the active mutable working copy
- the local PackFactory build pack takes precedence over the remote `adf-dev`
  copy

Later, when the source-of-truth mode is explicit enough, the promotion path is:

1. prove the remote build-pack loop can communicate with the target host
   reliably over repeated runs
2. prove the existing export surfaces are enough for PackFactory root to
   consume remote run state without hidden shell coupling
3. define the canonical remote-managed mode explicitly instead of inferring it
   from remote activity alone
4. only then let `ADF Remote` become the canonical build-pack home and keep
   PackFactory root in the orchestrator-and-consumer role

The explicit transition rule is:

- do not treat `adf-dev` as the canonical build-pack home until a later named
  source-of-truth change says the remote build pack now outranks the local
  PackFactory copy

The key guardrail is:

- remote activity does not become canonical only because it happened
- remote activity becomes canonical when the remote export, checkpoint, and
  source-of-truth rules say it is accepted

## Credential And Boundary Model

The split-host model needs explicit credential ownership.

Current decision:

- `Root` needs credentials and connection material for `ADF Remote`
- `ADF Remote` needs the task-scoped credentials, requests, or session
  material required to reach `ADF Target`
- `ADF Target` should not need inbound PackFactory-root credentials for the
  normal guided ADF workflow

Current connection detail:

- the `Root` to `ADF Remote` hop uses the existing SSH key authentication path
  to `adf-dev`

This keeps the boundary simple:

- `Root` manages the remote Codex host
- `ADF Remote` manages target-facing execution
- `ADF Target` remains the observed application system

## Source-Of-Truth Decision

The split-host model does not change the current checkpointed-sync rule.

Use this state model:

- `Root` is the canonical accepted ADF control-plane state
- `ADF Remote` is the active mutable runtime workspace while reachable
- `ADF Target` is the runtime evidence source, not the pack-state source of
  truth

That means accepted remote progress still becomes canonical only after a
bounded checkpoint, import, or explicit reconciliation decision.

## Supported Modes After This Plan

This note makes the mode decision explicit enough for later work:

- `local`
  ADF runs locally inside the PackFactory workspace only
- `remote-managed`
  ADF runs on one remote host that is also the effective target context
- `split-host remote-managed`
  PackFactory root orchestrates a remote Codex host, and that remote Codex
  host reaches a different target application host over the network

Current ADF planning target:

- `split-host remote-managed`

## What This Plan Does Not Approve

This plan does not approve:

- direct PackFactory-root minute-by-minute mirroring of the remote workspace
- treating the Rocky target as the default Codex runtime host
- broad PackFactory-wide redesign before ADF proves this bounded pattern
- hidden credential sharing between `Root`, `ADF Remote`, and `ADF Target`
- uncontrolled direct writes from `Root` into target application state

## Immediate Consequence For ADF

Future remote ADF investigation should assume:

- the remote Codex host is the place where the ADF build-pack runtime lives
- the current remote Codex host is `adf-dev`
- the target application host is a separate downstream evidence surface
- PackFactory-root workflows remain the only supported orchestration path
- the existing runtime-evidence export path is the default way to hand remote
  loop state back to PackFactory root
- target-backed artifact refresh should happen through `ADF Remote`, then flow
  back to `Root` through bounded PackFactory workflows
- the local PackFactory build pack remains the current precedence copy until a
  later explicit remote-canonical source-of-truth decision is recorded

This keeps the remote runtime model aligned with the checkpointed
reconciliation model and the existing PackFactory control-plane rules.
