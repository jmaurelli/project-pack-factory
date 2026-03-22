# Project Pack Factory Shallow Startup And Initialization Spec

## Status

Proposed specification for factory-level startup and initialization guidance.

This spec is for root-level factory docs only. It does not authorize changes to
internal documentation inside existing template packs or build packs.

## Problem Statement

Project Pack Factory correctly tells the agent to load enough machine-readable
state to provide a useful startup brief.

That is good and should be preserved.

The current issue is depth, not direction.

On `load AGENTS.md` and similar startup/orientation requests, the agent is
loading valid context, but it is too easy for that startup pass to become a
deeper research pass:

- it keeps reading after a useful surface-level project status is already
  available
- it starts reaching for broader background documents too early
- it spends time and tokens on detail before the operator has confirmed where
  to go next

The result is too much upfront depth for a task that should primarily answer:

- what is this factory
- where does work currently stand
- what looks active, completed, or retired
- what seems like the strongest next move at a high level

## Desired Outcome

Startup should become a bounded shallow pass.

The agent should still:

- know what the project is
- understand the current live pack state
- identify likely next actions
- sound informed and in control

But it should do that from a limited surface scan, not from early deep dives.

## Evidence

### 1. Current Startup Guidance Is Rich But Not Bounded

In [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md), the startup
flow correctly points the agent at:

- `registry/templates.json`
- `registry/build-packs.json`
- `registry/promotion-log.json`
- `deployments/` when needed

That is the right live-state foundation.

However, the current instructions do not define:

- a startup depth budget
- a maximum number of extra files or documents to inspect
- a stopping point once the startup brief is answerable
- a rule that explicitly distinguishes shallow status loading from deeper
  investigation

### 2. `First Reads` Still Encourages More Than A Pure Status Pass

In [AGENTS.md](/home/orchadmin/project-pack-factory/AGENTS.md), the `First
Reads` list still includes:

- `README.md`
- `PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

Those documents are useful, but a pure startup/status request does not usually
need all of them before replying.

Without a shallow-pass rule, agents have permission to keep reading because the
documents are available and relevant.

### 3. Operator Startup Language Rewards Richness But Not Restraint

In [README.md](/home/orchadmin/project-pack-factory/README.md), the operator
startup response is described in rich concierge terms and asks for a project
briefing with current state, recent work, and next-step options.

That is useful, but it still does not tell the agent when to stop reading and
answer.

### 4. Swarm Behavior Evidence

A startup-behavior swarm was invoked against the current `load AGENTS.md`
instructions so the spec could be informed by actual agent behavior rather than
doc reading alone.

What that exercise reinforced is that the current startup path has no explicit
bounded shallow-pass rule and no clear stop condition before deeper document
reads.

In practice, the agents had the current startup instruction stack, a broad
concierge objective, and no explicit rule saying:

- `once registry and recent promotion state are enough, stop reading and brief`

That missing stop condition is the behavior gap this spec is intended to fix.

## Required Startup Model

Startup should be split into two layers:

### Layer 1: Shallow Startup Pass

This is the default for:

- `load AGENTS.md`
- startup/orientation requests
- `what is going on here`
- `what is the current state`
- `what should we look at next`

The shallow startup pass is for overview only.

### Layer 2: Deepening Pass

This happens only after one of the following:

- the operator names a specific pack
- the operator asks a deeper product, workflow, or testing question
- the shallow pass reveals a concrete ambiguity that cannot be resolved from
  the live factory surfaces

The deepening pass is not part of the default startup brief.

## Required Shallow Startup Budget

For a normal `load AGENTS.md` or equivalent startup request, the agent should
read only this minimum bounded set before answering:

1. `AGENTS.md`
2. `README.md`
3. `registry/templates.json`
4. `registry/build-packs.json`
5. a shallow slice of recent relevant entries from `registry/promotion-log.json`

`deployments/` may be consulted only when:

- the startup brief needs to explain a current environment assignment
- the registry state points to a deployment pointer that materially affects the
  summary

The shallow startup pass should not read additional top-level product or
workflow specs unless one of the deepening conditions is met.

## Required Promotion Log Limit

The startup pass should not treat the full promotion log as required reading.

Instead, it should read only a bounded shallow slice sufficient to summarize
recent relevant work.

Required behavior:

- prefer the most recent relevant events first
- stop once the active, recently completed, and retired picture is clear
- do not keep digging through older history when it is not changing the
  startup summary

This spec intentionally leaves exact implementation flexible, but the behavior
must be visibly shallow and bounded.

## Required Stop Condition

The startup/orientation pass must stop and answer once all of the following are
true:

- the repo can be described in plain language
- current active, recently completed, and retired packs can be identified from
  registry state
- any currently assigned deployment can be named if relevant
- recent relevant factory work can be summarized at a high level
- practical next-step options can be offered

Once those conditions are satisfied, the agent must answer instead of
continuing to read more background material.

## Required Escalation Rule

The agent may deepen beyond the shallow pass only when needed.

Allowed reasons:

- the operator explicitly asks for more depth
- a pack has been named and pack-local context is now required
- a high-level startup claim would otherwise be wrong or materially incomplete
- a referenced deployment assignment needs confirmation from `deployments/`

Not allowed as standalone reasons:

- `this doc might be relevant`
- `more context is always better`
- `I want to be extra thorough before replying`

## Required Changes To Root Docs

The following factory-level docs should be updated.

### 1. Root `AGENTS.md`

Add a `Shallow Startup Rule` or equivalent working-rule block.

Required content:

- startup/orientation requests use a bounded shallow pass first
- the default startup pass is overview-only, not research-heavy
- the agent should stop after the minimum live-state surfaces are enough to
  answer
- deeper docs such as PRD/testing-policy/specs are for escalation, not default
  startup

### 2. `README.md`

Add a short `Startup Depth` or equivalent section.

Required content:

- operator startup should feel informed but lightweight
- the startup briefing should come from a shallow registry-first scan
- richer product or workflow docs are not default startup requirements
- the agent should answer once the current state is clear instead of continuing
  to dig

### 3. Optional Supporting Spec Updates

If desired, related factory-level specs may later be updated to stay aligned
with this shallow-startup model, but this spec does not require pack-internal
doc changes.

## Examples

### Good Startup Behavior

- read `AGENTS.md`
- read `README.md`
- inspect `registry/templates.json`
- inspect `registry/build-packs.json`
- inspect only recent relevant promotion-log entries
- check `deployments/` only if the summary needs to explain a live environment
  assignment
- answer with a concise project-oriented briefing

### Bad Startup Behavior

- read the full PRD during a basic status request
- open testing-policy or workflow specs before the startup summary is even
  answerable
- keep opening more docs after active/recent/retired state is already clear
- enter a pack before the operator confirms the target

## Acceptance Criteria

This specification is satisfied when:

- a fresh agent can answer `load AGENTS.md` from a bounded shallow pass
- the startup pass is visibly based on registry-first live-state sources
- the startup pass does not routinely open PRD, testing policy, or deeper tech
  specs before replying
- the startup reply still includes repo purpose, current state, recent work,
  and next-step options
- the agent stops reading once the startup brief is answerable
- deeper reads happen only after explicit operator direction or concrete
  blocking ambiguity

## Non-Goals

This spec does not:

- reduce startup quality to a one-line acknowledgment
- remove registry-based state reading
- prevent later deeper investigation
- change pack-target confirmation rules
- require changes to internal docs inside existing template packs or build
  packs
