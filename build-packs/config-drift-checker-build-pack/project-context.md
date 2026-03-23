# Project Context

This build-pack was materialized to support the following project goal:

- Provide a small deterministic tool for detecting configuration drift between
  a current JSON or YAML file and a declared baseline before promotion.

## Priority

1. Keep the standalone `check-drift` runtime deterministic and operator-usable.
2. Keep PackFactory validation and benchmark commands small and reliable.
3. Keep the pack easy to export, install, and inspect.

## Primary Runtime Surfaces

- `src/config_drift_checker_build_pack/drift_runtime.py`
- `src/config_drift_checker_build_pack/cli.py`
- `src/config_drift_checker_build_pack/validate_project_pack.py`
- `src/config_drift_checker_build_pack/benchmark_smoke.py`
- `contracts/config-drift-checker.contract.md`
- `benchmarks/active-set.json`
- `benchmarks/declarations/config-drift-checker-build-pack-smoke-small-001.json`
- `eval/latest/index.json`

## Pack-Local Fixtures

- `tests/fixtures/no-drift-sample.json`

## Local State

- local scratch state: `.pack-state/`
- standalone wheel exports: `dist/exports/`
