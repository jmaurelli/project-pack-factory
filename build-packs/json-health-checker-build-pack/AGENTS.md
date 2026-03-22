# JSON Health Checker Build Pack

This is the PackFactory-native build pack materialized from
`json-health-checker-template-pack` and currently used as a small testing
candidate.

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

- Treat this pack as an active build pack, not a source template.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this build pack.
- Keep this build pack easy for a fresh agent to inspect, test, and promote.
- Treat lineage in `lineage/source-template.json` as source history, not as the
  current pack identity.
