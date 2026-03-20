# Project Context

This build pack exists to deploy and validate the memory-first runtime in a build-pack shape.

## Priority

1. Preserve the template's restart-state behavior exactly.
2. Preserve deterministic traversal through machine-readable PackFactory state and lineage.
3. Keep the implementation small enough that agents can inspect the whole pack quickly.

## Primary Runtime Surfaces

- `src/agent_memory_first/agent_memory.py`
- `src/agent_memory_first/agent_memory_benchmark.py`
- `src/agent_memory_first/validate_project_pack.py`
- `contracts/agent-memory.schema.json`
- `contracts/agent-memory-reader.schema.json`
- `status/deployment.json`
- `lineage/source-template.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`
