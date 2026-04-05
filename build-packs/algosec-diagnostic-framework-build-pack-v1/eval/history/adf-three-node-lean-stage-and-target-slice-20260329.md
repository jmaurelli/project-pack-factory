# ADF Three-Node Lean Stage And Target Slice

Date: 2026-03-29

## Summary

This run proved the current three-node split in a small grounded way:

1. Local Pack Factory staged a lean ADF payload to `adf-dev`
2. `adf-dev` ran bounded target helpers against the target lab
3. Local Pack Factory remained the canonical control plane

## Lean Stage Proof

Latest staged payload under the reviewed policy:

- payload policy: `fresh-staging/v2`
- transport: `rsync`
- staged entries: `227`
- staged size: `2,546,911` bytes
- staged size: about `2.43 MiB`

This confirms the remote stage no longer behaves like a near-full local mirror.

## Target Slice Proof

From the staged ADF pack on `adf-dev`, the following bounded target-lab helper
commands passed against `algosec-lab` (`10.167.2.150`):

- `target-preflight`
- `target-heartbeat`
- `target-shell-command --command "hostname && uptime"`

Observed result:

- `adf-dev` reached the target lab with the non-login bash pattern
- the target shell returned the expected sentinel for preflight
- the target heartbeat returned the expected sentinel
- the target shell command returned:
  - hostname: `algosec`
  - uptime line showing the appliance was reachable and active

## Control Plane Fix

The lean restage also exposed one PackFactory control-plane bug:

- `push_build_pack_to_remote.py` created the remote pack root, run dir, and
  export dir, but not `.packfactory-remote`
- that caused the final manifest SCP step to fail even when the payload swap
  itself succeeded

This was fixed by creating `remote_pack_dir/.packfactory-remote` during the
remote payload swap.

## Meaning

The proof is intentionally small, but it is useful:

- Local Pack Factory can now send PackFactory-essential ADF inputs instead of a
  heavy local snapshot
- `adf-dev` can still act as the remote worker
- the target lab remains a separate runtime evidence node
- the three-node model is now validated at the stage-and-target-helper level

## Next Step

Use the same three-node split for one bounded real ADF task slice, not just
target helper commands:

- lean stage from Local Pack Factory to `adf-dev`
- one bounded `adf-dev -> target` evidence slice
- pull back only checkpoint and evidence artifacts
