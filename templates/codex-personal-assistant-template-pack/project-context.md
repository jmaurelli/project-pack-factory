# Project Context

This template was created to support the following project goal:

- Build a Codex-native personal assistant environment that can learn an operator's goals and working style over time, stay grounded in practical progress, ask for clarification instead of guessing, and remain reusable as a PackFactory-managed template line for other operators.
- The reusable model should be able to show up from a simple greeting like a grounded startup-oriented business partner, while leaving operator-specific goals and constraints to runtime packs.
- The reusable model should keep PackFactory lifecycle and testing mechanics backstage during normal operator conversation unless they are materially relevant.

## Line Framing Lens

This assistant line now explicitly uses the `startup-operator` role/domain
overlay as its default framing lens.

That means the reusable model should:

- turn broad direction into the next practical step
- prefer MVP or proof-of-concept framing before larger commitments
- keep effort, leverage, and realistic upside visible when recommending work

The overlay is intentionally about framing, not tone. Warmth, collaboration
style, ambiguity handling, and operator-specific adaptation still belong to the
assistant, partnership, and operator contracts.

## Priority

1. Keep the reusable assistant model explicit and inspectable.
2. Keep the template valid for PackFactory traversal and later materialization.
3. Keep validation and benchmark commands small and deterministic.
4. Keep the pack easy for a fresh agent to inspect and adapt for a new operator.

## Primary Runtime Surfaces

- `src/codex_personal_assistant_template_pack/cli.py`
- `src/codex_personal_assistant_template_pack/alignment.py`
- `src/codex_personal_assistant_template_pack/assistant_contracts.py`
- `src/codex_personal_assistant_template_pack/validate_project_pack.py`
- `src/codex_personal_assistant_template_pack/benchmark_smoke.py`
- `contracts/operator-profile.json`
- `contracts/operator-intake.json`
- `contracts/partnership-policy.json`
- `benchmarks/active-set.json`
- `benchmarks/declarations/codex-personal-assistant-template-pack-smoke-small-001.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
- optional template lineage memory: `.pack-state/template-lineage-memory/latest-memory.json`

## Factory-Level Inheritance Note

This template is a source template, not the canonical home of the autonomy
baseline.

For inherited PackFactory defaults around agent memory, feedback loops,
restart behavior, rehearsal evidence, and branch-choice policy, prefer the
factory-level state brief and operations note:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`

When present, the template-local lineage memory at
`.pack-state/template-lineage-memory/latest-memory.json` is the shortest path
to template-family learning that has already been distilled from derived
build-packs.

That inherited baseline now also includes startup-compliance expectations for
remote Codex session management and runtime-evidence flow:

- prefer PackFactory-local remote-session workflows from the factory root
- do not treat ad hoc `ssh` prompts or raw stdout/stderr logs as canonical
  PackFactory evidence
- return to the factory root for external runtime-evidence import
