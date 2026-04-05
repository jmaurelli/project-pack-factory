# Project Context

This build pack was materialized from template `agent-native-project-initialization-smoke-template-pack` and is the active runtime root for `Agent-Native Project Initialization Smoke Build Pack`.

The project goal carried forward from the template is:

- Prove the declaration-only agent-native initialization flow through template creation and build-pack materialization.

## Priority

1. Keep the build-pack control plane authoritative.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack easy for a fresh agent to inspect and continue.

## Primary Runtime Surfaces

- `pack.json`
- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
- optional feedback memory: `.pack-state/agent-memory/latest-memory.json`
- optional template lineage memory: `.pack-state/template-lineage-memory/latest-memory.json`

## Agent-Native Initialization

This build pack is operating with the PackFactory tracker-backed agent-native profile active.
This profile is descriptive only; canonical tracker discovery still comes from `pack.json.directory_contract` and `pack.json.post_bootstrap_read_order`.
Profile: `packfactory_tracker_backed_agent_native` (PackFactory Tracker-Backed Agent-Native).
Activation state: `build_pack_active`.
Work management model: `objective_backlog_work_state` / `tracker_backed_advisory_planning`.
Advisory planning does not override the canonical execution tracker.
This active mode was inherited from the template declaration during materialization.

## Template Lineage Note

The template remains the source-of-truth for reusable scaffold intent, but the build pack is the live control-plane instance.

## Optional Overlays

Treat `pack.json.personality_template` and `pack.json.role_domain_template` as composable guidance layers. They shape tone and framing, not canonical lifecycle, readiness, deployment, or tracker truth.

## Derived From

- Source template: `agent-native-project-initialization-smoke-template-pack`
- Build pack: `agent-native-project-initialization-smoke-build-pack-v1`
