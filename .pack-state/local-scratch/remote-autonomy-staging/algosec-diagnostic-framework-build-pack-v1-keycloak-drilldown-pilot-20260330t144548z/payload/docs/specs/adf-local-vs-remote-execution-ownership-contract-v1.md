# ADF Local Vs Remote Execution Ownership Contract V1

## Purpose

This note defines how ADF should split execution ownership between Local
PackFactory and the ADF agent running on `adf-dev`.

The goal is to make local-versus-remote ownership explicit instead of
accidental.

This contract is meant to help PackFactory grow remote autonomy without losing
canonical planner control, accepted evidence discipline, or the ability to
increase or decrease remote scope later.

## Goal

The current transition goal is:

- move bounded ADF project-goal and objective execution toward the ADF agent on
  `adf-dev`
- keep Local PackFactory as the canonical planner, canonical evidence accepter,
  and canonical source-of-truth owner

In plain language:

- Local PackFactory decides what is officially true
- `adf-dev` does the bounded work
- the target lab supplies runtime facts

## Why This Contract Exists

Without this contract:

- remote execution can drift into a second control plane
- local and remote state ownership can become ambiguous
- longer `adf-dev` runs can expand accidentally instead of intentionally
- PackFactory can lose clarity about what must come back before a result is
  accepted

With this contract:

- PackFactory can grow or shrink remote autonomy deliberately
- `adf-dev` can run longer bounded ADF work without guessing what it owns
- returned bundles can be judged against one explicit acceptance rule

## Current Mode

Current mode is:

- Local PackFactory = canonical control plane
- `adf-dev` = default bounded execution agent
- target lab = runtime evidence source

Current autonomy level is:

- `L1_local_canonical_remote_execution`

Meaning:

- Local PackFactory remains canonical for planning, readiness, memory, and
  evidence acceptance
- `adf-dev` may execute bounded ADF tasks and return checkpoint proposals
- no remote result becomes canonical without explicit local acceptance

This contract does not declare remote-canonical mode.

Until a later reviewed mode change is accepted:

- local planner state stays canonical
- local readiness state stays canonical
- local memory pointer stays canonical
- local evidence acceptance stays canonical

## Autonomy Levels

ADF autonomy should be managed through explicit levels, not informal drift.

### L0 Local-Only

- Local PackFactory executes the task directly
- `adf-dev` may be used only as a passive review or serving surface
- no remote execution ownership is assumed

### L1 Local Canonical, Remote Execution

- this is the current default mode
- Local PackFactory remains canonical
- `adf-dev` executes bounded tasks and returns checkpoint proposals
- the target lab remains the runtime evidence source

### L2 Local Canonical, Remote Multi-Checkpoint Execution

- Local PackFactory remains canonical
- `adf-dev` may continue across multiple bounded checkpoints in one run
- remote continuation is allowed only when checkpoint quality and restart
  continuity meet the reviewed promotion criteria

### L3 Selected Remote-Canonical Surfaces

- only specifically named surfaces may become remote-canonical
- Local PackFactory still owns registry, deployment, promotion, and final
  PackFactory truth
- this level requires an explicit reviewed mode-change artifact and is not
  implied by a successful long run

Allowed default transitions:

- `L0 -> L1`
- `L1 -> L2`
- `L2 -> L1`
- `L1 -> L0`

Restricted transitions:

- any move to `L3` requires explicit promotion review and recorded acceptance
- no level may skip directly to `L3`

Canonical rollback target:

- when a higher-autonomy run degrades or becomes ambiguous, rollback target is
  `L1_local_canonical_remote_execution` unless the failure is severe enough to
  require `L0_local_only`

## What Stays Local

The following surfaces stay local by default:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`
- accepted memory pointer and accepted restart memory
- accepted evidence notes
- factory promotion decisions
- template and tooling promotion decisions
- deployment or registry truth

Local PackFactory is the authority for:

- what the next task is
- what result counts as accepted
- what changes become canonical
- when a remote result is only advisory

## What Moves To ADF

`adf-dev` is the default execution owner for bounded ADF work.

The following work may move to `adf-dev`:

- bounded task continuation
- remote review-surface generation
- target helper execution
- bounded target evidence capture
- bounded candidate note generation
- bounded candidate source or state changes when the run contract allows them
- checkpoint writing
- restart-memory generation

In plain language:

- ADF on `adf-dev` should do the work
- Local PackFactory should judge the work

## What Must Flow Back

The remote side must return only what Local PackFactory needs to judge and
accept the run.

Minimum return contract:

- checkpoint bundle
- run summary
- loop events
- restart or feedback memory
- bounded evidence artifacts
- any proposed state changes
- any proposed source or note changes
- validation outputs when those are part of the task boundary

The remote side should return proof, not its whole workspace.

Required completeness rule:

- if a task declares required return artifacts, the run must return all of
  them to count as a successful autonomy checkpoint
- partial returns may be preserved as evidence-only, but they do not count as
  accepted task completion or accepted checkpoint success

Artifact-schema rule:

- each required artifact should be returned through an existing reviewed
  schema, manifest, or machine-readable PackFactory contract
- if an artifact has no reviewed contract yet, it cannot be treated as a
  required acceptance artifact

Durable acceptance rule:

- artifacts present only in local scratch do not satisfy durable acceptance by
  themselves
- imported runtime evidence preserved under `eval/history/` is the canonical
  durable evidence line for returned runtime proof
- any manifest, request, report, or audit artifact that must survive scratch
  cleanup must be written or copied to a durable PackFactory-managed path
  outside scratch before cleanup runs
- scratch-local copies may remain as transient mirrors, but they are not the
  canonical accepted artifact
- transient local staging, pulled `incoming/` bundle trees, and scratch cleanup
  are governed by
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md`

## What Must Not Move Automatically

The following must not silently become remote-owned:

- registry truth
- deployment truth
- promotion decisions
- whole-workspace archival history
- canonical local state acceptance
- broad remote-canonical mode changes

### Transient Local Scratch Boundary

- local remote-autonomy staging payloads are transient PackFactory-managed
  scratch
- local pulled roundtrip `incoming/` trees are transient PackFactory-managed
  scratch
- scratch-local target manifests, generated import requests, and roundtrip
  manifests are transport artifacts unless promoted to a durable
  PackFactory-managed surface
- transient scratch may be cleaned after the required durable outputs exist
- transient local staging and scratch cleanup behavior are governed by
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md`

## Runtime Invocation Rule

This contract should be invoked in two places:

### 1. Before A Run Starts

Local PackFactory chooses the run mode before `adf-dev` starts.

That mode should determine:

- what surfaces `adf-dev` may change
- how long the run may continue
- what artifacts must come back
- whether the run is execution-only, checkpoint-only, or broader authoring

Before the run begins, Local PackFactory should make the current mode explicit
in machine-readable state and in the remote request.

Minimum pre-run fields:

- active autonomy level
- allowed writable surfaces
- maximum bounded runtime
- checkpoint requirement
- required return artifacts
- local acceptance requirement
- resolved local scratch root
- deterministic per-run scratch path derived from that root

Canonical run-mode record:

- the canonical run mode must first exist in local machine-readable state
- the generated remote request must carry the same mode fields
- Local PackFactory runtime selects the scratch root
- remote run payloads, wrapper requests, pulled manifests, and imported bundles
  must not override that selected root
- the generated request may record the resolved scratch root for auditability
  and replay consistency
- later workflow steps must validate against the persisted resolved root from
  request-creation time
- if the persisted request root and the current ambient scratch-root
  configuration disagree, the workflow must fail closed with a scratch-root
  mismatch error
- if mode metadata is missing, stale, or contradictory before launch, the run
  must fail closed and not start as an autonomy run

### 2. At Each Checkpoint

At checkpoint time, the run should reference this contract to answer:

- can the run continue autonomously
- must it pause for review
- what must be exported back
- what is proposed versus already accepted

Checkpoint fail-closed rule:

- if the required checkpoint bundle is missing, the run is not a promotable
  autonomy success
- if required return artifacts are incomplete, the run falls back to
  evidence-only or blocked-boundary status
- if the checkpoint proposal conflicts with canonical local state, local state
  wins until an explicit acceptance step resolves the conflict

Pause or stop triggers:

- pause for review when the run reaches a named checkpoint reason
- pause for review when the next step would widen beyond the allowed writable
  surfaces or allowed autonomy level
- stop as `blocked_boundary` when required artifacts are missing
- stop as `blocked_boundary` when task-boundary validation fails
- stop as `blocked_boundary` when unexpected source or state diffs appear
  outside the allowed writable surfaces
- stop as `blocked_boundary` when the run exceeds its bounded runtime without a
  reviewed continuation rule
- stop as `blocked_boundary` when the task expands into a new branch that was
  not part of the approved run purpose

## Runtime Reference Surfaces

This contract should be referenced through four layers:

1. This spec
2. planner and state surfaces
3. remote request mode or reason
4. checkpoint bundle

That means:

- humans read this spec
- machine-readable state records the current ownership mode
- the remote request applies that mode
- the checkpoint bundle reports what happened under that mode

Precedence rule when surfaces disagree:

1. canonical local machine-readable state
2. explicit remote request generated from that state
3. checkpoint bundle returned by the run
4. this prose spec as explanatory guidance

Operational implication:

- the prose spec explains the model
- the canonical local state governs the run
- the remote request is the executable boundary contract
- the checkpoint bundle may propose changes but cannot override higher
  precedence surfaces by itself

In-flight override rule:

- emergency contraction is allowed only by issuing a new higher-precedence
  local request or by recording a local blocked-boundary decision
- the remote side may not silently widen its own mode during execution

Missing-metadata rule:

- if the remote request, checkpoint bundle, or returned artifacts omit the
  required mode fields, the result may be preserved as evidence-only but must
  not be accepted as canonical task execution

## Current Enforcement Surfaces

This contract is not only policy text. Parts of it are already enforced by the
current PackFactory and ADF codebase.

### Canonical Local Control Plane

Current canonical local ownership is already represented by:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`

Those files are the current machine-readable source of truth for:

- active task ownership
- next recommended task
- readiness direction
- local accepted state

### Remote Request Contract

The current executable remote request surface already exists in:

- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `tools/remote_autonomy_staging_common.py`
- `tools/prepare_remote_autonomy_target.py`
- `tools/push_build_pack_to_remote.py`

These surfaces already define or enforce:

- remote target identity
- remote pack location
- remote run location
- export location
- request schema loading
- lean staging payload behavior
- factory-local scratch-root selection remains authoritative even when the
  remote request records the resolved root for auditability
- transient local staging and pullback durability rules defer to
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md`

### Bounded Remote Loop Contract

The current bounded remote execution contract is already partially enforced in:

- `tools/run_remote_autonomy_loop.py`

That file already carries:

- remote request loading
- bounded execution-manifest handling
- prompt generation
- explicit writable-surface language in the remote prompt
- checkpoint-bundle instructions through
  `record-remote-checkpoint-bundle`

Important current reality:

- this is still a bounded remote loop, not a general authoring loop
- the contract in this spec should stay aligned with that current limitation

### Checkpoint Bundle And Runtime-Evidence Contract

The current checkpoint and export surfaces already exist in:

- `src/algosec_diagnostic_framework_template_pack/cli.py`
- `src/algosec_diagnostic_framework_template_pack/delegated_codex.py`
- `src/pack_export_runtime_evidence.py`
- `tools/pull_remote_runtime_evidence.py`
- `tools/import_external_runtime_evidence.py`

These surfaces already implement or partially implement:

- `record-remote-checkpoint-bundle`
- `adf-remote-checkpoint-bundle.json`
- runtime-evidence bundle export
- execution-manifest and target-manifest pullback
- import of reviewed returned evidence into local PackFactory history

### Remote Roundtrip Test Surfaces

The current reviewed wrapper paths already exist in:

- `tools/run_remote_autonomy_test.py`
- `tools/run_remote_active_task_continuity_test.py`
- `tools/run_remote_memory_continuity_test.py`

These surfaces already test or enforce:

- bounded remote roundtrip behavior
- delayed pullback recovery
- continuity behavior
- import-path review before local acceptance
- transport artifacts inside local scratch are not durable accepted evidence by
  default
- wrapper audit artifacts must be promoted out of scratch before cleanup if
  they need to survive as reviewed PackFactory outputs

### ADF Helper Execution Surfaces

The current helper-execution path on `adf-dev` already exists in:

- `docs/remote-targets/adf-dev/README.md`
- `src/algosec_diagnostic_framework_template_pack/cli.py`
- `docs/remote-targets/algosec-lab/target-connection-profile.json`

These surfaces already implement:

- `target-preflight`
- `target-heartbeat`
- `target-shell-command`
- the saved target profile for `algosec-lab`
- the non-login shell pattern used to avoid appliance menu interference

### Current Enforcement Status

Current enforcement is partial, not complete.

What is already enforced well:

- canonical local request and state precedence
- bounded remote request structure
- lean remote staging
- helper-based target access
- checkpoint and runtime-evidence bundle handling

What is still only partially enforced or still contract-led:

- explicit autonomy-level fields in machine-readable local state
- strict required-artifact completeness scoring for every task
- automatic downgrade behavior across all remote workflows
- a universal quarantine status model for every proposed source or state change
- PackFactory-managed scratch-root selection, persistence, and mismatch
  validation across replayed requests
- durable promotion of generated import requests, roundtrip manifests, and
  similar wrapper audit artifacts before scratch cleanup

This means the contract should reference the existing code directly, but should
not pretend every rule in this document is already fully automated.

## Writable Surface Contract

Remote execution must use an explicit allowlist, not an implied one.

Each run should name:

- allowed state files
- allowed note or history surfaces
- allowed generated output directories
- allowed memory surfaces
- prohibited canonical control-plane files

Default prohibition set:

- registry truth
- deployment truth
- silent edits to canonical local acceptance pointers
- edits outside the approved writable surfaces

If a run allows proposed edits to canonical local control-plane files such as
`tasks/active-backlog.json`, `status/work-state.json`, or `status/readiness.json`,
those edits remain proposed only until Local PackFactory explicitly accepts
them.

## Scope Elasticity

This contract is intentionally designed to support growth, reduction, and later
mode changes.

It should not hard-code one permanent split.

Instead, it should support:

- increasing remote autonomy
- decreasing remote autonomy
- widening or narrowing allowed remote execution surfaces
- extending or shortening bounded remote run time
- promoting or rolling back stronger remote ownership later

## Expansion Path

Examples of future expansion this contract should allow:

- longer bounded `adf-dev` run windows
- multi-checkpoint remote runs
- richer remote candidate edits
- greater remote ownership of bounded ADF iteration loops
- later reviewed remote-canonical mode for selected ADF surfaces

Expansion should only happen after explicit evidence shows:

- checkpoint quality is high
- restart continuity is reliable
- evidence bundles are complete
- local acceptance stays clear
- remote drift stays low

Promotion criteria for `L1 -> L2`:

- at least 3 reviewed runs under the current mode
- each reviewed run returns the required checkpoint bundle, run summary, loop
  events, and restart memory
- no run in the review set ends with conflicting state acceptance
- no run in the review set requires ad hoc shell babysitting
- Local PackFactory records an explicit acceptance note that the promotion is
  approved

Promotion criteria for any move toward `L3`:

- complete `L2 -> L1` promotion criteria first
- define the exact surfaces proposed for remote-canonical ownership
- record an explicit approval artifact naming the approved surfaces, approver,
  and rollback target
- update canonical local state to record the new level before the next run

Required approval artifact for stronger autonomy:

- a reviewed note or state artifact accepted locally that names:
  - source level
  - target level
  - approved surfaces
  - approver
  - evidence set used
  - rollback target

## Contraction Path

If autonomy quality degrades, this contract should allow the system to narrow
scope cleanly.

Examples:

- shorten run duration
- reduce writable surfaces
- require earlier checkpoint pauses
- move a task back to local execution
- treat remote output as evidence-only until the failure mode is fixed

Contraction decision owner:

- Local PackFactory declares degradation and records rollback or contraction

Automatic fail-closed contraction triggers:

- missing required checkpoint bundle
- missing required return artifacts
- conflicting proposed state versus canonical local state
- remote run widens beyond the allowed writable surface or allowed mode
- remote run requires ad hoc shell babysitting to stay on task

Default contraction behavior:

- `L2` degrades to `L1`
- `L1` degrades to evidence-only remote execution or to `L0` when even bounded
  remote execution is no longer trustworthy

Rollback record requirement:

- every contraction should leave one local accepted note or state update naming
  the trigger, the new level, and whether the remote result remains advisory,
  blocked, or acceptable as evidence-only

## Acceptance Rule

A remote result is not canonical just because it ran on `adf-dev`.

Local PackFactory must still decide:

- what is accepted
- what stays advisory
- what must be rerun
- what is blocked

The checkpoint bundle should therefore declare:

- what mode the run used
- what it is proposing
- what evidence supports that proposal
- what local still needs to accept

Minimum checkpoint acceptance fields:

- autonomy level used
- run purpose
- checkpoint reason
- required return artifacts present or missing
- proposed state changes
- proposed source or note changes
- explicit local-acceptance-needed flag

A checkpoint bundle, pulled export, or wrapper-generated audit file found only
in transient scratch is a proposed return surface, not yet a durable accepted
artifact. Local acceptance requires the reviewed artifact to exist in its
declared durable PackFactory-managed destination, or the run can only be
accepted as evidence-only.

Quarantine rule for proposed changes:

- every proposed state or source change returned from `adf-dev` is quarantined
  by default
- quarantined changes may be reviewed, preserved, diffed, or rejected
- quarantined changes are not canonical just because they are present in a
  returned bundle
- canonical local state changes only after an explicit local `accepted`
  decision

Acceptance outcomes should be one of:

- `accepted`
- `accepted_as_evidence_only`
- `blocked_boundary`
- `rejected`

Only `accepted` may change canonical local state beyond evidence preservation.

Automatic rejection or downgrade conditions:

- missing required mode metadata
- missing required return artifacts
- proposed changes outside allowed writable surfaces
- ambiguous accepted-versus-proposed boundary in the returned bundle
- conflicting canonical state update with no explicit local acceptance step

## Current Evidence

This contract is grounded in current ADF evidence, not only design intent.

Key proof artifacts:

- `docs/specs/adf-three-node-autonomy-contract-v1.md`
  This already defines the three-node split at the node-role level.
- `eval/history/adf-three-node-lean-stage-and-target-slice-20260329.md`
  This proved lean local stage to `adf-dev` plus a successful bounded
  `adf-dev -> target` helper slice.
- `eval/history/adf-three-node-live-later-workflow-helper-slice-20260329.md`
  This proved a support-useful live helper slice where the observed session was
  already beyond top-level `GUI down`.
- `eval/history/adf-three-node-live-analysis-options-helper-slice-20260329.md`
  This proved the same helper path can also preserve explicit negative results
  without overclaiming a sibling-branch proof.
- `docs/specs/adf-remote-autonomy-testing-workflow-v1.md`
  This already defines how bounded `adf-dev` autonomy should be tested without
  drifting into shell babysitting.

Current evidence supports `L1_local_canonical_remote_execution`.

Current evidence does not yet justify:

- `L2` promotion for longer unattended multi-checkpoint execution
- `L3` promotion for remote-canonical ownership of any ADF surface

## PackFactory Benefit

The benefit to PackFactory is simple:

- clearer ownership
- safer remote autonomy
- cleaner evidence return
- easier scaling to longer ADF runs
- less confusion about what is allowed to happen on `adf-dev`

In plain language:

This contract gives PackFactory a controlled way to grow remote autonomy
without losing source-of-truth discipline.

## Decision Rule

When deciding whether something stays local or moves to `adf-dev`, ask:

- does `adf-dev` need this to execute the next bounded ADF task?

When deciding whether something must flow back, ask:

- does Local PackFactory need this to judge, accept, or promote the result?

If the answer is no, do not move or sync it by default.
