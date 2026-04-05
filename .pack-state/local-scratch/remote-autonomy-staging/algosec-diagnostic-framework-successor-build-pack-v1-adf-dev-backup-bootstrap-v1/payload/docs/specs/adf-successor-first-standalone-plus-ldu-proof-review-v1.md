# ADF Successor First Standalone Plus LDU Proof Review v1

## Purpose

Record the first honest imported proof for the reviewed `standalone + LDU`
architecture after the earlier `standalone + remote agent` proof.

This review stays bounded. It compares two imported node-local proofs from one
deliberately rebuilt distributed lab shape:

- primary CM node `10.167.2.150`
- attached LDU node `10.167.2.153`

Both proofs were captured from `adf-dev` through the same bounded remote-owned
runtime flow and imported back into PackFactory as canonical evidence.

## Evidence

- `eval/history/import-external-runtime-evidence-20260403t195134z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t195134z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t195134z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- `eval/history/import-external-runtime-evidence-20260403t195039z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t195039z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t195039z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- `docs/remote-targets/algosec-lab-cm-150-distributed/target-connection-profile.json`
- `docs/remote-targets/algosec-ldu-153/target-connection-profile.json`

## Lab Shape

The reviewed distributed architecture is now:

- `standalone + LDU`

Current node mapping:

- `10.167.2.150` is the primary CM-style node
- `10.167.2.153` is the attached LDU-style node
- both nodes are currently on the same upgraded package line:
  `algosec-appliance-3300.10.260-34`, `fa-3300.10.260-80`,
  `fireflow-3300.10.260-80`, `fa-platform-3300.10.260-80`

That version match matters because the role differences below are much less
likely to be only patch-train drift.

## Shared Runtime Families

The imported proofs keep several families clearly shared across both nodes:

- `httpd`
- `ms-metro`
- `algosec-ms`
- `activemq`
- bounded AWS and Azure provider-driver surfaces

That means the LDU is not a paper-thin front door only. It still carries a
meaningful local runtime spine.

## CM-Side Signals

The CM-side proof on `10.167.2.150` retained the stronger control-plane and
session-facing signals:

- `keycloak`
- `aff-boot` on local `1989`
- Apache `aff.conf` routes for `/FireFlow/api` and `/aff/api`
- bounded AFF session parity
- `ms-bflow` route ownership through `/BusinessFlow`

In plain language, the CM node still looks like the place where the stronger
FireFlow, BusinessFlow, AFF, and identity-facing control paths live.

## LDU-Side Signals

The LDU-side proof on `10.167.2.153` retained a thinner edge-heavy and
provider-heavy shape:

- `httpd`
- `ms-metro`
- `algosec-ms`
- `activemq`
- degraded `ms-devicedriver-aws`
- degraded `ms-devicedriver-azure`

It did not retain the stronger CM-side packets around:

- `keycloak`
- `aff-boot`
- AFF boundary or session parity
- `ms-bflow`

That is enough to separate the LDU from the CM without pretending it is a pure
balancer-only host.

## New LDU Coordination Clues

The new imported LDU proof also adds one useful bounded signal that did not
exist in the old remote-agent framing:

- `algosec-ms`, `ms-configuration`, `ms-devicemanager`,
  `ms-devicedriver-aws`, and `ms-devicedriver-azure` retain peer clues back to
  `10.167.2.150:61616`

This is still not a complete east-west map. But it is enough to treat the LDU
side as visibly adjacent to CM-hosted messaging rather than only as a passive
HTTP front.

## What The Successor Can Now Say Honestly

The successor can now say all of the following without overreaching:

- the rebuilt `standalone + LDU` architecture has real imported proof
- the CM and LDU nodes share a meaningful runtime base
- the CM side retains stronger AFF, FireFlow, BusinessFlow, and identity-facing
  signals
- the LDU side retains a thinner edge-heavy and provider-heavy shape
- the LDU side shows bounded messaging adjacency back to CM `10.167.2.150`
  on `61616`

## What It Still Does Not Say

This proof still does not justify:

- a pure "LDU only" claim with no local application runtime
- a full east-west dependency graph
- exact ActiveMQ producer or consumer direction for every service family
- provider success, credential correctness, or sync freshness
- the later stacked `standalone + LDU + remote agent` story

Those remain later-phase expansions.

## Why This Matters

This is the clean first LDU-specific comparison that the reviewed rollout order
called for.

It isolates what changes when LDU is introduced by itself before the remote
agent is bolted back on later. That makes the next stacked architecture easier
to read because the successor already has one bounded CM-vs-LDU baseline.

## Next Step

Activate `capture_stacked_standalone_ldu_remote_agent_role_separated_proof`
after the operator bolts the remote agent back onto this `standalone + LDU`
architecture.
