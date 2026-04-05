# ADF Successor First DR Primary-Secondary Proof Review v1

## Purpose

Record the first clean imported disaster-recovery proof pair before stacking
additional roles onto the DR architecture.

## Reviewed Nodes

- primary CM node: `10.167.2.150`
- secondary DR node: `10.167.2.153`
- both rebuilt on the same upgraded `A33.10.260` line

Canonical imported proof:

- primary import:
  `eval/history/import-external-runtime-evidence-20260403t225431z/import-report.json`
- secondary import:
  `eval/history/import-external-runtime-evidence-20260403t225328z/import-report.json`

## What The Current Proof Supports

- `10.167.2.150` currently behaves like the active CM-facing side.
- `10.167.2.153` currently behaves like the colder standby DR side.
- the primary keeps the stronger AFF, FireFlow, BusinessFlow, and identity
  packets.
- the secondary keeps route and Apache-family hints but loses the deeper AFF
  ownership and session-parity proof.
- both sides still retain bounded AWS and Azure provider-driver surfaces, but
  provider-side success remains unproven.

## Primary Signals On `10.167.2.150`

- `/FireFlow/api` and `/aff/api` still land on `aff-boot` over local port
  `1989`
- `aff_fireflow_1989_route_owner` is present
- `aff_session_route_parity` is present and `parity_confirmed`
- `keycloak`, `ms-bflow`, `ms-metro`, `algosec-ms`, and `activemq` remain
  visible
- the provider packet keeps bounded coordination clues for `algosec-ms`,
  `ms-configuration`, and `ms-devicemanager`

## Secondary Signals On `10.167.2.153`

- Apache route hints still point at the local AFF path shape
- no bounded AFF route-owner packet survives
- no AFF session-parity packet survives
- `ms-hadr` and `logstash` are visible
- `activemq`, `ms-bflow`, and `ms-metro` are failed in the bounded pass
- the provider packet remains local-only and does not surface the same
  coordination clues

## Why This Matters

This is a cleaner active-versus-standby split than the earlier `standalone +
LDU` proof because the current pair differs in retained control-plane depth,
not just in edge or provider-heavy role shape. The successor can now
distinguish:

- an active CM-like DR primary
- a colder standby-style DR secondary
- the difference between route persistence and deeper runtime ownership

That gives the pack a real DR baseline before any later DR-plus-LDU stacking.

## Boundaries

The current proof does not justify these claims:

- full replication topology
- successful failover behavior
- exact DR synchronization freshness
- provider-side cloud success
- complete east-west orchestration

## Next Recommended Step

Use this DR-only proof as the baseline, then capture:

- `capture_disaster_recovery_plus_ldu_role_separated_node_proofs`

That next step should explain what changes when the LDU layer is added to the
current DR architecture instead of rewriting the DR-only readout.
