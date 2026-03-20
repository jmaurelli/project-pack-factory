# Agent Memory First Build Pack

This build pack is the deployable derivative of the memory-first template pack.

## Bootstrap Order

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `status/deployment.json`
7. `lineage/source-template.json`
8. `benchmarks/active-set.json`
9. `eval/latest/index.json`

## Working Rules

- Treat `record-agent-memory`, `read-agent-memory`, and `benchmark-agent-memory` as the primary runtime surface.
- Treat `validate-project-pack` as the fail-closed structural check before trusting local state.
- Use `status/deployment.json` plus `deployments/testing/agent-memory-first-build-pack.json` as the testing deployment projection surface.
- Treat this pack as the testing deployment candidate derived from the canonical memory-first template.
