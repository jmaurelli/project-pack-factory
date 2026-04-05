# ADF `adf-dev` Later-Content Branch Slice V4 Recovered Import - 2026-03-28

## Summary

The fresh later-content checkpoint is now real canonical local evidence.

The remote wrapper initially failed too early, but a later reviewed pullback
recovered the exported bundle and the factory importer preserved it locally.

## What the recovered checkpoint proved

- The preserved minute is `2026-03-28 17:56 EDT`.
- `/afa/php/home.php?segment=DEVICES` is already present in that window.
- `POST /afa/php/commands.php` returned the `GET_ANALYSIS_OPTIONS` dialog body
  for device `200132`.
- That is enough to stop calling the case top-level `GUI down`.

## Why this matters

- The later-content branch checkpoint itself is now complete.
- Support can branch out of top-level `GUI down` once the shell has reached the
  DEVICES segment and the Analyze dialog options fetch succeeds.
- Metro stayed supporting in this slice, but it was not the stop point.

## Recovery nuance

- The first wrapper attempt on v4 failed during pullback because it did not see
  a matching exported runtime bundle yet.
- A later helper-backed pullback showed that the remote bundle did exist and
  had been generated at `2026-03-28T22:01:51Z`.
- The importer then rejected the checkpoint target artifacts until the factory
  import contract was widened to accept `artifacts/artifacts/*`.

## Current judgment

Two things are true at once:

- `capture_fresh_later_content_branch_checkpoint` is complete.
- The next autonomy improvement is still real: one delayed pullback can be too
  short for late export bundles, so the wrapper should not treat that shape as a
  final failure without a stronger late-bundle recovery rule.
