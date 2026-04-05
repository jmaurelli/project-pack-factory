# ADF `adf-dev` Reports Branch Slice V2 Recovered Checkpoint - 2026-03-28

## Summary

The retried `REPORTS` slice returned a real content checkpoint after the
controller wait timed out.

The late pullback recovered the exported bundle, and that bundle preserved one
exact later-content minute that is support-useful.

## What the recovered checkpoint proved

- The preserved minute is `2026-03-28 19:27 EDT`.
- The same live AFA web session served
  `/afa/php/home.php?segment=DEVICES` with `200`.
- One second later, `GET /afa/php/commands.php?cmd=GET_REPORTS&TOKEN=<redacted>`
  returned `200`.
- The `GET_REPORTS` response reported `bCmdStatus=true` with an empty table
  payload (`recordsTotal=0`).

## Why this matters

- This session is no longer a top-level `GUI down` case.
- The useful next boundary is REPORTS-specific content or downstream workflow
  behavior.
- The autonomy path also proved something practical: a controller-timeout-shaped
  wait can still recover a valid exported bundle if the pullback runs after the
  remote export finishes.

## Recovery nuance

- The wrapper completed through `recovered_after_timeout`.
- The remote execution manifest reports `export_status = succeeded` and
  `terminal_reason = current_task_incomplete`.
- The roundtrip manifest shows the bundle was pulled at
  `2026-03-28T23:31:28Z`.

## Residual risk

This checkpoint reused an already-live authenticated web session instead of
capturing the REPORTS minute from a fresh login.

## Current judgment

Treat this as real content progress under `deepen_dependency_aware_playbooks`.

The next small slice should move to another support-useful later-content branch
or adjacent decision checkpoint, not re-prove REPORTS again unless a fresh-login
variant becomes specifically important.
