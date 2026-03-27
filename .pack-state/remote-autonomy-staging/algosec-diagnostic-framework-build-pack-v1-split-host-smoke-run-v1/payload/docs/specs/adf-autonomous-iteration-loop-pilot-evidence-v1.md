# ADF Autonomous Iteration Loop Pilot Evidence V1

Attempted task: deepen_asms_ui_service_command_packs

Evidence reviewed:
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
- `dist/candidates/algosec-lab-baseline/starlight-site/src/content/docs/playbooks/asms-ui-is-down.md`
- `.pack-state/remote-autonomy-staging/algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4/payload/dist/candidates/algosec-lab-baseline/support-baseline.json`
- local `generate-support-baseline` attempts against `dist/candidates/adf-baseline` and `dist/candidates/algosec-lab-baseline`

Outcome class: changed_artifact

Why not only bookkeeping: this iteration changed the canonical ADF generator
source for the ASMS UI service packs by adding one new Keycloak-specific log
check and one new ms-metro JVM-error check. It also recorded a real boundary
discovered during execution: running `generate-support-baseline` locally on the
current workspace host resolves to local Ubuntu host evidence, so it is not a
valid way to refresh the remote AlgoSec appliance-backed candidate artifacts.
After confirming that boundary, the iteration preserved the source change and
restored the last good remote-backed generated artifacts from preserved
PackFactory staging evidence instead of treating the invalid local refresh as
progress.

Changed pack-local artifact: `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`

Artifact refresh note:
- restored `dist/candidates/algosec-lab-baseline/*` generated files from
  `.pack-state/remote-autonomy-staging/algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4/payload/dist/candidates/algosec-lab-baseline/`
- restored `dist/candidates/adf-baseline/*` generated files from
  `.pack-state/remote-autonomy-staging/algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4/payload/dist/candidates/adf-baseline/`
- deferred any new appliance-backed render refresh until a PackFactory-root
  remote/runtime workflow can run against the real AlgoSec target
