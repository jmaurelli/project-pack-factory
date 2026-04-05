# ADF Symptom-To-Boundary Mapping Workflow v1

## Purpose

Record the systems-thinking workflow ADF should use to walk the target lab and
populate symptom-entry playbooks, boundary-confirmation pages, and deep guides.

This note is about discovery and mapping method.
It is not a requirement that the final operator-facing page uses the same
internal terms.

## Main Idea

Use systems thinking to discover the real troubleshooting path.
Use support language to present that path.

The lab method should remain evidence-first and bounded.
The goal is not to map the whole system for every symptom.

## Start Point

Start from a vague customer symptom, not from a chosen subsystem.

Examples:

- `The web page is not loading`
- `Login is failing`
- `ASMS opens but the customer cannot continue`

This keeps the mapping tied to real support entry conditions.

## Mapping Loop

For each symptom family:

1. Reproduce one bounded journey in the target lab.
2. Observe the visible checkpoints in the order a support engineer would meet
   them.
3. Prefer the lowest-cost, highest-signal safe check that can narrow the case.
4. Ask where the first useful decision happens.
5. Record that point as the current support boundary.
6. Stop when the next action is clear instead of widening into open-ended
   subsystem research.

## What Counts As A Boundary

A boundary is the first place where the engineer can make a safe, useful
decision that changes the next action.

This is a support boundary first, not automatically the deepest engineering
truth.

Examples of useful boundary outcomes:

- this is still a top-level page outage
- the page opens, so the problem is narrower than `GUI down`
- login is failing, so the next service to check is Keycloak
- the service is down, so the next step is logs plus escalation
- the service is up, so the engineer should continue to the next branch

If the next meaningful step would require R&D-only product knowledge,
unsupported mutation, or broad reverse engineering, stop at the support
boundary and record the escalation target instead of widening the walk.

If two candidate boundaries appear at the same time, prefer the one that:

1. is safer to check live
2. is easier for support to read and explain
3. rules out more ambiguity with fewer commands

## Lab Walk Method

Use this bounded walk for each symptom:

1. Start from the customer-visible symptom.
2. Run the first safe support checks.
3. Record the first branch point that reduces ambiguity.
4. Continue only until the next page or escalation target is clear.
5. Move deeper technical explanation into a guide instead of keeping it in the
   frontline path.

Do not keep walking just because more internal dependencies exist.
Do not widen into a second new service branch in the same pass unless the first
branch was already ruled out.

## Questions For Each Candidate Step

Keep a step in the frontline path only if all of these are true:

- a support engineer can run it safely during a live session
- it reduces ambiguity
- it changes what the engineer should do next

If a step does not meet all three, keep it out of the main playbook flow.

If two fast checks still do not narrow the case to a next page, next service,
or safe escalation packet, stop and record the ambiguity instead of widening
the frontline path by default.

## Page-Type Assignment Rule

Assign mapped findings like this:

- first branching point from vague symptom -> symptom-entry playbook
- named service or subsystem check -> boundary-confirmation page
- architecture, dependency explanation, or upstream references -> deep guide

If a finding does not clearly fit one of those three outputs yet, keep it in
mapping notes until the next support-useful shape is clear.

Do not promote one mapping slice into more than one primary page type.
Split frontline routing and deeper explanation into separate outputs.

## Page Creation Gate

Before creating a new page from a mapping run, ask:

1. Will this page help a frontline support engineer decide where to start or
   what to check next?
2. Is the new page type clear: symptom-entry, boundary-confirmation, or deep
   guide?
3. Can the page stay short enough for live-session use?

If any answer is no, do not create the page yet.

## Evidence Record

Each mapping run should capture:

- symptom statement
- the customer words that triggered the case entry
- target and time window
- exact checks used
- first branching result
- chosen page type
- primary support question answered
- named next service or next page
- rejected branches
- operator-facing wording for the next step
- what the engineer should save
- escalation stop point if the case is not support-resolvable

Each run should also preserve two output rows when possible:

- one internal mapping row for ADF authors
- one operator-facing row in plain support language

This keeps the method repeatable and easier to compare.

## Current ADF Application

For the current ADF phase:

- `ASMS UI is down` remains the main symptom-entry proving ground
- the live Keycloak-down condition is a useful pilot for boundary-confirmation
  content
- imported-module pages should be treated as second-stage checks unless the
  customer symptom already points there

## Practical Output Shape

The mapping workflow should eventually feed a small structured table for each
high-value symptom:

- customer symptom
- first check
- first branch result
- next page
- service to inspect
- what to save before escalation

This is the handoff between systems thinking and operator-facing content.

Keep the internal mapping row separate from the operator-facing row so the
generator does not accidentally reuse internal analysis wording in the main
frontline content.

## Current Code Anchors

This workflow is expected to anchor to the current backend map path in:

- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `build_support_baseline()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_diagnostic_flows()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_symptom_lookup()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_decision_playbooks()`

These functions already form the current mapping pipeline:

- evidence becomes `diagnostic_flows`
- flows become `decision_playbooks`
- flows also become `symptom_lookup`

That is the current code path this workflow is expected to tighten, not replace
from scratch.

## First Expected Change Surfaces

The first implementation-grade changes expected by this workflow should happen
in:

1. `_build_symptom_lookup()`
   Carry clearer symptom-entry routing and first-action data.

2. `_build_diagnostic_flows()`
   Preserve clearer branch and stop-point information from the lab-backed map.

3. `_build_decision_playbooks()`
   Carry operator-facing branch and handoff output from the mapping result
   instead of flattening everything into one generic playbook shape.

## Fail-Closed Rule

Stop the mapping pass when one of these becomes true:

- the next action is already clear for support
- the next check would require unsafe or unsupported change
- the next useful question belongs to R&D or a senior engineer
- the remaining investigation is mostly architecture learning rather than live
  triage value
