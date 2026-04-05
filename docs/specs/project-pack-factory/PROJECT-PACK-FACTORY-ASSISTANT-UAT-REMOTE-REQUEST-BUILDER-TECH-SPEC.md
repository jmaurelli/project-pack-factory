# Project Pack Factory Assistant UAT Remote Request Builder Tech Spec

## Purpose

Define a bounded PackFactory helper that generates the request pair for
assistant-style remote UAT:

- `remote-run-request.json`
- `remote-test-request.json`

The goal is to stop rebuilding long inline remote runners by hand whenever a
build-pack needs a prompt-driven remote Codex acceptance pass.

## Spec Link Tags

```json
{
  "spec_id": "assistant-uat-remote-request-builder",
  "amends": [
    "remote-autonomous-build-pack-execution",
    "external-runtime-evidence-import"
  ],
  "depends_on": [
    "remote-autonomy-target-workspace-and-staging"
  ],
  "integrates_with": [
    "factory-validation",
    "remote-roundtrip-control-plane"
  ],
  "adjacent_work": [
    "assistant-uat prompt bundles",
    "remote request ergonomics",
    "artifact boundary compliance"
  ]
}
```

## Problem

PackFactory already knows how to:

- stage remote runs
- execute a bounded remote runner
- pull runtime evidence back
- import `assistant-uat` artifacts as supplementary evidence

What it still lacks is a factory-native builder for assistant-style UAT
requests.

Today the control plane can run the test once the request pair exists, but the
request author still has to assemble:

- the remote run id
- the remote prompt bundle
- the allowed writable surfaces
- the inline remote runner program
- the import reason and staging paths

That is real operator work, and it is easy to get wrong.

## Evidence

Evidence was collected on 2026-03-30 from:

- `/home/orchadmin/project-pack-factory`

### Evidence A: Current Tools Generate Generic Request Pairs, Not Assistant-UAT Builders

Search:

```bash
rg -n "assistant-uat|remote request builder|remote-run-request|remote-test-request" \
  tools docs/specs/project-pack-factory -g '*.py' -g '*.md'
```

Observed matches include:

- `tools/run_remote_memory_continuity_test.py`
- `tools/run_remote_active_task_continuity_test.py`
- `tools/run_degraded_connectivity_autonomy_exercise.py`
- `tools/import_external_runtime_evidence.py`
- `tools/materialize_build_pack.py`

Interpretation:

- PackFactory knows the generic request-pair pattern
- PackFactory already recognizes `assistant-uat` as an artifact family
- there is still no dedicated assistant-UAT request builder

### Evidence B: The Current Assistant UAT Request Still Embeds A Large Inline Remote Runner

Current request:

- `.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v11/remote-run-request.json`

Observed shape:

- a long `remote_runner` string containing inline Python
- embedded prompt definitions
- embedded allowed-surface rules
- embedded report-writing logic

Interpretation:

- the control-plane path works
- authoring the request is still too handcrafted for a repeated workflow

### Evidence C: Assistant-UAT Artifacts Already Produce Useful Imported Evidence

Imported evidence:

- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t203722z/import-report.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t203722z/external-runtime-evidence/artifacts/assistant-uat/uat-report.json`

Observed result:

- import status `completed`
- copied `assistant-uat/*` artifacts into canonical pack history
- activated imported assistant memory for continuity review
- prompt return codes were all `0`

Interpretation:

- assistant-UAT is already valuable enough to deserve a first-class request
  builder instead of one-off handcrafted runners

### Evidence D: The Product Signal From Remote Assistant-UAT Is Strong Enough To Justify Reuse

Remote result excerpt:

- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260330t191427z/external-runtime-evidence/artifacts/assistant-uat/navigation_check_and_fundamentals-last-message.txt`

Observed message:

- the assistant classified the scenario as `fundamentals-first`
- it proposed one grounded next step instead of pretending certainty

Interpretation:

- the workflow is not just infrastructure noise
- it produces user-facing behavior evidence worth repeating cleanly

### Evidence E: The Builder Now Emits The Canonical Request Pair And Scenario Manifest

Implemented helper:

- `tools/build_assistant_uat_remote_request.py`

Implemented scenario contract:

- `docs/specs/project-pack-factory/schemas/assistant-uat-scenario.schema.json`
- `docs/specs/project-pack-factory/assistant-uat-scenarios/recurring-relationship-reflection-loop.json`

Generated request evidence:

- `.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v12/remote-run-request.json`
- `.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v12/remote-test-request.json`
- `.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v12/assistant-uat-scenario-manifest.json`

Interpretation:

- PackFactory now has a first-class builder for assistant-style remote UAT
- the helper still emits the existing remote roundtrip request pair
- the exact prompt bundle used for a run is now preserved as an auditable
  scenario manifest alongside the generated requests

### Evidence F: Contract-Profile Refinement Can Escape The Approved UAT Boundary

Boundary-failed run:

- `.pack-state/local-scratch/remote-autonomy-roundtrips/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v15/incoming/execution-manifest.json`

Remote write evidence:

- `.pack-state/autonomy-runs/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v15/assistant-uat/record_alignment_risk_reflection-last-message.txt` on `adf-dev`
- `.pack-state/autonomy-runs/assistant-uat-relationship-reflection-20260331t125839z/assistant-uat/record-operator-intake-result.json` on `adf-dev`

Observed result:

- PackFactory ended the run with `terminal_reason: unauthorized_writable_surface`
- the assistant reported that it "applied explicit bounded profile refinement"
- the recorded result named `profile_refinement_path: "contracts/operator-profile.json"`

Interpretation:

- assistant-UAT scenarios can accidentally mutate non-`.pack-state/` contract
  files if profile refinement is not explicitly bounded
- the builder needs a scenario-level switch so contract-profile refinement is
  opt-in instead of implicitly allowed by open-ended prompts

### Evidence G: The Hardened Builder Now Passes Cleanly With Scenario-Controlled Profile Refinement

Hardened scenario contract:

- `docs/specs/project-pack-factory/schemas/assistant-uat-scenario.schema.json`
- `docs/specs/project-pack-factory/assistant-uat-scenarios/recurring-relationship-reflection-loop.json`

Clean request and roundtrip evidence:

- `.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v19/remote-run-request.json`
- `.pack-state/remote-autonomy-roundtrips/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v19/artifacts/execution-manifest.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t145619z/import-report.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t145619z/external-runtime-evidence/artifacts/assistant-uat/uat-report.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t145619z/external-runtime-evidence/artifacts/assistant-uat/record_alignment_risk_reflection-last-message.txt`

Observed result:

- the scenario now keeps `allow_contract_profile_refinement: false`
- the generated remote runner uses `model_reasoning_effort="low"` for this recurring reflection scenario
- `export_status` is `succeeded`
- the imported `assistant-uat` bundle completed with all 3 prompts returning `0`
- the assistant explicitly recorded the alignment-risk reflection without passing `refine_profile_json` and without modifying `contracts/operator-profile.json`

Interpretation:

- the builder is now proved both as a request generator and as a bounded remote-UAT controller for assistant-style reflection scenarios
- scenario-controlled contract refinement is the right fail-closed default for assistant-UAT
- scenario-level reasoning-effort selection is a useful bounded control-plane lever for keeping repeated remote Codex passes prompt-fast without weakening the canonical roundtrip path

### Evidence G: The Hardened Builder Now Produces A Clean Boundary-Safe Roundtrip

Hardened scenario and builder surfaces:

- `tools/build_assistant_uat_remote_request.py`
- `docs/specs/project-pack-factory/schemas/assistant-uat-scenario.schema.json`
- `docs/specs/project-pack-factory/assistant-uat-scenarios/recurring-relationship-reflection-loop.json`

Generated request and successful import evidence:

- `.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v19/remote-run-request.json`
- `.pack-state/remote-autonomy-roundtrips/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v19/artifacts/execution-manifest.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t145619z/import-report.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t145619z/external-runtime-evidence/artifacts/assistant-uat/uat-report.json`
- `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t145619z/external-runtime-evidence/artifacts/assistant-uat/record_alignment_risk_reflection-last-message.txt`

Observed result:

- the scenario runs with `model_reasoning_effort="low"` to keep prompt latency bounded
- the remote execution manifest completed with `runner_returncode: 0` and `export_status: succeeded`
- the imported UAT report shows all three prompts returned `0`
- the recorded reflection explicitly avoided `refine_profile_json` and did not modify `contracts/operator-profile.json`

Interpretation:

- the builder now has a proved fail-closed path for relationship-reflection UAT
- PackFactory can keep assistant-UAT memory-first and inspectable without widening the approved writable surface to template/runtime contract files

### Evidence H: Stale Assistant-UAT Cleanup Is Now Bounded And Auditable

Updated builder behavior:

- `tools/build_assistant_uat_remote_request.py`

Recorded report fields:

- `stale_process_cleanup`
- `stale_process_cleanup_boundary`
- `killed_processes`
- `killed_process_groups`
- `skipped_processes`

Interpretation:

- stale assistant-UAT cleanup should remain pack-scoped and age-bounded
- pgid-aware termination is only appropriate when the process group is wholly assistant-UAT scoped
- the report should preserve the cleanup boundary and outcome so later audits can tell the difference between a stale-process cleanup and an unrelated remote Codex session

## Design Goals

- generate both request files from one bounded assistant-UAT input
- preserve the current remote roundtrip control plane
- keep writable surfaces limited to PackFactory-approved roots
- support reusable prompt bundles and named scenarios
- keep the imported evidence contract unchanged

## Non-Goals

- replacing `run_remote_autonomy_test.py`
- introducing ad hoc SSH orchestration outside the PackFactory control plane
- turning assistant-UAT into a general-purpose remote execution framework
- changing imported runtime evidence from supplementary to canonical truth

## Proposed Helper Contract

Recommended helper:

- `tools/build_assistant_uat_remote_request.py`

Recommended inputs:

- `--factory-root`
- `--build-pack-id`
- `--remote-target-label`
- `--remote-host`
- `--remote-user`
- `--scenario-id`
- `--reason`
- optional `--prompt-bundle-path`

Recommended outputs:

- one request directory under `.pack-state/remote-autonomy-requests/...`
- generated `remote-run-request.json`
- generated `remote-test-request.json`
- one prompt-bundle manifest or copied prompt bundle for auditability

Recommended scenario bundle roots:

- `docs/specs/project-pack-factory/assistant-uat-scenarios/`
- or a pack-local declared prompt bundle when the scenario is intentionally
  pack-specific

Implemented v1 scenario contract:

- `assistant-uat-scenario/v1`
- fields:
  - `scenario_id`
  - `summary`
  - `session_preamble`
  - `prompts[{name,prompt}]`
  - optional `model_reasoning_effort`
  - optional `allow_preview_bundle`
  - optional `allow_contract_profile_refinement`
  - optional `expected_sidecar_artifacts[]`

## Remote Runner Boundary

The generated runner should stay within the already-proven assistant-UAT
surfaces:

- `.pack-state/autonomy-runs/<run-id>/assistant-uat/`
- `dist/candidates/uat-preview/`
- existing assistant-local memory and review surfaces
- contract-profile refinement is off by default and must be explicitly enabled
  by the scenario when a prompt is meant to touch
  `contracts/operator-profile.json`
- stale assistant-UAT `codex exec` cleanup is allowed only inside the same
  pack-scoped `autonomy-runs/<run-id>/assistant-uat/` boundary, and the
  runner should prefer pgid-aware termination only when every process in that
  process group is clearly scoped to the same assistant-UAT run

The generated UAT report should record the cleanup boundary and the cleanup
outcome so later audits can distinguish a stale assistant-UAT cleanup from an
unrelated remote Codex session.

It should not improvise new writable roots.

## Evidence Contract

Each generated request should preserve:

- the scenario id
- the remote target identity
- the exact prompt bundle used
- the import reason
- the remote export directory

The imported evidence should continue to flow through the existing
PackFactory import path rather than a new custom importer.

## Validation

Use existing bounded control-plane surfaces:

```bash
python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```

The builder should remain compatible with:

```bash
python3 tools/run_remote_autonomy_test.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /home/orchadmin/project-pack-factory/.pack-state/remote-autonomy-requests/adf-dev/codex-personal-assistant-daily-driver-build-pack-v1/codex-personal-assistant-daily-driver-build-pack-v1-uat-autonomous-run-v19/remote-test-request.json \
  --output json
```

Implemented builder proof command:

```bash
python3 tools/build_assistant_uat_remote_request.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --build-pack-id codex-personal-assistant-daily-driver-build-pack-v1 \
  --remote-target-label adf-dev \
  --remote-host adf-dev \
  --remote-user adf \
  --scenario-id recurring-relationship-reflection-loop \
  --reason "the recurring relationship-reflection loop on the staged Codex personal assistant daily-driver pack" \
  --output json
```
