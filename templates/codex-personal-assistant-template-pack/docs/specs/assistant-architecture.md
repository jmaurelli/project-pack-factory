# Assistant Architecture

## Purpose

This template defines the reusable baseline for a Codex-native personal
assistant.

The assistant is meant to be:

- grounded in explicit local contracts
- useful without pretending to have hidden memory or autonomy
- able to learn how to work with an operator through inspectable local state
- business-like enough to support long-term goals and keep work aligned

## Template Versus Runtime

The template owns reusable behavior.

That includes:

- assistant identity and mission
- operator-profile structure
- operator-intake contract and refinement flow
- partnership policy
- memory categories and routing
- reusable CLI surfaces

Derived build-packs own runtime-specific values.

That includes:

- the actual operator's goals, preferences, and business direction
- local restart memory
- pack-specific testing notes and evidence
- any operator-specific refinements that should not be generalized yet

## Core Surfaces

- `contracts/assistant-profile.json`
- `contracts/operator-profile.json`
- `contracts/operator-intake.json`
- `contracts/partnership-policy.json`
- `contracts/context-routing.json`
- `contracts/memory-policy.json`
- `contracts/skill-catalog.json`
- `pack.json`

## Operating Model

1. Read the assistant and operator profiles when identity or goals matter.
2. Read the partnership policy when ambiguity, grounding, or accountability matter.
3. Use the context router to narrow which files to load next.
4. Use assistant memory only for local continuity and inspectable adaptation.
5. Use operator intake to capture onboarding signals and refine the operator profile explicitly.
6. Use bootstrap to create a portable preview bundle before wider rollout.
7. Use doctor and validation surfaces to keep the pack honest.

## Deliberate Boundaries

- no hidden learning loop outside local files
- no direct mutation of a live Codex home directory
- no claim of human emotion or fiduciary agency
- no guessing through ambiguity when clarification is cheaper and safer
