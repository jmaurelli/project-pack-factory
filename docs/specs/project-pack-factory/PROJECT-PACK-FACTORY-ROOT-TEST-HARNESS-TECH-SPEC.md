# Project Pack Factory Root Test Harness Tech Spec

## Purpose

Define the minimal repo-level test harness contract for Project Pack Factory so
the factory's canonical root test command exercises only the maintained factory
workflow suite, installs the few dependencies that suite actually needs, and
stops depending on retired fixture packs as active test inputs.

## Spec Link Tags

```json
{
  "spec_id": "root-test-harness",
  "depends_on": [
    "directory-hierarchy",
    "build-pack-materialization",
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration"
  ],
  "integrates_with": [
    "testing-policy"
  ],
  "adjacent_work": [
    "root pytest collection boundary",
    "minimal root dev dependencies",
    "fixture drift cleanup"
  ]
}
```

## Problem

The repo currently has no root pytest configuration and no canonical root test
environment definition.

That leaves `pytest` at the factory root to do three things the factory does
not actually want:

- recurse into nested historical pack-local test trees
- inherit dependency expectations from retired fixture packs
- treat retired template packs as still-valid test fixtures for root workflow
  tests

As a result, the repo-level test command gives misleading failures before it
reaches the maintained PackFactory workflow tests.

## Evidence

Evidence was collected on 2026-03-21 from the repo root at:

- `/home/orchadmin/project-pack-factory`

### Evidence A: Unbounded Root Collection

Command:

```bash
uvx --from pytest pytest -q
```

Observed result:

- pytest stopped during collection with `42` errors
- `34` were `ModuleNotFoundError: No module named 'click'`
- `8` were `import file mismatch` collisions caused by duplicate test module
  basenames across mirrored `build-packs/.../tests` and `templates/.../tests`

Representative failing paths:

- `build-packs/agent-memory-first-build-pack/tests/test_agent_memory_cli.py`
- `build-packs/ai-native-codex-build-pack/tests/test_project_bootstrap.py`
- `templates/ai-native-codex-package-template/tests/test_task_goal.py`
- `templates/agent-memory-first-template-pack/tests/test_agent_memory.py`

Interpretation:

- the repo-level failure is primarily a root collection-boundary problem
- the collection target is much larger than the maintained factory workflow
  suite

### Evidence B: Root Suite Needs One Shared Dependency

Command:

```bash
uvx --from pytest pytest -q tests
```

Observed result:

- pytest collected the root suite
- the run failed with `15 failed, 1 passed`
- the dominant error was repeated preflight failure:
  - `jsonschema is required for schema validation`

Representative failing files:

- `tests/test_create_template_pack.py`
- `tests/test_promote_build_pack.py`
- `tests/test_run_deployment_pipeline.py`

Interpretation:

- after the collection boundary is corrected, the maintained root suite still
  needs a minimal shared dependency declaration for `jsonschema`

### Evidence C: One Root Workflow Test Is Drifted To Retired State

Command:

```bash
uvx --with jsonschema --from pytest pytest -q tests/test_materialize_build_pack.py
```

Observed result:

- `4` tests failed
- each failure stopped on:
  - `ValueError: source template is not active`

Cause:

- `tests/test_materialize_build_pack.py` still requests
  `agent-memory-first-template-pack`
- current live registry state lists the active templates as:
  - `factory-native-smoke-template-pack`
  - `json-health-checker-template-pack`

Interpretation:

- the root materialization test is coupled to a retired historical template
  instead of an active factory source template

### Evidence D: Create Workflow Is Healthy Once The Harness Is Correct

Command:

```bash
uvx --with jsonschema --from pytest pytest -q tests/test_create_template_pack.py
```

Observed result:

- `4 passed`

Interpretation:

- the create workflow tests do not need broader remediation
- the remaining repo-level work should stay tightly scoped

## Design Goals

- keep the repo-level test harness aligned with the factory testing policy
- make the canonical root test command deterministic and small
- avoid reviving retired fixture-pack test trees as part of the factory root
  suite
- declare only the minimum shared root dependencies required by maintained
  workflow tests
- update the one stale root fixture to current active factory state
- avoid broad new tests or dependency growth

## Scope

This spec defines:

- the canonical root pytest collection boundary
- the minimal root test dependency contract
- the fixture-selection rule for maintained root workflow tests
- the required remediation for the stale materialization test fixture

This spec does not define:

- remediation of pack-local test suites inside retired templates or build packs
- installation of `click` for historical fixture-pack tests
- renaming duplicate test files across historical fixture trees
- broad new repo-wide test matrices

## Root Test Harness Boundary

Project Pack Factory has two different test layers:

- root factory workflow tests under `tests/`
- pack-local tests owned by individual template or build-pack directories

For the repo root, the canonical suite is only the maintained factory workflow
layer.

### Canonical Root Collection Rule

The root pytest configuration must restrict default collection to:

- `tests/`

The root harness must not collect by default from:

- `templates/**/tests`
- `build-packs/**/tests`

Those pack-local suites remain traversable and runnable when explicitly
targeted from within their own pack context, but they are not part of the
factory root suite.

### Rationale

This matches the repo's testing policy:

- small
- high-signal
- workflow-focused

It also prevents retired fixture packs from breaking the factory root suite
through unrelated dependency or module-name assumptions.

## Root Dependency Contract

The repo root must declare the minimal shared dependencies needed by the
maintained root workflow tests.

For v1 that shared root test environment must include:

- `pytest`
- `jsonschema`

The root harness must not add `click` just to satisfy retired nested fixture
tests that are no longer part of the canonical root suite.

### Canonical Root Command

The canonical root suite command becomes:

```bash
uv run pytest -q
```

This command must succeed from the repo root without requiring operators to
manually add `--with jsonschema`.

## Root Fixture Selection Rule

Maintained root workflow tests must use active factory state unless a test is
explicitly proving retirement behavior.

That means root tests must not rely on:

- retired template packs as the default source template for happy-path
  materialization
- retired build packs as assumed valid live candidates

Using retired fixtures is still allowed when a test is explicitly about:

- retirement handling
- historical traversal
- isolation from unrelated invalid fixture state

But those tests must make that purpose explicit.

## Required Remediation

### 1. Add A Root Pytest Collection Boundary

Add root pytest configuration that makes `tests/` the default collection target
for repo-level runs.

The compliant minimal implementation is:

- a root `pytest.ini`
- `testpaths = tests`

No extra discovery customization is required in v1 unless needed for the root
suite itself.

### 2. Add A Minimal Root Test Environment Definition

Add a root project configuration that supports the canonical command:

- `uv run pytest -q`

The compliant minimal implementation is:

- a root `pyproject.toml`
- `pytest` and `jsonschema` declared for the root dev environment
- root project packaging disabled if no root package is needed

This root `pyproject.toml` is required for compliance. This configuration
exists for the root harness only. It does not replace pack-local
`pyproject.toml` files.

### 3. Repoint The Materialization Workflow Test To An Active Template

Update `tests/test_materialize_build_pack.py` to use an active template pack as
its happy-path source template.

Preferred source template:

- `factory-native-smoke-template-pack`

This keeps the fixture minimal and aligned with the current active baseline.

The test must also stop asserting benchmark-specific gate ids from a retired
template line when the underlying workflow contract only requires:

- validation gate `not_run`
- benchmark entries seeded as `not_run`
- required gate state synthesized from the active source template

The remediation must also remove other retired-line assumptions in that file,
including:

- agent-memory-specific `.pack-state/agent-memory` fixture seeding
- direct expectation of the retired `agent_memory_restart_small_001` gate id

The replacement assertions should stay generic to the active template contract:

- local state contents under `.pack-state/` are not copied through
  materialization
- `validate_build_pack_contract` is seeded as `not_run`
- at least one non-validation benchmark-backed gate is seeded as `not_run`
- `eval/latest/index.json` records `not_run` benchmark entries for the active
  source template

## Non-Goals

- adding root support for `click`
- making `uvx --from pytest pytest -q` the canonical command
- repairing every historical nested test suite in this repo
- increasing the workflow test count beyond the existing maintained suite

## Implementation Notes

- keep the change localized to root harness files and the stale materialization
  test
- do not edit historical nested test trees as part of this remediation
- do not add new workflow tests unless a current test must be replaced to
  preserve the same behavioral coverage

## Acceptance Criteria

The remediation is complete when all of the following are true:

1. `uv run pytest --collect-only -q` at the repo root collects only `tests/`.
2. `uv run pytest -q` succeeds from the repo root.
3. Root workflow tests do not depend on retired template packs for happy-path
   materialization.
4. No pack-local historical test tree is modified just to make the root suite
   pass.
5. `uv run pytest -q tests/test_materialize_build_pack.py` passes against
   active fixture state.
6. The workflow test count remains within the testing-policy budget.

## Verification

Required verification:

```bash
uvx --from pytest pytest --collect-only -q
uv run pytest --collect-only -q
uv run pytest -q
uv run pytest -q tests/test_materialize_build_pack.py
```

Expected outcomes after implementation:

- the first command must collect only root `tests/`; if it still fails, the
  remaining failure must be dependency-related rather than nested-pack
  collection
- the second command must collect only root `tests/`
- the canonical command must pass
- the materialization test file must pass against active fixture state
