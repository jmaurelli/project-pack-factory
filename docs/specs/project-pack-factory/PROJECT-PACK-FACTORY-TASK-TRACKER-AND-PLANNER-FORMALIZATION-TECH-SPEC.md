# Project Pack Factory Task Tracker And Planner Formalization Tech Spec

## Status

Implemented v1 authority model for formalizing the distinction between
PackFactory's canonical execution tracker and its advisory planning context.

## Goal

Make the existing PackFactory behavior explicit:

- the task tracker is the canonical execution control plane
- planning context is advisory and may explain the tracker, but it does not
  become a second state machine

## Problem

PackFactory already behaves as though the distinction exists, but before this
spec the boundary was not named tightly enough.

That left room for confusion about:

- where alternatives and deferred ideas belong
- which surfaces an agent may mutate during execution
- whether dashboard, memory, or planning notes can compete with backlog and
  work-state

## Review Outcome

Adversarial review rejected the earlier attempt to formalize the planner as a
second pseudo-object with its own lifecycle states and canonical fields inside
execution documents.

The approved v1 model is narrower:

- no canonical planner object
- no planner lifecycle states in canonical JSON
- no planner provenance fields in backlog/work-state
- no new planner state inside `contracts/project-objective.json`,
  `tasks/active-backlog.json`, or `status/work-state.json`

The tightened reading that fell out of the review is also simple:

- advisory planning context stays optional rather than becoming a placeholder
  document
- task provenance remains diagnostic only and never routes execution
- generated startup surfaces should point at the tracker, not duplicate it
- if a task does not have bounded planning context, the field should stay
  absent

Recorded review artifact:

- [agent-native-project-initialization-and-tracker-planner-adversarial-review-20260401.md](/home/orchadmin/project-pack-factory/eval/history/agent-native-project-initialization-and-tracker-planner-adversarial-review-20260401.md)

## Evidence

### Evidence A: the execution tracker already exists

PackFactory already has a canonical tracker model through:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

See:

- [PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md)

### Evidence B: advisory planning already exists, but heterogeneously

PackFactory already stores advisory planning context in several places:

- template creation `planning_summary`
- root planning lists
- root memory
- dashboard briefing layers
- request/report evidence

See:

- [template-creation-request.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/template-creation-request.schema.json)
- [PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md)
- [.pack-state/agent-memory/latest-memory.json](/home/orchadmin/project-pack-factory/.pack-state/agent-memory/latest-memory.json)

This is evidence of advisory planning context, not evidence of a canonical
planner object.

### Evidence C: the root already prefers the tracker over advisory context

PackFactory root behavior already treats the tracker as primary and memory as
advisory:

- [contracts/project-objective.json](/home/orchadmin/project-pack-factory/contracts/project-objective.json)
- [tasks/active-backlog.json](/home/orchadmin/project-pack-factory/tasks/active-backlog.json)
- [status/work-state.json](/home/orchadmin/project-pack-factory/status/work-state.json)
- [tools/refresh_factory_autonomy_memory.py](/home/orchadmin/project-pack-factory/tools/refresh_factory_autonomy_memory.py)

## Formal Model

### Task tracker

The tracker is the canonical execution control plane.

It answers:

- what work is currently accepted for execution
- what is active now
- what is blocked
- what has completed
- what the next executable task is

Canonical tracker surfaces remain:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

### Advisory planning context

Advisory planning context explains why the tracker exists and what broader
options shaped it.

It may include:

- rationale
- alternatives
- deferred work
- sequencing ideas
- assumptions
- open questions

But in v1 it is intentionally not normalized into one canonical planner object
or lifecycle.

That means the root planning list, memory, and request/report evidence may
carry the "why" context, but the tracker itself should stay small and
execution-focused.

## Authority Rules

### Canonical

These remain canonical:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- lifecycle, readiness, deployment, eval, registry, retirement, and promotion
  state

### Advisory or derived

These remain advisory or derived:

- planning lists
- dashboard summaries
- agent memory
- request/report planning evidence
- template-lineage and autonomy-distillation notes

## Fail-Closed Rule

Advisory planning context must never participate directly in:

- `active_task_id`
- `next_recommended_task_id`
- task status transitions
- blocker state
- validator consistency logic

If a task becomes executable, it must be fully represented in the canonical
tracker without consulting planner-only state.

Planner provenance should remain an explanatory note, not a task-selection
input.

## Relationship To Agent-Native Initialization

V1 formalization becomes visible through the agent-native profile declaration:

- `canonical_tracker_mode = objective_backlog_work_state`
- `planner_mode = tracker_backed_advisory_planning`

That makes the distinction explicit without introducing a second planner file
or planner state machine.

## V1 Implementation Slice

V1 implementation is intentionally declaration-only:

1. declare the planner/tracker boundary through the new
   `agent_native_project_profile.work_management_model`
2. render that distinction in generated startup surfaces
3. preserve broader planning rationale in request/report evidence, not in the
   canonical tracker schemas
4. leave `advisory_planning_context` empty when a project does not need it

## Explicit Deferrals

These are deferred beyond v1 unless later evidence justifies them:

- `advisory_planning_context` inside `contracts/project-objective.json`
- planner lifecycle states such as `candidate`, `accepted`, or `superseded`
- task-level planner provenance fields
- any planner artifact that an agent could mistake for a second execution
  authority

## Success Criteria

- PackFactory explicitly distinguishes advisory planning from execution state.
- The canonical tracker remains the only execution authority.
- A fresh agent can learn the distinction from the manifest and startup
  surfaces without consulting chat history.
- PackFactory does not create a second planner control plane by accident.
