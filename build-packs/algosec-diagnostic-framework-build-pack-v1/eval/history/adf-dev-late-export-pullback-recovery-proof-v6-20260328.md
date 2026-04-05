# ADF `adf-dev` Late-Export Pullback Recovery Proof V6 - 2026-03-28

## Summary

The late-export pullback recovery improvement is now proven end to end.

I reran the later-content slice with an intentionally short first delayed
pullback (`5s`) plus bounded late-export recovery attempts (`3` attempts,
`20s` apart). The wrapper still returned a normal pulled bundle instead of
failing during pullback.

## What changed

- `tools/pull_remote_runtime_evidence.py` now retries recovered bundle
  discovery for a bounded extra window before it settles on a no-bundle result.
- `tools/import_external_runtime_evidence.py` now accepts checkpoint-declared
  target artifacts under `artifacts/artifacts/*`, which the recovered v4 and v6
  bundles use.

## Proof

- The remote run started at `2026-03-28T22:29:25Z`.
- The remote run exported successfully at `2026-03-28T22:36:17Z`.
- The local wrapper pulled the bundle successfully at `2026-03-28T22:36:20Z`.
- The wrapper exited with `status = completed` and `stopped_without_bundle = false`.

Relevant local pullback evidence:

- `.pack-state/remote-autonomy-roundtrips/adf-dev/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-later-content-branch-slice-v6/incoming/execution-manifest.json`
- `.pack-state/remote-autonomy-roundtrips/adf-dev/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-later-content-branch-slice-v6/incoming/bundle/artifacts/run-summary.json`
- `.pack-state/remote-autonomy-roundtrips/adf-dev/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-later-content-branch-slice-v6/incoming/bundle/artifacts/adf-remote-checkpoint-bundle.json`

## Current judgment

Treat `tune_late_export_pullback_recovery` as complete.

The PackFactory wrapper no longer needs perfect timing on the first delayed
pullback to recover a late export bundle from this ADF slice. The next task
should move back to normal content or checkpoint work instead of more wrapper
triage.
