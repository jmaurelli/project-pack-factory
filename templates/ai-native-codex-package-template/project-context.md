# Project Context

## Mission

`ai-native-codex-package-template` is a benchmark-oriented Python package scaffold for testing how effectively an AI agent can build and refine software projects from a reusable template pack.

## Current Intent

- keep the package small and deterministic
- optimize for AI-agent readability and execution
- capture friction in package creation, validation, and build workflows
- improve the template pack based on measured build experience

## Package Standards

- Python 3.12+
- `uv`-first local workflows
- thin CLI entrypoint
- small deterministic modules
- minimal, high-signal tests only
- test-first for new behavior when feasible
- task records are the lightweight goal contracts for small implementation loops
- the first validation command is the primary goal gate
- keep iterating if it fails
- stop only when the declared validation path passes
- local evidence should be read in this order when present: agent memory snapshot, latest task-goal telemetry, local telemetry summary, then local build-run manifest
- typed public interfaces where practical
- approved CLI framework baseline: click
- documentation impact should be recorded with code changes
- agent docs are mandatory from project start
- human-facing docs can be deferred until the task needs them

## Agent Tooling

- `record-agent-memory` writes one local-only restart-state artifact for goals, environment anchors, and lineage
- `read-agent-memory` returns a prioritized restart snapshot for the next agent before they scan local notes manually
- duplicate `memory_id` writes fail closed unless `--replace-existing` is explicit
- prefer structured goal, environment, and history inputs such as task-record, delegation-brief, telemetry, run-manifest, `--supersedes-memory-id`, and `--conflicts-with-memory-id`
- `validate-task-goal` checks that the task record is a usable goal contract
- `run-task-goal-loop` runs the primary goal gate and broader validation commands
- `summarize-task-goal-telemetry` summarizes repeated local attempts
- `read-agent-telemetry` is the default local evidence reader and should be used before manually scanning hidden pack directories
- `build-run-manifest` records broader local benchmark evidence for the current project root

## Default Artifact Root

- `/srv/adf/artifacts/<package-name>`

## Success Criteria For Small Benchmark Tasks

- one small feature can be built without broad architectural changes
- the goal gate can fail safely and tell the agent to keep iterating
- validation is reproducible from the package root
- another agent can understand the package quickly from local docs alone
- friction points are easy to record and compare across runs

## Environment Notes

- prefer `uv` when available
- on the target host, user-installed Python CLI tools may resolve from `$HOME/.local/bin`
- package validation should remain reproducible even when host PATH is incomplete

## Docs With Code

- docs-with-code updates are tracked in `docs/doc-update-record.json`
- validation should fail when public or CLI-facing code changes do not record corresponding agent documentation updates
- human-facing docs can be added later when the task or operator asks for them

## What This Means

Use plain language in human-facing docs. If the package uses terms like artifact, contract, validator, or schema, explain them in a way a new human collaborator can understand without prior package context. For agent memory specifically, describe it as restart state for environment, history, and goals rather than as human notes.

## Framework Profiles

- current approved profile: `python-cli-click`
- reference-only profiles can document future variants such as API packs
- framework profile docs should explain what is approved now versus what is only a reference
