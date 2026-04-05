# Operator Intake Model

## Goal

The operator intake model is the reusable onboarding and refinement layer for
the assistant.

It lets the assistant learn from explicit, inspectable signals before those
signals are promoted into the longer-lived operator profile.

The live status surfaces are also inspectable:

- `show-operator-intake` reports the latest intake pointer, latest intake id,
  intake count, and whether the latest intake carried an explicit profile
  refinement payload.
- `show-alignment` exposes a lightweight intake status block so the operator
  can see whether the assistant is learning from intake without digging into
  raw files.

Related session-distillation surfaces stay separate on purpose:

- `distill-session-memory` records bounded session-learning decisions before
  any durable relationship memory is promoted.
- `read-memory` and `show-alignment` expose the latest distillation status
  without turning every session summary into a profile change.

The grounding/accountability cadence is separate again:

- `show-alignment` exposes the grounding status block so drift handling stays
  visible.
- the assistant should name drift plainly and ask for refinement instead of
  guessing when the operator's intent is unclear.

## Core Contracts

### `contracts/operator-intake.json`

This contract defines:

- the intake categories and prompts
- the local storage location for intake artifacts
- the latest-pointer file for restart continuity
- which stable signals may refine the operator profile
- the bounded merge rules for refinement

## Operating Model

The assistant should use intake when a signal is useful but not yet fully
established as a durable operator trait.

Recommended flow:

1. ask the operator for a focused signal
2. store the response as an inspectable intake artifact
3. write a local pointer to the most recent intake
4. record a relationship memory signal explicitly
5. refine `operator-profile.json` only when the signal is stable and clearly
   mapped to allowed profile fields

## Guardrails

- no hidden learning loop
- no silent profile mutation outside the intake record
- no profile refinement unless it is explicitly requested through
  `record-operator-intake` and captured in the intake artifact
- no guessing when the signal is ambiguous
- no replacement of PackFactory lifecycle state
- no hidden drift-handling logic outside the visible alignment status block

## CLI Surfaces

- `show-operator-intake`
- `record-operator-intake`
