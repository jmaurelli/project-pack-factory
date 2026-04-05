# ADF Three-Node Autonomy Contract V1

## Purpose

This note defines the current three-node autonomy model for ADF.

The goal is to make the node roles explicit so PackFactory does not treat
remote sync as a generic copy problem and ADF does not drift into a second
control plane.

Current nodes:

1. Local Pack Factory
2. Remote ADF Dev
3. Target Lab

## Node Roles

### 1. Local Pack Factory

Local Pack Factory is the control plane and canonical memory owner.

It owns:

- build-pack source of truth
- contracts, backlog, work-state, readiness
- accepted evidence notes
- accepted restart memory
- promotion and template inheritance decisions
- cross-run performance and autonomy metrics

It does not own:

- direct target-lab diagnosis as the normal default when `adf-dev` can do it
- remote review serving as the main runtime surface
- long-running target-session state

### 2. Remote ADF Dev

`adf-dev` is the autonomous worker and review surface.

It owns:

- bounded Codex execution
- build-pack continuation work
- generated ADF review surfaces
- checkpoint writing
- target-facing delegated workflows
- temporary runtime state needed to keep a slice moving

It does not own:

- canonical planner authority
- final acceptance of source, state, or evidence
- registry, deployment, or promotion truth

### 3. Target Lab

The target lab is the runtime evidence source.

It owns:

- live Linux application state
- service and process behavior
- logs, shell output, HTTP behavior, and restartable services
- reproduced customer-like evidence

It does not own:

- PackFactory planner state
- ADF authoring state
- accepted historical evidence outside bounded returned artifacts

## Data Flow

### Local Pack Factory -> Remote ADF Dev

Send only what the remote worker needs to continue a bounded task:

- pack contracts and state
- current docs and source
- runtime helper surfaces
- lightweight memory
- small generated inputs that the remote host should reuse

Do not send:

- historical evidence archives
- bulky lab snapshot artifacts unless a specific run needs them
- local-only preserved runtime export bundles

### Remote ADF Dev -> Target Lab

Use this hop for bounded runtime work:

- shell commands
- log collection
- HTTP checks
- service checks and safe restart actions
- browser-backed or delegated evidence capture

This hop should be treated as the runtime observation plane, not as the source
of planner truth.

### Target Lab -> Remote ADF Dev

Return only bounded runtime evidence:

- command results
- copied artifacts
- delegated result bundles
- target-backed observations for the current slice

### Remote ADF Dev -> Local Pack Factory

Return only what the control plane needs to learn or accept:

- checkpoint bundles
- run summary and loop events
- restart memory
- candidate source or state changes
- review artifacts
- bounded runtime evidence bundles
- measured performance and payload facts

Local Pack Factory then decides what becomes canonical.

## Authority Rules

- Local Pack Factory remains canonical unless an explicit later mode change is
  recorded.
- `adf-dev` is the live execution workspace, not the canonical home.
- Target-lab evidence is authoritative about runtime behavior, but not about
  PackFactory state.
- Imported runtime evidence remains supplementary history until local
  PackFactory accepts and records the result.

## Current Sync Direction

The current remote sync should support node roles, not mirror the entire local
 pack.

Current practical rule:

- sync PackFactory-essential ADF inputs to `adf-dev`
- let `adf-dev` regenerate its own review artifacts when possible
- let `adf-dev` collect target evidence directly
- pull back only checkpointed results and accepted evidence candidates

## Current Autonomy Direction

The autonomy target is not "make the target lab autonomous."

The autonomy target is:

- `adf-dev` should be able to continue bounded ADF work with minimal human
  supervision
- Local Pack Factory should absorb returned proof, metrics, and lessons
- the target lab should remain the observed runtime system

## Named Planning Line

ADF now has one explicit planning line for the next ownership shift:

- `plan_goal_and_objective_execution_transition_to_adf_dev_agent`

That planning line is the concrete place to track the question of how project
goal and objective execution should move from the local PackFactory
orchestrator to `adf-dev` without changing the current canonical ownership
model early.

Current split for that planning line:

- Local Pack Factory stays the canonical planner, readiness owner, accepted
  evidence owner, and state accepter
- `adf-dev` is the default bounded execution agent and review surface for ADF
  content, continuity, and remote helper work
- the target lab remains the runtime evidence source

Minimum local control surfaces that should stay local while that planning line
is open:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`
- accepted evidence notes and accepted restart memory
- promotion and template inheritance decisions
- registry, deployment, and factory-wide orchestration truth

Minimum remote surfaces that may move with the planning line as bounded ADF
execution:

- bounded task continuation
- review-surface generation
- checkpoint writing
- target-facing delegated workflows
- temporary runtime state needed to keep a slice moving
- restart-memory generation for the ADF slice being worked

In plain language:

- the planning line is about who executes ADF work next
- it is not a silent claim that `adf-dev` is already canonical
- it is the named place to record the future handoff before any mode change is
  accepted

## What To Test Next

The next useful tests should validate the three-node split directly:

1. confirm lean local-to-`adf-dev` staging is sufficient for real ADF work
2. confirm `adf-dev` can regenerate the review surface without needing the
   heavy local lab snapshot
3. confirm `adf-dev` can continue bounded target-lab evidence work and return
   useful checkpoint bundles
4. confirm Local Pack Factory can absorb the returned results without treating
   `adf-dev` as a second control plane

## Decision Rule

When deciding whether data belongs in the remote payload, ask:

- does `adf-dev` need this to continue the next bounded task?

When deciding whether returned data belongs in canonical local state, ask:

- does Local Pack Factory need this to learn, judge, or promote the result?

If the answer is no, do not sync it by default.
