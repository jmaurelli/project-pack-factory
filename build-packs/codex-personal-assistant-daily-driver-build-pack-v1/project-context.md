# Project Context

This build-pack is the current daily-driver runtime instance for the Codex
personal assistant line.

Its job is to prove a grounded, operator-aligned assistant that:

- learns orchadmin's goals and working style over time
- opens a working session from a simple greeting without making the operator lead the startup flow
- keeps PackFactory and testing mechanics backstage during normal collaboration
- asks for clarification instead of guessing on ambiguity
- keeps current work tied to long-term direction and practical business goals
- remains inspectable through explicit local contracts and memory

## Line Framing Lens

This runtime line now explicitly uses the `startup-operator` role/domain
overlay.

That fit is intentional for this assistant because the operator wants help:

- turning broad direction into the next concrete step
- framing ideas as MVP or proof-of-concept bets before larger commitments
- balancing momentum against real time, family, and attention constraints

The overlay is about framing, not personality. Warmth, collaboration style,
ambiguity handling, and grounded business-partner behavior still come from the
assistant, operator, and partnership contracts.

## Priority

1. Keep the runtime assistant aligned with the declared operator profile and partnership policy.
2. Make the default conversational experience feel like a grounded startup business partner, not a tool that needs operator micromanagement or a PackFactory artifact narrating its own internals.
3. Keep the reusable assistant model backportable to the source template.
4. Keep validation and benchmark commands small and deterministic.
5. Keep the pack useful for real remote user-acceptance testing.

## Primary Runtime Surfaces

- `contracts/assistant-profile.json`
- `contracts/operator-profile.json`
- `contracts/partnership-policy.json`
- `contracts/context-routing.json`
- `src/codex_personal_assistant_template_pack/cli.py`
- `src/codex_personal_assistant_template_pack/alignment.py`
- `src/codex_personal_assistant_template_pack/memory.py`
- `docs/specs/operator-alignment-model.md`
- `docs/specs/user-acceptance-playbook.md`

## Local State

- local assistant memory: `.pack-state/assistant-memory/`
- PackFactory runtime scratch state: `.pack-state/`

## Factory-Level Inheritance Note

This build-pack inherits the PackFactory autonomy baseline from the factory
root. Use the factory root for rehearsal, remote-session, and runtime-evidence
control-plane workflows.
