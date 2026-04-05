# Project Pack Factory Assistant Template Lineage Improvement Capture Tech Spec

## Purpose

Define how PackFactory should record the reusable grounded-assistant behavior
bundle that was proved in the Codex personal assistant line and backported into
`codex-personal-assistant-template-pack`.

This is a template-lineage capture workflow, not a request to promote those
assistant behaviors into every PackFactory template by default.

## Spec Link Tags

```json
{
  "spec_id": "assistant-template-lineage-improvement-capture",
  "amends": [
    "autonomy-operations-note"
  ],
  "depends_on": [
    "template-lineage-memory",
    "autonomy-improvement-promotion"
  ],
  "integrates_with": [
    "factory-root-memory",
    "root-work-tracker"
  ],
  "adjacent_work": [
    "codex personal assistant template",
    "grounded business-partner behavior",
    "assistant reflection cadence"
  ]
}
```

## Problem

The Codex personal assistant line now contains a real reusable behavior family:

- grounded business-partner positioning
- navigation under uncertainty
- business review and continuity closeout
- thin-history carry-forward
- recurring relationship reflection

The source template has already inherited these surfaces, and remote UAT has
already proved important parts of the behavior family.

What is still missing is an explicit factory-level record saying:

- which improvement bundle was proved
- which source template now carries it
- which proof artifacts justify that claim
- whether the lesson is template-specific or promoted further into factory
  defaults

## Evidence

Evidence was collected on 2026-03-30 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: The Template Now Carries The Assistant Relationship And Grounding Cadences Directly

Template contract:

- `templates/codex-personal-assistant-template-pack/contracts/partnership-policy.json`

Observed sections include:

- `grounding_accountability_cadence`
- `navigation_guidance_loop`
- `business_review_loop`
- `relationship_reflection_loop`

Interpretation:

- the reusable assistant behavior bundle is no longer runtime-only
- the source template itself now carries the business-partner and reflection
  model

### Evidence B: The Template Runtime Surface Mirrors The New Behavior Family

Template source paths:

- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/grounding.py`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/alignment.py`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/cli.py`
- `templates/codex-personal-assistant-template-pack/src/codex_personal_assistant_template_pack/doctor.py`
- `templates/codex-personal-assistant-template-pack/docs/specs/operator-alignment-model.md`

Interpretation:

- the template source now exposes code and documentation, not just a contract
  stub

### Evidence C: Remote Assistant-UAT Already Proved Core Parts Of The Behavior Bundle

Imported remote proof:

- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t191427z/external-runtime-evidence/artifacts/assistant-uat/navigation_check_and_fundamentals-last-message.txt`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t203722z/import-report.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t203722z/external-runtime-evidence/artifacts/assistant-uat/uat-report.json`

Observed results include:

- the assistant classified the operator scenario as `fundamentals-first`
- the imported evidence bundle completed successfully
- all `v10` prompt return codes were `0`
- continuity memory was activated from imported evidence

Interpretation:

- the assistant template line has real remote behavioral proof for core
  grounded-guidance and continuity surfaces

### Evidence D: The Factory Already Has Capture Tooling, But No Recorded Improvement For This Assistant Line Yet

Relevant tooling and guidance:

- `tools/record_autonomy_improvement_promotion.py`
- `tools/refresh_template_lineage_memory.py`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`

Search over current promotion reports:

```bash
files=$(find .pack-state/autonomy-improvement-promotions -maxdepth 2 -type f -name "promotion-report.json")
if [ -n "$files" ]; then
  rg -n "codex-personal-assistant|relationship-reflection|business-grounding|navigation guidance" $files || true
fi
```

Observed result:

- no matches

Interpretation:

- the improvement family is real and locally proved
- the factory has not yet recorded it as an autonomy-improvement promotion or
  refreshed template-lineage memory around it

## Design Goals

- record the assistant improvement family with concrete proof paths
- make the template-specific inheritance status explicit
- keep assistant-template behavior separate from factory-global defaults
- refresh template lineage memory after recording the improvement

## Non-Goals

- promoting assistant-specific behaviors into every template by default
- rewriting root memory as if the improvement were already factory-global
- inventing a second lineage system outside existing promotion and memory tools

## Improvement Bundle To Capture

Recommended improvement id:

- `codex-personal-assistant-grounded-relationship-learning`

Recommended scope summary:

- grounded business-partner framing
- navigation-under-uncertainty guidance
- business review and continuity closeout
- thin-history carry-forward
- recurring relationship reflection

## Capture Contract

The first bounded recording pass should:

- use `tools/record_autonomy_improvement_promotion.py`
- set `source_build_pack_id = codex-personal-assistant-daily-driver-build-pack-v1`
- set `source_template_id = codex-personal-assistant-template-pack`
- mark `source_template_tracking` as `adopted`
- leave `factory_root_discoverability` and `factory_root_memory` pending
  unless the behavior is later generalized beyond the assistant template line

After recording the improvement, PackFactory should refresh:

- `tools/refresh_template_lineage_memory.py --template-id codex-personal-assistant-template-pack ...`

## Evidence Contract

The recorded improvement should include at least:

- one template contract or code path
- one remote UAT artifact
- one imported evidence report

If later work promotes part of this assistant behavior bundle into
factory-global defaults, that should be recorded as a separate follow-on
promotion decision rather than rewriting the assistant-template record.

## Validation

Use the existing capture and memory-refresh surfaces:

```bash
python3 tools/record_autonomy_improvement_promotion.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --improvement-id codex-personal-assistant-grounded-relationship-learning \
  --summary "Record the grounded business-partner, navigation, continuity, thin-history, and recurring relationship-reflection behavior bundle now inherited by the Codex personal assistant template line." \
  --source-build-pack-id codex-personal-assistant-daily-driver-build-pack-v1 \
  --source-template-id codex-personal-assistant-template-pack \
  --proof-path build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t191427z/external-runtime-evidence/artifacts/assistant-uat/navigation_check_and_fundamentals-last-message.txt \
  --proof-path build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t203722z/import-report.json \
  --adopted-surface source_template_tracking \
  --pending-surface factory_root_discoverability \
  --pending-surface factory_root_memory \
  --output json
```

```bash
python3 tools/refresh_template_lineage_memory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --template-id codex-personal-assistant-template-pack \
  --actor codex \
  --output json
```

```bash
python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```
