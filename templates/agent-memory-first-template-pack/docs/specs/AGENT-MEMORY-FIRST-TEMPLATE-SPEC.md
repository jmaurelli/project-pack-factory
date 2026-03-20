# Agent Memory First Template Spec

This pack deliberately narrows the template surface to agent memory and traversal.

## Canonical Runtime Surface

- `src/agent_memory_first/agent_memory.py`
- `src/agent_memory_first/agent_memory_benchmark.py`
- `src/agent_memory_first/validate_project_pack.py`
- `src/agent_memory_first/cli.py`

## Canonical State Surface

- `pack.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/deployment.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

## Local Restart State

- active and historical memory artifacts live under `.pack-state/agent-memory/`
