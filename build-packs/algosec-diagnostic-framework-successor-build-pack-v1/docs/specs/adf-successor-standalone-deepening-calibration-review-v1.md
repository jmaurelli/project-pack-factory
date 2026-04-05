# ADF Successor Standalone Deepening Calibration Review v1

## Purpose

Record the first `.150`-free standalone deepening pass while the operator keeps
building the next distributed architecture.

This pass intentionally skipped `10.167.2.150` and widened the current
standalone calibration set through the official `adf-dev`-owned roundtrip path.

## Proof Base

The current bounded proof set is:

1. `algosec-lab-alt-192` (`10.167.2.192`)
   `eval/history/import-external-runtime-evidence-20260404t134215z/`
2. `algosec-lab-alt-177` (`10.167.2.177`)
   `eval/history/import-external-runtime-evidence-20260404t134425z/`
3. `algosec-lab-alt-132` (`10.167.2.132`)
   `eval/history/import-external-runtime-evidence-20260404t134927z/`
4. `algosec-lab-alt-213` (`10.167.2.213`)
   `eval/history/import-external-runtime-evidence-20260404t135116z/`

Those four imported bundles are the canonical evidence for this pass.

## What Stayed Stable

Across all four standalone nodes, the successor kept the same bounded runtime
story:

- `/FireFlow/api` and `/aff/api` still land on `aff-boot` over local port
  `1989`
- `aff_session_route_parity` remains `parity_confirmed`
- `keycloak`, `algosec-ms`, `ms-metro`, and `httpd` remain the strongest
  repeated node-local anchors
- AWS and Azure stay at
  `local_provider_health_partially_classified`
- both provider-driver families stay degraded through local-listener failure
  rather than provider-side success or failure claims
- the same adjacent provider-facing families stay visible:
  `ms-aad-azure-sensor`, `ms-aad-log-sensor`, `ms-cloudflow-broker`,
  `ms-cloudlicensing`
- the same fail-closed unknowns remain in force:
  no full dependency order, no cross-node topology activation, and no
  provider-side success claim

In plain language, the successor's standalone capture shape is now portable
across four independent nodes without drifting into topology theory.

## What Drifted

The useful drift is not in the AFF or session spine. It is in version-line
local detail around provider-driver placement and local failure texture.

### Older A33.10 sibling

`10.167.2.192` stays on the thinner older standalone shape:

- `apache_activemq` `6.1.7`
- AWS `8116`
- Azure `8102`
- adjacent provider-facing surfaces on `8107`, `8145`, `8106`
- bounded peer clue `ms-devicemanager peers 10.20.2.169,10.20.2.169`

### A33.20.100

`10.167.2.132` keeps the same stable standalone spine but shifts the provider
surface again:

- `apache_activemq` `6.2.0`
- AWS `8098`
- Azure `8135`
- adjacent provider-facing surfaces on `8133`, `8153`, `8110`
- bounded peer clue `ms-devicemanager peers 10.20.2.169`

### A33.20.120 variant one

`10.167.2.177` keeps the stable standalone spine while adding richer failure
texture:

- `apache_activemq` `6.2.0`
- AWS `8157`
- Azure `8131`
- adjacent provider-facing surfaces on `8169`, `8170`, `8151`
- journal-side `runtime_failure x4` for both provider-driver families
- coordination clue
  `ms-devicemanager peers 10.20.2.169,10.20.209.210 journal polling`

### A33.20.120 variant two

`10.167.2.213` stays on the same broad line as `10.167.2.177` but shows the
strongest local degradation texture in the set:

- `apache_activemq` `6.2.0`
- AWS `8174`
- Azure `8115`
- adjacent provider-facing surfaces on `8149`, `8184`, `8180`
- journal-side `runtime_failure x10` for both provider-driver families
- coordination clue
  `ms-devicemanager peers 10.178.4.231,10.178.4.231 journal polling`

## What This Means

The standalone deepening lane is now validated, not exhausted.

What this pass proves:

- the successor has a real `.150`-free standalone calibration set
- the AFF and session edge remains stable across four independent nodes
- the repeated AWS and Azure degradation pattern is now a cross-node motif,
  not a one-off local accident
- provider coordination clues drift by version line or environment family
  while the core standalone runtime shape stays consistent

What this still does not prove:

- distributed topology
- peer-role ownership
- provider credential validity
- provider-side sync freshness
- cloud-side success

The right next standalone deepening seam is therefore not broader mapping. It
is tighter comparison around `ms-devicedriver-aws`,
`ms-devicedriver-azure`, and `ms-devicemanager` peer and polling behavior.

## Autonomy-Loop Fit

This pass used the official `adf-dev` roundtrip path successfully for all four
standalone imports.

The bounded continuity tools were also checked honestly:

- active-task continuity failed closed because the long-lived pack currently
  has no `active_task_id`
- ready-boundary memory continuity failed closed because the current
  `work-state` autonomy boundary is not `ready_for_deploy`

That is still a useful result. It means the remote roundtrip path is proven
for this lane, while continuity tooling must wait for a tracker state that
actually matches its contract instead of being forced into a fake pass.
