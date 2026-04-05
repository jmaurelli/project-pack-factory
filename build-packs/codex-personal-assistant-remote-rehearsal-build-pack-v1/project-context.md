# Project Context

This template was created to support the following project goal:

- Build a Codex-native personal assistant environment that can act as a daily-driver workspace with explicit identity, context routing, restart memory, reusable skills, install/update commands, and PackFactory-managed lifecycle evidence.

## Priority

1. Keep the template valid for PackFactory traversal and later materialization.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack easy for a fresh agent to inspect.

## Primary Runtime Surfaces

- `src/codex_personal_assistant_template_pack/cli.py`
- `src/codex_personal_assistant_template_pack/validate_project_pack.py`
- `src/codex_personal_assistant_template_pack/benchmark_smoke.py`
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
