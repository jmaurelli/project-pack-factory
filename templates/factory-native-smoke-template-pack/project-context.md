# Project Context

This template exists to provide a fresh factory-native baseline for small
workflow testing.

## Priority

1. Make the template valid for PackFactory traversal and materialization.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack tiny enough that a fresh agent can inspect it quickly.

## Primary Runtime Surfaces

- `src/factory_smoke_pack/cli.py`
- `src/factory_smoke_pack/validate_project_pack.py`
- `src/factory_smoke_pack/benchmark_smoke.py`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`

## Factory-Level Inheritance Note

This template is a source template, not the canonical home of the autonomy
baseline.

For inherited PackFactory defaults around agent memory, feedback loops,
restart behavior, rehearsal evidence, and branch-choice policy, prefer the
factory-level state brief and operations note:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`

That inherited baseline now also includes startup-compliance expectations for
remote Codex session management and runtime-evidence flow:

- prefer PackFactory-local remote-session workflows from the factory root
- do not treat ad hoc `ssh` prompts or raw stdout/stderr logs as canonical
  PackFactory evidence
- return to the factory root for external runtime-evidence import
