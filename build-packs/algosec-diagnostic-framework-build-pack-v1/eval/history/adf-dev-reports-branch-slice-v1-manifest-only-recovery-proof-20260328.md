# ADF `adf-dev` Reports Branch Slice V1 Manifest-Only Recovery Proof - 2026-03-28

## Summary

The PackFactory pullback path now preserves pre-invocation startup stalls as a
structured `manifest_only` result instead of crashing or returning only an
ambiguous synthetic manifest file.

## What changed

- `tools/pull_remote_runtime_evidence.py` now writes a
  `recovery-remote-state.json` artifact whenever it synthesizes a startup-stall
  execution manifest.
- Missing remote `invocation-context.json` no longer crashes the recovery path.
- Synthetic startup-stall execution manifests now satisfy the manifest schema.
- When `export_status` is not `succeeded`, the pullback tool now returns a
  reviewed `manifest_only` result with the execution manifest, target manifest,
  and recovery snapshot paths instead of failing before the caller can inspect
  the stall shape.

## Proof

For `algosec-diagnostic-framework-build-pack-v1-reports-branch-slice-v1`,
`incoming-manual-check-v5` returned:

- `status = manifest_only`
- `terminal_reason = pre_invocation_control_plane_startup_stall`
- `local_recovery_snapshot_path` populated

The recovery snapshot shows:

- `run_dir_exists = true`
- `loop_events_exists = false`
- `run_summary_exists = false`
- `checkpoint_exists = false`
- `invocation_context_exists = false`

That is a much stronger and more reusable classifier than the earlier
startup-stall notes because the raw remote-state shape is now preserved as an
artifact, not inferred only from a crash or a thin note.

## Current judgment

Treat this as a promoted PackFactory control-plane improvement.

The ADF content task is still blocked on intermittent remote launch health, but
future agents can now see exactly what the stalled run did and did not write
without rebuilding the same diagnosis path from scratch.
