# Project Pack Factory Shallow Startup Initialization Spec

## Status

Proposed specification for factory-level startup and orientation guidance only.

Core root-level behavior from this shallow-startup line of work is now
reflected in `AGENTS.md` and `README.md`.

Canonical shallow-startup behavior lives in
`PROJECT-PACK-FACTORY-SHALLOW-STARTUP-AND-INITIALIZATION-SPEC.md`.

This file should be treated as a companion note rather than as a separate
authoritative startup contract.

This document is one of several related shallow-startup design notes and
should be read as additive context rather than as a competing instruction
layer.

Some evidence and gap statements below describe the state of the docs at the
time this spec was proposed.

This spec does not authorize changes to internal documentation inside existing
template packs or build packs.

## Problem Statement

At the time this spec was proposed, the factory startup behavior got the
important part right:

- it loads machine-readable factory state
- it gives the operator a project status and current-work summary
- it uses `registry/*.json` as source of truth
- it keeps the startup reply project-oriented and concierge-style

That is correct and should be preserved.

The failure mode identified here was depth, not direction.

The agent can dig too deep too early during initialization because the current
startup guidance says what the reply should contain, but it does not define a
shallow-pass budget or a clear stop point before broader reading begins.

That can waste:

- startup time
- tokens
- operator attention

before the operator has even confirmed what deeper work is needed.

## Goal

Keep startup useful, informed, and status-aware while making it intentionally
shallow.

The agent should:

- load enough context to give a credible factory status briefing
- avoid deeper repo or pack investigation during the first pass
- stop after a bounded set of sources unless the operator explicitly asks for
  more depth or names a target pack

## Evidence

### 1. The Current Startup Prompt Requires A Rich Brief But Not A Bounded Pass

In [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md) and
[README.md](/home/orchadmin/project-pack-factory/README.md), the startup brief
must:

- summarize what the repo is
- summarize where work stands
- identify active, recently completed, and retired packs
- explain what looks promising or worth attention next
- optionally mention environment assignment
- optionally mention recent repo-level tooling/doc work

This is a useful output contract, but it does not define a shallow stop rule.

### 2. The Current Read Order Encourages Expansion

[AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md) lists:

1. `AGENTS.md`
2. `README.md`
3. PRD when product intent or scope is needed
4. testing policy when workflow tests change
5. registry sources
6. `deployments/` when environment assignment matters

That sequencing is reasonable, but startup guidance still leaves too much room
for an agent to keep reading after the registry pass instead of replying.

### 3. Swarm Behavior Confirms The Expansion Risk

In the startup-behavior swarm exercise for the plain operator prompt
`load AGENTS.md`, the expected first-pass behavior anchored on:

- `AGENTS.md`
- `README.md`
- `registry/templates.json`
- `registry/build-packs.json`
- `registry/promotion-log.json`

That part was correct.

The problem exposed by the exercise is that the current docs do not clearly say
when to stop after those reads.

Because the startup contract also mentions:

- `deployments/`
- recent git commits when repo-level tooling/doc work matters
- additional specs in `First Reads`

a conscientious agent can keep expanding its initialization pass before it ever
sends the first status response.

## Required Behavioral Change

The factory must define startup as a two-phase process:

- a shallow status pass
- a deeper follow-up pass only after operator direction or a clearly triggered
  need

### Phase 1: Shallow Status Pass

When the operator says `load AGENTS.md`, asks for startup, or asks for current
factory status, the agent must stay in shallow-startup mode.

In shallow-startup mode, the agent's job is:

- determine what this repo is
- determine where factory work currently stands
- identify the active and recently relevant packs
- produce a useful overview without deeper repo excavation

### Phase 2: Deeper Follow-Up

The agent may only move beyond the shallow pass when one of the following is
true:

- the operator explicitly asks for deeper detail
- the operator names a target pack
- the operator asks for product intent or scope
- the operator asks about workflow-test policy
- the shallow sources are insufficient to answer the startup brief faithfully

## Shallow Startup Read Budget

For the default `load AGENTS.md` startup case, the agent should read only the
minimum bounded startup set:

### Mandatory Sources

- `AGENTS.md`
- `README.md`
- `registry/templates.json`
- `registry/build-packs.json`
- recent relevant entries from `registry/promotion-log.json`

### Optional Source

The agent may read one optional surface during shallow startup:

- the specific `deployments/` file needed to explain a current environment
  assignment

### Deferred Sources

The agent should not read these during shallow startup unless explicitly
triggered:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md`
- other technical specs under `docs/specs/project-pack-factory/`
- pack-local `AGENTS.md`, `project-context.md`, or `pack.json`
- tool source files
- broad directory listings
- git history, except under the narrow rule below

## Narrow Git-Log Rule

Startup should not check git commits by default.

The agent may inspect the most recent `3` commits only if both are true:

- recent repo-level tooling or doc work is materially relevant to the startup
  summary
- that relevance is not already clear from `registry/promotion-log.json`

If the agent checks git history in shallow startup, it should do so after the
registry summary is already formed, not before.

## Promotion Log Bound

For shallow startup, the agent should inspect only recent relevant entries from
`registry/promotion-log.json`, not perform a broad historical read.

Recommended bound:

- start from the newest entries
- stop after enough events to explain the current active, recently completed,
  and retired baseline
- do not keep scanning older history once the current baseline is clear

## Stop Rule

After the shallow read budget is complete, the agent must stop reading and
produce the startup brief.

The startup brief should be drafted before any deeper reading into:

- product docs
- testing policy
- technical specs
- pack-local files
- tool implementations

The agent should not keep reading simply because more related documents exist.

## Required Output Shape For Shallow Startup

The shallow startup reply should contain:

- a plain-language summary of what the repo is
- a concise summary of where work currently stands
- active, recently completed, and retired packs from registry state
- current environment assignment only when needed to explain active deployment
  state
- one short note on what looks most worth attention next
- a short list of practical next-step options
- a closing question asking what the operator wants to do next

The shallow reply should not include:

- deep product interpretation
- broad historical analysis
- pack-internal detail
- detailed tool or workflow mechanics

## Required Documentation Updates

The following factory-level docs should be updated.

### 1. Root `AGENTS.md`

Add a startup-depth rule that:

- defines `load AGENTS.md` as a shallow status pass by default
- names the bounded startup source set
- adds a stop rule after the registry pass
- explicitly defers PRD, testing policy, other specs, tool code, and pack-local
  docs until triggered

### 2. `README.md`

Add a short startup-depth section for operators that explains:

- the startup brief is intentionally shallow
- it is designed to provide a useful overview before deeper investigation
- deeper reading happens after operator direction or an explicit trigger

### 3. Optional Supporting Spec Update

If needed, add a short factory-level technical note clarifying startup-phase
discipline and bounded read order.

This should remain factory-level and must not require pack-local doc updates.

## Acceptance Criteria

This specification is satisfied when:

- a fresh agent handling `load AGENTS.md` can produce a useful startup brief
  after reading only the bounded startup set
- the first reply does not require PRD, testing policy, broader tech specs, or
  pack-local files
- the first reply still includes the current active/recently completed/retired
  baseline from registry state
- the agent stops reading after the shallow set unless a deeper trigger occurs
- startup time and token use are lower because the first pass is deliberately
  bounded

## Non-Goals

This spec does not:

- remove project context from the factory docs
- weaken the requirement to use registry state as source of truth
- prevent deeper reading after the operator directs it
- change pack-local bootstrap order after a target pack is confirmed
