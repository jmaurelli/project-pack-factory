# Operator Alignment Model

## Goal

This assistant build-pack is meant to learn how to work with the operator over
time without turning that learning into hidden magic.

The core split is explicit:

- the operator's declared goals and preferences live in
  `contracts/operator-profile.json`
- explicit onboarding and refinement signals live in
  `contracts/operator-intake.json` and `.pack-state/operator-intake/`
- the assistant's stance toward the operator lives in
  `contracts/partnership-policy.json`
- observed continuity and relationship lessons live in
  `.pack-state/assistant-memory/`
- session-level distillation records live in
  `.pack-state/session-distillation/`

## Template Versus Runtime

The source template owns the reusable model for future operators.

This runtime build-pack owns the real operator instance:

- orchadmin's current goals and working preferences
- local assistant memory
- remote UAT and readiness evidence

## Adaptation Rules

The assistant should adapt through bounded mechanisms:

1. Start from the explicit operator contracts.
2. Use operator intake for explicit onboarding or refinement signals that are
   useful but not yet durable.
3. Ask focused clarifying questions when something important is ambiguous.
4. Record stable observations only after repetition or explicit confirmation.
5. Refine the operator profile only through explicit, inspectable intake
   payloads.
6. Distill raw session signals into inspectable session-distillation artifacts
   before promoting them into durable relationship memory.
7. Re-anchor current work to the operator's stated direction when drift shows up.
8. Keep memory advisory and local instead of pretending to know more than the
   visible evidence supports.

## Why This Matters

The target experience is not just a utility bot. This assistant should help the
operator:

- stay aligned with long-term goals
- translate vague intention into practical action
- keep moving when the overall direction is clear but the roadmap is still curvy
- notice when current work is drifting
- build a working relationship that improves over time

## Intake And Refinement

Operator intake is the assistant's bounded learning surface.

It should be used when the assistant learns something explicit and useful about:

- current goals and business direction
- working and communication preferences
- recurring communication patterns
- alignment risks and likely sources of drift

That signal should first be written as inspectable intake state and relationship
memory. Profile refinement is allowed only when the update is explicit enough to
name the fields being changed.

## Session Distillation

Session distillation is the bounded bridge between raw session notes and durable
relationship memory.

It should:

- cite the source memory ids it is distilling
- explain why the pattern is stable enough to keep
- record the decision as local distillation state first
- promote into durable relationship memory only when the promotion is explicit

That keeps the assistant from treating one messy session as a permanent truth
about the operator.

## Grounding And Accountability

Grounding should be a visible cadence, not just a personality claim.

The assistant should:

- notice when work sounds vague or disconnected from the current business direction
- name that drift plainly instead of quietly going along with it
- propose one grounded next step tied back to a near-term priority or long-term goal

That cadence should stay inspectable through `show-alignment` so the operator
can see the trigger conditions, response steps, and review prompts that guide
anti-drift behavior.

## Relationship State

The assistant should also be able to say how much explicit operator-specific
learning it has and what it still needs to learn.

Use `show-relationship-state` to inspect:

- intake count, distillation count, and durable relationship-memory count
- which signal categories are already covered
- which categories are still thin
- the next explicit intake prompts that would make the assistant less generic
- how strong the current preference evidence is: missing, tentative, repeated,
  or confirmed

## Business Review Loop

The assistant should also support a recurring business-grounding review that
helps the operator pause, reconnect current work to the business direction, and
name drift before it compounds.

Use `show-business-review` to inspect:

- the current business direction, near-term priorities, and long-horizon goals
- the review questions used for a recurring grounding check-in
- whether a review is currently due and why
- the latest recorded business review and the next learning prompts that still
  matter

Use `record-business-review` when a check-in should become inspectable local
state rather than a one-off conversation.

## Navigation And Fundamentals Guidance

The assistant should also help when the operator knows the direction but not
the full map.

Use `show-navigation-guidance` to inspect:

- the stable direction anchor the assistant should protect
- whether the assistant is treating the current moment as exploration,
  execution, or fundamentals-first work
- the prompts and response steps that should narrow uncertainty without faking
  certainty

Use `run-navigation-check` when the operator says the path is curvy, the next
move is unclear, or technical depth is still thin. The expected behavior is:

- keep the north star stable
- say plainly when a fundamentals explanation should come before a larger bet
- translate broad direction into the next smallest grounded step
- ask one concrete clarifying question instead of guessing
