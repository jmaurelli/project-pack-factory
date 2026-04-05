# Project Pack Factory Remote Autonomous Build-Pack Execution Tech Spec

## Purpose

Define the reusable PackFactory-native execution contract for running an
autonomous build-pack on a remote target after staging.

This spec covers:

- reusable remote bootstrap and invocation
- remote agent execution boundaries
- remote autonomy-loop behavior
- remote runtime evidence generation

This spec is about the execution plane only.

## Spec Link Tags

```json
{
  "spec_id": "remote-autonomous-build-pack-execution",
  "part_of": [
    "remote-autonomy-spec-family-overview"
  ],
  "depends_on": [
    "remote-autonomy-target-workspace-and-staging",
    "portable-build-pack-autonomy-runtime-helpers",
    "autonomous-build-pack-handoff-and-work-state",
    "autonomous-loop-and-agent-memory-measurement",
    "external-build-pack-runtime-evidence-export"
  ],
  "integrates_with": [
    "runtime-agent-memory",
    "external-runtime-evidence-import"
  ],
  "followed_by": [
    "remote-autonomy-end-to-end-roundtrip"
  ]
}
```

## Relationship To Remote Autonomy Spec Family

This is the third spec in the remote-autonomy family.

It assumes:

- a remote workspace has already been prepared and staged
- the staged build-pack already carries the portable helper surfaces it needs

It defines the execution-plane behavior that runs between those setup layers
and the final roundtrip import layer.

This spec flows directly from the family overview and from the first two
family specs:

- the family overview defines this as the bounded execution layer
- the staging spec defines the quarantined staged remote copy this spec may use
- the helper spec defines the portability amendment and helper manifest this
  spec must preflight before agent launch

Success here proves only bounded execution-plane behavior on the staged remote
copy.

It does not by itself prove:

- remote staging correctness
- helper seeding correctness during materialization
- local pullback or evidence import correctness

Read it after:

- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md)

Read it before:

- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md)

Its relationship to the broader project is:

- the remote agent becomes the execution plane
- PackFactory still owns the authoritative local promotion and deployment
  decisions

## Problem

The factory can already prove a bounded autonomous run locally.

What it does not yet define is the reusable execution contract for:

- invoking a remote agent against a staged build-pack
- keeping that agent inside the pack-local control-plane bounds
- recording runtime loop evidence on the remote side
- stopping at the correct local completion boundary

Without this spec:

- remote autonomous runs become operator-specific
- execution prompts drift between targets
- success and failure conditions become hard to compare
- later imported evidence does not prove the same thing each time

## Design Goals

- keep remote execution host-agnostic and request-driven
- keep the remote agent scoped to the staged build-pack only
- preserve the PackFactory control-plane and execution-plane split
- require the remote run to stop at the correct workflow boundary
- make remote runtime evidence export part of the same bounded contract

## Non-Goals

This spec does not:

- create a persistent remote daemon
- require a particular model vendor or CLI brand in v1
- let a remote agent promote or deploy a build-pack directly
- let a remote run import its own evidence into PackFactory

## Local Scratch Note

The transient local staging path that prepares a remote execution run is
PackFactory scratch, not canonical evidence.

- the configured scratch root may live on another directory or partition
- the remote execution contract does not allow a request payload to choose a
  different scratch root than the local PackFactory runtime selected
- if a workflow needs durable artifacts from the staging side, it must copy or
  write them outside scratch before cleanup runs

## Proposed Reusable Script

V1 should add:

- `tools/run_remote_autonomy_loop.py`

This tool should:

- connect to the target declared in a request file
- bootstrap the remote execution environment if needed
- invoke the remote agent against the staged build-pack
- ensure the run produces local runtime evidence
- invoke the pack-local runtime evidence exporter

## Request Contract

The remote runner should consume:

- `remote-autonomy-run-request/v1`

The request must be explicit about:

- source build-pack identity
- remote target identity
- run id
- remote directories
- remote runner program
- operator reason

The remote runner must not derive those values heuristically from a hostname or
directory listing alone.

V1 should keep the shared run request as the cross-spec operator intent
contract.

Request-authoring helpers may generate `remote-autonomy-run-request/v1`
documents for bounded scenarios such as assistant-UAT, but those helpers must
still emit the shared request contract rather than inventing a parallel remote
execution format.

Execution-specific resolved behavior that is not already modeled in
`remote-autonomy-run-request/v1` must be recorded in execution-side evidence,
not improvised from runner defaults without audit.

That means the runner must record, at minimum:

- which remote runner program was invoked
- whether bootstrap ran as presence-check-only
- the request checksum and staged target-manifest linkage
- the terminal outcome and export outcome for the run

V1 does not authorize execution-time bootstrap modes that are not explicitly
modeled by the shared request contract.

In particular, this execution layer must not create a pack-local virtual
environment merely because an implementation-specific runner default chooses
to.

## Remote Preflight Contract

Before invoking any remote agent, the remote runner must validate that the
staged build-pack is execution-ready.

At minimum the runner must verify:

- `.packfactory-remote/request.json` exists and matches the selected request
- `.packfactory-remote/target-manifest.json` exists and matches the same
  `source_build_pack_id`, `run_id`, and resolved remote directories
- `pack.json` exists and declares a build-pack manifest
- the canonical handoff files declared in `pack.json.directory_contract`
  exist when required by the build-pack
- the declared portability helper paths and helper manifest exist for
  portability-enabled build-packs
- starter task commands do not retain factory-relative helper paths such as
  `../../tools/...` for portability-enabled build-packs
- `pack.json.entrypoints.export_runtime_evidence_command` exists when the run
  is expected to export runtime evidence

If these preflight checks fail, the runner must abort before any remote
pack-local mutation begins.

## Remote Execution Contract

The remote agent must operate only inside the staged build-pack root.

`pack.json` is the primary remote execution contract.

After the initial bootstrap reads, the runner and remote agent must use:

- `pack.json.post_bootstrap_read_order` as the canonical post-bootstrap
  traversal list
- `pack.json.directory_contract` to resolve canonical handoff, readiness,
  benchmark, and runtime-evidence paths when those paths are declared

For portability-enabled build-packs, the runner must also inspect the declared
portable helper manifest before agent launch.

The execution layer must not infer canonical file paths from directory contents
alone when `pack.json` already declares them.

## Runner Lifecycle Safety

The remote execution layer must manage remote runner lifecycle state explicitly
enough that replaying a bounded run does not require manual process cleanup.

At minimum it must:

- record the currently managed remote run under `.packfactory-remote/`
- clean up a stale recorded run when the same staged pack is replayed and the
  previous managed process is no longer authoritative
- preserve durable execution-manifest fields that show whether stale cleanup
  ran and whether the remote runner was interrupted by a controller-side signal

This lifecycle tracking is execution-plane state only.

It does not change the rule that imported runtime evidence remains
supplementary rather than canonical local control-plane truth.

At minimum it should read:

- `AGENTS.md`
- `project-context.md`
- `pack.json`

Then it should continue with the pack’s declared post-bootstrap traversal
contract and any canonical paths resolved from `pack.json.directory_contract`.

Optional runtime memory remains advisory:

- `.pack-state/agent-memory/`
- `.pack-state/autonomy-runs/`

## Writable Path Contract

V1 remote execution must use a narrow pack-local writable allowlist.

Allowed remote writes are limited to:

- the declared task backlog file
- the declared work-state file
- the declared readiness file when updated by bounded pack-local workflows
- the declared eval history and latest-index paths when updated by bounded
  pack-local workflows
- `.pack-state/`
- the declared runtime-evidence export directory

All other staged pack paths are read-only by default for this initial
remote-autonomy proof family unless a later spec amendment explicitly expands
that authority.

That means the remote runner and agent must not rewrite, by default:

- `pack.json`
- `.packfactory-remote/request.json`
- `.packfactory-remote/target-manifest.json`
- prompts, docs, or source files unrelated to the declared starter backlog
- deployment pointers or other factory-level artifacts

Execution-plane metadata under `.packfactory-remote/` may still be rewritten by
the control plane itself to restore canonical staged contents before boundary
diffing. That restoration is a controller-owned integrity step, not added agent
write authority.

## Remote Agent Prompt Boundary

The remote invocation contract must instruct the remote agent to:

- treat the staged build-pack as the only writable work packet
- use declared pack-local validation and benchmark surfaces only
- treat the initial remote-autonomy proof as starter-backlog-only execution
- stop when:
  - the completion definition is satisfied
  - promotion or deployment becomes the next valid action
  - an escalation condition is reached

The remote invocation contract must also instruct the agent not to:

- mutate local or remote factory registry truth
- create deployment pointers
- invent new tests without explicit operator approval
- invent new backlog items or broaden the declared starter backlog
- edit unrelated implementation files beyond the allowed execution surfaces
- bypass the pack’s own stop conditions

## Memory Precedence Contract

For v1, canonical pack-local files remain authoritative.

That means:

- `contracts/project-objective.json`
- the declared task backlog file
- the declared work-state file
- declared readiness and eval surfaces

take precedence over any advisory memory surface.

Runtime memory may inform explanation, resume context, or task selection only
when it is consistent with canonical pack-local state.

Advisory memory must never override canonical pack-local files for mutation
decisions.

If runtime memory is stale, incomplete, or inconsistent with canonical
pack-local state, the runner or agent must:

- record that condition in loop evidence
- ignore the stale or incomplete memory for mutation decisions
- continue from canonical pack-local truth or stop and escalate if canonical
  truth is itself insufficient

For the initial remote-autonomy proof family, `.pack-state/autonomy-runs/` may
be read as advisory history, while `.pack-state/agent-memory/` remains
optional and ignored by default unless a later amendment explicitly enables it
for remote execution.

## Remote Bootstrap Contract

V1 remote bootstrap may be small and host-specific in implementation, but the
contract must be generic and fail closed:

- verify the remote working directory exists
- verify Python is available
- avoid depending on root access or machine-global package mutation

The remote run must remain runnable by an ordinary SSH-authenticated account.

For v1, bootstrap is presence-check-only.

It must not:

- create a new pack-local virtual environment by default
- mutate machine-global packages
- rely on host-specific bootstrap side effects that are not captured in
  execution evidence

## Execution Manifest Contract

V1 should add:

- `docs/specs/project-pack-factory/schemas/remote-execution-manifest.schema.json`

The remote runner should write:

- `.packfactory-remote/execution-manifest.json`

At minimum it should include:

- `schema_version`
- `source_build_pack_id`
- `run_id`
- `request_sha256`
- `target_manifest_sha256`
- `remote_runner`
- `bootstrap_mode`
- `started_at`
- `stopped_at`
- `terminal_outcome`
- `terminal_reason`
- `export_command`
- `export_bundle_path`
- `export_completed_at`
- `exported_run_id`
- `control_plane_mutations`

All `control_plane_mutations.*` must be `false`.

This manifest is the audit record that proves which execution contract actually
ran on the remote side.

## Execution-Plane Mutation Boundary

Remote execution may write bounded pack-local state under the staged copy, but
those writes remain quarantined execution evidence only.

That includes allowed remote updates to:

- declared task backlog and work-state files
- declared readiness and eval surfaces
- `.pack-state/`
- the declared runtime-evidence export directory

Those remote mutations must not be treated as local PackFactory truth and must
not reconcile back into the local source build-pack by direct copy or sync.

## Runtime Evidence Contract

Each remote run must produce at least:

- `.pack-state/autonomy-runs/<run-id>/loop-events.jsonl`
- `.pack-state/autonomy-runs/<run-id>/run-summary.json`

After the remote loop completes or stops, the runner must invoke:

- `pack.json.entrypoints.export_runtime_evidence_command`

for the selected `run_id`.

The exported bundle remains supplementary runtime evidence only.

Before export, the remote run must record an explicit terminal outcome in loop
evidence and run summary.

V1 terminal outcomes must distinguish at least:

- completed the declared starter backlog
- stopped at the promotion-or-deployment boundary
- stopped due to escalation

The runner must then verify that the exported bundle corresponds to the same
`run_id` that just executed.

At minimum it should verify that the bundle contains:

- the matching `run-summary.json`
- the matching `loop-events.jsonl`
- the same `run_id`
- an export completion timestamp later than the terminal loop event

Exporting stale or previously generated runtime evidence must fail closed.

## Remote Success Criteria

A remote autonomous run is successful when all of the following are true:

1. The remote agent starts from the staged build-pack’s seeded control-plane
   files.
2. The agent completes the declared starter backlog or reaches a declared stop
   condition.
3. The remote run writes autonomy-loop evidence under `.pack-state/`.
4. The remote run records a terminal execution outcome in both loop evidence
   and `.packfactory-remote/execution-manifest.json`.
5. The build-pack exports a runtime evidence bundle successfully for the same
   `run_id` that just executed.
6. The remote run does not mutate any PackFactory registry, promotion, or
   deployment authority surface.

## Canonical Completion Boundary

For the initial end-to-end test family, the expected remote completion boundary
is starter-backlog-only execution.

That means the remote agent may complete the declared starter tasks and
reconcile canonical pack-local state to the correct stop boundary, but it may
not invent new tasks, broaden the backlog, or continue into promotion or
deployment work.

The expected pack-local stop boundary is:

- the declared task backlog file shows the starter tasks as completed
- the declared work-state file records `autonomy_state = ready_for_deploy` or
  another declared terminal state
- the declared work-state file records `next_recommended_task_id = null`
- the declared readiness file records `ready_for_deployment = true`

That means the build-pack is complete as a pack-local work packet, even though
it is not yet promoted or deployed by the factory.

## Minimal Validation Plan

Verification for this spec must follow the PackFactory testing policy:

- keep verification intentionally small
- prefer contract checks over host, provider, or model matrices
- protect only the few behaviors that would materially break bounded remote
  execution

V1 verification should stay absolute minimal and focus on:

- one happy-path remote execution smoke check from preflight through terminal
  outcome through bundle export
- one fail-closed preflight or boundary check, such as missing helper
  prerequisites, missing exporter entrypoint, or forbidden writable-surface
  behavior
- one authority-boundary assertion that remote execution evidence remains
  quarantined and does not claim local control-plane mutation

Do not add:

- broad host or cloud matrices
- model-vendor matrices
- deep bootstrap permutations
- expansive tests for incidental runner plumbing
