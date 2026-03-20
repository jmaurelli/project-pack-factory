# First Benchmark Task

## Goal

Use this package as the baseline benchmark pack for AI-assisted software building and template-pack optimization.

## First Small Task

Add one small benchmark-oriented command or output that helps an agent turn a short project brief into a deterministic build plan.

Recommended shape:
- accept a short task or brief
- normalize it into a small structured plan
- keep the CLI thin
- keep logic local to this package only

## Allowed Scope

- package-local Python modules under `src/ai_native_package/`
- package-local docs and prompts
- one focused scaffold or behavior test if needed

## Avoid

- cross-package changes
- broad framework adoption
- large test expansion
- unrelated cleanup

## Validation

Run from `<package-root>`.

Preferred when `uv` is available:

```bash
uv run python -m ai_native_package --help
uv run --extra dev pytest -q tests/test_ai_native_package_scaffold.py
uv run --extra dev ruff check .
uv run --extra dev mypy src
```

Portable fallback:

```bash
PYTHONPATH=src python3 -m ai_native_package --help
pytest -q tests/test_ai_native_package_scaffold.py
make validate
```

## Local Evidence

- if local agent memory exists, use `read-agent-memory` before scanning ad hoc notes or handoff files
- treat agent memory as restart state for environment, history, and goals rather than as human notes
- if a task-goal loop already wrote local telemetry, use `read-agent-telemetry` before manually scanning hidden pack directories
- if several attempts already exist, use `summarize-task-goal-telemetry` to understand the local pattern first
- use `build-run-manifest` when the benchmark task needs broader local run evidence

## Friction To Record

- missing package-local instructions
- agent handoff details that are easy to lose between sessions
- ambiguous commands or workflow steps
- rename or metadata drift
- validation commands that are easy to forget
- missing host tools such as `uv`, `ruff`, or `mypy`
- tool choices an agent has to infer instead of discover

## Environment Note

On the target host, user-installed Python CLI tools may live under `$HOME/.local/bin`. The package `Makefile` prepends that path automatically for validation commands.
