# Project Pack Factory Directory Hierarchy Tech Spec

## Purpose

Define an agent-optimized factory layout for:

- authoring and testing reusable template packs
- deriving deployable build packs from those templates
- tracking whether a pack is still under test
- tracking whether a build pack is ready for production deployment

This spec optimizes for deterministic agent traversal, machine-readable state,
and fail-closed promotion decisions.

## Spec Link Tags

```json
{
  "spec_id": "directory-hierarchy",
  "prerequisite_for": [
    "template-pack-planning-and-creation",
    "build-pack-materialization",
    "build-pack-promotion",
    "ci-cloud-deployment-orchestration",
    "retire-workflow",
    "runtime-agent-memory"
  ],
  "adjacent_work": [
    "validator and tooling updates that make linked specs executable"
  ]
}
```

## Scope

This spec defines:

- the factory root hierarchy
- the required pack-local directory contract
- the required machine-readable files for identity, lifecycle, readiness,
  deployment, lineage, benchmark intent, and latest evaluation evidence
- the promotion contract from `template_pack` to `build_pack`
- the exact JSON Schemas for the machine-readable files

This spec does not define:

- CI implementation details
- cloud deployment tooling
- container image layout
- language-specific internal source structure beyond pack-level directories

## Design Goals

- every pack should expose the same startup anchors
- agents should not infer state from folder names alone
- template packs should be clearly non-deployable
- build packs should be the only deployable artifacts
- readiness and deployment should fail closed when state is incomplete
- environment-level lookup should be fast without creating split-brain authority

## Directory Model

The factory root should use this shape:

```text
project-pack-factory/
  templates/
    <template-pack-id>/
      AGENTS.md
      project-context.md
      pack.json
      status/
        lifecycle.json
        readiness.json
        retirement.json
        deployment.json
      docs/
        specs/
        runbooks/
      prompts/
      contracts/
      src/
      tests/
      benchmarks/
        declarations/
        baselines/
        active-set.json
      eval/
        latest/
          index.json
        history/
      dist/
        exports/
      .pack-state/

  build-packs/
    <build-pack-id>/
      AGENTS.md
      project-context.md
      pack.json
      lineage/
        source-template.json
      status/
        lifecycle.json
        readiness.json
        retirement.json
        deployment.json
      docs/
        specs/
        runbooks/
      prompts/
      contracts/
      src/
      tests/
      benchmarks/
        declarations/
        baselines/
        active-set.json
      eval/
        latest/
          index.json
        history/
      dist/
        candidates/
        releases/
      .pack-state/

  deployments/
    testing/
      <build-pack-id>.json
    staging/
      <build-pack-id>.json
    production/
      <build-pack-id>.json
```

## Pack Shape Rules

Stable files in every pack root:

## Runtime Agent Memory Link

Runtime agent memory is a linked subsystem, not a second control plane.

The runtime-memory spec extends this directory spec by defining:

- `.pack-state/agent-memory/` as the preferred PackFactory-native local storage
  root for runtime memory
- runtime-memory contracts and benchmarks that integrate through
  `benchmarks/active-set.json`, `status/readiness.json`, and
  `eval/latest/index.json`

This base spec does not make any additional runtime-memory file under `status/`
or `eval/latest/` authoritative unless a future coordinated revision says so.

- `AGENTS.md`
- `project-context.md`
- `pack.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/retirement.json`
- `status/deployment.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

Stable directories in every pack root:

- `docs/`
- `prompts/`
- `contracts/`
- `src/`
- `tests/`
- `benchmarks/`
- `eval/`
- `dist/`
- `.pack-state/`

Build packs add one required lineage directory:

- `lineage/`

Dist layout is intentionally kind-specific:

- template packs use `dist/exports/`
- build packs use `dist/candidates/` and `dist/releases/`

That gives agents one stable root contract while still making deployable
artifacts visually and structurally distinct from template sources.

## Agent Traversal Contract

### Fixed Bootstrap Order

An agent entering any pack root must always read these three files first:

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`

This bootstrap order is global. It is not inferred from `pack.json`.

### Post-Bootstrap Read Order

After reading `pack.json`, the agent should follow the `post_bootstrap_read_order`
declared in that manifest. The allowed read order is fail-closed and differs by
pack kind:

- template pack:
  - `status/lifecycle.json`
  - `status/readiness.json`
  - `status/retirement.json`
  - `status/deployment.json`
  - `benchmarks/active-set.json`
  - `eval/latest/index.json`
- build pack:
  - `status/lifecycle.json`
  - `status/readiness.json`
  - `status/retirement.json`
  - `status/deployment.json`
  - `lineage/source-template.json`
  - `benchmarks/active-set.json`
  - `eval/latest/index.json`

Agents should read `docs/specs/` only when implementation detail is required
after the state surface has been loaded.

## Source Of Truth Rules

`pack.json`
- sole identity authority for `pack_id` and `pack_kind`
- authoritative for directory contract and pack-local traversal contract

`status/lifecycle.json`
- authoritative for release maturity intent

`status/readiness.json`
- authoritative for deployment readiness state

`status/retirement.json`
- authoritative for terminal retirement state
- when `retirement_state = retired`, agents must treat the pack as historical
  rather than active

`status/deployment.json`
- authoritative for build-pack deployment state
- required in both pack kinds so traversal stays stable
- template packs must remain explicitly non-deployable in this file

`lineage/source-template.json`
- authoritative for the source template of a build pack

`deployments/<environment>/<build-pack-id>.json`
- derived environment index for fast reverse lookup
- never overrides `status/deployment.json`

The tracked state boundary must also stay explicit for fresh agents.

Tracked PackFactory control-plane state is the canonical source for factory
identity, readiness, deployment, lineage, benchmark, and historical-evidence
questions:

- `templates/`
- `build-packs/`
- `deployments/`
- `registry/`
- pack-local `eval/` artifacts that are referenced by canonical state surfaces

`.pack-state/` remains local mutable runtime state. Agents may read it for
restart help, including `.pack-state/agent-memory/`, but must not treat it as
authoritative for readiness, promotion, deployment, lineage, or benchmark
conclusions unless the relevant fact is promoted into the tracked surfaces
above.

Ad hoc operator inputs, such as `requests/`, plus caches and interpreter
byproducts, are local scratch rather than canonical factory truth.

Directory placement alone must never be treated as truth.

## Cross-File Invariants

JSON Schema cannot fully enforce cross-file equality, so every factory must run
a cross-file validator with these minimum invariants:

- every machine-readable file inside a pack must match `pack.json.pack_id`
- every machine-readable file inside a pack must match `pack.json.pack_kind`
- every machine-readable file inside a pack must match
  `status/retirement.json.pack_id` and `status/retirement.json.pack_kind`
- `lineage/source-template.json.build_pack_id` must equal `pack.json.pack_id`
- when `status/deployment.json.projection_state = projected`, the matching
  environment pointer must exist and must match the active environment, release
  id, release path, and deployment transaction id
- when `status/deployment.json.projection_state = drifted`, agents must fail
  closed on environment-level deployment conclusions until repaired

## Testing And Production Tracking

A pack is **under testing** when it is not retired and either of these are true:

- `status/lifecycle.json.lifecycle_stage` is `draft`, `testing`, or
  `release_candidate`
- `status/readiness.json.ready_for_deployment` is `false`

A pack is **retired** when both of these are true:

- `status/lifecycle.json.lifecycle_stage` is `retired`
- `status/retirement.json.retirement_state` is `retired`

Retired packs are never classified as under testing, ready for deployment, or
currently deployed.

Only build packs can be **ready for production deployment**.

A build pack is **ready for production deployment** only when all of these are
true:

- `status/lifecycle.json.lifecycle_stage` is `release_candidate` or `maintained`
- `status/readiness.json.ready_for_deployment` is `true`
- every mandatory readiness gate is `pass` or `waived`
- `status/deployment.json.deployment_state` is one of `not_deployed`,
  `testing`, `staging`, or `production`

A build pack is **currently deployed to production** only when all of these are
true:

- `status/deployment.json.deployment_state` is `production`
- `status/deployment.json.active_environment` is `production`
- `status/deployment.json.projection_state` is `projected`
- `deployments/production/<build-pack-id>.json` matches the active release id,
  active release path, and deployment transaction id

Template packs may be thoroughly tested, but they are never production
deployable in this model.

## Promotion Model

Promotion should use this transaction-safe path:

1. update the source template under `templates/`
2. derive or sync a target build pack under `build-packs/`
3. run tests and required benchmark gates
4. mark readiness in `status/readiness.json`
5. create or update a candidate release under `dist/candidates/`
6. promote the candidate to `dist/releases/`
7. write `status/deployment.json` with a new `deployment_transaction_id`
   and set `projection_state = pending`
8. materialize or update `deployments/<environment>/<build-pack-id>.json`
   from that deployment record
9. update `status/deployment.json` to `projection_state = projected`

The pack-local deployment file is the canonical deployment record. The
environment pointer is a derived projection used for environment-first lookup.

## Required Machine-Readable Files

### `pack.json`

Schema:
- [pack.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/pack.schema.json)

Purpose:
- identify the pack
- declare whether it is a `template_pack` or `build_pack`
- define the stable directory contract
- declare the allowed post-bootstrap read order

### `status/lifecycle.json`

Schema:
- [lifecycle.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/lifecycle.schema.json)

Purpose:
- capture release maturity and promotion intent

### `status/readiness.json`

Schema:
- [readiness.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/readiness.schema.json)

Purpose:
- capture readiness gates, blockers, and next actions

### `status/deployment.json`

Schema:
- [deployment.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/deployment.schema.json)

Purpose:
- capture the canonical deployment state of a build pack
- keep template packs explicitly non-deployable
- record deployment transaction and pointer projection state

### `lineage/source-template.json`

Schema:
- [source-template.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/source-template.schema.json)

Purpose:
- capture template lineage for build packs

### `benchmarks/active-set.json`

Schema:
- [benchmark-active-set.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/benchmark-active-set.schema.json)

Purpose:
- expose the active benchmark declarations an agent should care about first

### `eval/latest/index.json`

Schema:
- [eval-latest-index.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/eval-latest-index.schema.json)

Purpose:
- expose the current evaluation surface without requiring a directory scan

### `deployments/<environment>/<build-pack-id>.json`

Schema:
- [deployment-pointer.schema.json](/home/orchadmin/ai-orchestrator-lab/packages/ai-native-codex-package-template/docs/specs/project-pack-factory/schemas/deployment-pointer.schema.json)

Purpose:
- provide an environment-indexed projection of build-pack deployment state

## Example JSON

### Example `pack.json` For A Template Pack

```json
{
  "schema_version": "pack-manifest/v2",
  "pack_id": "ai-native-codex-package-template",
  "pack_kind": "template_pack",
  "display_name": "AI-Native Codex Package Template",
  "owning_team": "orchadmin",
  "runtime": "python",
  "bootstrap_read_order": [
    "AGENTS.md",
    "project-context.md",
    "pack.json"
  ],
  "post_bootstrap_read_order": [
    "status/lifecycle.json",
    "status/readiness.json",
    "benchmarks/active-set.json",
    "eval/latest/index.json"
  ],
  "entrypoints": {
    "cli_command": "uv run python -m ai_native_package --help",
    "validation_command": "uv run python -m ai_native_package validate-project-pack --project-root . --output json",
    "benchmark_command": "uv run python -m ai_native_package benchmark-agent-memory --output json"
  },
  "directory_contract": {
    "docs_dir": "docs",
    "prompts_dir": "prompts",
    "contracts_dir": "contracts",
    "source_dir": "src",
    "tests_dir": "tests",
    "benchmarks_dir": "benchmarks",
    "benchmark_active_set_file": "benchmarks/active-set.json",
    "eval_dir": "eval",
    "eval_latest_index_file": "eval/latest/index.json",
    "eval_history_dir": "eval/history",
    "status_dir": "status",
    "lifecycle_file": "status/lifecycle.json",
    "readiness_file": "status/readiness.json",
    "deployment_file": "status/deployment.json",
    "lineage_dir": null,
    "lineage_file": null,
    "dist_dir": "dist",
    "candidate_release_dir": null,
    "immutable_release_dir": null,
    "template_export_dir": "dist/exports",
    "local_state_dir": ".pack-state"
  },
  "identity_source": "pack.json",
  "notes": [
    "Template packs are canonical source templates and are never directly deployed."
  ]
}
```

### Example `status/readiness.json` For A Build Pack Under Testing

```json
{
  "schema_version": "pack-readiness/v2",
  "pack_id": "adf-build-benchmark-pack",
  "pack_kind": "build_pack",
  "readiness_state": "in_progress",
  "ready_for_deployment": false,
  "last_evaluated_at": "2026-03-18T00:00:00Z",
  "blocking_issues": [
    "Production smoke deployment has not been validated yet."
  ],
  "recommended_next_actions": [
    "Run the production smoke deployment.",
    "Attach the benchmark evidence to the missing deployment gate."
  ],
  "required_gates": [
    {
      "gate_id": "contract_validation",
      "mandatory": true,
      "status": "pass",
      "summary": "Pack contract validation passed.",
      "last_run_at": "2026-03-18T00:00:00Z",
      "evidence_paths": [
        "eval/history/contract-validation-20260318.json"
      ]
    },
    {
      "gate_id": "benchmark_suite",
      "mandatory": true,
      "status": "pass",
      "summary": "Required benchmark suite passed within envelope.",
      "last_run_at": "2026-03-18T00:00:00Z",
      "evidence_paths": [
        "eval/latest/index.json"
      ]
    },
    {
      "gate_id": "production_smoke_deploy",
      "mandatory": true,
      "status": "not_run",
      "summary": "Deployment smoke gate has not executed yet.",
      "last_run_at": null,
      "evidence_paths": []
    }
  ]
}
```

### Example `status/deployment.json` For A Production Build Pack

```json
{
  "schema_version": "pack-deployment/v2",
  "pack_id": "adf-build-benchmark-pack",
  "pack_kind": "build_pack",
  "deployment_state": "production",
  "active_environment": "production",
  "active_release_id": "2026-03-18.rc2",
  "active_release_path": "dist/releases/2026-03-18.rc2",
  "deployment_pointer_path": "deployments/production/adf-build-benchmark-pack.json",
  "deployment_transaction_id": "promote-20260318-010000z",
  "projection_state": "projected",
  "last_promoted_at": "2026-03-18T01:00:00Z",
  "last_verified_at": "2026-03-18T01:15:00Z",
  "last_rollback": {
    "rolled_back_from_release_id": "2026-03-18.rc1",
    "rolled_back_to_release_id": "2026-03-17.rc4",
    "rolled_back_at": "2026-03-17T21:00:00Z",
    "rollback_reason": "Regression in delegated smoke validation."
  },
  "deployment_notes": [
    "Production points to an immutable release directory."
  ]
}
```

### Example `lineage/source-template.json`

```json
{
  "schema_version": "pack-lineage/v2",
  "build_pack_id": "adf-build-benchmark-pack",
  "source_template_id": "ai-native-codex-package-template",
  "source_template_version": "0.1.0",
  "source_template_revision": "1fd19f7d5bb8c35491545b702d243bfd7d9aeae9",
  "derivation_mode": "synced",
  "sync_state": "current",
  "last_sync_at": "2026-03-18T00:30:00Z",
  "last_sync_summary": "Build pack is aligned with the current template baseline.",
  "inherited_entrypoints": [
    "cli_command",
    "validation_command",
    "benchmark_command"
  ],
  "inherited_contracts": [
    "project-pack",
    "doc-update-record",
    "task-record"
  ]
}
```

### Example `benchmarks/active-set.json`

```json
{
  "schema_version": "pack-benchmark-active-set/v1",
  "pack_id": "adf-build-benchmark-pack",
  "pack_kind": "build_pack",
  "default_benchmark_id": "agent-memory-restart-small-001",
  "active_benchmarks": [
    {
      "benchmark_id": "agent-memory-restart-small-001",
      "declaration_path": "benchmarks/declarations/agent-memory-restart-small-001.json",
      "objective": "Measure restart-state quality for agent handoff and recovery.",
      "required_for_readiness": true
    },
    {
      "benchmark_id": "schema-validator-small-001",
      "declaration_path": "benchmarks/declarations/schema-validator-small-001.json",
      "objective": "Validate baseline pack contract health.",
      "required_for_readiness": true
    }
  ]
}
```

### Example `eval/latest/index.json`

```json
{
  "schema_version": "pack-eval-index/v1",
  "pack_id": "adf-build-benchmark-pack",
  "pack_kind": "build_pack",
  "updated_at": "2026-03-18T00:45:00Z",
  "benchmark_results": [
    {
      "benchmark_id": "agent-memory-restart-small-001",
      "status": "pass",
      "latest_run_id": "local-template-pack-agent-memory-restart-20260317t232138z",
      "run_artifact_path": "eval/history/local-template-pack-agent-memory-restart-20260317t232138z/run.json",
      "summary_artifact_path": "eval/history/local-template-pack-agent-memory-restart-20260317t232138z/agent-memory-scorecard.json"
    }
  ]
}
```

### Example `deployments/production/<build-pack-id>.json`

```json
{
  "schema_version": "pack-deployment-pointer/v2",
  "environment": "production",
  "pack_id": "adf-build-benchmark-pack",
  "pack_kind": "build_pack",
  "pack_root": "build-packs/adf-build-benchmark-pack",
  "source_deployment_file": "build-packs/adf-build-benchmark-pack/status/deployment.json",
  "active_release_id": "2026-03-18.rc2",
  "active_release_path": "dist/releases/2026-03-18.rc2",
  "deployment_transaction_id": "promote-20260318-010000z",
  "promotion_evidence_ref": "eval/latest/index.json",
  "updated_at": "2026-03-18T01:00:05Z"
}
```

## Operational Rules

- keep mutable local run state under `.pack-state/`
- keep latest evaluation lookup in `eval/latest/index.json`
- keep immutable evidence in `eval/history/`
- keep active benchmark intent in `benchmarks/active-set.json`
- keep template exports under `dist/exports/`
- keep candidate releases under `dist/candidates/`
- keep immutable promoted releases under `dist/releases/`
- keep environment pointers as JSON projection files, not symlinks
- never infer deployability from directory names alone

## Default Agent Policy

If an agent needs to decide whether a build pack can be deployed, it should:

1. read `status/readiness.json`
2. fail closed if any mandatory gate is not `pass` or `waived`
3. fail closed if `blocking_issues` is not empty
4. read `status/deployment.json`
5. confirm the active release path exists when `deployment_state` is not
   `not_deployed`
6. treat `projection_state = pending` as a legal in-progress projection window
7. treat `projection_state = drifted` as a repair-required state
8. read the environment pointer only when an environment-level lookup is needed

If an agent needs to answer "what is live in production", it may read the
environment pointer first, but it should confirm the matching build pack's
`status/deployment.json` before taking action that depends on exact release
truth.

## Migration Guidance

When migrating an existing pack family into this hierarchy:

1. create `pack.json`
2. create `status/lifecycle.json`
3. create `status/readiness.json`
4. create `status/deployment.json`
5. create `benchmarks/active-set.json`
6. create `eval/latest/index.json`
7. create `lineage/source-template.json` for build packs
8. move transient agent state into `.pack-state/`
9. move historical evaluation artifacts into `eval/history/`

Migration is successful when an agent can determine identity, readiness,
lineage, benchmark intent, and deployment state without scanning arbitrary
directories or relying on prose outside the bootstrap files.
