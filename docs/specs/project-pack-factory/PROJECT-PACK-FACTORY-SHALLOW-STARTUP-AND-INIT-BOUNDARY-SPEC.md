# Project Pack Factory Shallow Startup And Initialization Boundary Spec

## Status

Proposed specification for factory-level startup and orientation guidance.

This spec is for `load AGENTS.md` and similar factory startup requests only.

## Problem Statement

Project Pack Factory correctly instructs the agent to load machine-readable
state before giving a live startup brief. That is the right foundation.

The current problem is depth, not direction.

At startup, the agent can drift from:

- a bounded project-status pass

into:

- a deeper initialization sequence
- repeated file-loading attempts
- premature detail gathering
- avoidable troubleshooting before the first useful reply

That wastes tokens, increases time-to-context, and delays the operator-facing
overview that `load AGENTS.md` is supposed to provide.

The desired behavior is a shallow, high-signal startup pass:

- enough context to know the project
- enough live state to summarize status accurately
- not enough digging to become a deep research phase

## Evidence From Current Docs

### 1. Startup Is Correctly Registry-First

In [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md), concierge
startup already says to read:

- `registry/templates.json`
- `registry/build-packs.json`
- recent relevant entries in `registry/promotion-log.json`

and to use `deployments/` only when environment assignment needs explanation.

This is correct and should remain the source-of-truth path for live state.

### 2. Startup Depth Is Not Explicitly Bounded

The same guidance says to summarize where work stands, identify active and
retired packs, explain what looks promising next, and provide practical
next-step options.

Those are good goals, but the docs do not currently define:

- how much reading is enough for the first reply
- what the agent must not read during the first pass
- how many retries are acceptable when a source is blocked
- when the startup phase should stop and defer deeper digging

That absence creates room for over-initialization.

### 3. The Product Already Values Fast Context Recovery

In
[PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md),
success criteria and measurable outcomes already include:

- quick determination of pack state from startup anchors
- lower time-to-context for a newly started agent
- lower restart friction after interruption or handoff

A shallow startup boundary directly supports those product outcomes.

## Evidence From Observed Agent Behavior

On 2026-03-22, I ran a behavior study using a small swarm of fresh `codex exec`
agents, each given the current [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md)
as the startup instruction anchor and the plain operator prompt:

- `load AGENTS.md`

Observed behavior:

- both study agents immediately attempted deeper startup reads before giving
  the operator a useful overview
- both agents treated successful access to the registry files as a hard gating
  condition for the startup brief
- both agents drifted into shell/setup troubleshooting instead of staying in a
  bounded startup mode
- both agents ultimately produced fallback replies saying they could not give a
  truthful live startup brief yet
- both agents actually inspected only `AGENTS.md` successfully before stopping
- additional swarm agents overreached in the opposite direction: instead of
  returning the requested startup-behavior simulation, they jumped ahead and
  authored specs immediately

Observed cost:

- study run A used about `9,833` tokens
- study run B used about `10,160` tokens

Observed failure mode:

- startup effort was spent on read attempts, environment friction, or
  over-completion instead of on a useful shallow project-status summary

This shows two related missing boundaries in the current startup model:

- no clear shallow-read stop rule
- no clear task-completion stop rule once the requested startup/status output is
  answerable

This is strong evidence that the current startup instructions need an explicit
initialization boundary.

## Desired Startup Model

For `load AGENTS.md` and similar startup/orientation prompts, the agent should
use a two-phase model:

### Phase 1: Shallow Startup Pass

Goal:

- deliver a useful, current-status overview quickly

Characteristics:

- registry-first
- bounded
- low-token
- surface-level
- operator-facing

### Phase 2: Deepening Pass

Goal:

- gather more detail only after the startup brief is delivered or the operator
  requests deeper work

Characteristics:

- targeted
- intentional
- pack-specific or workflow-specific
- triggered by a concrete need

The key rule is:

- Phase 1 must not silently expand into Phase 2

## Required Startup Boundary

### Allowed Sources In Phase 1

The shallow startup pass may read:

1. `AGENTS.md`
2. `README.md`
3. `registry/templates.json`
4. `registry/build-packs.json`
5. a bounded recent slice of `registry/promotion-log.json`
6. `deployments/` only when environment assignment actually needs explanation

### Bounded Promotion Log Rule

`recent relevant entries` in `registry/promotion-log.json` must be interpreted
as a bounded slice, not an open-ended log review.

Default boundary:

- read at most the `8` most recent relevant events

The startup pass should summarize those events, not inspect linked reports
unless the operator asks for detail.

### Deployment Read Boundary

The shallow startup pass should inspect deployment pointers only when needed to
answer:

- which build-pack is assigned to an environment

Default boundary:

- read at most the deployment pointer files needed to explain current active
  environment assignments

The startup pass must not traverse into deployment-linked pack internals.

## Sources Deferred Until After Startup

Unless the operator explicitly asks for deeper detail, the shallow startup pass
must not read:

- pack-local `AGENTS.md`
- pack-local `project-context.md`
- pack-local `pack.json`
- `eval/history/`
- benchmark artifacts
- workflow reports
- technical specs beyond the startup docs already loaded
- git history, unless repo-level tooling/doc work clearly matters to the
  startup brief and cannot be explained from the registry state first

This means startup should stay at the factory overview layer.

## Retry And Failure Boundaries

The startup pass should not become a troubleshooting loop.

If a required startup source is blocked or unreadable:

- attempt a simple read once
- allow at most one lightweight retry if the failure looks transient
- do not spiral into shell-wrapper or environment debugging during the startup
  phase

If the source still cannot be read:

- provide the best bounded startup summary available from the sources that were
  successfully read
- explicitly name the missing source and the uncertainty it creates
- stop there and ask whether the operator wants deeper troubleshooting

## Required Output Behavior

The startup reply should remain surface-level.

It should answer:

- what this repo is
- where work currently stands
- which packs are active, recently completed, and retired
- what looks most worth attention next

It should not:

- front-load deep technical detail
- explain pack internals
- narrate every file read
- troubleshoot the environment inline unless the operator asked for that

## Required Response Shape

The shallow startup response should be:

- concise
- current-state oriented
- operator-friendly
- high signal

The reply may include:

- one short phrase per relevant pack
- one short recent-work summary
- a short list of practical next steps

The reply should avoid:

- long document tours
- large file inventories
- report-path spelunking
- deep causal analysis before the operator picks a direction

## Required Documentation Updates

The following factory-level docs should be updated.

### 1. Root `AGENTS.md`

Add a `Startup Depth Boundary` rule set that:

- defines `load AGENTS.md` as a shallow startup pass by default
- explicitly separates shallow startup from later deepening
- bounds the allowed sources and retries
- says the startup pass must stop once it has enough information for an honest
  project-status brief

### 2. `README.md`

Add a short operator-facing explanation that:

- startup is intentionally shallow and status-oriented
- deeper investigation happens after the overview or on request
- the startup pass uses bounded registry reads rather than broad document
  traversal

### 3. `PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md`

Add a short tie-in to the existing time-to-context goal, explaining that
shallow startup is part of the intended operator experience.

### 4. `PROJECT-PACK-FACTORY-TEMPLATE-PLANNING-AND-CREATION-TECH-SPEC.md`

If that spec continues to reference concierge startup, it should stay
consistent with the same shallow-first boundary and avoid implying that startup
is a deep planning session by default.

## Acceptance Criteria

This specification is satisfied when:

- a fresh agent can answer `load AGENTS.md` with a useful project-status brief
  after a bounded shallow pass
- the startup pass reads only the allowed factory-level sources listed above
  unless the operator explicitly asks for more
- the startup pass does not open pack-local docs, eval artifacts, or deep tech
  specs by default
- `registry/promotion-log.json` is handled as a bounded recent slice, not a
  broad log review
- blocked reads do not cause prolonged troubleshooting before the first useful
  operator reply
- the reply remains current, honest, and surface-level even when one or more
  startup sources are unavailable

## Non-Goals

This spec does not:

- reduce the importance of registry state as the source of truth
- authorize guessing when required live state is unavailable
- eliminate deeper investigation when the operator asks for it
- change pack-level read order after the operator confirms a specific target
- replace evidence-backed startup with directory-name heuristics
