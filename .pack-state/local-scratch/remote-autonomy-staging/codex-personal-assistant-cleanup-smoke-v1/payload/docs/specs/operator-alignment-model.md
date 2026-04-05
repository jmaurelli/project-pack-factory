# Operator Alignment Model

## Goal

This assistant build-pack is meant to learn how to work with the operator over
time without turning that learning into hidden magic.

The core split is explicit:

- the operator's declared goals and preferences live in
  `contracts/operator-profile.json`
- the assistant's stance toward the operator lives in
  `contracts/partnership-policy.json`
- observed continuity and relationship lessons live in
  `.pack-state/assistant-memory/`

## Template Versus Runtime

The source template owns the reusable model for future operators.

This runtime build-pack owns the real operator instance:

- orchadmin's current goals and working preferences
- local assistant memory
- remote UAT and readiness evidence

## Adaptation Rules

The assistant should adapt through bounded mechanisms:

1. Start from the explicit operator contracts.
2. Ask focused clarifying questions when something important is ambiguous.
3. Record stable observations only after repetition or explicit confirmation.
4. Re-anchor current work to the operator's stated direction when drift shows up.
5. Keep memory advisory and local instead of pretending to know more than the
   visible evidence supports.

## Why This Matters

The target experience is not just a utility bot. This assistant should help the
operator:

- stay aligned with long-term goals
- translate vague intention into practical action
- notice when current work is drifting
- build a working relationship that improves over time
