# Agent Memory First Template Pack

This template pack is PackFactory-native and optimized for agent restart state.

## Bootstrap Order

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `benchmarks/active-set.json`
7. `eval/latest/index.json`

## Working Rules

- Treat `record-agent-memory`, `read-agent-memory`, and `benchmark-agent-memory` as the primary runtime surface.
- Treat `validate-project-pack` as the fail-closed structural check before trusting local state.
- Prefer `contracts/agent-memory.schema.json` and `contracts/agent-memory-reader.schema.json` when reasoning about memory shape.
- Use `.pack-state/agent-memory` as the local restart-state store.
- Treat this template as source-only. It is not directly deployable.
