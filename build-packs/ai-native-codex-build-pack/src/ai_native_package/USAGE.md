# ai_native_package usage

Use this package to generate deterministic delegated workflow payloads and to serve as a benchmark harness for AI-assisted software building.

## Local Development Setup

```bash
cd <package-root>
make setup-env
.venv/bin/python -m ai_native_package --help
make validate
```

## CLI Example

```bash
cd <package-root>
.venv/bin/python -m ai_native_package print-plan \
  --task "sample-target" \
  --backend delegated_worker \
  --output-dir /srv/adf/artifacts/<package-name>
```

## Python Example

```python
from ai_native_package.workflow import build_workflow_payload

payload = build_workflow_payload(
    task_name="sample-target",
    backend="delegated_worker",
    output_dir="/srv/adf/artifacts/<package-name>",
    contract="/ai-workflow/adf/runtime-contract.json",
    operation_class="delegated_execution",
    cycle_root="/ai-workflow/adf/artifacts/orchestration",
    mode="run",
)

print(payload["task_name"])
```

## Build Plan Artifacts

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package plan-build-brief \
  --brief "Build a small Python CLI that prints a JSON plan." \
  --artifacts-dir /tmp/ai-native-codex-package-template-demo
```

## Project Root Resolution

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package plan-build-brief \
  --brief "Build a small Python CLI that prints a JSON plan." \
  --project-root /srv/projects/example-app
```

If `--project-root` is omitted, the plan records `project_root.selection_mode = agent_deferred` and leaves artifact writing deferred unless `--artifacts-dir` is provided explicitly.

## Goal-Driven Loop

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package validate-task-goal \
  --task-record src/ai_native_package/templates/task-record.yaml

PYTHONPATH=src .venv/bin/python -m ai_native_package run-task-goal-loop \
  --task-record src/ai_native_package/templates/task-record.yaml \
  --output json
```

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package run-task-goal-loop \
  --task-record src/ai_native_package/templates/task-record.yaml \
  --build-run-manifest-path /srv/project/.ai-native-codex-package-template/run-manifests/example-run.json \
  --output json
```

When telemetry is requested with `--telemetry-output-path`, `--run-id`, or `--build-run-manifest-path`, the loop persists a pack-scoped telemetry artifact by default at `<project-root>/.ai-native-codex-package-template/task-goal-telemetry/<task_name>.json`. Relative telemetry output paths resolve from the absolute task `operating_root`. If the root is ambiguous, telemetry writing fails closed and the command exits nonzero without creating canonical eval writes.

## Agent Memory

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package record-agent-memory \
  --project-root "$PWD" \
  --memory-id blocker-001 \
  --memory-type blocker \
  --summary "Predispatch fails when approval_state is missing." \
  --next-action "Inspect predispatch approval handling." \
  --file-path src/ai_native_package/orchestration/predispatch.py

PYTHONPATH=src .venv/bin/python -m ai_native_package read-agent-memory \
  --project-root "$PWD" \
  --output json
```

The memory system persists local-only JSON artifacts under `<project-root>/.ai-native-codex-package-template/agent-memory/`. The reader snapshot prioritizes active blockers, next-step summaries, action items, decisions, and focus files so another agent can resume work quickly without scanning ad hoc notes.
Treat the memory artifact as restart state for environment, history, and goals. Use explicit CLI inputs for `--task-record-path`, `--delegation-brief-path`, `--task-goal-telemetry-path`, `--build-run-manifest-path`, `--supersedes-memory-id`, and `--conflicts-with-memory-id` when you want the next agent to recover lineage and working context without re-inferring it from prose.
Duplicate `memory_id` writes fail closed unless `--replace-existing` is explicit, in which case the old artifact is archived first.

To benchmark the restart surface itself, run the deterministic local memory benchmark:

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package benchmark-agent-memory \
  --output-path artifacts/agent-memory-scorecard.json \
  --snapshot-output-path artifacts/agent-memory-snapshot.json
```

The scorecard reports whether restart-state retrieval preserved goals, environment context, history context, omitted active memory visibility, and next actions for the next agent.

## Task-Goal Telemetry Summary

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package summarize-task-goal-telemetry \
  --telemetry-path /srv/project/.ai-native-codex-package-template/task-goal-telemetry/task-a.json \
  --telemetry-path /srv/project/.ai-native-codex-package-template/task-goal-telemetry/task-b.json \
  --output json
```

The summary command consumes explicit telemetry paths in v1, validates every source artifact against the task-goal telemetry schema, and writes one local-only summary artifact at `<project-root>/.ai-native-codex-package-template/task-goal-telemetry/task-goal-telemetry-summary.json` unless `--output-path` is provided. It fails closed on malformed telemetry and does not write canonical eval artifacts or compare reports.

## Agent Telemetry Reader

```bash
cd <package-root>
make setup-env
PYTHONPATH=src .venv/bin/python -m ai_native_package read-agent-telemetry \
  --project-root "$PWD" \
  --output json
```

The reader stays local-only. It loads the pack-scoped summary when present, selects the latest validated task-goal telemetry artifact, and returns one deterministic JSON payload for agent consumption without writing or mutating canonical eval artifacts.
