# ADF `adf-dev` Launcher Hardening Proof Run V2 - 2026-03-28

## Summary

The launcher-hardening proof run now completes through the normal PackFactory
roundtrip path on `adf-dev`.

This is the first real proof that the hardened wrapper path can:

- wait through a slow remote slice without dropping it early,
- pull a full exported bundle back to the factory root, and
- return a structured result instead of the earlier `run_started`-only or
  manifest-only recovery shapes.

## What happened

- The proof run started at `2026-03-28T21:35:25Z`.
- The remote ADF loop ran on `adf-dev` for about eight minutes and stopped at
  `2026-03-28T21:43:03Z`.
- The remote side wrote:
  - `.pack-state/autonomy-runs/algosec-diagnostic-framework-build-pack-v1-launcher-hardening-proof-run-v2/run-summary.json`
  - `.pack-state/autonomy-runs/algosec-diagnostic-framework-build-pack-v1-launcher-hardening-proof-run-v2/adf-remote-checkpoint-bundle.json`
  - `dist/exports/runtime-evidence/external-runtime-evidence-algosec-diagnostic-framework-build-pack-v1-launcher-hardening-proof-run-v2-20260328T214303Z/bundle.json`
- The local wrapper then pulled the bundle successfully into:
  - `.pack-state/remote-autonomy-roundtrips/adf-dev/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-launcher-hardening-proof-run-v2/incoming/bundle/`

## What this proves

- The launcher-hardening work is now beyond theory.
- The reviewed execution timeout floor plus delayed-pullback wrapper path no
  longer leaves this proof slice stranded at `run_started`.
- The remote control plane can now return a normal bundled result for a slow
  bounded `adf-dev` run.

## What it did not prove

- This was still a launcher/control-plane proof slice, not a fresh later-content
  content checkpoint.
- The remote checkpoint bundle stayed measurement-only:
  - `checkpoint_reason = evidence_ready`
  - no candidate source, doc, or work-state changes were proposed
  - the checkpoint note only asked to preserve launcher-hardening evidence

## Current judgment

Treat `stabilize_remote_codex_launcher_against_interactive_menu` as completed.

The next blocker is no longer launcher uncertainty. The next real task is to
retry the fresh later-content checkpoint with the now-proven control-plane path
and judge that run on content evidence, not on startup or wrapper survival.
