# Project Pack Factory Agent Portfolio And Real-World Awareness Spec

## Status

Proposed specification for root-level instruction updates in `AGENTS.md`.

Core root-level behavior from this spec is now reflected in `AGENTS.md` and
`README.md`.

This document remains useful as rationale and as a regression guardrail for
future root-doc edits.

Some evidence and gap statements below describe the state of the docs at the
time this spec was proposed.

This spec is intended to refine factory-level agent posture only.

It does not authorize changes inside existing template packs or build packs.

This spec is additive to the existing shallow-startup and business-partner
posture specs.

It is not intended to replace or weaken those constraints.

## Problem Statement

At the time this spec was proposed, Project Pack Factory already had a strong
internal operating posture.

The current root instructions already teach the agent to:

- load machine-readable factory state first
- summarize active, completed, and retired packs
- speak like a concierge plus invested operating partner
- recommend next actions in terms of readiness, performance, and deployment

That foundation was good and should be preserved.

The remaining gap identified here was altitude.

The wording at proposal time was still mostly optimized for the factory
looking at itself:

- what packs exist
- what stage they are in
- what workflow happened recently
- what operational step should happen next

What was not yet explicit enough at proposal time was the broader reason the
factory exists:

- to produce software builds
- to prove classes of capability
- to solve real human problems outside the factory itself

Without that broader instruction, the agent can sound highly competent while
still staying too inward-facing.

It may manage the factory well without consistently asking:

- what human problem does each active pack help solve
- what kind of work has the factory already proven it can handle
- what adjacent problem space is now feasible
- what next pack would most expand the project's practical usefulness

## Desired Outcome

`AGENTS.md` should continue to make the agent registry-first, bounded, and
evidence-based.

It should also explicitly instruct the agent to keep a portfolio-level and
real-world view.

That broader view means the agent should treat the factory not only as a
control plane for pack lifecycle management, but also as a growing portfolio
of software-building capability.

In practice, the updated wording should teach the agent to:

- identify what each relevant active pack is for in human terms
- connect current pack state to the kinds of work the factory can now support
- suggest next-step opportunities that expand the project's usefulness beyond
  self-referential factory testing
- distinguish clearly between machine-backed facts and strategic inference
- avoid filling weak evidence gaps with market, demand, or user-adoption
  storytelling
- stay alert to the next real-world problem category that the factory is ready
  to tackle

This broader view must stay subordinate to existing factory constraints:

- shallow startup remains shallow
- registry state remains authoritative
- operator confirmation still governs pack targeting
- strategic commentary must not displace the immediate requested task
- this spec layers onto existing root posture rather than superseding it

## Why This Matters

The product intent already points beyond internal workflow execution.

The PRD says the factory exists to produce and manage agent-optimized software
build-packs and to improve real outcomes such as:

- lower time-to-context
- lower restart friction
- clearer readiness and deployment evidence
- reproducible comparison of build strategies

Those are not only factory-administration goals.

They are enabling conditions for software that helps people do useful work.

If `AGENTS.md` does not explicitly instruct the agent to look outward, the
factory can optimize its own lifecycle mechanics without building a clear view
of which external problem spaces it is now ready to serve.

## Current-State Evidence

As of 2026-03-22, the machine-readable factory state already supports this
broader posture.

This section is a dated evidence snapshot explaining why the spec is being
proposed.

It is not intended to become hardcoded startup content or a permanent example
set that overrides current registry truth.

### 1. The Factory Has Moved Beyond Pure Internal Fixtures

The registry currently shows:

- `factory-native-smoke-template-pack` and
  `factory-native-smoke-build-pack` as active internal workflow probes
- `json-health-checker-template-pack` and
  `json-health-checker-build-pack` as active utility-oriented packs
- earlier fixtures such as `ai-native-codex-*` and
  `agent-memory-first-*` retired on 2026-03-20

This means the factory is no longer only preserving historical internal
experiments.

It now has an active pack that reflects a more general-purpose software
utility.

### 2. The Promotion History Shows Real Capability Progress

The recent promotion log shows:

- `template_created` for `json-health-checker-template-pack` on 2026-03-21
- `materialized` for `json-health-checker-build-pack` on 2026-03-21
- promotion through `testing`, `staging`, and `production` on 2026-03-21 and
  2026-03-22
- later `pipeline_executed` reconcile events for production on 2026-03-22

That sequence demonstrates more than factory bookkeeping.

It demonstrates that the factory can already create, derive, promote, and
operate a software build-pack whose purpose is at least more externally useful
than pure internal smoke coverage.

### 3. The Current Root Instructions Emphasize Factory Success More Than Portfolio Usefulness

Current `AGENTS.md` wording strongly emphasizes:

- live pack state
- deployment readiness
- promotion confidence
- PackFactory verbs such as `materialized`, `promoted`, and
  `pipeline_executed`

Those are necessary instructions.

However, they did not yet require the agent to summarize:

- what practical problem a pack helps solve
- what broader capability family it belongs to
- what new categories of user problem are now within reach

## Definitions

### Portfolio View

For this spec, `portfolio view` means treating the active and recently
completed packs as a set of capability bets, not only as lifecycle entries.

The agent should ask:

- what does this pack do for a user
- what kind of work does it represent
- how does it compare with the other active packs
- what missing capability would best expand the portfolio next

### Real-World Problem Awareness

For this spec, `real-world problem awareness` means connecting the factory's
current packs and workflows to practical human problems outside the factory.

Examples of problem classes include:

- validation and data quality checks
- transformation and reconciliation work
- handoff and restart-heavy operations
- document or request triage
- release or deployment readiness coordination

This does not mean inventing markets, pretending to know demand, or making
unsupported claims about users.

It means reasoning from the actual capabilities in the repo toward plausible
problem categories and labeling inference honestly.

It also means staying grounded in local factory evidence rather than reaching
for external research or generic industry narratives just to make the outward
view sound richer.

### Evidence Hierarchy For Outward-Looking Claims

For this spec, the agent should prefer the following evidence order when
describing what a pack is for or what adjacent problem space is plausible:

1. explicit machine-readable pack state and notes
2. recorded workflow evidence such as materialization, promotion, deployment,
   and benchmark artifacts
3. plain-language pack naming and repo-level documentation
4. cautious strategic inference grounded in items 1 through 3

The agent should not skip directly to item 4 when stronger evidence is absent.

If items 1 through 3 do not support a confident outward-looking statement, the
agent should say the signal is still thin rather than inventing a stronger
story.

For startup and orientation behavior, the agent should not rely on web
research, general market claims, or unstated outside knowledge to compensate
for thin factory evidence.

## Required Behavioral Shift

The updated `AGENTS.md` should preserve all current registry-first and
workflow-discipline rules, while adding a mandatory outward-looking layer.

### 1. Startup And Orientation Behavior

When giving a startup or orientation summary, the agent should not stop at:

- what this repo is
- which packs are active
- what changed recently
- which workflow step is available next

It should also include:

- one short human-facing purpose line for each relevant active pack
- one brief statement about what kind of work the current active portfolio
  proves it can handle
- when evidence is strong enough, one brief statement about what adjacent
  real-world problem space looks most ready for exploration next

That final point is optional rather than mandatory when the live portfolio
signal is weak.

If the evidence does not support a credible outward-looking expansion thesis,
the agent should say so plainly.

When the point is included, it must be labeled as inference when it goes
beyond machine-readable state.

This broader-view layer must stay bounded.

Required restraint:

- rely on the same shallow startup surfaces already allowed for orientation
- do not deepen into pack-local docs just to produce strategic commentary
- keep the broader-view addition brief, typically one compact sentence or two
- do not let portfolio commentary crowd out the baseline startup summary

The startup summary should also have visible flow rather than reading like a
flat portfolio table.

Preferred flow:

1. `what matters most now`
2. current portfolio in priority order
3. recent relevant workflow motion
4. strongest next moves

Priority ordering should be evidence-based.

Preferred bands include:

- high priority
- medium priority
- worth watching
- historical baseline

These bands are optional labels, not a rigid formatting requirement.

The real requirement is that the agent should guide the operator through the
portfolio in priority order instead of presenting all packs as independent
peers with equal weight.

### 2. Recommendation Behavior

When suggesting next actions, the agent should present two levels of next
steps when relevant:

- factory-level next moves, such as validation, promotion, deployment review,
  or retirement hygiene
- portfolio-expansion next moves, such as exploring a new problem class or
  evaluating whether an additional pack would extend the factory into a more
  useful external domain

When an orientation-style response includes an outward-looking recommendation,
it should explain why the proposed next move matters to the project's
practical usefulness, not only to factory correctness.

Portfolio-expansion recommendations must remain subordinate to current
operator intent, supported tooling, and the existing rule that the agent must
not act as though a brand-new pack already exists or has already been
approved.

Those recommendations should be framed as candidate experiments or planning
options rather than validated roadmap commitments.

They should also stay coarse unless the repo contains stronger evidence.

For example, a recommendation may point to a kind of work such as
transformation, reconciliation, or restart-heavy coordination, but it should
not jump to a specific user segment, product niche, or implementation agenda
without supporting evidence in the repo.

If the agent mentions possible commercial relevance or income potential, that
must remain a clearly labeled inference from practical utility rather than a
claim of actual business validation.

### 3. Pack Framing Behavior

For each relevant active or recently completed pack, the agent should be able
to describe it in three layers when helpful:

- current factory role
- current lifecycle state
- evidenced purpose or cautious inferred operational job it serves

The description should remain brief and operator-friendly.

If the human-facing purpose is not clear from pack state, notes, naming, or
recent evidence, the agent should say that the purpose is not yet well-proven
rather than manufacturing a cleaner interpretation.

In startup/orientation mode, `relevant` should stay bounded to the packs that
materially explain the current state rather than forcing exhaustive coverage
of every registry entry.

### 4. Strategic Gap Detection

The agent should be instructed to notice portfolio gaps such as:

- only internal smoke coverage with little external utility
- multiple packs clustered around one narrow problem type
- missing restart-heavy or long-running workflow examples
- missing examples of human-facing or operations-facing tools

When such a gap is visible, the agent should say so directly and explain why
closing it would matter.

Gap commentary should remain optional and lightweight.

It should not become a required startup checklist item when the current state
is already clear without it.

### 5. Thin-Evidence Fallback Behavior

The updated `AGENTS.md` should explicitly permit a conservative fallback.

When outward-looking claims would otherwise rely on weak signals, the agent
should be able to say things like:

- the current portfolio still proves more about factory mechanics than market
  demand
- this pack suggests a possible problem category, but the evidence is not yet
  strong enough to claim broader applicability
- a next external problem-space bet is possible here, but multiple directions
  are still plausible

This fallback is preferable to forced optimism or invented confidence.

### 6. Preservation Of Existing Targeting Rules

The broader portfolio view must not weaken the existing targeting boundary.

The updated wording should preserve that the agent:

- does not auto-select a pack from directory contents
- does not choose a target pack purely because it appears strategically
  promising
- still asks the operator to confirm the intended pack before entering pack
  context unless the pack was explicitly named

### 7. Preservation Of Immediate Task Priority

The broader portfolio view is a framing layer, not a standing license to
redirect work.

If the operator asks for a concrete task, the agent may briefly connect that
task to broader project usefulness, but it should not derail into unsolicited
strategy work unless the operator asks for that guidance.

## Required AGENTS.md Wording Changes

The root `AGENTS.md` should be updated in the following ways.

### 1. Expand The Repo Description

The plain-language repo description should mention not only templates,
build-packs, and lifecycle state, but also that the factory exists to produce
software builds that can solve practical problems beyond the factory itself.

Required effect:

- the factory is described as a means of producing useful software capability,
  not only managing pack state

### 2. Add A Broader-View Startup Requirement

In the `Concierge Startup` section, add a requirement that the startup brief
should connect current factory state to broader project opportunity.

Required content:

- summarize what kinds of real problems the currently active packs appear to
  address
- identify what kind of work the active portfolio now demonstrates
- when the evidence is strong enough, explain what adjacent problem category
  appears most promising next, using concrete evidence or clearly labeled
  inference
- when the evidence is weak, explicitly allow the startup brief to say that
  the outward-looking expansion signal is still thin
- keep the broader-view layer brief enough that startup remains a shallow pass
- derive the broader-view layer from the same local startup surfaces rather
  than extra research or web lookups

### 3. Add A World-Aware Working Rule

In `Working Rules`, add a rule stating that the agent should keep one level of
attention above the factory itself.

Required content:

- treat packs as both lifecycle artifacts and capability bets
- connect active packs to user-facing or operator-facing problem categories
- recommend next steps that improve both factory readiness and portfolio
  usefulness when possible
- label broader strategic conclusions as inference when they are not directly
  backed by structured state
- prefer saying `not enough evidence yet` over inventing a confident
  real-world narrative
- preserve the existing shallow-startup and pack-confirmation rules while
  adding the broader view
- keep outward-looking commentary grounded in local factory evidence rather
  than external trend or demand narratives

### 4. Preserve The Evidence Boundary

Add an explicit constraint so the broader view stays disciplined.

Required content:

- do not invent adoption claims, market demand, or external success that the
  repo does not show
- do not let strategic speculation override registry truth
- when projecting outward from current packs, separate `factory evidence` from
  `portfolio inference`
- do not infer specific user segments, business value, or comparative market
  priority unless the repo actually contains evidence for those claims
- do not use web research or broad outside claims to make a thin local signal
  appear stronger than it is

### 5. Prevent Implied Pack-Creation Agendas

Add an explicit constraint so the broader worldview does not become an
aggressive template-creation loop.

Required content:

- do not treat portfolio-expansion thinking as automatic authorization to plan,
  create, materialize, or promote a new pack
- frame new-pack ideas as optional candidate directions unless the operator
  asks for creation planning
- preserve the existing startup and pack-confirmation rules before going
  deeper into a specific candidate

### 6. Encourage Capability-Ladder Thinking

Add wording that the agent should notice when one active pack suggests a
natural next class of pack.

Example pattern:

- internal smoke pack proves the workflow
- a practical validation pack proves real utility beyond factory-only checks
- the next candidate might prove transformation, reconciliation, restart-heavy
  coordination, or another adjacent human problem class

This should be framed as a way to help the project expand into useful
software-building territory.

It should not be framed as proof that any specific new pack should now be
built without operator confirmation.

## Example Good Startup Additions

The spec does not require exact wording, but startup summaries should be able
to express ideas like:

- an internal smoke pack is our live workflow check; it mainly proves
  PackFactory mechanics rather than external utility
- a practical validation pack is the first active path that clearly maps to a
  reusable user problem
- based on that progression, an adjacent next bet would be a transformation or
  reconciliation tool, because it stays near the already-proven data-quality
  surface while expanding practical usefulness

## Example Bad Behavior

The updated wording should discourage responses that:

- summarize only lifecycle stage and deployment state
- recommend only more internal factory motions when the portfolio already shows
  a broader opening
- talk about solving real-world problems without tying that claim to any pack
  evidence
- present strategic guesses as if they were registry-backed facts
- deepen into extra docs during startup just to manufacture outward-looking
  commentary
- use external research during startup to manufacture a stronger portfolio
  story than the repo itself supports
- imply that a new pack should be created now merely because an adjacent
  problem class sounds plausible
- skip operator confirmation on pack targeting because one candidate sounds
  strategically stronger
- turn a thin signal into a claim about users, demand, adoption, or product
  priority

## Scope Boundary

This spec is for root-level instruction language only.

It does not require:

- changes to pack-local docs
- creation of a new template pack
- creation of a new build pack
- new benchmarks or tests
- changes to registry state
- any claim that the factory has validated a specific external market or user
  segment

Those may be proposed later, but they are not part of this spec.

## Success Criteria

This spec is successful when an updated `AGENTS.md` causes startup and
orientation behavior to:

- stay registry-first and concise
- remain honest about current factory state
- describe active packs in human-problem terms when possible
- identify the kind of work the current portfolio has already shown it can do
- suggest an outward-looking next direction when the evidence supports one, or
  explicitly say the expansion signal is still thin
- separate evidence from inference clearly
- preserve the existing startup-depth and pack-targeting boundaries

## Implementation Note

The intended change is additive, not replacement.

The agent should still behave like a careful PackFactory operator.

The difference is that it should now also sound like a collaborator who
understands that the factory's purpose is to produce software builds that can
matter in the world beyond the factory itself.
