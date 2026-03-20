# Project Pack Factory Runtime Agent Memory Tech Spec

## Purpose

Define how runtime agent memory is built into the canonical PackFactory
build-pack runtime without creating a second control plane.

This spec covers the runtime subsystem agents use to recover:

- current goals
- environment anchors
- execution history
- blockers
- decisions
- next actions

It does not replace PackFactory identity, lifecycle, readiness, deployment, or
retirement state.

## Spec Link Tags

```json
{
  "spec_id": "runtime-agent-memory",
  "depends_on": [
    "directory-hierarchy"
  ],
  "integrates_with": [
    "build-pack-materialization",
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration",
    "retire-workflow"
  ],
  "historical_examples": [
    "templates/agent-memory-first-template-pack",
    "build-packs/agent-memory-first-build-pack"
  ],
  "follow_on_work": [
    "validator-aware runtime-memory status surfaces if PackFactory later chooses to make them canonical"
  ]
}
```

## Related Specs

This spec extends and must remain consistent with:

- `PROJECT-PACK-FACTORY-DIRECTORY-HIERARCHY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-MATERIALIZATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-CI-CLOUD-DEPLOYMENT-ORCHESTRATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-RETIRE-WORKFLOW-TECH-SPEC.md`

## Spec Status

This is a v1 integration spec for the existing agent-memory prototype.

In v1:

- runtime agent memory is a built-in runtime subsystem, not a pack type
- PackFactory control-plane authority remains unchanged
- the existing `agent-memory/v1`, `agent-memory-reader/v1`, and
  `agent-memory-benchmark/v1` payloads remain the wire-compatible contracts
- the existing benchmark id and readiness gate remain canonical

This spec does not currently make any new runtime-memory file part of the
stable PackFactory bootstrap or validator contract.

## Current Evidence Anchors

The current PackFactory-native example source is:

- `templates/agent-memory-first-template-pack`

The current canonical template with the mature agent-memory implementation is:

- `templates/ai-native-codex-package-template`

The retired isolated-memory build-pack experiment remains historical evidence
only:

- `build-packs/agent-memory-first-build-pack`

The pre-PackFactory repo-local predecessor is also relevant historical context:

- `/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template`

## Problem

PackFactory now has concrete specs for:

- directory hierarchy and pack-local state
- build-pack materialization
- build-pack promotion
- CI and cloud deployment orchestration
- retirement-aware lifecycle management

What remained underspecified was how an agent recovers runtime context while
actively building software inside a pack.

Without a runtime-memory contract:

- restart behavior drifts between packs
- handoffs depend on ad hoc notes
- readiness evidence for restart quality is inconsistent
- agents cannot tell how runtime memory relates to canonical PackFactory state

## Design Goals

- runtime memory must be a core runtime subsystem of the build pack
- runtime memory must remain subordinate to PackFactory control-plane state
- agents must recover goals, environment, history, blockers, decisions, and
  next actions deterministically
- the subsystem must reuse the live prototype contract wherever possible
- restart quality must be benchmarkable through the existing readiness model
- the subsystem must integrate with materialization, promotion, CI, and
  retirement without introducing split-brain authority

## Non-Goals

This spec does not define:

- a remote memory service
- human-authored free-form notes as an authority surface
- a new pack kind
- a new bootstrap file
- a new `status/` authority file for runtime memory in v1
- deployment or promotion bypasses based on runtime memory alone

## Authority Model

PackFactory control-plane authority remains:

- `pack.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/retirement.json`
- `status/deployment.json`
- `lineage/source-template.json` for build packs
- `benchmarks/active-set.json`
- `eval/latest/index.json`
- `eval/history/*`
- factory registries and deployment pointers

Runtime agent memory is runtime-local advisory state.

If runtime memory disagrees with canonical PackFactory state:

- canonical PackFactory state wins
- runtime memory is treated as stale or incomplete context

## Traversal Contract

PackFactory bootstrap remains unchanged:

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`

Post-bootstrap traversal also remains unchanged:

- agents must read the pack’s canonical `status/`, `benchmarks/active-set.json`,
  and `eval/latest/index.json` surfaces first
- runtime memory is consulted only after canonical state when the agent is
  continuing active work, recovering from interruption, or handing work off

In v1, agents should not expect a new canonical `status/runtime-memory.json`
file.

Instead, agents should discover runtime memory through:

- pack entrypoints in `pack.json`
- the benchmark/readiness evidence already indexed in
  `status/readiness.json` and `eval/latest/index.json`
- the pack-local runtime-memory storage root when the task explicitly requires
  deeper runtime inspection

## Canonical V1 Runtime Surface

For runtime-memory-enabled packs, the canonical v1 surface is:

- runtime commands:
  - `record-agent-memory`
  - `read-agent-memory`
  - `benchmark-agent-memory`
- contracts:
  - `contracts/agent-memory.schema.json`
  - `contracts/agent-memory-reader.schema.json`
- benchmark declaration id:
  - `agent-memory-restart-small-001`
- readiness gate id:
  - `agent_memory_restart_small_001`
- benchmark evidence artifacts:
  - `agent-memory-scorecard.json`
  - `agent-memory-snapshot.json`
- pack-local mutable storage root for factory-native packs:
  - `.pack-state/agent-memory/`

The runtime-memory subsystem is enabled per pack through existing control-plane
surfaces:

- `pack.json.entrypoints`
- `benchmarks/active-set.json`
- `status/readiness.json.required_gates`
- `eval/latest/index.json`

## Historical Mapping

The review identified a real compatibility boundary between earlier and newer
work. This spec makes that mapping explicit.

Factory-native canonical local state is:

- `.pack-state/agent-memory/`

The earlier repo-local prototype used a package-hidden root:

- `.ai-native-codex-package-template/agent-memory/`

For PackFactory-native packs:

- `.pack-state/agent-memory/` is the preferred local storage root

For imported or historical predecessor implementations:

- the older package-hidden storage root remains acceptable compatibility
  evidence
- the payload shape remains the important contract, not the older storage root

Benchmark and gate naming are intentionally unchanged from the prototype:

- benchmark id: `agent-memory-restart-small-001`
- readiness gate id: `agent_memory_restart_small_001`

## Local Storage Contract

Runtime memory is mutable local state.

For PackFactory-native packs, live runtime-memory artifacts must live under:

- `.pack-state/agent-memory/`

Recommended subpaths are:

- `.pack-state/agent-memory/`
- `.pack-state/agent-memory/revisions/`

Live runtime-memory artifacts must not be treated as stable control-plane
authority and must not be written under:

- `status/`
- `deployments/`
- `registry/`

Live runtime-memory artifacts must never be copied into:

- `dist/exports/`
- `dist/candidates/`
- `dist/releases/`

## Scope Model

The live v1 runtime-memory model is keyed by:

- absolute `project_root`
- optional `task_name`

This matches the shipped agent-memory implementation and avoids assuming that
control-plane IDs such as task-run IDs or session IDs exist in every pack-local
runtime.

In v1:

- `task_name` is a filter and handoff label
- control-plane IDs may appear only as optional contextual evidence
- no PackFactory contract depends on `task_id`, `session_id`, `run_id`, or
  `agent_id` being present in every runtime-memory artifact

## Entry Contract

The raw memory artifact remains wire-compatible with:

- `agent-memory/v1`

The PackFactory reference schema for this contract is:

- `schemas/runtime-memory-entry.schema.json`

That schema intentionally mirrors the live runtime payload shape rather than
inventing a new one.

Required fields include:

- `schema_version`
- `generated_at`
- `producer`
- `project_root`
- `memory_id`
- `task_name`
- `memory_type`
- `importance`
- `status`
- `summary`
- `details`
- `next_actions`
- `tags`
- `file_paths`
- `evidence_paths`
- `goal_state`
- `environment_context`
- `history_context`

The v1 path contract remains wire-compatible with the live prototype:

- `project_root` is absolute
- environment anchors such as task-record, delegation-brief, run-manifest,
  telemetry, and project-context references remain absolute when recorded from a
  live workspace
- `file_paths` may still point to pack-relative source files, matching the
  existing implementation

## Snapshot Contract

The derived reader payload remains wire-compatible with:

- `agent-memory-reader/v1`

The PackFactory reference schema for this contract is:

- `schemas/runtime-memory-snapshot.schema.json`

The required top-level sections are:

- `schema_version`
- `reader`
- `project_root`
- `task_name_filter`
- `retrieval_focus`
- `local_artifact_counts`
- `prioritized_memories`
- `omitted_active_memories`
- `restart_state`
- `handoff_summary`
- `notes`

The snapshot contract must preserve two agent-critical behaviors:

- active important memories are prioritized first
- omitted active memories remain visible rather than disappearing from restart
  state

## Retrieval Contract

The default retrieval behavior remains aligned with the live implementation:

1. active memories before resolved or archived memories
2. importance before memory type
3. type priority:
   - `blocker`
   - `next_step`
   - `decision`
   - `validation`
   - `lesson`
   - `context`
4. newest first within ties

The reader payload must continue to expose:

- prioritized selected memories
- omitted active memories
- aggregated restart state
- compact handoff next actions

## Benchmark Contract

The canonical runtime-memory readiness benchmark remains:

- `agent-memory-restart-small-001`

The scorecard payload remains wire-compatible with:

- `agent-memory-benchmark/v1`

The PackFactory reference schema for this contract is:

- `schemas/runtime-memory-benchmark-report.schema.json`

The benchmark continues to produce PackFactory-readable evidence through the
existing eval model:

- `eval/history/<run-id>/agent-memory-scorecard.json`
- `eval/history/<run-id>/agent-memory-snapshot.json`
- `eval/latest/index.json`

The benchmark must remain behavioral.

Required pass behavior includes:

- critical active memory remains prioritized
- omitted active memory remains visible
- goals and goal statuses survive reader derivation
- environment context remains recoverable
- history context remains recoverable
- next actions and compact handoff survive derivation

## Readiness Integration

Runtime memory does not introduce a second readiness state machine.

It integrates through the current readiness contract only.

For packs that enable the subsystem:

- `benchmarks/active-set.json` declares `agent-memory-restart-small-001`
- `status/readiness.json.required_gates` includes
  `agent_memory_restart_small_001`
- evidence paths point to the current scorecard and snapshot artifacts

For packs that do not enable the subsystem:

- no runtime-memory benchmark or gate is required

This resolves the failure-model ambiguity from the review:

- runtime memory is not globally mandatory for every pack
- when a pack declares the runtime-memory benchmark as a mandatory gate, failing
  that gate blocks readiness and therefore promotion

## Materialization Integration

This spec extends the materialization workflow without changing its authority
model.

When a source template enables runtime memory, the materializer must:

- copy runtime-memory code, contracts, tests, and benchmark declarations through
  the existing copy rules for `src/`, `contracts/`, `tests/`, and
  `benchmarks/`
- never copy live `.pack-state/agent-memory/` contents
- inherit the `agent-memory-restart-small-001` benchmark declaration through the
  existing benchmark-copy rules
- synthesize the corresponding `agent_memory_restart_small_001` readiness gate
  through the existing inherited-gate rule

A newly materialized build pack must start with:

- no inherited live runtime-memory entries
- no inherited runtime-memory revisions
- inherited runtime-memory readiness evidence in `not_run`

The build pack does not need a separate runtime-memory status file for this
state to be traversable.

## Promotion And Deployment Integration

Runtime memory does not create new deployment states or deployment pointers.

Promotion uses the existing readiness model:

- `ready_for_deployment = true`
- all mandatory gates pass

For runtime-memory-enabled packs, this means the existing
`agent_memory_restart_small_001` gate contributes to promotion readiness.

Deployment artifacts may include:

- runtime-memory code
- runtime-memory contracts
- runtime-memory benchmark declarations

Deployment artifacts must not include live runtime-memory state.

## CI And Cloud Orchestration Integration

Runtime memory integrates with the CI/cloud orchestration spec through the
existing pack entrypoint and readiness model.

The pipeline should:

- derive runtime-memory benchmark execution from the pack benchmark entrypoint
- use the benchmark declaration in `benchmarks/active-set.json`
- treat the resulting scorecard and snapshot as ordinary eval-history artifacts
- publish benchmark status through `eval/latest/index.json`
- rely on `status/readiness.json` to decide whether the runtime-memory gate
  passed

This spec does not add a second "latest benchmark summary" surface.

## Retirement Integration

Runtime memory follows the existing retirement model.

Retired packs:

- remain readable as historical evidence
- must not be promoted or deployed
- may retain runtime-memory eval history and local restart artifacts when the
  pack is intentionally preserved inside the factory

The retired isolated-memory build-pack remains historical reference only. It is
not the canonical product shape for future build packs.

## Failure Model

Missing runtime memory degrades to:

- restart context unavailable

Malformed runtime-memory artifacts should:

- surface as runtime-memory validation or benchmark failures when the subsystem
  is explicitly invoked
- not create a second global factory-invalid state outside the declared
  readiness-gate model

This means:

- a pack without the subsystem enabled is not invalid
- a runtime-memory-enabled pack can fail promotion if its mandatory
  runtime-memory gate fails
- PackFactory control-plane traversal remains available even when runtime-memory
  artifacts are missing or stale

## Required Reference Schemas

This spec adds three PackFactory reference schemas:

- `schemas/runtime-memory-entry.schema.json`
- `schemas/runtime-memory-snapshot.schema.json`
- `schemas/runtime-memory-benchmark-report.schema.json`

These schemas are compatibility mirrors of the live v1 runtime-memory payloads.

This spec does not currently require:

- `status/runtime-memory.json`
- `eval/latest/runtime-memory-summary.json`
- a capture-request schema separate from the pack CLI contract

Those may be proposed later only through coordinated updates across the base
directory, validator, materialization, promotion, and CI specs.

## Cross-File Invariants

The spec-level invariants for runtime-memory-enabled packs are:

- `benchmarks/active-set.json` uses benchmark id `agent-memory-restart-small-001`
  when runtime memory is declared
- `status/readiness.json.required_gates` uses gate id
  `agent_memory_restart_small_001` for the same benchmark
- readiness evidence paths for that gate point to
  `agent-memory-scorecard.json` and `agent-memory-snapshot.json`
- `eval/latest/index.json` must index the latest run for the
  `agent-memory-restart-small-001` benchmark
- live runtime-memory state must not be copied during materialization
- live runtime-memory state must not be included in release artifacts
- runtime memory must never override canonical PackFactory identity, readiness,
  deployment, or retirement state
