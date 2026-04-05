# Project Pack Factory Runtime-Template Parity And Backport Tech Spec

## Purpose

Define the smallest explicit PackFactory workflow that records when a reusable
behavior was proved in a runtime build-pack, whether it was backported into
the source template, and what still remains pending.

This is a factory control-plane improvement, not a request to auto-sync every
runtime file back into its template.

## Spec Link Tags

```json
{
  "spec_id": "runtime-template-parity-and-backport",
  "amends": [
    "template-planning-and-creation",
    "build-pack-materialization"
  ],
  "depends_on": [
    "template-lineage-memory"
  ],
  "integrates_with": [
    "factory-validation",
    "root-work-tracker"
  ],
  "adjacent_work": [
    "assistant template backports",
    "runtime-template drift visibility",
    "task-tracker consistency"
  ]
}
```

## Problem

PackFactory already has clear surfaces for:

- source templates
- materialized runtime build-packs
- template lineage memory
- autonomy-improvement promotion notes

What it still lacks is a bounded parity workflow for this common pattern:

1. a reusable behavior is first proved in a runtime build-pack
2. the same behavior is then manually mirrored into the source template
3. the factory has no explicit parity record showing whether that backport
   happened, is still pending, or is intentionally not required

That leaves an avoidable gap between:

- runtime proof
- template inheritance truth
- factory-level discoverability of what has or has not been backported

## Evidence

Evidence was collected on 2026-03-30 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: The Current Factory Surfaces Do Not Name A Parity Or Backport Workflow

Search:

```bash
rg -n "parity|backport" tools docs/specs/project-pack-factory AGENTS.md README.md \
  -g '*.py' -g '*.md'
```

Observed result:

- no matches

Interpretation:

- the factory currently has no named root-level workflow, spec family, or
  tool surface for runtime-to-template parity tracking

### Evidence B: The Assistant Runtime And Template Both Carry The Same New Behavior, But Only Through Manual Mirroring

Runtime tracking shows the recurring reflection slice completed and the pack
paused in review state:

- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/tasks/active-backlog.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/status/work-state.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/status/readiness.json`

Template mirrors now exist separately in:

- `templates/codex-personal-assistant-template-pack/contracts/partnership-policy.json`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/grounding.py`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/alignment.py`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/cli.py`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/doctor.py`

Interpretation:

- the reusable behavior now exists on both sides
- the repo does not currently expose a first-class factory record saying that
  the template inheritance step is complete for this runtime-proved slice

### Evidence C: Manual Tracker Drift Is Already Visible In The Assistant Line

Search:

```bash
rg -n 'navigation_and_fundamentals_guidance_loop' \
  build-packs/codex-personal-assistant-daily-driver-build-pack-v1/tasks/active-backlog.json
```

Observed result:

- line `308`: `task_id = "navigation_and_fundamentals_guidance_loop"`
- line `347`: `task_id = "navigation_and_fundamentals_guidance_loop"`

Interpretation:

- even within one proved assistant line, manual planning drift can survive
  current validation
- a parity workflow should stay inspectable and validator-friendly rather than
  depending on memory alone

## Design Goals

- make runtime-to-template backport status explicit
- keep the workflow bounded to reusable behaviors rather than whole-pack sync
- preserve template autonomy and build-pack autonomy as separate artifacts
- make parity evidence discoverable from the factory root
- keep validation light and fail-closed

## Non-Goals

- auto-merging runtime files into templates
- forcing every runtime-only experiment to backport into a template
- replacing template lineage memory with a second unrelated memory system
- broadening this into generic cross-pack synchronization

## Proposed Workflow

When a runtime build-pack proves a behavior that is intended to be reusable for
future packs from the same source template, PackFactory should record a parity
artifact with at least:

- `runtime_build_pack_id`
- `source_template_id`
- `improvement_summary`
- `proof_paths`
- `runtime_paths`
- `template_paths`
- `parity_status`
- `pending_follow_up`

Recommended `parity_status` values:

- `runtime_only`
- `template_backported`
- `template_backported_and_lineage_refreshed`
- `not_required`

Recommended storage root:

- `.pack-state/template-parity-reports/`

Recommended control-plane behavior:

- the parity record is created when the operator or agent decides the behavior
  is reusable and template-relevant
- template-lineage capture may reference the parity record instead of
  restating the whole backport story
- root planning surfaces can point to the parity record when asking whether a
  runtime lesson has really become template inheritance

## Validator Follow-Through

This spec does not require an immediate validator hard-error.

A bounded first step is enough:

- validate the parity artifact schema when it exists
- optionally warn when a declared reusable runtime improvement has no parity
  record yet
- keep duplicate task-id detection as adjacent follow-up work rather than a
  hidden side effect of parity implementation

## Evidence Contract

A parity record should only claim `template_backported` when it includes:

- one runtime proof path
- one template source path
- one factory-visible planning or lineage path

At least one proof path should be machine-readable when possible.

## Validation

Use existing bounded surfaces:

```bash
python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```

For the assistant proving line, parity work should also stay consistent with:

```bash
cd /home/orchadmin/project-pack-factory/build-packs/codex-personal-assistant-daily-driver-build-pack-v1
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack benchmark-smoke --project-root . --output json
```

```bash
cd /home/orchadmin/project-pack-factory/templates/codex-personal-assistant-template-pack
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack benchmark-smoke --project-root . --output json
```
