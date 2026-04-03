# ADF Successor First Distributed Role-Separated Proof Review v1

## Purpose

Record the first honest distributed-lab proof for the successor after the
standalone calibration set.

This review stays bounded. It compares two imported node-local proofs from one
deliberately distributed lab shape:

- primary CM node `10.167.2.150`
- attached remote-agent node `10.167.2.153`

Both proofs were captured from `adf-dev` through the same bounded remote-owned
runtime flow and imported back into PackFactory as canonical evidence.

## Evidence

- `eval/history/import-external-runtime-evidence-20260403t172733z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- `eval/history/import-external-runtime-evidence-20260403t172516z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- `docs/remote-targets/algosec-lab-cm-150-distributed/target-connection-profile.json`
- `docs/remote-targets/algosec-remote-agent-153/target-connection-profile.json`

## Lab Shape

The first reviewed distributed architecture is:

- `standalone + remote agent`

Current node mapping:

- `10.167.2.150` is the primary CM-style node
- `10.167.2.153` is the attached remote-agent-style node
- both nodes are currently on the same upgraded package line:
  `algosec-appliance-3300.10.260-34`, `fa-3300.10.260-80`,
  `fireflow-3300.10.260-80`, `fa-platform-3300.10.260-80`

That version match matters because the role differences below are much less
likely to be just patch-train drift.

## Shared Runtime Families

The imported proofs keep several families clearly shared across both nodes:

- `httpd`
- `ms-metro`
- `algosec-ms`
- `activemq`
- bounded AWS and Azure provider-driver surfaces

That means the successor is no longer comparing unrelated standalone boxes
only. It has its first repeated multi-node runtime base inside one distributed
lab shape.

## CM-Side Signals

The CM-side proof on `10.167.2.150` retained the stronger control-plane and
session-facing signals:

- `aff-boot` on local `1989`
- Apache `aff.conf` routes for `/FireFlow/api` and `/aff/api`
- bounded AFF session parity
- `ms-bflow` route ownership through `/BusinessFlow`
- `keycloak` identity-side surface

In plain language, the CM node still looks like the place where the stronger
FireFlow, BusinessFlow, and identity-facing control paths live.

## Remote-Agent-Side Signals

The remote-agent proof on `10.167.2.153` retained a thinner management and
provider-facing shape:

- `ms-configuration`
- `ms-devicemanager`
- `ms-genericdevice`
- `ms-devicedriver-aws`
- `ms-devicedriver-azure`

It did not retain the stronger CM-side packets around:

- `aff-boot`
- `keycloak`
- AFF boundary or session parity

The RA node still exposes `httpd`, `ms-metro`, `algosec-ms`, and `activemq`,
but the imported readout is noticeably more provider-driver and
management-service heavy.

## What The Successor Can Now Say Honestly

The successor can now say all of the following without overreaching:

- the first distributed architecture has real role-separated imported proof
- the CM and remote-agent nodes share a meaningful core runtime base
- the CM side retains stronger AFF, FireFlow, BusinessFlow, and identity-facing
  signals
- the remote-agent side retains a thinner configuration, device-management, and
  provider-driver shape
- the current evidence supports a thin cross-node envelope

## What It Still Does Not Say

This proof still does not justify:

- a full suite-wide dependency graph
- complete east-west request flow order
- cluster membership or failover behavior
- provider health or remote API correctness
- a total product-behavior model

Those remain later-phase expansions.

## Why This Matters

This is the first point where the successor can widen from repeated node-local
maps into a bounded multi-node picture without inventing topology.

The next step is therefore no longer "find another node." The next honest step
is to activate a thin topology surface that distinguishes:

- node-local role signals
- shared runtime families
- cross-node similarity
- unresolved links

## Next Step

Activate `activate_multi_node_topology_map`.
