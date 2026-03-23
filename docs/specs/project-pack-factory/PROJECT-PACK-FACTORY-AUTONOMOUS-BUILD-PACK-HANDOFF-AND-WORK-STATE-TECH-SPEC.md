# Project Pack Factory Autonomous Build-Pack Handoff And Work-State Tech Spec

## Purpose

Define the minimal PackFactory-native control-plane contract that lets the
factory hand a build-pack to an autonomous agent with enough machine-readable
state to run implementation and testing loops to completion.

The intended model is:

- Project Pack Factory defines the work
- the build-pack carries the bounded handoff
- the agent executes inside those bounds
- runtime memory helps the agent resume
- canonical PackFactory state remains authoritative

This spec is about the missing handoff and work-state layer between factory
materialization and autonomous execution.

The retired or migrated memory/task-loop lines are useful idea sources only.
They are not treated here as direct PackFactory authority for ordinary packs
unless a current Project Pack Factory spec already adopted the idea.

## Spec Link Tags

```json
{
  "spec_id": "autonomous-build-pack-handoff-and-work-state",
  "amends": [
    "directory-hierarchy",
    "build-pack-materialization"
  ],
  "depends_on": [
    "runtime-agent-memory"
  ],
  "integrates_with": [
    "readiness",
    "deployment-pipeline",
    "build-pack-promotion",
    "factory-validation"
  ],
  "historical_idea_sources": [
    "templates/agent-memory-first-template-pack",
    "templates/ai-native-codex-package-template"
  ]
}
```

## Problem

Project Pack Factory already knows how to:

- create templates
- materialize build-packs
- seed canonical lifecycle, readiness, deployment, and eval surfaces
- run bounded validation, benchmark, pipeline, promotion, and retirement
  workflows

What it does not yet do generically is hand off a build-pack as an executable
work packet with a canonical machine-readable answer to:

- what the project objective is
- how success is measured
- what tasks exist
- which task is active now
- what is blocked
- what should happen next
- when the agent should stop, escalate, or promote

Today the factory can tell an agent whether a pack is ready. It cannot yet tell
an agent a structured ordered backlog and current resume point for an
autonomous run-to-completion loop.

## Current Factory Evidence

### Evidence A: Template And Build-Pack Creation Already Seed Canonical Next-Step Hints

Current factory creation/materialization code already writes:

- `project-context.md`
- `status/readiness.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

Relevant code:

- `tools/create_template_pack.py`
- `tools/materialize_build_pack.py`

Concrete evidence:

- `tools/create_template_pack.py` seeds `status/readiness.json` with
  `blocking_issues`, `recommended_next_actions`, and `required_gates`
- `tools/materialize_build_pack.py` does the same for build-packs

Interpretation:

- the factory already creates a machine-written starting state
- but that state is pack-level and shallow, not task-level

### Evidence B: Readiness Already Carries Canonical Next-Step And Gate State

Current schema:

- `docs/specs/project-pack-factory/schemas/readiness.schema.json`

Concrete evidence:

- readiness already requires:
  - `blocking_issues`
  - `recommended_next_actions`
  - `required_gates`
  - `ready_for_deployment`
  - `last_evaluated_at`

Interpretation:

- the factory already has one canonical place for high-level blocker and
  next-step state
- but it is only arrays of strings plus gate summaries
- it is not a structured work queue

### Evidence C: The Factory Already Supports Bounded Autonomous Workflow Execution

Current workflow code:

- `tools/run_deployment_pipeline.py`
- `tools/promote_build_pack.py`
- `tools/retire_pack.py`

Concrete evidence:

- `run_deployment_pipeline.py` already executes a bounded stage loop:
  validate factory, validate build-pack, run benchmarks, package, deploy,
  verify, finalize promotion
- `promote_build_pack.py` already updates canonical deployment state and
  promotion evidence fail-closed
- `retire_pack.py` already performs a bounded terminal lifecycle workflow

Interpretation:

- bounded automation is already accepted in the factory
- the missing piece is pre-deployment implementation work, not workflow
  automation in general

### Evidence D: Canonical State Is Already Cross-File And Validator-Bound

Current authority and validation code:

- `tools/validate_factory.py`
- `tools/promote_build_pack.py`
- `docs/specs/project-pack-factory/schemas/deployment.schema.json`
- `docs/specs/project-pack-factory/schemas/readiness.schema.json`

Interpretation:

- any autonomous loop must preserve cross-file invariants
- live lifecycle, deployment, registry, and promotion state must remain under
  existing workflow control
- an autonomous loop cannot safely use canonical deployment files as a
  scratchpad

### Evidence E: The Factory Already Reserves A Non-Canonical Local State Area

Current directory contract evidence:

- `docs/specs/project-pack-factory/schemas/pack.schema.json`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md`

Concrete evidence:

- `.pack-state/` is already the reserved pack-local mutable state root
- runtime agent memory is already defined as advisory local state, not a second
  control plane

Interpretation:

- the repo already distinguishes canonical control-plane state from mutable
  runtime memory
- this spec should preserve that split

### Evidence F: Pack-Local Objective And Metric Specs Already Fit The Repo Model

Current evidence:

- `build-packs/config-drift-checker-build-pack/docs/specs/config-drift-checker-objective-brief.md`
- `build-packs/config-drift-checker-build-pack/contracts/config-drift-checker.contract.md`

Interpretation:

- a build-pack can already carry richer objective, metric, and contract
  surfaces
- the gap is that this is optional and hand-authored today
- the factory does not yet generate a canonical machine-readable version by
  default

### Evidence G: The Current Manifest And Validator Do Not Yet Have Slots For These New Surfaces

Current schema and validator evidence:

- `docs/specs/project-pack-factory/schemas/pack.schema.json`
- `tools/validate_factory.py`

Concrete evidence:

- `pack.schema.json` currently defines canonical directory-contract paths for
  docs, prompts, contracts, source, tests, benchmarks, eval, status, lineage,
  dist, and `.pack-state`
- it does not yet define a canonical `tasks/` directory or explicit
  project-objective or work-state file references
- `tools/validate_factory.py` currently validates only the existing canonical
  files in `SCHEMA_BY_RELATIVE_PATH`

Interpretation:

- implementation of this spec requires explicit manifest, schema, and validator
  extensions
- the new surfaces are proposed control-plane additions, not already-present
  canonical files

## Scope Boundary

This spec defines a new PackFactory-native control-plane layer for:

- build-pack objective handoff
- structured task backlog
- current work-state
- explicit stop, escalate, and done conditions

This spec does not:

- replace readiness, deployment, lifecycle, retirement, registry, or eval
  authority
- redefine runtime memory as canonical control-plane state
- require generic packs to enable runtime-memory commands in v1
- require every agent to use delegation or sub-agents
- add direct deployment or promotion bypasses
- require broad new workflow or benchmark matrices
- authorize new or strengthened tests by default

## Directory And Migration Boundary

This spec amends the build-pack directory contract by proposing:

- `tasks/`
- `tasks/active-backlog.json`
- `status/work-state.json`

These are new canonical build-pack surfaces, not existing ones.

Migration rule:

- pre-existing packs remain valid until the factory explicitly rolls these
  files out for newly materialized build-packs
- v1 should not require immediate historical backfill
- validator enforcement for these files must be phased in with that rollout

## Control Plane And Execution Plane Model

The factory should act as the control plane.

The autonomous agent should act as the execution plane.

The control plane defines:

- project objective
- output contract
- metrics
- completion criteria
- current canonical task state
- allowed validation surfaces
- escalation rules

The execution plane performs:

- implementation
- testing
- evidence generation
- work-state updates
- escalation when the declared rules require it

Runtime memory remains advisory resume support for the execution plane.

## Design Goals

- keep the first implementation tightly scoped to a small number of new
  canonical surfaces
- preserve current PackFactory authority boundaries
- let an agent resume deterministically without depending on scattered prose
- keep runtime memory optional and advisory
- keep validation and testing minimal and aligned with
  `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

## Canonical New Surfaces

This spec adds three new build-pack-local canonical surfaces.

### 1. `contracts/project-objective.json`

This file is the machine-readable source of project intent.

It must capture:

- `objective_id`
- `objective_summary`
- `problem_statement`
- `intended_inputs`
- `intended_outputs`
- `success_criteria`
- `metrics`
- `non_goals`
- `completion_definition`
- `promotion_readiness_requirements`

This is the canonical machine-readable counterpart to a human-facing objective
brief.

Authority rule:

- `contracts/project-objective.json` is factory-authored seed state
- it may be revised only by explicit objective or planning work
- it is not part of the agent's normal per-loop mutable execution state

### 2. `tasks/active-backlog.json`

This file is the canonical structured work queue.

It must contain ordered task objects with at least:

- `task_id`
- `summary`
- `status`
- `objective_link`
- `acceptance_criteria`
- `validation_commands`
- `files_in_scope`
- `dependencies`
- `blocked_by`
- `escalation_conditions`
- `completion_signals`

Minimum supported task statuses:

- `pending`
- `in_progress`
- `blocked`
- `completed`
- `escalated`
- `cancelled`

This file is authoritative for task ordering and work decomposition.

Determinism rules:

- backlog order is canonical
- at most one task may have `status = in_progress`
- tasks with unmet dependencies must not be selected as next recommended tasks
- blocked tasks must not be selected as next recommended tasks

### 3. `status/work-state.json`

This file is the canonical current resume point for an autonomous agent.

It must capture at least:

- `autonomy_state`
- `active_task_id`
- `next_recommended_task_id`
- `pending_task_ids`
- `blocked_task_ids`
- `completed_task_ids`
- `last_outcome`
- `last_outcome_at`
- `last_validation_results`
- `last_agent_action`
- `resume_instructions`
- `stop_conditions`
- `escalation_state`

This file is authoritative for what the agent should do next right now.

Minimum value rules:

- `autonomy_state` must be one of:
  - `idle`
  - `actively_building`
  - `blocked`
  - `awaiting_operator`
  - `ready_for_review`
  - `ready_for_deploy`
  - `completed`
- `last_outcome` must be one of:
  - `task_completed`
  - `validation_failed`
  - `blocked`
  - `escalated`
  - `stopped`
- `escalation_state` must be one of:
  - `none`
  - `pending`
  - `raised`
  - `resolved`

Tie-break rule:

- `tasks/active-backlog.json` is authoritative for task ordering and task
  status
- `status/work-state.json.next_recommended_task_id` must be derived from the
  backlog state and may diverge only when an explicit stop or escalation
  condition is recorded in work-state

## Manifest And Traversal Changes Required

Because these are proposed new canonical surfaces, the first implementation
must also extend:

- `pack.schema.json`
- generated `pack.json.directory_contract`
- generated `pack.json.post_bootstrap_read_order`
- `tools/validate_factory.py`

At minimum, the manifest must gain canonical references for:

- the project-objective file
- the task backlog file
- the work-state file

## Relationship To Existing Surfaces

The new surfaces do not replace current PackFactory status.

### Readiness

`status/readiness.json` remains the canonical answer to:

- whether the pack is ready for deployment
- which required gates have passed
- which high-level issues remain

`status/work-state.json` and `tasks/active-backlog.json` answer a different
question:

- what implementation work remains before readiness can change

### Eval Surfaces

`eval/latest/index.json` and `eval/history/*` remain the canonical evidence
surfaces for completed validation and benchmark runs.

`status/work-state.json` may reference those artifacts, but it does not replace
them.

### Runtime Memory

Runtime memory under `.pack-state/agent-memory/` remains advisory.

If runtime memory disagrees with:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- existing canonical PackFactory `status/*`, `eval/*`, registry, or deployment
  surfaces

then canonical PackFactory state wins.

## Materialization Rollout Boundary

V1 rollout for this spec should be limited to newly materialized build-packs.

V1 does not require:

- template-creation synthesis
- repo-wide historical backfill
- broad validator contradiction logic
- generic factory-generated implementation-task planning

### Build-Pack Materialization

At build-pack materialization time, the factory should synthesize:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

Initial synthesized state should be minimal but usable:

- one explicit objective
- one starter task for pack validation
- one starter task for benchmark execution
- `status/work-state.json.next_recommended_task_id` must reference a real task
- readiness `recommended_next_actions` should remain as a human-readable shadow
  of the canonical work state, not the primary machine-readable queue

Follow-on work, not required for v1:

- template-creation synthesis
- richer objective planning inputs
- factory-generated first implementation tasks

## Autonomous Loop Contract

The intended autonomous loop is:

1. agent reads `AGENTS.md`, `project-context.md`, `pack.json`
2. agent reads canonical pack state:
   - `status/lifecycle.json`
   - `status/readiness.json`
   - `status/deployment.json`
   - `contracts/project-objective.json`
   - `tasks/active-backlog.json`
   - `status/work-state.json`
   - `benchmarks/active-set.json`
   - `eval/latest/index.json`
3. agent optionally reads runtime memory from `.pack-state/agent-memory/`
4. agent selects `next_recommended_task_id`
5. agent executes only within declared task scope and validation surfaces
6. agent writes evidence through existing pack-local artifacts
7. agent updates `tasks/active-backlog.json` and `status/work-state.json`
8. agent updates readiness only by running existing bounded validation,
   benchmark, pipeline, or lifecycle workflow surfaces
9. agent repeats until:
   - completion definition is satisfied
   - an escalation condition is reached
   - a promotion/deployment workflow becomes the next valid action

## Control-Plane Boundaries

An autonomous agent may update:

- `tasks/active-backlog.json`
- `status/work-state.json`
- human-facing pack-local docs
- pack runtime code
- pack-local eval evidence by running existing validation and benchmark
  commands

An autonomous agent may revise `contracts/project-objective.json` only when the
declared task explicitly concerns objective or planning changes.

An autonomous agent must not directly edit as free-form runtime state:

- deployment pointers under `deployments/`
- factory registry truth under `registry/`
- canonical promotion log entries
- canonical deployment state that should instead be updated through
  `promote_build_pack.py`
- canonical lifecycle endpoints that should instead go through existing factory
  workflows
- tests, unless explicit operator approval authorizes test creation or
  strengthening under the PackFactory testing policy

This preserves the existing control-plane boundary.

## Validator Expectations

Future validator support for this spec should be phased.

V1 validator scope should enforce only:

- `contracts/project-objective.json` exists and is schema-valid
- `tasks/active-backlog.json` exists and is schema-valid
- `status/work-state.json` exists and is schema-valid
- `status/work-state.json.active_task_id` refers to a real task when autonomy
  is active
- `status/work-state.json.next_recommended_task_id` refers to a real non-final
  task
- blocked tasks are not also marked as active

Follow-on validator scope, not required for v1:

- deeper contradiction checks between readiness and work-state
- completion-signal enforcement beyond basic task-reference integrity
- historical-pack migration enforcement

## Borrowed Patterns

The following sources are useful idea banks only. They are not direct current
PackFactory authority for ordinary packs:

- `templates/agent-memory-first-template-pack`
- `build-packs/agent-memory-first-build-pack`
- `build-packs/ai-native-codex-build-pack`

Useful patterns worth borrowing deliberately:

- task-level objective plus acceptance criteria contracts
- machine-readable next-action and blocker memory cards
- explicit goal validation commands
- restart-aware handoff summaries
- dispatchability and escalation policy

These patterns should be adapted into PackFactory-native generic contracts
rather than imported wholesale as if they were already the default factory
model.

## Acceptance Criteria

This spec is satisfied when all of the following are true:

1. A newly materialized build-pack carries a canonical machine-readable
   objective surface, task backlog, and work-state surface.
2. The factory-generated next recommended task is no longer only a free-form
   string in readiness state for those newly materialized build-packs.
3. An autonomous agent can determine, without reading scattered prose, what
   the current objective is, what task is active, what task comes next, and
   what validation commands define task completion.
4. Runtime memory remains advisory and subordinate to canonical PackFactory
   state.
5. Existing promotion, deployment, and retirement workflows remain the only
   valid path for changing canonical lifecycle and environment assignment
   state.
6. The first implementation can be verified with a minimal bounded surface:
   - one build-pack materialization happy-path test
   - one validator smoke check for file presence and task-reference integrity
   - no template-creation expansion in the same pass

## Minimal Verification Boundary

This spec follows PackFactory's minimal-test pattern.

V1 verification should prefer:

- one build-pack materialization happy-path test
- one validator smoke test for schema validity and cross-reference integrity
- existing bounded workflow surfaces where possible

V1 should not require:

- template-creation test expansion
- broad new contradiction suites
- autonomous-loop simulation tests
- any new or strengthened tests without explicit operator approval under the
  PackFactory testing policy

## Recommended Next Step

The next implementation step after this spec is to define three schemas:

- `project-objective.schema.json`
- `task-backlog.schema.json`
- `work-state.schema.json`

and wire their initial synthesis into:

- `tools/materialize_build_pack.py`

Template-creation support should be treated as later follow-on work once the
build-pack materialization path is proven.
