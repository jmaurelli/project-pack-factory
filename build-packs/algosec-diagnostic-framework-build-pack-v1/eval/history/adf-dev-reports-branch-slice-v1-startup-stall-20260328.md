# ADF `adf-dev` Reports Branch Slice V1 Startup Stall - 2026-03-28

## Summary

The first bounded `REPORTS` branch slice did not produce a content checkpoint.

The packet staged cleanly to `adf-dev`, but the reviewed remote roundtrip never
returned a bundle through the normal wrapper path. A later manual PackFactory
pullback recovered only an execution manifest and target manifest.

## What was attempted

- Run id: `algosec-diagnostic-framework-build-pack-v1-reports-branch-slice-v1`
- Goal: preserve one fresh exact later-content minute with `/afa/php/home.php`
  already present plus a clear `GET_REPORTS` marker, then stop with a support
  note that the case is no longer top-level `GUI down`.

## Observed shape

- The local wrapper stayed inside the reviewed remote execution wait and never
  reached a normal pulled bundle.
- A manual PackFactory pullback recovered:
  - `incoming-manual-check/execution-manifest.json`
  - `incoming-manual-check/target-manifest.json`
- No `bundle.json`, `run-summary.json`, `loop-events.jsonl`, or
  `adf-remote-checkpoint-bundle.json` was recovered for this run.

## Current judgment

Treat this as another `pre_invocation_control_plane_startup_stall`, not as a
content result.

The content target is still reasonable, but this specific `REPORTS` slice did
not make support-useful progress. The next move should either reclassify the
intermittent startup stall more tightly or retry the content slice only after
the launch path looks healthy again.
