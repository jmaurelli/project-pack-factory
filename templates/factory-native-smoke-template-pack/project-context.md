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
