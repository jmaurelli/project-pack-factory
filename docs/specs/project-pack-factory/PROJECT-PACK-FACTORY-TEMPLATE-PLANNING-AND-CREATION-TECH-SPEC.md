# Project Pack Factory Template Planning And Creation Tech Spec

## Purpose

Define a single PackFactory-native workflow for:

- starting a new project planning session at the operator level
- deciding whether the current active template is sufficient
- creating a brand-new `template_pack` only when that decision is justified

This closes the current gap between concierge startup guidance and actual
factory capabilities.

## Spec Link Tags

```json
{
  "spec_id": "template-pack-planning-and-creation",
  "depends_on": [
    "directory-hierarchy"
  ],
  "integrates_with": [
    "runtime-agent-memory",
    "retire-workflow"
  ],
  "followed_by": [
    "build-pack-materialization"
  ],
  "adjacent_work": [
    "template scaffold profiles and creation tooling"
  ]
}
```

## Problem

Project Pack Factory can already:

- validate factory state
- materialize build packs from active templates
- promote build packs through environments
- retire templates and build packs

It does not yet define a first-class workflow for the step before
materialization: deciding what new work should begin and whether that work
needs a new template at all.

Without this workflow:

- concierge startup can imply unsupported automation too early
- agents can blur the difference between project planning and template creation
- operators do not get a deterministic decision path for reuse versus new
  template creation
- future template creation risks becoming another ad hoc manual copy path

## Design Goals

- keep operator startup project-oriented and human-facing
- separate planning from creation
- prefer reusing the active template unless a new template is justified
- keep the creation tool minimal and deterministic
- write machine-readable evidence when a new template is created
- keep testing intentionally small

## Scope

This spec defines:

- the concierge-level planning flow that happens before template creation
- the decision contract for reusing an active template versus creating a new
  one
- the deterministic workflow for creating a new template pack
- the evidence artifact for template creation
- the JSON Schemas for the template-creation request and report

This spec does not define:

- general idea generation or open-ended product strategy
- AI-authored template design from scratch
- automatic build-pack creation
- broad template customization matrices
- cloud deployment behavior

## Operator Model

The operator is a human-in-the-loop administrator, not a low-level template
author by default.

That means startup guidance should first help the operator answer:

- what are we trying to build
- is this best treated as a small script, reusable component, or larger
  software project
- can the current active template already support this work
- if not, what specifically justifies a new template

The operator should not be pushed directly into a creation command before that
conversation happens.

## Phase 1: New Project Planning Session

The concierge startup surface should present `start a new project planning
session` as the top-level option.

Planning is the decision gate before any template-creation tool is invoked.

The planning session should begin from machine-readable factory state:

- `registry/templates.json`
- `registry/build-packs.json`
- recent relevant entries in `registry/promotion-log.json`
- `deployments/` only when environment assignment matters to the decision

### Required Planning Questions

The planning session must gather, at minimum:

- `project_goal`
- `delivery_shape`
  - one of: `script`, `component`, `application`, `library`, `other`
- `runtime`
  - for the current PackFactory scope, usually `python`
- `reuse_active_template`
  - `true` or `false`
- `new_template_rationale`
  - required when `reuse_active_template = false`
- `initial_benchmark_intent`
  - short text describing the smallest useful validation or smoke benchmark

### Planning Decision Rule

If the active template is sufficient for the stated goal, the agent should not
recommend creating a new template.

Instead it should recommend:

- continue with the active template
- adapt the active template through normal pack work
- materialize a build pack later when the template is ready

If the active template is not sufficient and the rationale is concrete, the
agent may recommend invoking the template-creation workflow.

### Planning Output

The planning session should end in one of two outcomes:

- `reuse_active_template`
- `create_new_template`

Planning itself does not need a dedicated persisted artifact in v1.

When the operator chooses `create_new_template`, the planning answers are
carried into the creation request and preserved there as evidence.

## Phase 2: Template Creation Workflow

The canonical future tool is:

- `tools/create_template_pack.py`

Canonical invocation:

```bash
python3 tools/create_template_pack.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /abs/path/template-creation-request.json \
  --output json
```

The request file is the source of truth for deterministic creation.

## Preconditions

Before template creation starts:

- the requested `template_pack_id` must not already exist in:
  - `templates/<template_pack_id>/`
  - `registry/templates.json`
- the factory root must pass `tools/validate_factory.py`
- the planning decision must be `create_new_template`
- the request must include a concrete `new_template_rationale`
- the selected scaffold strategy must be supported by the tool

If any precondition fails, the tool must stop before writing the new template
directory.

## Minimal Scaffold Strategy

To keep the tool small, v1 template creation supports exactly one scaffold
strategy:

- `minimal_python_text_pack`

This means the tool creates one bounded PackFactory-native skeleton rather than
trying to generate arbitrary project shapes.

The initial scaffold should resemble the current minimal smoke template in
structure, but with fresh identity and neutral starter content.

## Files Created

The tool must create a new directory under:

- `templates/<template_pack_id>/`

The created template must include:

- `AGENTS.md`
- `README.md`
- `project-context.md`
- `pack.json`
- `pyproject.toml`
- `contracts/README.md`
- `docs/specs/README.md`
- `prompts/README.md`
- `benchmarks/active-set.json`
- at least one benchmark declaration under `benchmarks/declarations/`
- `eval/latest/index.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/retirement.json`
- `status/deployment.json`
- `src/<module_name>/__init__.py`
- `src/<module_name>/__main__.py`
- `src/<module_name>/cli.py`
- `src/<module_name>/validate_project_pack.py`
- `tests/README.md`
- `dist/exports/.gitkeep`
- `.pack-state/.gitkeep`
- `.gitignore`

The scaffold may include a minimal benchmark command and CLI help surface, but
must stay text-only and low-complexity.

The presence of `tests/README.md` in the scaffold documents the testing area
for the future template shape. It is not standing authorization for later
agents to add tests during ordinary testing work without explicit approval.

## Files Synthesized

The tool must synthesize complete schema-valid state files, including:

- `pack.json`
- `status/lifecycle.json`
- `status/readiness.json`
- `status/retirement.json`
- `status/deployment.json`
- `eval/latest/index.json`

Required initial state:

- `pack.json.pack_kind = template_pack`
- `status/lifecycle.json.lifecycle_stage = maintained`
- `status/readiness.json.readiness_state = ready_for_review`
- `status/retirement.json.retirement_state = active`
- `status/deployment.json.deployment_state = not_deployed`
- `status/deployment.json.active_environment = none`

## Registry Effects

After successful creation:

- `registry/templates.json` must contain a new active entry for the template
- the registry entry must include:
  - `pack_id`
  - `pack_kind = template_pack`
  - `pack_root`
  - `lifecycle_stage`
  - `retirement_state = active`
  - `latest_eval_index`
  - `active_benchmark_ids`
  - `notes`
- `registry/build-packs.json` must not be changed by template creation alone

## Operation Log Effects

After successful creation:

- `registry/promotion-log.json` must receive `event_type = template_created`

Every `template_created` event must include:

- `creation_id`
- `template_pack_id`
- `template_creation_report_path`

## Evidence Contract

Successful creation must write a report at:

- `templates/<template_pack_id>/eval/history/<creation_id>/template-creation-report.json`

The report is the canonical evidence artifact for template creation.

The report must preserve:

- the planning summary
- the reuse-versus-new-template decision
- the selected scaffold strategy
- the created file set summary
- the registry mutation summary
- the operation-log mutation summary
- the result of post-write factory validation
- recommended next actions

The created template should also seed `eval/latest/index.json` with a bootstrap
`not_run` benchmark entry consistent with the existing PackFactory eval
contract.

## Request Schema

The request schema is:

- `docs/specs/project-pack-factory/schemas/template-creation-request.schema.json`

The request must include:

- `schema_version`
- `template_pack_id`
- `display_name`
- `owning_team`
- `requested_by`
- `runtime`
- `scaffold_strategy`
- `planning_summary`

The `planning_summary` must include:

- `project_goal`
- `delivery_shape`
- `reuse_active_template`
- `new_template_rationale`
- `initial_benchmark_intent`

## Report Schema

The report schema is:

- `docs/specs/project-pack-factory/schemas/template-creation-report.schema.json`

The report must include:

- `schema_version`
- `creation_id`
- `status`
- `template_pack_id`
- `created_at`
- `created_by`
- `planning_summary`
- `scaffold_strategy`
- `artifact_paths`
- `factory_mutations`
- `next_recommended_actions`

The `factory_mutations` section must include:

- whether `registry/templates.json` was updated
- whether `registry/promotion-log.json` was updated
- whether post-write factory validation passed

## Concierge Guidance Alignment

Until the creation tool exists, startup guidance must not present `create a new
template` as an already-supported top-level action.

Instead concierge replies should offer:

- `start a new project planning session`
- `rerun the existing checks for the active testing candidate`
- `review recent results before deciding`
- `retire historical work that should stay frozen`

Only after the planning session identifies a justified need should the agent
recommend the template-creation workflow defined here.

For clarity, generic operator requests to `test` or `continue testing` a pack
should be interpreted as rerunning the existing validation, benchmark, or
workflow surfaces that already exist. Those requests do not authorize adding or
strengthening tests.

## Minimal Test Posture

Keep testing intentionally small.

Generic testing requests in this workflow family mean rerunning the existing
checks that already exist for the workflow. They do not authorize creating,
expanding, or strengthening tests.

For this workflow family, the recommended budget is:

- `4` tests maximum

Suggested coverage:

- planning decision rejects creation when the active template is sufficient
- creation happy path writes a schema-valid template and registry entry
- creation fail-closed path blocks duplicate `template_pack_id`
- creation writes the canonical evidence report

Do not spend test budget on:

- wording permutations in concierge text
- helper internals
- broad scaffold customization matrices
- metrics formatting

## Validation

The implemented workflow should validate through:

- JSON schema validation for the request and report contracts
- `tools/validate_factory.py`
- the minimal workflow tests allowed above

## Relationship To Existing Specs

This spec provides the missing step before:

- `PROJECT-PACK-FACTORY-BUILD-PACK-MATERIALIZATION-TECH-SPEC.md`

It must remain consistent with:

- `PROJECT-PACK-FACTORY-DIRECTORY-HIERARCHY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-RETIRE-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-RUNTIME-AGENT-MEMORY-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

The base directory-hierarchy spec should also recognize this workflow as a
prerequisite built on the same pack-level contract.
