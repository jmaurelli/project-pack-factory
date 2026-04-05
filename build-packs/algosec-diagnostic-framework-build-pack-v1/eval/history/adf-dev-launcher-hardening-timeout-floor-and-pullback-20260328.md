# ADF `adf-dev` Launcher Hardening Timeout Floor And Pullback - 2026-03-28

## What Changed

- `tools/run_remote_autonomy_loop.py` now treats the main remote execution wait
  as its own bounded control-plane setting.
- The remote execution path now defaults to a 900-second controller wait when
  no explicit execution timeout is set.
- `PACKFACTORY_REMOTE_EXECUTION_TIMEOUT_SECONDS` is now the reviewed override
  for the main remote run.
- Remote execution now fails closed when a caller forces the controller wait
  below 600 seconds.
- `tools/run_remote_autonomy_test.py` and
  `tools/run_remote_active_task_continuity_test.py` now do one short delayed
  pullback attempt after a controller-timeout-shaped failure so a slow remote
  export can still be recovered through the normal PackFactory path.

## Why This Matters

- The March 28 compare-first diagnosis showed that `adf-dev` evidence-only
  slices can stay on `run_started` for several minutes before they write their
  first checkpoint artifact.
- That made short controller-side waits look like launcher failure even when
  the remote side could still finish and export a usable bundle.
- The new guardrail separates `controller wait policy` from `launcher failure`
  more cleanly and gives the reviewed delayed-pullback rule an actual wrapper
  implementation.

## Fast Proof

- Local syntax check passed for:
  - `tools/run_remote_autonomy_loop.py`
  - `tools/run_remote_autonomy_test.py`
  - `tools/run_remote_active_task_continuity_test.py`
- A fail-closed proof run used:
  - `PACKFACTORY_REMOTE_SSH_TIMEOUT_SECONDS=420`
  - `python3 tools/run_remote_autonomy_loop.py --factory-root /home/orchadmin/project-pack-factory --request-file /home/orchadmin/project-pack-factory/.pack-state/remote-autonomy-requests/adf-dev/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-compare-remote-run-shapes-v1/remote-run-request.json --output json`
- The loop now stops immediately with the reviewed guardrail instead of
  misclassifying the short controller wait as a launcher failure:
  - `ValueError: PACKFACTORY_REMOTE_SSH_TIMEOUT_SECONDS must be at least 600 seconds for remote autonomy execution; unset it or set PACKFACTORY_REMOTE_EXECUTION_TIMEOUT_SECONDS to a value >= 600`

## Current Judgment

This is a real launcher-hardening checkpoint, not final completion proof.

What is now better:

- short controller waits no longer silently cut off `adf-dev` evidence slices
  without an explicit fail-closed signal
- the wrapper path now has the one delayed pullback retry that the ADF testing
  workflow already recommended

What still needs proof:

- one real `adf-dev` launcher-hardening proof run should confirm that the
  wrapper-level delayed pullback actually recovers a slow remote run or at
  least preserves a clearer stopped boundary than the earlier
  `run_started`-only shape
