# Assistant Architecture

## Purpose

This build-pack turns the PackFactory scaffold into a Codex-native personal
assistant baseline that can become an operator-aligned working partner.

The design stays intentionally bounded:

- machine-readable contracts define the assistant, the operator, and the
  partnership stance
- CLI commands expose those capabilities directly
- local assistant memory captures continuity about goals, preferences, and
  alignment risks
- bootstrap exports create a portable preview workspace rather than mutating
  the real Codex home automatically

## Template Versus Runtime

The source template owns the reusable assistant product line:

- assistant behavior model
- operator-profile schema
- partnership and ambiguity policy
- routing, memory, bootstrap, and doctor surfaces

This derived build-pack owns the runtime instance:

- orchadmin's concrete goals and working preferences
- local assistant memory
- readiness and evaluation evidence
- remote user-acceptance testing surfaces

## Core Surfaces

- `contracts/assistant-profile.json`
- `contracts/operator-profile.json`
- `contracts/partnership-policy.json`
- `contracts/context-routing.json`
- `contracts/memory-policy.json`
- `contracts/skill-catalog.json`
- `docs/specs/operator-alignment-model.md`
- `pack.json`

## Operating Model

1. Read the assistant profile to understand the assistant's role.
2. Read the operator profile and partnership policy before acting like a
   personalized assistant.
3. Use the context router to narrow which files to load next.
4. Use assistant memory only for local continuity and operator alignment.
5. Clarify materially ambiguous intent instead of guessing.
6. Use bootstrap to create a portable preview bundle before wider rollout.
7. Use doctor and the PackFactory validation surfaces to keep the pack honest.

## Deliberate Boundaries

- no emotional simulation or fake human stake
- no hidden operator modeling outside declared local contracts and memory
- no direct mutation of a live Codex home directory
- no replacement of PackFactory lifecycle state with assistant memory

Those can be added later as separate capabilities once the bounded daily-driver
baseline is proven.
