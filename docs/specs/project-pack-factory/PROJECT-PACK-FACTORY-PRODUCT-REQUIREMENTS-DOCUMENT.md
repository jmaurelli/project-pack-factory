# Project Pack Factory Product Requirements Document

## Document Status

- product: `project-pack-factory`
- document_type: `prd`
- status: `draft-baseline`
- owner: `orchadmin`

## Product Summary

Project Pack Factory is an agent-optimized system for authoring, testing,
deriving, validating, promoting, deploying, and retiring software build-packs.

Its purpose is to make agentic software builds deterministic, observable, and
recoverable across the full build-pack lifecycle.

In practical terms, Project Pack Factory provides:

- canonical template packs as reusable sources
- derived build packs as deployable artifacts
- machine-readable lifecycle, readiness, deployment, and retirement state
- benchmark and evaluation evidence tied directly to each pack
- deterministic agent traversal so a new agent can quickly recover context and
  continue work

## Problem Statement

Agentic software builds become unreliable when the system around them is
implicit.

Without a factory model:

- pack structure drifts between projects
- build-pack creation becomes ad hoc
- readiness and deployment decisions are difficult to audit
- restart and handoff quality depend on memory outside the system
- agents waste time rediscovering context instead of continuing validated work

This creates operational risk, slows iteration, and makes it hard to compare
different agent-optimized build strategies.

## Product Vision

Project Pack Factory should become the canonical environment for producing and
operating agent-optimized software build-packs.

The product should let an agent:

- enter a pack and determine what it is, what state it is in, and what to do
  next
- derive a deployable build-pack from a trusted template
- prove readiness with bounded evidence instead of informal judgment
- recover runtime context after interruption or handoff
- move a build-pack through testing, staging, production, and retirement
  without losing provenance or operational history

## Product Goal

Provide a factory that produces and manages agent-optimized software
build-packs where agents can:

- understand the pack quickly
- recover work context reliably
- act against deterministic machine-readable state
- generate evidence for validation, promotion, deployment, and retirement

## Users

Primary users:

- orchestration agents managing pack lifecycle
- implementation agents operating inside template packs and build packs
- observability agents measuring build effectiveness and restart quality

Secondary users:

- operators supervising pack readiness and deployment
- human collaborators reviewing pack structure, evidence, and promotion state

## Product Scope

Project Pack Factory is responsible for:

- defining the canonical directory hierarchy for template packs and build packs
- tracking pack identity, lifecycle, readiness, deployment, and retirement
  state
- materializing build packs from templates
- promoting build packs through controlled environments
- recording evaluation and benchmark evidence
- supporting runtime agent memory as a build-pack runtime subsystem
- preserving historical fixtures and retired artifacts without confusing them
  with active deployment targets

## Non-Goals

Project Pack Factory is not intended to be:

- a general-purpose source code hosting platform
- a cloud vendor implementation
- a secret-management system
- a human-only project documentation portal
- a replacement for the internal runtime logic of every software project

## Core Product Principles

- agent-first traversal: the product must be easy for a fresh agent to inspect
- machine-readable authority: important state must live in structured files
- fail-closed decisions: promotion and deployment should block when evidence is
  incomplete
- evidence over assertion: readiness and quality claims must point to artifacts
- restart continuity: runtime context should survive interruption and handoff
- historical integrity: retired and superseded work should remain readable
  without being mistaken for active targets

## Functional Requirements

### FR1: Canonical Pack Structure

The system must provide a deterministic directory pattern for:

- template packs
- build packs
- deployments
- registry state

### FR2: Stable Pack State

Each pack must expose machine-readable state for:

- identity
- lifecycle
- readiness
- deployment
- retirement

### FR3: Deterministic Build-Pack Creation

The system must support deterministic materialization of a build pack from a
template pack with explicit lineage and evidence.

### FR4: Controlled Promotion

The system must support bounded promotion of build packs through:

- testing
- staging
- production

### FR5: Observable Validation And Benchmarking

The system must record validation and benchmark results as pack-local evidence
that later agents can inspect.

### FR6: Runtime Agent Memory

The system must support runtime agent memory as a built-in subsystem of the
build-pack runtime so agents can recover:

- goals
- environment anchors
- history
- blockers
- decisions
- next actions

### FR7: Retirement

The system must support explicit retirement of packs while preserving their
historical evidence and lineage.

## Success Criteria

Project Pack Factory is successful when:

- a new agent can determine a pack’s state quickly from startup anchors and
  machine-readable files
- build packs are derived from templates through repeatable workflows rather
  than manual copying
- promotion and deployment decisions can be explained from recorded evidence
- runtime restart quality is measurable and can improve over time
- retired experiments remain useful historical context without polluting active
  deployment decisions

## Measurable Outcomes

Target product outcomes include:

- lower time-to-context for a newly started agent
- lower restart friction after interruption or handoff
- higher percentage of packs with complete readiness evidence
- lower ambiguity in promotion and deployment state
- reproducible comparison of different agent-optimization strategies

## Relationship To The Technical Specs

This PRD defines the product intent and scope.

The following technical specs define how that intent is implemented:

- `PROJECT-PACK-FACTORY-TEMPLATE-PLANNING-AND-CREATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-DIRECTORY-HIERARCHY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-MATERIALIZATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-CI-CLOUD-DEPLOYMENT-ORCHESTRATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-RETIRE-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md`

The testing constraint for the current small-project operating model lives in:

- `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

## Current Strategic Thesis

The factory is not only for tracking build artifacts.

It is for producing software build environments that are optimized for agent
execution.

That means the product has two coupled responsibilities:

- deterministic build-pack production and lifecycle control
- runtime conditions that help agents understand, continue, and complete
  software-building work effectively

## Open Product Question

An important ongoing design boundary remains:

- what state belongs to PackFactory control-plane authority
- what state belongs to runtime agent memory inside the build-pack runtime

The current product direction is:

- PackFactory owns canonical lifecycle and evidence state
- runtime agent memory is a core runtime subsystem, but not a second control
  plane
