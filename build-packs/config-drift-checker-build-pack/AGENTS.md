# Config Drift Checker Build Pack

This is a PackFactory-native build-pack materialized from the Config Drift Checker template.

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

- Treat this pack as an active build-pack.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this build-pack.
- Keep this build-pack easy for a fresh agent to inspect and adapt.
- Prefer the standalone `check-drift` CLI and machine-readable JSON output.
