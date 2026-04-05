# Project Pack Factory ADF Successor Initial Role/Domain Lens First Test

## Status

Draft v1 bounded selection test for the initial role/domain lens of the fresh
ADF successor line.

## Purpose

Choose the first role/domain lens that should guide the ADF successor's first
wave, specifically the shallow surface map slice, without turning role/domain
selection into a long abstract design exercise.

## Why Test The Lens Now

The ADF successor line should choose its initial role/domain framing before the
creation request is prepared, but it does not need a perfect lifetime identity
up front. The role/domain only needs to be strong enough to help the first
slice succeed.

That means the right test is:

- compare a few plausible lenses
- judge them against the first slice
- pick the best initial fit
- leave refinement for after the first artifact exists

## First-Slice Reference

This test is explicitly anchored to the first-wave shallow surface map:
[PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md)

The first slice is:

- read-only
- evidence-first
- host-and-runtime observable
- machine-readable first
- operator-reviewable second
- intentionally shallow

Any initial role/domain lens that does not improve those behaviors is the wrong
first lens.

## Test Criteria

The initial lens should help the agent:

1. map the live system before theorizing
2. separate observed evidence from inference
3. produce machine-readable diagnostic structure
4. stay support-useful rather than academically interesting
5. stop at a shallow useful boundary instead of over-deepening

## Candidate Lenses

### Candidate A: `research-analyst`

Source: existing PackFactory catalog entry in
[agent-role-domain-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-role-domain-template-catalog.json)

Strengths:

- strongly evidence-first
- clearly separates fact from inference
- well aligned to bounded uncertainty handling

Weaknesses for ADF wave 1:

- can lean too far toward synthesis and caution instead of useful system
  extraction
- does not naturally encode support-stop-point thinking
- does not naturally emphasize derived playbook usefulness

Judgment:

- strong adjacent fit
- not the best direct first-wave ADF lens

### Candidate B: `diagnostic-systems-analyst`

Proposed custom ADF line-specific lens.

Intended framing:

- map the running system before interpreting it
- treat processes, services, ports, configs, logs, and JVM surfaces as first
  observable seams
- produce machine-readable diagnostic structure from those seams
- keep support-useful stop points visible
- treat unknowns explicitly without freezing progress

Strengths:

- matches the shallow surface map directly
- supports system and dependency mapping without requiring deep reverse
  engineering on day one
- aligns naturally with machine-readable artifact creation
- keeps the line centered on diagnostic structure, not just prose analysis

Weaknesses:

- still needs careful wording so it does not imply full systems mastery
- should stay line-local first until it proves reusable

Judgment:

- best first-wave fit

### Candidate C: `support-playbook-architect`

Proposed custom ADF line-specific lens.

Intended framing:

- shape findings into support-friendly playbook structure
- optimize for step ordering, stop points, and engineer-readable guidance

Strengths:

- strong downstream fit for derived operator output
- aligns with the eventual support-facing product layer

Weaknesses for ADF wave 1:

- too downstream for the first slice
- risks pushing language and playbook structure too early, before the machine-
  readable diagnostic layer is strong enough

Judgment:

- likely a later-wave secondary framing, not the best initial lens

## Result

The recommended initial ADF role/domain lens is:

- `diagnostic-systems-analyst`

Why:

- it best matches the first slice
- it privileges live evidence and structure over speculation
- it supports the machine-readable-first product model
- it can still derive support-facing artifacts later without making the first
  slice prematurely about prose

## Recommended First-Pass Lens Definition

The initial ADF successor role/domain lens should tell the agent to:

- map the live system before theorizing about it
- treat processes, services, ports, configs, logs, and JVM surfaces as the
  first diagnostic seams
- separate observed evidence from inference
- prefer machine-readable structure over narrative explanation when both are
  possible
- optimize for support-useful stop points rather than broad technical
  completeness
- keep deeper subsystem reasoning for later slices unless the shallow layer
  clearly demands it

## Decision Boundary

This first test does not require PackFactory catalog expansion yet.

The recommended path is:

- use `diagnostic-systems-analyst` as a line-specific initial role/domain lens
  in the successor-line creation request
- test it through the shallow surface map slice
- only later decide whether it should be promoted into the shared role/domain
  catalog

## Evidence

This test is grounded in:

- the bounded successor-line model in
  [PROJECT-PACK-FACTORY-BOUNDED-AGENT-CENTERED-ADF-SUCCESSOR-LINE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-BOUNDED-AGENT-CENTERED-ADF-SUCCESSOR-LINE-TECH-SPEC.md)
- the first-slice definition in
  [PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md)
- the current PackFactory role/domain catalog in
  [agent-role-domain-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-role-domain-template-catalog.json)
- the current ADF objective and lessons in
  [project-objective.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/contracts/project-objective.json)
  and
  [work-state.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json)

## Decision

For the first test of the initial ADF role/domain lens, `diagnostic-systems-analyst`
is the recommended first-wave choice.
