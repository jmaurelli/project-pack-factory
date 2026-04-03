# Project Context

This build pack was materialized from template `algosec-diagnostic-framework-successor-template-pack` and is the active runtime root for `AlgoSec Diagnostic Framework Successor Build Pack v1`.

The project goal carried forward from the template is:

- Create a bounded agent-centered ADF successor template that learns from incomplete technical documentation plus live Rocky 8 appliance discovery, builds machine-readable diagnostic content first, and proves value through an early shallow surface map slice before deeper dependency or predictive work.

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

## Runtime Ownership

The current reviewed operating model is:

- PackFactory root is the canonical build-pack home and control plane
- `adf-dev` is the operational runtime home
- the downstream Rocky 8 or appliance target at `10.167.2.150` is the observed runtime source
- `adf-dev` is currently reachable at `10.167.2.151` and also serves the
  support-facing diagnostic pages consumed by support engineers

Keep remote runtime work heavy and local return thin. The normal return path is
bounded exported runtime evidence plus intentional source or tracker changes,
not a full copy-back of the staged remote workspace.

## Lab Posture

The current successor lab posture is operator-provided and intentionally more
exploratory than a fragile customer environment:

- the current target lab at `10.167.2.150` is quickly redeployable
- bounded misconfiguration or temporary lab breakage is acceptable during
  discovery work
- later distributed-architecture labs are expected as future discovery targets

## Optional Overlays

Treat `pack.json.personality_template` and `pack.json.role_domain_template` as composable guidance layers. They shape tone and framing, not canonical lifecycle, readiness, deployment, or tracker truth.

## Line-Specific Role/Domain Lens

This build pack currently uses the line-specific `diagnostic-systems-analyst`
lens recorded in:

- `docs/specs/adf-successor-diagnostic-systems-analyst-role-domain-lens-v1.md`

Use it to keep the first wave focused on bounded live system mapping,
machine-readable diagnostic structure, and support-useful stop points.
For the current first wave, also use:

- `docs/specs/adf-successor-shallow-surface-map-first-slice-v1.md`
- `docs/specs/adf-successor-remote-owned-runtime-thin-local-canonical-return-contract-v1.md`

## Derived From

- Source template: `algosec-diagnostic-framework-successor-template-pack`
- Build pack: `algosec-diagnostic-framework-successor-build-pack-v1`
