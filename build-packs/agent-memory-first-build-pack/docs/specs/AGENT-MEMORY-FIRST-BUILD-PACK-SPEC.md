# Agent Memory First Build Pack Spec

This build pack preserves the template's memory-first runtime while adding build-pack state, lineage, and testing deployment surfaces.

## Canonical Runtime Surface

- `src/agent_memory_first/agent_memory.py`
- `src/agent_memory_first/agent_memory_benchmark.py`
- `src/agent_memory_first/validate_project_pack.py`
- `src/agent_memory_first/cli.py`

## Build-Pack State Surface

- `pack.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/deployment.json`
- `lineage/source-template.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`
