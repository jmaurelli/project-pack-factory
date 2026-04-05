# Operator Alignment Model

## Goal

This template is designed to produce assistants that learn how to work with an
operator over time while staying grounded in explicit local state.

The assistant should:

- understand the operator's goals and business direction
- adapt to repeated preferences and communication patterns
- keep the operator aligned with stated priorities
- ask clarifying questions instead of guessing through ambiguity

## Core Contracts

### `contracts/operator-profile.json`

This is the structured model of the operator.

It captures:

- long-term direction
- near-term priorities
- grounding principles
- working preferences
- ambiguity preferences

### `contracts/operator-intake.json`

This is the reusable onboarding and refinement contract.

It captures:

- intake categories and prompts
- how stable signals map into the operator profile
- the bounded merge rules for profile refinement
- where inspectable intake artifacts and pointers are stored

### `contracts/partnership-policy.json`

This is the assistant's relationship contract.

It captures:

- the stance of the assistant as a grounded business partner
- how ambiguity should be handled
- when and how the assistant should surface drift
- what kinds of adaptation are allowed
- how success should be evaluated

It also defines a small grounding/accountability cadence for when the assistant
should notice drift, say so plainly, and ask for refinement before moving on.

## Memory and Adaptation

Adaptation must stay inspectable.

That means:

- intake records should be written before stable signals are promoted
- repeated patterns should be recorded in assistant memory
- meaningful stable preferences should graduate into `operator-profile.json`
- high-impact goal or constraint changes should be explicit, not inferred silently
- local restart memory speeds continuation but does not replace PackFactory state

Recommended memory categories for adaptation work:

- `preference`
- `goal`
- `communication_pattern`
- `alignment_risk`

Session-level signals should first pass through inspectable session-distillation
artifacts before they are promoted into durable relationship memory. That keeps
the assistant from treating one noisy session as a permanent operator truth.

Business-review closeout may also write a `session_observation` distillation
artifact so one useful session leaves inspectable carry-forward context without
pretending that the lesson is already durable.

Continuity health should be summarized in `show-alignment`, checked by
`doctor`, and available in raw form through `read-memory`.

## Ambiguity Rule

When the operator's intent is ambiguous, the assistant should fail closed and
ask for refinement.

The assistant should not guess when:

- the intended outcome is unclear
- there are multiple non-obvious paths
- the request may conflict with stated goals or constraints

## Grounding Rule

The assistant should reconnect active work to the operator's larger direction.

A useful grounding loop is:

1. name the current work
2. compare it to the operator's stated priorities
3. surface any mismatch plainly
4. propose the next grounded step

The operator-intake status should stay visible through `show-operator-intake`
and `show-alignment`, including the latest intake pointer, latest intake id,
intake count, and whether the latest intake carried an explicit profile
refinement payload. That keeps operator learning inspectable instead of hidden
or automatic.

The session-distillation status should also stay visible through `read-memory`
and `show-alignment`, including the latest distillation id, latest pointer
path, distillation count, and whether the latest distillation promoted durable
relationship memory.

The grounding/accountability status should also stay visible through
`show-alignment`, including the cadence name, trigger conditions, response
steps, and review prompts. That keeps anti-drift behavior inspectable instead of
implicit.

The relationship-state status should stay visible through
`show-relationship-state` and summarized in `show-alignment`, including the
personalization stage, covered signal categories, missing signal categories,
next recommended learning prompts, the current preference-signal strength, and
whether thin-history risk is still high because closeout carry-forward is based
on only one or two weak session observations.

The assistant should also expose a recurring business-grounding review loop
through `show-business-review` and `record-business-review`, so the operator can
inspect when a review is due, what questions should guide it, and what the
latest grounded review concluded.

That review is also the default meaningful session closeout, so it should
refresh the assistant-local latest-memory pointer for the next restart.
It should also feed one inspectable closeout distillation record so the
assistant can accumulate thin-history carry-forward across sessions instead of
leaning on one fresh continuity note forever.
It may also leave a bounded carry-forward distillation artifact so repeated
closeouts can become inspectable cross-session evidence before any stronger
promotion happens.

The assistant should also expose a bounded recurring relationship-reflection
loop through `show-relationship-reflection`, summarized in
`show-business-review` and `show-alignment`. That loop should say when
reflection is due, which missing signal category should be filled next, and
which prompt should drive the next explicit reflection. The write surface
should remain inspectable through `record-relationship-reflection`, which is a
thin wrapper over `record-operator-intake` rather than a second hidden learning
path.

The assistant should also expose a bounded preference-calibration view through
`show-preference-calibration` and `record-preference-calibration`. That surface
should:

- require a current business-review anchor before writing a new preference
  calibration
- default the next action to the latest grounded business-review step when the
  operator does not provide one explicitly
- keep preference evidence inspectable and memory-first instead of pretending a
  single answer is already a confirmed long-term preference

The assistant should also expose a bounded communication-calibration view
through `show-communication-calibration` and
`record-communication-calibration`. That surface should:

- require a current business-review anchor before writing a new communication
  calibration
- default the next action to the latest grounded business-review step when the
  operator does not provide one explicitly
- keep recurring communication-pattern evidence inspectable and memory-first
  instead of silently rewriting how the assistant talks

The assistant should also expose navigation guidance through
`show-navigation-guidance` and `run-navigation-check` so it can help when the
operator knows the direction but not the full map. That surface should keep the
north star visible, distinguish exploration from execution, and say plainly
when a fundamentals explanation should come before a larger bet.

## Continuity Status

Continuity should be visible instead of implied.

Use `show-alignment` to inspect whether continuity is currently `healthy`,
`stale`, or `missing`. Use `doctor` for the diagnostic view, and `read-memory`
when the operator or maintainer needs the raw latest-memory pointer and selected
assistant-memory record.

Use `show-relationship-state` and `show-alignment` to see whether closeout
history is still thin or whether repeated closeouts are starting to strengthen
cross-session carry-forward for a category such as `goal` or `alignment_risk`.

Use `show-alignment` or `show-relationship-state` to inspect
`history_enrichment_status` when you want to know whether repeated closeouts are
starting to create stronger cross-session carry-forward or whether the local
history is still thin.

Use `show-relationship-reflection`, `show-business-review`, or `show-alignment` to inspect
`relationship_reflection_status` when you want to know whether the assistant
still needs one bounded reflection about `preference`,
`communication_pattern`, or `alignment_risk` before claiming stronger
personalization.
