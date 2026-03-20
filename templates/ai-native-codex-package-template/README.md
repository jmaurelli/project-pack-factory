# ai-native-codex-package-template

Reusable local source template for AI-native packages with a Codex-native delegated backend.

This template now includes benchmark-friendly ergonomics such as deterministic build-plan artifacts, local build-run manifests, docs-with-code validation, and project-pack contract checks. Those capabilities are intended to be copied into remote build packs and then renamed for the target package.

## Read First

- `AGENTS.md`
- `docs/benchmark-first-task.md`
- `project-context.md` when present

## Local Usage

```bash
cd <package-root>
make setup-env
.venv/bin/python -m ai_native_package --help
make validate
```

## Validation Surface

Preferred deterministic path:

```bash
cd <package-root>
make setup-env
.venv/bin/python -m ai_native_package --help
.venv/bin/pytest -q tests/test_ai_native_package_scaffold.py tests/test_task_goal.py
.venv/bin/ruff check .
.venv/bin/mypy src
```

`make setup-env` uses `uv sync --extra dev` when `uv` is installed, otherwise it creates `.venv` with `python3 -m venv` and installs the package plus dev tools there.

Host-Python fallback is for recovery only, not the preferred benchmark path:

```bash
cd <package-root>
PYTHONPATH=src python3 -m ai_native_package --help
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
make validate
```

## Package Role

Use this package to:
- create small benchmarkable Python build tasks
- measure agent friction during project setup and implementation
- improve the underlying template-pack workflow for future projects

## Copy And Rename

Use `src/ai_native_package/TEMPLATE-RENAMES.md` as the rename checklist after copying this package root.

## Host Tooling Note

If `uv`, `ruff`, or `mypy` were installed with `python3 -m pip --user`, ensure `$HOME/.local/bin` is on `PATH` for direct shell use. `make validate` already prepends that location automatically.
Generated projects should still rely on their package-local `.venv` instead of ambient host tools whenever possible.

## Benchmark Artifacts

`plan-build-brief` can now persist deterministic benchmark artifacts including `build-plan.json` and `build-plan.md`. `build-run-manifest` can persist a machine-readable benchmark run manifest with selected profile, commands, validations, metrics, and outcome. Project root is a runtime input: user-provided when known, or explicitly deferred for later agent selection.

An optional helper command can also render a plain-language `project-summary.md` from a short brief:

```bash
PYTHONPATH=src python3 -m ai_native_package render-brief-summary \
  --brief "Build a small Python CLI that writes a markdown project summary." \
  --output-path artifacts/project-summary.md
```

The template can also render a real markdown checklist from a YAML task file:

```bash
cat > artifacts/tasks.yaml <<'EOF'
title: Release Checklist
tasks:
  - title: Confirm tests pass
    done: true
  - Publish release notes
EOF

PYTHONPATH=src python3 -m ai_native_package render-task-checklist \
  --task-file artifacts/tasks.yaml \
  --output-path artifacts/release-checklist.md \
  --title "Release Checklist"
```

For task-driven implementation loops, use the task record as the goal contract and validate it with:

```bash
PYTHONPATH=src python3 -m ai_native_package validate-task-goal \
  --task-record src/ai_native_package/templates/task-record.yaml
```

When a project already has local task-goal telemetry or a local build-run manifest,
use the reader instead of manually scanning hidden directories:

```bash
PYTHONPATH=src python3 -m ai_native_package read-agent-telemetry \
  --project-root "$PWD" \
  --output json
```

For cross-session memory that another agent should inherit, write one local-only memory artifact and read it back through the prioritized memory snapshot:

```bash
PYTHONPATH=src python3 -m ai_native_package record-agent-memory \
  --project-root "$PWD" \
  --memory-id approval-blocker-001 \
  --memory-type blocker \
  --summary "Predispatch fails when approval_state is missing." \
  --task-record-path "$PWD/task-record.yaml" \
  --delegation-brief-path "$PWD/delegation-brief.md" \
  --build-run-manifest-path "$PWD/.ai-native-codex-package-template/run-manifests/run-001.json" \
  --task-goal-telemetry-path "$PWD/.ai-native-codex-package-template/task-goal-telemetry/task-a.json" \
  --supersedes-memory-id approval-blocker-000 \
  --next-action "Inspect predispatch approval handling." \
  --file-path src/ai_native_package/orchestration/predispatch.py

PYTHONPATH=src python3 -m ai_native_package read-agent-memory \
  --project-root "$PWD" \
  --output json
```

The memory snapshot is local-only and agent-oriented. It is restart state for environment, history, and goals. Use it to carry forward the task record, delegation brief, telemetry, run-manifest, and lineage inputs another agent needs to resume quickly without treating scratch memory as canonical benchmark evidence. Duplicate `memory_id` writes fail closed unless `--replace-existing` is explicit.

For deterministic measurement of the restart surface itself, run the benchmark command and keep the emitted scorecard plus reader snapshot as the eval artifacts:

```bash
PYTHONPATH=src python3 -m ai_native_package benchmark-agent-memory \
  --output-path artifacts/agent-memory-scorecard.json \
  --snapshot-output-path artifacts/agent-memory-snapshot.json
```

The benchmark scores whether the restart snapshot keeps active goals, environment anchors, history, omitted active memory visibility, and next actions available to the next agent.

## Deployment Root

For repeated deployment, the real project root is a runtime decision. Pass `--project-root` when the user provides it, or omit it when the agent should defer that choice until runtime.

## Project-Pack Contract

The package ships a machine-readable project-pack contract and `validate-project-pack` command so determinism, required docs, testing policy, and framework constraints stay explicit.

## Docs With Code

The package requires a machine-readable `docs/doc-update-record.json` artifact so code changes explicitly record whether documentation changed with them. Use `build-doc-update-record`, `validate-doc-update-record`, and `validate-doc-updates` when a changed-files manifest exists.

## Docs Workflow

Generate the canonical docs-with-code artifact with `build-doc-update-record`, validate it with `validate-doc-update-record`, and use `validate-doc-updates` only when you also have a changed-files artifact to compare against the record. Agent docs are mandatory from project start. Human-facing docs such as `README.md` and `project-context.md` are optional until the task asks for them or the team wants to generate them from the agent docs.

## Key Terms

- Artifact: a saved output file produced by the package or a validation run.
- Contract: a machine-readable rule file that defines required structure or behavior.
- Validator: a command that checks whether files or records follow the package rules.
- Schema: the JSON structure a machine-readable file must follow.

## Why This Matters

The pack is structured for agents, but the wording should stay in plain language so a human can understand what the package is doing without learning internal shorthand first. Human-facing docs are intentionally optional at project start so the agent can focus on building software and maintaining accurate agent docs first.

## Framework Profiles

Framework-specific documentation profiles live under `docs/framework-profiles/`. The current approved baseline is `python-cli-click`. Reference-only profiles can document common frameworks without approving them for this pack.
