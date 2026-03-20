# Factory Native Smoke Template Pack

This is the fresh minimal template for PackFactory workflow testing.

## Bootstrap Order

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `status/retirement.json`
7. `status/deployment.json`
8. `benchmarks/active-set.json`
9. `eval/latest/index.json`

## Working Rules

- Treat this pack as the active small testing template for live factory workflow checks.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for pipeline smoke coverage.
- Keep this pack intentionally tiny and easy for a fresh agent to inspect.
- Treat this template as source-only. It is not directly deployable.
