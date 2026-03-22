# Project Context

This build pack exists to support the following project goal:

- Provide a tiny PackFactory-native build pack for validating a JSON file
  against a required field set and reporting pass or fail clearly.

## Priority

1. Keep the build pack valid for PackFactory traversal, testing, and promotion.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the runtime behavior focused on one small JSON health-check task.
4. Keep the pack easy for a fresh agent to inspect.

## Primary Runtime Surfaces

- `src/json_health_checker_template_pack/cli.py`
- `src/json_health_checker_template_pack/json_health_checker.py`
- `src/json_health_checker_template_pack/validate_project_pack.py`
- `src/json_health_checker_template_pack/benchmark_smoke.py`
- `benchmarks/active-set.json`
- `benchmarks/declarations/json-health-checker-build-pack-smoke-small-001.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
