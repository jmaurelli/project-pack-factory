# Project Pack Factory Agent-Native Project Initialization Tech Spec

## Status

Draft v1 specification for making agent-operable project setup an explicit
PackFactory control-plane feature rather than an emergent property of a few
well-configured build-packs.

## Goal

PackFactory should support `agent-native project initialization`, meaning a
project can be initialized with an explicit machine-readable declaration that:

- the agent is expected to operate from the beginning of the project lifecycle
- the agent has a declared framing lens and collaboration mode when selected
- the agent has canonical objective and execution-tracker surfaces
- the agent can discover tooling, memory, and autonomy boundaries without
  reconstructing them from prose alone

This model should stay:

- optional
- additive to the current PackFactory control plane
- compatible with template reuse
- declaration-only in V1
- clear about the difference between canonical execution state and advisory
  planning or memory

## Problem

PackFactory already produces projects that are often agent-operable in
practice, but that behavior is currently assembled from multiple adjacent
surfaces:

- optional personality overlays
- optional role/domain overlays
- optional memory systems
- canonical objective/backlog/work-state files on build-packs
- entrypoints and directory-contract declarations

That is close to an `agent-native` model, but it is not yet declared as one.
So a fresh agent can often infer the pattern, but the project was not
explicitly initialized around that operating model.

The result is:

- agent-centered operation is real but not first-class
- initialization intent is harder to discover than it should be
- planner-versus-tracker behavior is implicit rather than declared
- future templates can inherit good structure without explicitly declaring why
  that structure exists

## Adversarial Review Tightenings

The v1 boundary is intentionally narrow:

- the profile is a declaration, not a runtime subsystem or a second planner
  file
- `agent_native_project_profile` only matters when enabled and resolved into
  startup surfaces
- the suggested `planning_artifacts` array stays empty in V1 unless a later
  spec explicitly introduces bounded planning artifacts
- generated `AGENTS.md` and `project-context.md` snippets stay short and do
  not repeat the full tracker or planning contents

The practical effect is that the model becomes explicit without inventing a
new execution plane.

## Desired Model

PackFactory should support one optional profile that can be declared at
template creation and activated at build-pack materialization:

- `agent_native_project_profile`

That profile should answer:

- should this line be treated as agent-native from the first real build-pack
- how should the agent discover tooling
- what memory model should the agent expect
- what work-management model is in force
- what autonomy boundary applies

The profile should not:

- replace canonical lifecycle, readiness, deployment, or registry truth
- create a second execution control plane
- imply broad unsupervised autonomy beyond PackFactory's bounded workflows
- force every template or build-pack into an agent-native mode

## Evidence

PackFactory already has most of the runtime contract pieces needed for this
model.

### Evidence A: Build-packs already carry canonical execution state

The autonomous handoff spec already defines:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

as the canonical execution surfaces for build-packs:

- [PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md)

This means the core `agent-native` execution contract already exists for
build-packs. The gap is making that model explicit earlier in initialization.

### Evidence B: Materialization already synthesizes the agent-operable tracker

The build-pack materializer already writes the canonical execution files into
derived build-packs and advertises them through `pack.json.directory_contract`
and `pack.json.post_bootstrap_read_order`:

- [tools/materialize_build_pack.py](/home/orchadmin/project-pack-factory/tools/materialize_build_pack.py)
- [PROJECT-PACK-FACTORY-BUILD-PACK-MATERIALIZATION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-BUILD-PACK-MATERIALIZATION-TECH-SPEC.md)
- [pack.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/pack.schema.json)

That means PackFactory already knows how to create an agent-operable build-pack
from a template; it simply does not yet declare that as an explicit model.

### Evidence C: Template creation already carries planning intent

The template-creation workflow already preserves operator planning information
through `planning_summary` in both request and report surfaces:

- [template-creation-request.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/template-creation-request.schema.json)
- [template-creation-report.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/template-creation-report.schema.json)
- [PROJECT-PACK-FACTORY-TEMPLATE-PLANNING-AND-CREATION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TEMPLATE-PLANNING-AND-CREATION-TECH-SPEC.md)

That is a natural insertion point for declaring agent-native initialization
intent at project birth instead of only after the first build-pack exists.

### Evidence D: PackFactory already supports optional framing layers

PackFactory now has explicit optional overlays for:

- personality
- role/domain

through request schemas, manifests, catalogs, generated `AGENTS.md`, and
materialization logic:

- [agent-personality-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-personality-template-catalog.json)
- [agent-role-domain-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-role-domain-template-catalog.json)
- [tools/create_template_pack.py](/home/orchadmin/project-pack-factory/tools/create_template_pack.py)
- [tools/materialize_build_pack.py](/home/orchadmin/project-pack-factory/tools/materialize_build_pack.py)

This is the right adjacent control-plane pattern to mirror for agent-native
initialization.

### Evidence E: Root PackFactory work already models planner-versus-tracker separation

The root itself already behaves like:

- tracker: `contracts/project-objective.json`, `tasks/active-backlog.json`,
  `status/work-state.json`
- advisory planning/memory: planning list, dashboard, factory memory

Concrete surfaces:

- [contracts/project-objective.json](/home/orchadmin/project-pack-factory/contracts/project-objective.json)
- [tasks/active-backlog.json](/home/orchadmin/project-pack-factory/tasks/active-backlog.json)
- [status/work-state.json](/home/orchadmin/project-pack-factory/status/work-state.json)
- [PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md)
- [.pack-state/agent-memory/latest-memory.json](/home/orchadmin/project-pack-factory/.pack-state/agent-memory/latest-memory.json)

That means the broader control-plane philosophy already matches the proposed
agent-native model.

## Proposed Control-Plane Addition

Add one optional manifest/request/report surface:

- `agent_native_project_profile`

V1 should be a declaration, not a new autonomous runtime subsystem.

It should minimally declare:

- `enabled`
- `initialization_scope`
- `memory_model`
- `tooling_awareness_mode`
- `autonomy_boundary_mode`
- `work_management_model`

### Suggested V1 Shape

```json
{
  "enabled": true,
  "initialization_scope": "template_declared_build_pack_activated",
  "memory_model": "canonical_tracker_plus_advisory_memory",
  "tooling_awareness_mode": "pack_manifest_entrypoints_and_directory_contract",
  "autonomy_boundary_mode": "bounded_packfactory_control_plane",
  "work_management_model": {
    "canonical_tracker_mode": "objective_backlog_work_state",
    "planner_mode": "tracker_backed_planning",
    "objective_file": "contracts/project-objective.json",
    "task_backlog_file": "tasks/active-backlog.json",
    "work_state_file": "status/work-state.json",
    "planning_artifacts": []
  }
}
```

V1 interpretation:

- templates declare the intended build-pack operating model
- build-packs activate the model concretely
- planning remains tracker-backed and advisory rather than becoming a second
  primary state machine
- the declaration stays bounded to the existing PackFactory control plane

## Initialization Scope

The profile should support two clean stages:

- `template_declared_build_pack_activated`
  - the template declares the intended agent-native operating model for future
    derived build-packs
- `pack_active`
  - the build-pack is already operating under that model with concrete control
    plane surfaces

This keeps template truth honest while still letting PackFactory declare the
model from project initialization.

## Interaction With Existing Overlays

The `agent_native_project_profile` is adjacent to, not a replacement for:

- `personality_template`
- `role_domain_template`

Layering order:

1. canonical PackFactory control-plane truth
2. `agent_native_project_profile`
3. role/domain overlay
4. personality overlay
5. advisory memory and dashboard/briefing layers

Why this matters:

- the agent-native profile declares how the project is meant to operate
- overlays declare how the agent frames and communicates inside that model

## Generated Startup Surfaces

When present, generated `AGENTS.md` and `project-context.md` should surface a
short `Agent-Native Initialization` section that tells a fresh agent:

- this line is agent-native
- where the canonical tracker lives
- how tooling awareness should be discovered
- that planner context is advisory and tracker-backed
- what autonomy boundary applies

The section should stay concise and must not repeat the full tracker or
planning contents.

## V1 Implementation Slice

The smallest real control-plane implementation is:

1. add optional `agent_native_project_profile` to template-creation
   `planning_summary`
2. add optional `agent_native_project_profile_selection` to build-pack
   materialization requests
3. add optional `agent_native_project_profile` to `pack.json`
4. surface the profile in generated `AGENTS.md` and `project-context.md`
5. record the resolved profile in creation/materialization reports

This is enough to make the model real without inventing a new planner file,
runtime subsystem, or validation matrix.

## Non-Goals

- introducing a second execution control plane beside
  objective/backlog/work-state
- forcing agent-native initialization onto every template or build-pack
- requiring a runtime memory subsystem that every current product line does
  not yet have
- inventing broad unsupervised autonomy semantics beyond current PackFactory
  workflows

## Success Criteria

- a template can declare an agent-native initialization model at creation time
- a materialized build-pack can inherit or override that model explicitly
- a fresh agent can discover the model from manifest + startup docs
- the current canonical tracker remains the only execution authority
- factory validation remains green after the change
