# Project Pack Factory Agent Instruction Discoverability For Autonomy And External Runtime Evidence Tech Spec

## Purpose

Define the minimal instruction-layer changes needed so a PackFactory runtime
agent can reliably discover and use the new autonomy handoff surfaces and the
new external runtime evidence export and import workflows.

This spec is about discoverability and operator guidance.

It does not create the autonomy or evidence features themselves. Those now
exist in PackFactory. The gap is that the agent instructions do not yet teach
the runtime agent how to find or use them consistently.

This spec now also sits inside the dashboard era of PackFactory startup:

- the published dashboard is now the normal fast operator briefing surface
- root `load AGENTS.md` behavior should stay concise by default
- instruction-surface changes should optimize scan order and comprehension
  instead of rebuilding longer executive summaries in chat

## Spec Link Tags

```json
{
  "spec_id": "agent-instruction-discoverability-for-autonomy-and-external-runtime-evidence",
  "depends_on": [
    "autonomous-build-pack-handoff-and-work-state",
    "external-build-pack-runtime-evidence-export",
    "external-runtime-evidence-import"
  ],
  "integrates_with": [
    "build-pack-materialization"
  ]
}
```

## Problem

Project Pack Factory now has three important runtime-facing capabilities:

- pack-local autonomy handoff state
- pack-local external runtime evidence export
- factory-level external runtime evidence import

But the current agent instructions do not yet expose those capabilities as a
clear operating model.

Without explicit instruction updates:

- a runtime agent may fail to read the autonomy handoff files even when they
  exist
- a runtime agent may not realize a build-pack can export its own runtime
  evidence when running externally
- a factory-level agent may not realize import is now a supported bounded
  workflow
- agents are more likely to rediscover these surfaces indirectly from code than
  to use them intentionally

## Current Repo Evidence

### Evidence A: Root PackFactory AGENTS Does Not Yet Mention The New Runtime Surfaces

In root [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md), `First Reads`
currently ends with the target pack's `AGENTS.md`, `project-context.md`, and
`pack.json`, and does not mention `contracts/project-objective.json`,
`tasks/active-backlog.json`, `status/work-state.json`,
`entrypoints.export_runtime_evidence_command`, or
`tools/import_external_runtime_evidence.py`.

Interpretation:

- the root instruction layer still reflects the older PackFactory operating
  model
- the new runtime surfaces exist, but the root instructions do not tell an
  agent to look for them

### Evidence B: The Autonomy Handoff Surfaces Are Already Canonical

The current materializer writes `contracts/project-objective.json`,
`tasks/active-backlog.json`, and `status/work-state.json`, the pack schema
models those files in `directory_contract`, and the autonomy handoff spec
already defines them as canonical pack-local control-plane files.

Interpretation:

- these files are no longer experimental side notes
- they should now be part of the runtime agent’s normal traversal behavior

### Evidence C: The Current Materializer Is Coded To Add Export Manifest Fields For Future Python Build-Packs

When `runtime == "python"`, the current materializer adds
`entrypoints.export_runtime_evidence_command` and
`directory_contract.runtime_evidence_export_dir`, and it also writes
`src/pack_export_runtime_evidence.py`.

No current checked-in build-pack manifest is cited here yet as evidence of this
surface.

Interpretation:

- export is machine-discoverable from `pack.json`
- but only if the runtime agent has been told that this new manifest surface is
  meaningful

### Evidence D: External Runtime Evidence Import Exists As A Factory Tool, Not A Pack-Local Surface

Import is implemented as a factory-level tool under `tools/`. Current pack
manifests define `cli_command`, `validation_command`, `benchmark_command`, and
optional `export_runtime_evidence_command`, but no import entrypoint, and the
pack bootstrap and post-bootstrap surfaces remain pack-local.

Interpretation:

- import is discoverable to a factory-level agent that reads tools and specs
- it is not naturally discoverable to a pack-local runtime agent unless the
  instruction layer explains the split

### Evidence E: Pack-Local AGENTS Can Be Stale Relative To The Current Build-Pack Runtime Model

Concrete current example:

- [AGENTS.md](/home/orchadmin/project-pack-factory/build-packs/release-evidence-summarizer-build-pack-v3/AGENTS.md)

Concrete evidence:

- the file still opens with `Release Evidence Summarizer Template Pack`
- it says `Treat this pack as an active source template`
- it does not mention:
  - `contracts/project-objective.json`
  - `tasks/active-backlog.json`
  - `status/work-state.json`

Interpretation:

- pack-local AGENTS files are not yet a reliable guide to the new runtime model
- this example shows drift on autonomy guidance; it does not by itself prove
  export discoverability drift

### Evidence F: The Operator Dashboard Now Exists As The Normal Fast Briefing Surface

PackFactory now ships a published dashboard path under
`.pack-state/factory-dashboard/latest/`, with the canonical Astro publication
wrapper at `tools/build_factory_dashboard_astro.py` and the local operator
viewing path at `tools/serve_factory_dashboard.py`.

Interpretation:

- root startup no longer needs to reconstruct a long executive summary by
  default
- instruction work should optimize for quick orientation, exact fallback
  verification, and lower prompt overhead
- the dashboard should shorten root startup rather than compete with the truth
  layer

## Design Goals

- make the autonomy handoff surfaces explicitly discoverable to runtime agents
- make the export capability explicitly discoverable to eligible build-packs
- make the factory-level import workflow explicitly discoverable to factory
  agents
- make root startup behavior dashboard-first and concise by default
- optimize scan order around project purpose, current state, and current
  trajectory rather than duplicating a long executive summary in chat
- preserve the control-plane/data-plane split in the instruction layer
- keep the instruction changes small and precise

## Non-Goals

This spec does not:

- change the canonical bootstrap order
- move import into a pack-local entrypoint
- make imported runtime evidence canonical control-plane state
- require every pack-local AGENTS file to become a full operational manual
- add new runtime workflows beyond the ones already implemented
- authorize new tests outside the existing PackFactory testing policy

## Required Root Instruction Changes

### 1. Root AGENTS Must Mention The New Runtime Surfaces

The root [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md) must add a
short instruction block explaining that:

- newly materialized build-packs may carry:
  - `contracts/project-objective.json`
  - `tasks/active-backlog.json`
  - `status/work-state.json`
- those files are canonical pack-local control-plane handoff surfaces for the
  selected build-pack when declared by `pack.json.directory_contract` or
  included in `pack.json.post_bootstrap_read_order`
- after the operator confirms the intended build-pack, the agent should read
  those files when the manifest declares them; do not infer them from
  directory contents alone

### 2. Root AGENTS Must Mention Export As A Pack-Local Capability

The root [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md) must tell
the agent that:

- newly materialized Python build-packs may expose
  `pack.json.entrypoints.export_runtime_evidence_command`
- when the task concerns an externally running build-pack or exporting local
  runtime evidence, the agent should inspect `pack.json.entrypoints` and
  `pack.json.directory_contract` for that capability

### 3. Root AGENTS Must Mention Import As A Factory-Level Workflow

The root [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md) must tell
the agent that:

- external runtime evidence import is a factory-level bounded workflow
- the canonical tool is:
  - `tools/import_external_runtime_evidence.py`
- import is not a pack-local runtime command
- import preserves audit-only evidence under `eval/history/` and does not
  directly change readiness, work-state, deployment, or registry state

## Required Pack-Local Instruction Changes

### 1. Materialized Build-Packs Must Carry A Current Build-Pack AGENTS File

The build-pack materialization workflow should stop inheriting a template-only
instruction voice for ordinary build-packs.

After template copy, materialization must generate or overwrite `AGENTS.md` for
the derived build-pack. Copying the template `AGENTS.md` unchanged is not
sufficient. If `AGENTS.md` is rewritten, the materialization report should
record a distinct action for that rewrite.

For newly materialized build-packs, the pack-local `AGENTS.md` should:

- identify the pack as a `build pack`, not a source template
- keep the bootstrap order short
- direct the agent to read:
  - `status/lifecycle.json`
  - `status/readiness.json`
  - `status/deployment.json`
  - `contracts/project-objective.json` when present
  - `tasks/active-backlog.json` when present
  - `status/work-state.json` when present

### 2. Eligible Build-Packs Must Mention Export Discoverability

For newly materialized Python build-packs that carry
`entrypoints.export_runtime_evidence_command`, the pack-local `AGENTS.md`
should state:

- this build-pack can export bounded runtime evidence when running externally
- the canonical invocation surface is `pack.json.entrypoints.export_runtime_evidence_command`
- exported bundles remain supplementary runtime evidence only

### 3. Pack-Local AGENTS Must Not Blur Import Authority

Pack-local `AGENTS.md` files must not imply that the build-pack can import its
own external evidence or that imported evidence is a pack-local authority
surface.

Import remains a factory-level workflow.

`project-context.md` may remain inherited template problem framing. When it
differs from materialized build-pack runtime state, authority belongs to
`pack.json`, `status/*.json`, `contracts/project-objective.json`,
`tasks/active-backlog.json`, and `status/work-state.json`.

## Discoverability Rules

### Rule 1: Autonomy Files Must Be Discoverable Through The Pack Manifest

After the operator confirms the target build-pack, the runtime agent should:

1. read `AGENTS.md`, `project-context.md`, and `pack.json`
2. use `pack.json.post_bootstrap_read_order` as the canonical
   post-bootstrap traversal list
3. use `pack.json.directory_contract` to resolve
   `contracts/project-objective.json`, `tasks/active-backlog.json`, and
   `status/work-state.json` when those surfaces are declared

Root and pack-local `AGENTS.md` files may call out these surfaces for
discoverability, but they must not restate a competing canonical read order.

### Rule 2: Export Is Discoverable From The Pack Manifest

If `pack.json.entrypoints.export_runtime_evidence_command` exists, the runtime
agent may treat export as a supported bounded pack-local capability.

If the field is absent, the agent must not assume export exists.

### Rule 3: Import Remains A Factory-Level Workflow

The runtime agent should treat external runtime evidence import as a
factory-level workflow discoverable from root PackFactory instructions and
`tools/import_external_runtime_evidence.py`.

Pack-local `AGENTS.md` may mention import only to redirect the agent back to
that factory-level workflow. They must not present import as a pack-local
entrypoint, pack-local command, or pack-local authority surface.

## Authority Clarification

The instruction layer must state this explicitly:

- `contracts/project-objective.json`, `tasks/active-backlog.json`, and
  `status/work-state.json` are canonical pack-local control-plane files
- they guide pack-local execution but do not override factory-level authority
  for registry state, deployment pointers, lifecycle state, readiness state,
  or `eval/latest/index.json`
- export bundles are supplementary runtime evidence only
- imported external runtime evidence is audit-only preserved evidence

## Implementation Notes

This spec should be implemented in two small places:

- root [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md)
- build-pack materialization so newly materialized build-packs get a current
  build-pack-oriented `AGENTS.md`

Existing historical build-packs may remain as-is until a separate migration
pass is approved.

No `tools/validate_factory.py` behavior change is required by this spec.

## Minimal Validation Plan

Modify
`tests/test_materialize_build_pack.py::test_materialize_build_pack_happy_path_creates_pack_and_registry`
in place only.

Keep validation minimal:

- do not add a new test case
- do not add a new test file
- do not add validator-specific checks for AGENTS prose
- do not add a broader workflow matrix
- keep assertions to a few stable markers in generated `AGENTS.md` rather than
  a full prose snapshot
