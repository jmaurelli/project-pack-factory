# JSON Health Checker Template Pack

This is a PackFactory-native template created through the template creation workflow.

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

- Treat this pack as an active source template.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this template.
- Keep this template easy for a fresh agent to inspect and adapt.
- Treat this template as source-only. It is not directly deployable.
