# Project Context

This template was created to support the following project goal:

- Create a small PackFactory-native template for detecting configuration drift between a current JSON or YAML file and a declared baseline before promotion.

## Priority

1. Keep the template valid for PackFactory traversal and later materialization.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack easy for a fresh agent to inspect.

## Primary Runtime Surfaces

- `src/config_drift_checker_template_pack/cli.py`
- `src/config_drift_checker_template_pack/validate_project_pack.py`
- `src/config_drift_checker_template_pack/benchmark_smoke.py`
- `benchmarks/active-set.json`
- `benchmarks/declarations/config-drift-checker-template-pack-smoke-small-001.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
