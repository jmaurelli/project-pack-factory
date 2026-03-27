# ADF Autonomy Baseline Gap Review

Date: 2026-03-26

Pack: `algosec-diagnostic-framework-build-pack-v1`

Purpose: record the bounded gap between the existing ADF build-pack and the
current PackFactory build-pack autonomy baseline so the retrofit can follow an
explicit checklist instead of chat memory.

## Current Assessment

The ADF source template is reasonably current, but the existing materialized
ADF build-pack predates a large portion of the newer PackFactory autonomy,
memory, and feedback-loop inheritance layer.

In plain language: ADF already has real build-pack structure and real planning
state, but it does not yet behave like a freshly materialized build-pack from
today's PackFactory baseline.

## Easy Inherited Refresh

- Refresh build-pack startup guidance in `AGENTS.md` to match the current
  materialized build-pack baseline:
  - startup surfacing for `status/readiness.json.operator_hint_status`
  - canonical use of `status/work-state.json.branch_selection_hints`
  - memory-first restart guidance through `.pack-state/agent-memory/latest-memory.json`
  - remote-session compliance through factory-root workflows
  - explicit references to rehearsal, continuity, import, and fail-closed
    branch-choice guidance
- Refresh build-pack manifest notes in `pack.json` so the legacy ADF
  materialization explicitly records that it has been brought forward to the
  current autonomy baseline.

## Moderate Retrofit

- Update `status/work-state.json` to add the current canonical
  `branch_selection_hints` surface without disturbing the existing ADF backlog.
- Merge the newer memory-first resume instruction into ADF's existing
  scenario-rich `resume_instructions` without replacing its domain-specific
  operating notes.
- Update `contracts/project-objective.json` to add:
  - `autonomy_rehearsal_requirement`
  - advisory-by-default `autonomy_quality_requirement`
  - promotion-readiness wording that matches the current PackFactory baseline
- Refresh the `.packfactory-runtime` helper bundle in place so ADF carries the
  newer autonomy run-summary and feedback-memory contracts.

## Likely Manual Carry-Forward

- Activate real pack-local memory surfaces under `.pack-state/agent-memory/`
  on the live ADF line instead of stopping at inherited helper availability.
- Prove at least one bounded ADF-specific memory/restart workflow after the
  retrofit so the new surfaces are not only present on disk, but actually in
  use.
- Introduce readiness-side hint and continuity surfacing carefully so the ADF
  line gains the newer PackFactory control-plane behaviors without flattening
  its current operator-facing review state.

## Runtime Helper Gap

The ADF portable runtime bundle is older than current materializer output.

Missing or outdated surfaces include:

- `.packfactory-runtime/schemas/autonomy-feedback-memory.schema.json`
- `.packfactory-runtime/schemas/autonomy-feedback-memory-pointer.schema.json`
- the newer `record_autonomy_run.py` contract fields such as:
  - `feedback_memory_path`
  - `block_summary`
  - `autonomy_budget`
  - `operator_intervention_summary`
  - `resolved_block_summary`
  - `delta_summary`
  - `negative_memory_summary`
  - `memory_validity`
  - `memory_tier`

This helper gap appears refreshable in place because the portable runtime
layout is unchanged.

## Intended Retrofit Order

1. Startup and manifest refresh
2. Objective and work-state contract refresh
3. Portable runtime helper bundle refresh
4. Bounded validation and compatibility check
5. Root memory refresh and planning-state update
