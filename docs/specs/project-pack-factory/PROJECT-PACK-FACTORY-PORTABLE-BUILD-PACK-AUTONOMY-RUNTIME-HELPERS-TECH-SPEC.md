# Project Pack Factory Portable Build-Pack Autonomy Runtime Helpers Tech Spec

## Purpose

Define the minimal PackFactory-native portability layer that lets a materialized
build-pack carry the bounded helper surfaces it needs for autonomous execution
outside the factory repo.

This spec closes the current portability gap where a build-pack can carry a
machine-readable backlog, but some seeded task commands still assume a nearby
factory checkout.

## Spec Link Tags

```json
{
  "spec_id": "portable-build-pack-autonomy-runtime-helpers",
  "part_of": [
    "remote-autonomy-spec-family-overview"
  ],
  "amends": [
    "build-pack-materialization",
    "autonomy-starter-task-canonical-evidence-alignment",
    "external-build-pack-runtime-evidence-export"
  ],
  "depends_on": [
    "autonomous-build-pack-handoff-and-work-state"
  ],
  "integrates_with": [
    "factory-validation",
    "remote-autonomy-target-workspace-and-staging",
    "remote-autonomous-build-pack-execution"
  ],
  "followed_by": [
    "remote-autonomous-build-pack-execution",
    "remote-autonomy-end-to-end-roundtrip"
  ]
}
```

## Relationship To Remote Autonomy Spec Family

This is the second spec in the remote-autonomy family.

It sits between remote staging and remote execution:

- staging decides where the build-pack goes
- this spec decides what portable helper surfaces the build-pack must carry
- remote execution then relies on those helpers

This spec flows directly from the family overview and from the staging spec:

- the family overview defines this as the portability amendment in the setup
  layer
- the staging spec defines how a selected build-pack is copied as materialized
- this spec defines what helper contents that materialized build-pack must
  already contain before staging preserves and copies it

Success here proves only that the build-pack carries the bounded helper
surfaces needed to remain executable outside the factory checkout.

It does not by itself prove:

- remote workspace preparation
- remote host interpreter or dependency availability
- remote agent execution correctness
- remote runtime evidence pull/import correctness

Read it after:

- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md)

Read it before:

- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md)

Its relationship to the broader project is:

- it preserves the PackFactory control-plane boundary
- it makes autonomy starter-task execution portable outside the local factory
  checkout

## Problem

Project Pack Factory now seeds starter tasks that correctly use bounded
evidence-writing workflows.

But those starter tasks currently depend on helper tools that live under the
factory repo.

That means a copied build-pack can carry:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

while still failing to execute its own declared task commands outside the
factory.

For a true external autonomous run, the build-pack must remain executable when:

- copied to a remote host
- unpacked in an isolated directory
- run without local access to the original factory root

## Current Repo Evidence

### Evidence A: Starter Task Commands Still Depend On Factory-Relative Tool Paths

Current seeded starter task shape:

- `python3 ../../tools/run_build_pack_readiness_eval.py --pack-root . ...`

Interpretation:

- the bounded workflow is correct
- the location contract is not portable outside the factory

### Evidence B: Export Portability Already Exists For Runtime Evidence

Current exporter surface:

- `src/pack_export_runtime_evidence.py`
- `pack.json.entrypoints.export_runtime_evidence_command`

Interpretation:

- the repo has already accepted the pattern of pack-local helper seeding for
  external execution
- the same approach should be applied to bounded autonomy runtime helpers

### Evidence C: Current Helper Implementations Still Depend On Factory Discovery Patterns

Current helper implementations in the repo still use broad helper imports and
factory-adjacent schema discovery patterns:

- `tools/run_build_pack_readiness_eval.py`
- `tools/record_autonomy_run.py`
- `tools/factory_ops.py`

Interpretation:

- changing the starter command text alone is not enough
- the portable helper bundle must resolve its support files from pack-local
  paths
- the helper bundle must be a reduced bounded subset rather than a blind copy
  of the full repo-level helper surface

## Design Goals

- keep autonomous starter task execution portable outside the factory repo
- keep the helper set intentionally small
- preserve bounded workflow behavior and control-plane ownership
- keep the pack-local helper location deterministic
- make the staged remote build-pack self-sufficient for the starter loop
- keep helper contents deterministic and auditable across materialization and
  staging
- prevent ambient dependency leakage from the factory checkout or host Python
  environment

## Non-Goals

This spec does not:

- create a generic remote agent SDK
- make all factory tools portable into every build-pack
- let pack-local helpers mutate registry, promotion, or deployment authority
- require every historical build-pack to be backfilled immediately
- let remote staging compose, inject, or rewrite helper contents at copy time
- rely on ambient factory-relative imports, `PYTHONPATH` leakage, or
  third-party host packages that are not explicitly carried by the build-pack

## Eligibility And Rollout Contract

V1 applies only to newly materialized autonomy-carrying Python build-packs
that are intended to execute starter tasks outside the factory checkout.

For this spec, that means the build-pack:

- carries the canonical autonomy handoff surfaces
- seeds bounded readiness-evaluation starter tasks
- is treated by the factory as a portability-enabled remote-autonomy candidate

Historical build-packs and non-Python build-packs remain outside this rollout
unless a later amendment opts them in explicitly.

If a build-pack is treated as portability-enabled, later staging and remote
execution workflows must fail closed when:

- the declared helper directories are missing
- the helper manifest is missing
- seeded starter commands still point at factory-relative helper paths

## Proposed Portable Helper Surface

V1 should extend newly materialized autonomy-carrying Python build-packs with:

- `.packfactory-runtime/tools/run_build_pack_readiness_eval.py`
- `.packfactory-runtime/tools/record_autonomy_run.py`
- `.packfactory-runtime/tools/factory_ops.py`
- `.packfactory-runtime/manifest.json`
- `.packfactory-runtime/schemas/`

The seeded helper set must be only the minimum needed for:

- starter-task readiness evaluation
- local autonomy-run recording
- local schema validation for those helper outputs

The helper surface is seeded during materialization.

Remote staging does not compose or inject helper contents.

It only copies the helper surface already present in the materialized
build-pack, as defined by:

- [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md)

`factory_ops.py` is a narrow pack-local compatibility shim, not a generic
factory bridge.

It must remain limited to bounded helper support such as:

- pack-local path resolution
- pack-local schema loading
- pack-local evidence-writing helpers already allowed by bounded workflows

It must not expose:

- registry mutation helpers
- deployment mutation helpers
- promotion mutation helpers
- SSH or remote orchestration helpers
- broad arbitrary subprocess wrappers beyond the bounded local helper commands

## Portable Runtime Contract

The helper surface must be self-contained at the pack level.

Portable helper execution must rely only on:

- the host `python3` interpreter
- Python standard library modules
- modules shipped under the declared `.packfactory-runtime/` helper tree
- pack-local files already allowed by the bounded workflow contracts

It must not rely on:

- imports from the surrounding factory checkout
- relative imports that escape the build-pack root
- ambient `PYTHONPATH` or editable-install behavior from the source repo
- host-specific virtualenv directories copied from local development state
- undeclared third-party packages that happen to exist on one remote target

If future autonomy work needs non-stdlib runtime dependencies, that must be
added as an explicit later amendment with its own portability and validator
contract.

This portability layer also complements, and must not replace, the existing
pack-local runtime evidence export surface declared by:

- `pack.json.entrypoints.export_runtime_evidence_command`
- `src/pack_export_runtime_evidence.py`

The autonomous helper layer owns starter-task portability.

The existing export entrypoint remains the canonical runtime evidence export
surface for eligible packs.

## Manifest Contract

`pack.json.directory_contract` should gain optional fields:

- `portable_runtime_tools_dir`
- `portable_runtime_schemas_dir`
- `portable_runtime_helper_manifest`

For newly materialized autonomy-carrying Python build-packs, these should be:

- `.packfactory-runtime/tools`
- `.packfactory-runtime/schemas`
- `.packfactory-runtime/manifest.json`

These paths are pack-local support surfaces.

They must not:

- become local registry authority
- replace `tools/` in the factory repo
- be promoted as user-facing product runtime commands

For portability-enabled build-packs, helper entrypoints must resolve helper
files and schemas from these declared pack-local paths first.

They must not require:

- upward discovery of a nearby factory checkout
- access to factory-level `docs/specs/project-pack-factory/schemas` outside the
  copied pack-local schema directory
- helper paths that escape the build-pack root

If a build-pack declares these paths but the referenced helper or schema files
are missing, the portable helper workflow must fail closed.

The helper manifest should record the exact bounded helper set carried by the
pack.

At minimum it should include:

- `schema_version`
- `portable_runtime_helper_set_version`
- `materialized_at`
- `materialized_by`
- `materializer_version`
- `tools`
- `schemas`
- `helper_entries`
- `seeded_by_materializer`

This manifest is the validator-facing inventory for what the portability layer
actually shipped with the pack.

Each `helper_entries[*]` record should capture at minimum:

- `relative_path`
- `sha256`
- `size_bytes`

Two different helper payloads must not be allowed to look equivalent merely
because they share the same top-level helper-set version label.

## Materialization Ownership Contract

This spec amends build-pack materialization, not remote staging.

For portability-enabled autonomy-carrying Python build-packs, materialization
must seed:

- the bounded helper bundle
- the declared pack-local helper paths in `pack.json`
- the helper manifest inventory
- starter task commands that target those pack-local helper entrypoints

The staging spec then copies that already-materialized payload as-is.

It must not invent, compose, or repair missing helper contents during
source-to-target transfer.

## Seeded Starter Command Contract

For portability-enabled build-packs, materialization should seed:

- `run_build_pack_validation.validation_commands[0]` as:
  - `python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop`
- `run_inherited_benchmarks.validation_commands[0]` as:
  - `python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode benchmark-only --invoked-by autonomous-loop`

This keeps the starter task contract:

- bounded
- canonical
- portable outside the factory repo

Materialization owns the command rewrite.

Remote staging must copy these rewritten commands as already materialized and
must not rewrite them again during source-to-target transfer.

For portability-enabled build-packs, starter task commands must not retain
factory-relative helper paths such as `../../tools/...`.

## Helper Boundary Contract

The portable helper copies must preserve the same authority boundary as their
factory counterparts.

They may update only the same pack-local canonical surfaces already allowed by
their corresponding bounded workflows.

They must not:

- edit `registry/`
- edit `deployments/`
- create promotion records
- bypass existing promotion workflows
- import remote evidence into local canonical history
- treat staged remote state as local PackFactory truth

They also must not:

- discover or mutate files outside the declared pack root
- fall back to `../../tools/` or other factory-relative helper locations
- auto-install dependencies from the network or host package managers
- invoke SSH, rsync, scp, or other transport tools that belong to the staging
  and execution layers

## Validator Expectations

Future validator support should ensure that when a build-pack declares
portable runtime helper paths:

- the declared helper files exist
- the declared helper manifest exists
- the helper manifest enumerates the same helper files actually present
- the helper manifest includes hash entries for the actual helper files present
- starter task commands refer to those pack-local helper paths
- starter task commands do not retain factory-relative tool references such as
  `../../tools/`
- the declared pack-local schema directory exists
- required helper schemas exist under the declared pack-local schema directory
- declared helper paths stay under the pack root rather than escaping to the
  surrounding factory checkout or host filesystem
- helper files do not import from factory-relative paths outside the declared
  helper tree

Historical packs remain valid until the materializer rollout adopts this
contract.

## Minimal Validation Plan

Verification for this spec must follow the PackFactory testing policy:

- keep verification intentionally small
- prefer contract checks over broad helper-behavior matrices
- protect only the few portability failures that would materially break remote
  starter-task execution

V1 verification should stay absolute minimal and focus on:

- one happy-path materialization check that the helper files, helper manifest,
  and rewritten starter commands are all present
- one fail-closed validation check for a missing declared helper file or a
  lingering factory-relative command
- one boundary assertion that the helper inventory and starter commands remain
  pack-local, bounded, and free of forbidden fallback behavior

Do not add:

- cross-platform helper matrices
- transport-coupled staging tests in this spec
- deep fixture forests for helper internals
- broad unit tests for low-risk helper plumbing

When possible, prefer validator coverage, existing factory validation, and
small contract-level smoke checks over new expansive test files.

## Success Criteria

This spec is satisfied when all of the following are true:

1. A newly materialized autonomy-carrying Python build-pack can execute its
   seeded starter task commands without relying on a nearby factory checkout.
2. The pack carries only the minimum bounded helper set needed for the starter
   loop and local autonomy recording.
3. The seeded task commands remain canonical and deterministic.
4. The portable helper layer does not gain any new authority over local or
   factory control-plane state.
5. The portable helper entrypoints resolve required helper files and schemas
   from declared pack-local paths rather than ambient factory-root discovery.
