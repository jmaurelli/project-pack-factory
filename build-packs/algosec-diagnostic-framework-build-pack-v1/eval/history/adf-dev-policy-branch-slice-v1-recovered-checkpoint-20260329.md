# ADF `adf-dev` Policy Branch Slice V1 Recovered Checkpoint - 2026-03-29

## Summary

The first bounded `POLICY` branch slice returned a real later-content checkpoint
after the controller wait timed out and the late pullback recovered the bundle.

## What the recovered checkpoint proved

- The preserved minute is `2026-03-28 20:02 EDT`.
- The same preserved session served `/afa/php/home.php?segment=DEVICES` with
  `200`.
- One second later, `POST /afa/php/commands.php?cmd=GET_POLICY_TAB` returned
  `200`.
- The response body included device-policy clues such as:
  - `rule_iframe_src=...PolicyTabIframe.php?...`
  - `policy=10_2_2_160_benedum_admin_fw_01_vsys1_benedum_admin_fw.panorama`
  - `device=200132`
  - `total_rules=82`

## Why this matters

- This session is no longer a top-level `GUI down` case.
- We now have later-content branch proof for both `REPORTS` and `POLICY`.
- That gives the playbook a stronger support rule: once the device shell can
  open these branch-specific surfaces, support should pivot into the narrower
  workflow instead of staying in first-shell diagnosis.

## Recovery nuance

- The wrapper completed through `recovered_after_timeout`.
- The remote execution manifest reports `export_status = succeeded` and
  `terminal_reason = current_task_incomplete`.
- The roundtrip manifest shows the bundle was pulled at
  `2026-03-29T00:05:00Z`.

## Residual risk

This checkpoint reused a preserved authenticated session and observed the PHP
session owner as `FireFlow_batch`, so it proves the branch boundary but not a
fresh-login `POLICY` minute.

## Current judgment

Treat this as real content progress under `deepen_dependency_aware_playbooks`.

The next best small slice is `CHANGES`, because `REPORTS` and `POLICY` are now
both preserved as later-content branch proofs and `GET_MONITORING_CHANGES` is
the next clean marker in the same operator-facing family.
