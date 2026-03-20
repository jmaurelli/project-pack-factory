# Project Context

This template exists to optimize agent restarts.

## Priority

1. Recover goals, environment, and history from local memory artifacts.
2. Preserve deterministic traversal through machine-readable PackFactory state.
3. Keep the implementation small enough that agents can inspect the whole pack quickly.

## Primary Runtime Surfaces

- `src/agent_memory_first/agent_memory.py`
- `src/agent_memory_first/agent_memory_benchmark.py`
- `src/agent_memory_first/validate_project_pack.py`
- `contracts/agent-memory.schema.json`
- `contracts/agent-memory-reader.schema.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

## Local State

- local memory notes: `.pack-state/agent-memory/`
- archived revisions: `.pack-state/agent-memory/revisions/`
