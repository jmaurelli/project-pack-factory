# Project Context

This build pack exists to provide a fresh factory-native baseline for small
workflow testing.

## Priority

1. Keep the build pack valid for PackFactory traversal, testing, and promotion.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the runtime behavior tiny enough that a fresh agent can inspect it quickly.

## Primary Runtime Surfaces

- `src/factory_smoke_pack/cli.py`
- `src/factory_smoke_pack/validate_project_pack.py`
- `src/factory_smoke_pack/benchmark_smoke.py`
- `benchmarks/active-set.json`
- `benchmarks/declarations/factory-smoke-small-001.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
