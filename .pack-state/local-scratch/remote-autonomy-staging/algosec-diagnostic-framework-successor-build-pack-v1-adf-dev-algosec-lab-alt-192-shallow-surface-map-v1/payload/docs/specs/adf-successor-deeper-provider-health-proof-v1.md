# ADF Successor Deeper Provider Health Proof v1

## Purpose

Record the first explicit widening step after the bounded successor frontier was
closed: a deeper provider-health pass for the already-visible AWS and Azure
driver families on the distributed CM-plus-remote-agent lab.

This pass stays fail-closed. It does not claim provider API success, credential
correctness, sync freshness, or cloud-side health. It only sharpens the current
node-local provider packet from broad placement into bounded local
reachability-or-degradation evidence.

## Evidence Base

- `src/algosec_diagnostic_framework_successor_template_pack/shallow_surface_map.py`
- `eval/history/import-external-runtime-evidence-20260403t181007z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t181007z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t181044z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t181044z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `docs/specs/adf-successor-health-validated-integration-model-v1.md`

## What Changed

The successor now extends the existing provider packet with two bounded local
checks per visible provider-driver family:

- recent bounded journal inspection for the provider service unit
- short localhost loopback TCP-connect probing on the observed backend port

That keeps the health model local and evidence-first:

- `configured` still means the route family, service unit, listener, or jar is
  present
- `reachable` would require a successful local loopback probe
- `degraded` is now allowed when the local listener is not reachable or recent
  strong failure markers are visible in the service journal
- `healthy` is still not used for AWS or Azure from this local-only proof

## Current Readout

### CM `10.167.2.150`

- `AWS` via `ms-devicedriver-aws` is now `degraded`
- `Azure` via `ms-devicedriver-azure` is now `degraded`

Why:

- neither observed provider-driver listener passed the bounded localhost
  loopback probe
- both driver journals retained repeated runtime-failure markers centered on
  `NumberFormatException` and failed `logback` property-setting for
  `logging.file.maxHistory_IS_UNDEFINED`

### Remote Agent `10.167.2.153`

- `AWS` via `ms-devicedriver-aws` is now `degraded`
- `Azure` via `ms-devicedriver-azure` is now `degraded`

Why:

- neither observed provider-driver listener passed the bounded localhost
  loopback probe
- both driver journals retained the same repeated runtime-failure pattern seen
  on the CM-side node

## Why It Matters

This is stronger than the earlier `configured`-only readout.

The successor can now say:

- the AWS and Azure driver families are not just present on both nodes
- the current local proof shows consistent node-local degradation signals on
  both nodes
- that still does not mean the cloud providers themselves are down or that the
  credentials are wrong

In plain language, the successor has crossed from "the provider-driver surfaces
exist" into "the provider-driver runtime itself is presently showing local
trouble on both nodes."

## Boundaries

This proof still does not justify:

- provider API success or failure claims
- credential-validity claims
- cross-node directionality claims
- sync-freshness claims
- claims that `algosec-ms` or another shared family is definitively the
  provider-call orchestrator

## Next Stop

The next honest seam is `strengthen_cross_node_directionality_proof`.

Now that the same degraded provider-driver pattern appears on both nodes, the
remaining useful ambiguity is not whether provider trouble exists locally. It
is how provider-facing work is actually divided across the CM and remote-agent
roles, and whether the successor can prove any stable directionality without
inventing unseen cross-node links.
