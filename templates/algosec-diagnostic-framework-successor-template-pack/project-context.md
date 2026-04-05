# Project Context

This template was created to support the following project goal:

- Create a bounded agent-centered ADF successor template that learns from incomplete technical documentation plus live Rocky 8 appliance discovery, builds machine-readable diagnostic content first, and proves value through an early shallow surface map slice before deeper dependency or predictive work.

## Priority

1. Keep the template valid for PackFactory traversal and later materialization.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack easy for a fresh agent to inspect.

## Primary Runtime Surfaces

- `src/algosec_diagnostic_framework_successor_template_pack/cli.py`
- `src/algosec_diagnostic_framework_successor_template_pack/validate_project_pack.py`
- `src/algosec_diagnostic_framework_successor_template_pack/benchmark_smoke.py`
- `benchmarks/active-set.json`
- `benchmarks/declarations/algosec-diagnostic-framework-successor-template-pack-smoke-small-001.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
- optional template lineage memory: `.pack-state/template-lineage-memory/latest-memory.json`

## Agent-Native Initialization

This template declares a default agent-native posture for future derived build-packs.
It does not claim active pack-local tracker files here; build-pack materialization is where live activation can happen.
Profile: `packfactory_tracker_backed_agent_native` (PackFactory Tracker-Backed Agent-Native).
Activation state: `template_declared`.
Work management model: `objective_backlog_work_state` / `tracker_backed_advisory_planning`.
When a derived build-pack activates this profile, discover tracker surfaces through `pack.json.directory_contract` and `pack.json.post_bootstrap_read_order`.
Default for derived build-packs: `true`.
Treat this profile as declaration-only until a derived build-pack activates it.

## Factory-Level Inheritance Note

This template is a source template, not the canonical home of the autonomy
baseline.

For inherited PackFactory defaults around agent memory, feedback loops,
restart behavior, rehearsal evidence, and branch-choice policy, prefer the
factory-level state brief and operations note:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`

When present, the template-local lineage memory at
`.pack-state/template-lineage-memory/latest-memory.json` is the shortest path
to template-family learning that has already been distilled from derived
build-packs.

That inherited baseline now also includes startup-compliance expectations for
remote Codex session management and runtime-evidence flow:

- prefer PackFactory-local remote-session workflows from the factory root
- do not treat ad hoc `ssh` prompts or raw stdout/stderr logs as canonical
  PackFactory evidence
- return to the factory root for external runtime-evidence import

## Optional Overlays

When `pack.json.personality_template` exists, treat it as an optional overlay
for briefing tone, recommendation framing, and operator-facing collaboration.

When `pack.json.role_domain_template` exists, treat it as an optional overlay
for problem framing, default task heuristics, and functional perspective.

These overlays should stay composable with the template itself:

- one source template can still feed multiple build-packs with different
  overlay combinations
- personality guidance should shape tone and collaboration posture, not role
  authority or operator-specific runtime truth
- role/domain guidance should shape problem framing and default heuristics, not
  tone, identity, or literal credentials
- overlays should not replace the project goal, runtime surfaces, or
  control-plane files
- canonical lifecycle, readiness, deployment, and promotion state always win
  over overlay guidance when they point in different directions

## Line-Specific Role/Domain Lens

This template family currently uses the line-specific `diagnostic-systems-analyst`
lens recorded in:

- `docs/specs/adf-successor-diagnostic-systems-analyst-role-domain-lens-v1.md`

Use that contract as the active ADF-specific framing layer for future derived
build-packs until the lens is either promoted into the shared catalog or
replaced by a later family-specific revision.
