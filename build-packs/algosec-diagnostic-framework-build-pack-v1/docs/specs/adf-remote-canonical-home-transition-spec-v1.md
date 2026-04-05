# ADF Remote Canonical Home Transition Spec v1

## Purpose

Define the future-mode transition needed if `adf-dev` becomes the canonical
home for the ADF build pack while Local PackFactory remains the factory control
plane.

This is a planning specification only. It does not change the current
ownership model.

Current planning line:

- `define_remote_canonical_adf_home_transition`

This note exists so the future transition is tracked as a named planning line
instead of being inferred from successful remote runs or repeated restaging.

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

### 4a. Current friction that motivates the change

The March 30, 2026 live Keycloak page review on `adf-dev` exposed the exact
operator friction this future mode is meant to reduce.

Observed under the current local-canonical model:

- the live preview host answered, but the rendered Keycloak page still showed
  older staged content instead of the current local accepted content
- an old preview process was still running from a deleted working directory,
  which made the URL look alive while returning `404` for routes that existed in
  the replacement workspace
- an older remote request surface had drifted out of the current PackFactory
  schema, so the clean restage path depended on choosing the newer request file
- after a valid restage, the remote Starlight review surface still needed
  regeneration, dependency reinstall, static rebuild, and preview restart before
  the operator-visible page matched the current local pack

In plain language:

- "restage to `adf-dev`" is still too indirect as an operator mental model
- the review surface, the staged source, and the preview process can all be out
  of sync with each other even when the remote host is healthy

This does not activate remote-canonical mode by itself. It does show why a
later reviewed remote-canonical ADF mode could remove a real class of friction:
the rendered review surface and the active ADF working copy would stop depending
on repeated whole-pack replacement from Local PackFactory for normal day-to-day
content review

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
- the reviewed transition remains future-mode until the planner and readiness
  surfaces explicitly accept a new ownership mode
- future agents should return to this note when revisiting the handoff, but
  should not treat it as proof that `adf-dev` already owns the ADF pack

## Related Contracts

- [adf-local-vs-remote-execution-ownership-contract-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-local-vs-remote-execution-ownership-contract-v1.md)
- [adf-three-node-autonomy-contract-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-three-node-autonomy-contract-v1.md)
- [adf-remote-runtime-decoupling-plan-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-remote-runtime-decoupling-plan-v1.md)
