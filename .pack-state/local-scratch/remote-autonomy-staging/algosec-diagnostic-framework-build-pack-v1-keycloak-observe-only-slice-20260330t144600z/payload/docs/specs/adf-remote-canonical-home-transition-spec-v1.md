# ADF Remote Canonical Home Transition Spec v1

## Purpose

Define the future-mode transition needed if `adf-dev` becomes the canonical
home for the ADF build pack while Local PackFactory remains the factory control
plane.

This is a planning specification only. It does not change the current
ownership model.

## Current Model

Today the reviewed model is:

- Local PackFactory is the canonical ADF planner, state accepter, and durable
  evidence owner
- `adf-dev` is the remote execution worker and review surface
- the target lab is the runtime evidence source

That current rule is still the active contract.

## Target Future Model

The future model under consideration is:

- Local PackFactory remains canonical for factory tooling, registry,
  promotions, cross-pack orchestration, and cross-run learning
- `adf-dev` becomes canonical for day-to-day ADF pack content, state, review
  surfaces, and remote execution continuity
- the target lab remains the runtime evidence source

In plain language:

- Local PackFactory owns the factory
- `adf-dev` owns ADF
- the target lab owns runtime facts

## What Would Change

### 1. Ownership contract

The current local-vs-remote ownership contract would need a reviewed new mode
beyond the current local-canonical default.

Suggested future mode name:

- `L3_remote_canonical_adf_pack`

That mode should be explicit, not inferred from successful remote runs.

### 2. Instruction surfaces

The current ADF instruction layer still says Local PackFactory is canonical.

These surfaces would need reviewed updates:

- `AGENTS.md`
- `project-context.md`
- `pack.json`
- `docs/specs/adf-local-vs-remote-execution-ownership-contract-v1.md`
- `docs/specs/adf-three-node-autonomy-contract-v1.md`
- `docs/specs/adf-remote-runtime-decoupling-plan-v1.md`

### 3. Machine-readable ownership state

The pack-local control surfaces would need explicit ownership fields that can
say:

- canonical ADF home = `adf-dev`
- Local PackFactory role = factory control plane
- remote ADF role = canonical ADF content and state owner

Primary machine-readable surfaces:

- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`

### 4. Push and pull semantics

This is the most important tooling shift.

Today the remote push path treats the local pack as authoritative and replaces
the entire remote pack directory during refresh.

If `adf-dev` becomes canonical for ADF, the normal control path should change
to something closer to:

- bootstrap from local once
- let `adf-dev` remain the ongoing canonical ADF workspace
- pull accepted ADF state and evidence back to Local PackFactory when needed
- push only factory-level control inputs, explicit overlays, or reviewed
  recovery refreshes

That means the existing whole-directory remote replacement path is not the
right steady-state model for remote-canonical ADF.

### 5. Acceptance rules

Local PackFactory would still accept and preserve factory-relevant outputs, but
ADF pack-local state and content could originate canonically from `adf-dev`.

This means acceptance rules would need to distinguish:

- ADF-local canonical changes that originate on `adf-dev`
- factory-level accepted evidence and promotions that still belong to Local
  PackFactory

## What Should Still Stay Local

Even in the future remote-canonical ADF mode, these should remain Local
PackFactory responsibilities:

- factory tooling and schemas
- registry truth
- deployment truth
- pack promotion decisions
- template inheritance and promotion decisions
- cross-pack metrics and autonomy scoring
- factory-wide memory and orchestration logic

## What Could Become Remote-Canonical

The first candidate remote-canonical surfaces are:

- ADF pack-local docs and specs
- ADF pack-local playbook content
- ADF pack-local generated review surfaces
- ADF pack-local execution continuity state
- ADF pack-local agent memory used for the ongoing ADF project

This should start narrow. Do not move every surface at once.

## Migration Strategy

The clean path is:

1. define the new reviewed mode explicitly
2. decide the exact ADF surfaces that become remote-canonical first
3. update instruction and state surfaces to reflect that mode
4. update push and pull semantics so local no longer overwrites the remote ADF
   home by default
5. prove restart continuity and evidence return under the new model
6. only then treat `adf-dev` as the canonical ADF home in normal operations

## Why This Matters

This model gives stronger separation:

- Local PackFactory stays focused on factory governance
- `adf-dev` becomes the natural long-lived ADF runtime and authoring home
- the review surface and the canonical ADF content live in the same place
- the target lab stays only the runtime evidence plane

That should reduce confusion between:

- remote worker copy
- remote runtime surface
- remote canonical ADF project state

## Current Decision

Do not assume this mode is active yet.

Current status:

- useful future direction
- not the active ownership contract
- requires a reviewed transition plan before implementation

## Related Contracts

- [adf-local-vs-remote-execution-ownership-contract-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-local-vs-remote-execution-ownership-contract-v1.md)
- [adf-three-node-autonomy-contract-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-three-node-autonomy-contract-v1.md)
- [adf-remote-runtime-decoupling-plan-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-remote-runtime-decoupling-plan-v1.md)
