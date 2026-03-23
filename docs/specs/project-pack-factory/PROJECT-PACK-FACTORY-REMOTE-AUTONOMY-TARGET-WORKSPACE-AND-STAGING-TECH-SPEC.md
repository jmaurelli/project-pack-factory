# Project Pack Factory Remote Autonomy Target Workspace And Staging Tech Spec

## Purpose

Define the reusable PackFactory-native staging contract that prepares a remote
execution target for autonomous build-pack work without making the workflow
specific to any one host alias, hostname, or environment.

This spec covers:

- deterministic remote parent and child directory naming
- reusable remote target preparation
- reusable build-pack staging to a remote execution target
- auditable request and manifest files for remote staging runs

This spec is about the reusable source-to-target handoff before the remote
agent starts working.

## Spec Link Tags

```json
{
  "spec_id": "remote-autonomy-target-workspace-and-staging",
  "part_of": [
    "remote-autonomy-spec-family-overview"
  ],
  "depends_on": [
    "autonomous-build-pack-handoff-and-work-state",
    "external-build-pack-runtime-evidence-export"
  ],
  "integrates_with": [
    "build-pack-control-plane-dataplane-integrity",
    "external-runtime-evidence-import",
    "portable-build-pack-autonomy-runtime-helpers"
  ],
  "followed_by": [
    "remote-autonomous-build-pack-execution",
    "remote-autonomy-end-to-end-roundtrip"
  ]
}
```

## Relationship To Remote Autonomy Spec Family

This is the first spec in the remote-autonomy family.

It defines the source-to-target workspace and staging layer that the rest of
the family builds on.

This is the first spec in reading order, not a claim that implementation
dependencies begin and end here.

In implementation terms, this staging layer is paired with the portable helper
layer because the staged payload must include any pack-local portable runtime
helpers that later remote execution depends on.

Success here proves only deterministic workspace preparation and bounded
payload handoff.

It does not by itself prove:

- pack portability outside the factory checkout
- remote agent execution correctness
- remote runtime evidence return-path correctness

Read it before:

- [PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md)

Its relationship to the broader project is:

- PackFactory remains the source control plane
- the remote target becomes the bounded execution destination
- no registry, promotion, or deployment authority moves to the target

## Problem

Project Pack Factory already knows how to:

- materialize a build-pack locally
- seed canonical objective, backlog, and work-state files
- export bounded runtime evidence from an externally running build-pack
- import that evidence back into factory history

What it does not yet define is a reusable staging contract for:

- preparing a remote target workspace
- naming those remote workspaces deterministically
- copying a selected build-pack into that target
- doing so in a way that is host-agnostic and repeatable

Without this spec:

- remote execution tends to become host-specific shell history
- workspace naming drifts between operators and targets
- copied payload contents become hard to compare across runs
- later evidence review loses context about what was actually staged

## Current Repo Evidence

### Evidence A: Existing Specs Already Distinguish Factory Control Plane From External Execution

Current specs:

- [PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-BUILD-PACK-CONTROL-PLANE-AND-DATAPLANE-INTEGRITY-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-BUILD-PACK-CONTROL-PLANE-AND-DATAPLANE-INTEGRITY-TECH-SPEC.md)

Interpretation:

- the factory already treats registry, deployment, and promotion state as
  canonical control-plane truth
- external execution must remain outside that authority boundary

### Evidence B: Existing Export And Import Specs Already Assume An External Runtime Exists

Current specs:

- [PROJECT-PACK-FACTORY-EXTERNAL-BUILD-PACK-RUNTIME-EVIDENCE-EXPORT-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-EXTERNAL-BUILD-PACK-RUNTIME-EVIDENCE-EXPORT-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-EXTERNAL-RUNTIME-EVIDENCE-IMPORT-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-EXTERNAL-RUNTIME-EVIDENCE-IMPORT-TECH-SPEC.md)

Interpretation:

- the repo already values portable runtime evidence
- it still lacks a canonical way to create the remote execution workspace that
  produces that evidence

## Design Goals

- keep remote staging reusable across arbitrary SSH-reachable targets
- keep naming deterministic and human-readable
- distinguish PackFactory as source and remote host as target in directory names
- stage only the build-pack execution payload, not the whole factory
- produce auditable machine-readable requests and manifests
- keep local control-plane authority unchanged during remote staging

## Non-Goals

This spec does not:

- define how the remote agent itself makes decisions
- define promotion or deployment after remote execution
- require a specific remote hostname, alias, or cloud provider
- grant remote scripts any authority over local registry or deployment state
- require long-running remote services or agents in v1

## Proposed Reusable Scripts

V1 should add:

- `tools/prepare_remote_autonomy_target.py`
- `tools/push_build_pack_to_remote.py`

These tools must be reusable orchestration helpers, not host-specific shell
fragments.

## Request Contract

V1 should add:

- `docs/specs/project-pack-factory/schemas/remote-autonomy-run-request.schema.json`

Both staging tools should accept the same request-file contract:

- `schema_version = remote-autonomy-run-request/v1`
- `source_factory_root`
- `source_build_pack_id`
- `source_build_pack_root`
- `run_id`
- `remote_host`
- `remote_user`
- `remote_target_label`
- `remote_parent_dir`
- `remote_pack_dir`
- `remote_run_dir`
- `remote_export_dir`
- `remote_reason`
- `staged_by`
- `remote_runner`

The request file is the source of truth for operator intent and remote
coordinates.

Within that request contract:

- `source_factory_root`
- `source_build_pack_root`

are provenance-only local source references.

They exist so later operators and agents can audit where the staged payload
came from.

They must not be treated as:

- remote execution paths
- remote dereference targets
- later sync-back destinations
- authority to overwrite local source content

The staging tools may derive deterministic default paths from the request-file
values, but they must not infer pack identity, remote path ownership, or run
layout heuristically from remote directory contents alone.

V1 request semantics must stay deterministic:

- `remote_parent_dir` is the canonical resolved parent directory for the run
- `remote_pack_dir`, `remote_run_dir`, and `remote_export_dir` are resolved
  descendants recorded in the request, not free-form alternate layouts
- both staging tools must recompute the expected descendant paths from
  `remote_parent_dir`, `source_build_pack_id`, and `run_id`
- if the recorded resolved paths do not match the deterministic formulas in
  this spec, the request must be rejected

V1 path-segment inputs that participate in directory naming must use a shared
slug contract.

At minimum this applies to:

- `remote_target_label`
- `run_id`
- `source_build_pack_id` when used as a path segment

Those values must:

- use lowercase ASCII letters, digits, and internal hyphens only
- begin and end with an alphanumeric character
- reject `/`, `\\`, whitespace, `..`, shell metacharacters, and non-ASCII
  lookalike separators
- stay short enough that the full derived path remains comfortably below host
  path-length limits

The staging tools must also validate path containment fail-closed:

- `remote_pack_dir` must resolve within `remote_parent_dir`
- `remote_run_dir` must resolve within `remote_pack_dir`
- `remote_export_dir` must resolve within either:
  - `remote_pack_dir`
  - or a stricter run-scoped child under `remote_run_dir` when a future
    amendment chooses that layout

Any request whose normalized paths escape those boundaries must be rejected.

## Deterministic Naming Contract

### Default Parent Directory

The default remote parent directory should be:

- `~/packfactory-source__<remote_target_label>__autonomous-build-packs`

This keeps three things obvious:

- the source is PackFactory
- the target is a named remote execution environment
- the contents are autonomous build-pack workspaces

`remote_target_label` is a request value, not a hostname requirement.

### Default Pack Directory

The default remote pack directory should be:

- `<remote_parent_dir>/<source_build_pack_id>`

Example:

- `~/packfactory-source__adf-target__autonomous-build-packs/release-evidence-summarizer-build-pack-v4`

### Default Run Directory

The default remote run directory should be:

- `<remote_pack_dir>/runs/<run_id>`

The run directory is for remote orchestration metadata and local runtime
artifacts that should remain distinct between repeated executions.

### Default Remote Export Directory

The default remote export directory should be:

- `<remote_pack_dir>/dist/exports/runtime-evidence`

This keeps exported runtime evidence inside the staged build-pack root, where
the pack-local exporter already expects to work.

For v1 this remains a pack-local remote output path only.

It must not be treated as:

- a local source-of-truth export directory
- a target for remote-to-local sync
- a reason to overwrite local `dist/exports/` content by direct copy

## Remote Workspace Layout

The staged remote pack directory should contain:

- the copied build-pack root as the working root
- `.packfactory-remote/target-manifest.json`
- `.packfactory-remote/request.json`
- `runs/<run_id>/`

The build-pack root remains the remote execution root.

The `.packfactory-remote/` directory is staging metadata only.

It must not:

- become canonical PackFactory control-plane state
- be imported as readiness evidence
- be copied back into local control-plane files

## Staging Payload Contract

The push tool must stage:

- the selected build-pack root as already materialized locally
- the remote run request file
- a target manifest that records what was staged

Helper composition and helper seeding do not belong to this staging spec.

Those concerns belong to:

- [PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md)

This staging layer only preserves and copies whatever portable helper contents
the selected build-pack already carries.

V1 must use an explicit fresh-staging payload policy rather than copying every
file found under the local build-pack root.

The default payload policy must include the materialized build-pack contents
needed for remote execution and must exclude local residue such as:

- `.packfactory-remote/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.pack-state/autonomy-runs/`
- `eval/history/`
- `dist/exports/runtime-evidence/`
- other local cache or editor-temp directories that are not part of the
  materialized build-pack contract

If a future workflow needs resume-oriented staging that intentionally carries
prior autonomy history or prior exported runtime bundles, that must be added
as an explicit later amendment rather than inferred from directory contents.

The push tool must not stage:

- local factory registry files
- local deployment pointers
- unrelated build-packs
- unrelated local scratch history outside the selected build-pack

The push tool must treat the remote copy as a quarantined execution payload,
not as a mirror that will later be synced back into the local source
build-pack.

Once staged, the copied remote build-pack root is remote execution state, not
local PackFactory truth, even when it contains canonical-looking files such as
`status/*`, `tasks/*`, `contracts/*`, or `eval/*`.

## Target Manifest Contract

V1 should add:

- `docs/specs/project-pack-factory/schemas/remote-execution-payload-manifest.schema.json`

The push tool should write:

- `.packfactory-remote/target-manifest.json`

At minimum it should include:

- `schema_version = remote-execution-payload-manifest/v1`
- `payload_policy_version`
- `source_build_pack_id`
- `source_build_pack_root`
- `run_id`
- `remote_target_label`
- `remote_parent_dir`
- `remote_pack_dir`
- `remote_run_dir`
- `remote_export_dir`
- `remote_host`
- `remote_user`
- `request_sha256`
- `staged_at`
- `staged_by`
- `transport_mode`
- `excluded_paths`
- `payload_entries`
- `control_plane_mutations`

All `control_plane_mutations.*` must be `false`.

Each `payload_entries[*]` record should capture at minimum:

- `relative_path`
- `sha256`
- `size_bytes`

The manifest is the audit record for what was actually staged, not only a note
that a copy operation happened.

## Transport Contract

V1 transport may use:

- `rsync`
- `scp`
- another bounded file-copy primitive

Transport choice is an implementation detail.

The reusable contract is:

- deterministic target paths
- staged manifest output
- no local control-plane mutations
- clean-room remote staging semantics for the working tree
- fail-closed behavior when the remote path cannot be created or the stage copy
  is incomplete

V1 must not rely on merge semantics at the remote pack root.

Before a run becomes executable, the push tool must ensure that the remote
working tree under `remote_pack_dir` is a clean snapshot of the selected local
payload policy.

This may be satisfied by:

- staging into a temporary sibling and then atomically replacing the working
  tree
- or a purge-and-verify flow that removes stale files before the copy is
  accepted

In either case, stale files from prior runs must not survive at the remote
working root outside intentionally separate run metadata under `runs/<run_id>/`.

## Remote Copy Quarantine Rule

The prepared and staged remote build-pack is an execution copy only.

That means:

- the remote copy may later diverge from the local source build-pack
- that divergence is expected once a remote agent begins writing pack-local
  state
- staging tools must not treat later remote mutations as content that should be
  copied or synced back into the local source build-pack

This quarantine applies to the entire staged remote build-pack root, not only
to `.packfactory-remote/`.

The only allowed return path from the remote side is a bounded runtime
evidence bundle handled by later specs in this family.

## Control-Plane Boundary

Neither staging script may update:

- `registry/`
- `deployments/`
- local promotion logs
- local readiness state
- local work-state
- local `eval/latest/index.json`
- local release artifacts

Remote staging is preparation only.

Any local changes must be limited to:

- request files
- local orchestration scratch under non-canonical staging roots
- local staging metadata written by the staging tools themselves
- later pulled runtime evidence outside canonical control-plane truth

No direct copy, sync, or reconcile step in this staging layer may overwrite the
local source build-pack after remote execution begins.

V1 staging tools should document their local writable paths explicitly and
should treat all other local writes as forbidden by default.

## Minimal Validation Plan

Verification for this spec must follow the PackFactory testing policy:

- keep tests intentionally small
- prefer contract-level assertions over broad transport matrices
- protect only the few behaviors that would materially break remote staging

V1 verification should stay absolute minimal and focus on:

- one happy-path request-driven staging flow
- one fail-closed request or path precondition
- one manifest/evidence assertion that proves the staged payload was described
  deterministically

Do not add:

- broad host matrices
- transport-specific test duplication
- deep fixture forests
- tests that restate low-risk shell plumbing

When possible, prefer schema validation, existing factory validation, and small
workflow-style smoke checks over new expansive test files.

## Success Criteria

This spec is satisfied when all of the following are true:

1. A remote target workspace can be prepared from a request file without any
   host-specific hardcoding.
2. The default remote directory names clearly distinguish PackFactory source,
   remote target, and autonomous build-pack purpose.
3. A selected build-pack can be staged to the remote target using reusable
   tooling.
4. The staging tool writes a machine-readable manifest describing what it
   copied.
5. No local factory control-plane files are mutated by target preparation or
   staging.
