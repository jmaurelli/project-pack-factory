# ADF Successor Health-Validated Integration Model v1

## Purpose

Record the first bounded integration-health surface for the successor after the
topology and dependency layers became available.

This model stays fail-closed. It uses only the current imported proof base and
classifies visible integration families into:

- `healthy`
- `reachable`
- `configured`
- `degraded`
- `uncertain`

If the evidence does not justify a stronger state, this artifact leaves the
claim weaker on purpose.

## Evidence Base

- `docs/specs/adf-successor-bounded-dependency-graph-v1.md`
- `eval/history/import-external-runtime-evidence-20260403t172733z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t181007z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t181007z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t181044z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t181044z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t110310z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t105216z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t105216z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`

## Health Scale

### Healthy

Use only when the current proof shows more than local presence and includes a
bounded positive health or parity result.

### Reachable

Use when the current proof shows a working path or carried request surface, but
not enough to say the underlying integration is broadly healthy.

### Configured

Use when the current proof shows local config, service, listener, route, or
runtime placement, but does not prove successful interaction health.

### Degraded

Use only when the current proof shows the integration family should be working
but is currently failing or clearly unhealthy.

### Uncertain

Use when the current proof is too thin, role-dependent, or ambiguous to
classify more strongly.

## Current Integration Classifications

### 1. AFF Session Boundary On CM `10.167.2.150`

State:

- `healthy`

Why:

- Apache `/FireFlow/api/session` and direct local
  `http://localhost:1989/aff/api/external/session` returned the same bounded
  response
- both probes returned HTTP `200`
- both probes agreed on `INVALID_SESSION_KEY`
- BusinessFlow deep health also retained `AFF connection = true`
- `httpd`, `ms-bflow`, and `aff-boot` all reported active in the same packet

Boundary:

- this is bounded AFF edge health, not proof of a complete logged-in FireFlow
  workflow

### 2. AFA Or Metro Bridge Surface On CM `10.167.2.150`

State:

- `reachable`

Why:

- FireFlow session token carry-forward is visible through
  `/afa/external//bridge/storeFireflowCookie`
- the same token family later appears on `/afa/external//session/extend`
- `/afa/external` and `/afa/api/v1` are route-hinted to `ms-metro` on `8080`

Boundary:

- the bridge is clearly live enough to carry a bounded session handoff
- this still does not prove full AFA-side business health or user-visible
  success

### 3. AWS Driver Family On CM `10.167.2.150`

State:

- `degraded`

Why:

- Apache family `ms-devicedriver-aws` routes to local `8104`
- `ms-devicedriver-aws.service` is visible
- the local runtime jar is visible
- a bounded journal entrypoint is available
- the bounded localhost probe did not reach the local `8104` listener
- the bounded journal window retained repeated runtime-failure markers around
  `NumberFormatException` and failed `logback` property-setting for
  `logging.file.maxHistory_IS_UNDEFINED`

Boundary:

- this is local driver-runtime degradation evidence, not proof of an AWS-side
  outage
- the proof explicitly does not show external API success, credential validity,
  sync freshness, or provider-side health

### 4. Azure Driver Family On CM `10.167.2.150`

State:

- `degraded`

Why:

- Apache family `ms-devicedriver-azure` routes to local `8113`
- `ms-devicedriver-azure.service` is visible
- the local runtime jar is visible
- a bounded journal entrypoint is available
- the bounded localhost probe did not reach the local `8113` listener
- the bounded journal window retained repeated runtime-failure markers around
  `NumberFormatException` and failed `logback` property-setting for
  `logging.file.maxHistory_IS_UNDEFINED`

Boundary:

- this is local driver-runtime degradation evidence, not proof of an
  Azure-side outage
- the proof explicitly does not show external API success, credential validity,
  sync freshness, or provider-side health

### 5. AWS Driver Family On Remote Agent `10.167.2.153`

State:

- `degraded`

Why:

- Apache family `ms-devicedriver-aws` routes to local `8143`
- `ms-devicedriver-aws.service` is visible on the RA node
- the local runtime jar is visible
- the same driver family repeats across both distributed nodes
- the bounded localhost probe did not reach the local `8143` listener
- the bounded journal window retained the same repeated runtime-failure pattern
  seen on the CM node

Boundary:

- repeated presence across nodes now pairs with repeated local degradation
  signals
- it still does not prove successful AWS-side communication or root cause

### 6. Azure Driver Family On Remote Agent `10.167.2.153`

State:

- `degraded`

Why:

- Apache family `ms-devicedriver-azure` routes to local `8086`
- `ms-devicedriver-azure.service` is visible on the RA node
- the local runtime jar is visible
- the same driver family repeats across both distributed nodes
- the bounded localhost probe did not reach the local `8086` listener
- the bounded journal window retained the same repeated runtime-failure pattern
  seen on the CM node

Boundary:

- repeated presence across nodes now pairs with repeated local degradation
  signals
- it still does not prove successful Azure-side communication or root cause

### 7. Keycloak On CM `10.167.2.150`

State:

- `configured`

Why:

- `keycloak` is visible with ports `8443`, `9000`, and `28897`
- Apache `keycloak.conf` routes `/keycloak/` toward local `8443`
- the service fragment, environment file, and config root are visible

Boundary:

- this proof does not include a successful auth probe
- this proof therefore does not justify `reachable` or `healthy` yet

### 8. Keycloak On Remote Agent `10.167.2.153`

State:

- `uncertain`

Why:

- no matching Keycloak packet or summary surface is retained on the RA proof

Boundary:

- absence in this pass may reflect role separation rather than degradation
- the current proof does not justify a degraded claim

### 9. Cross-Node Provider Integration Health

State:

- `uncertain`

Why:

- both nodes repeat AWS and Azure driver placement
- both nodes now also repeat bounded local degradation signals for those same
  driver families
- the proof still lacks provider-side success, sync, credential, or freshness
  signals
- the proof also lacks cross-node directionality

Boundary:

- this model can now say the provider families are distributed and locally
  degraded on both nodes
- it still cannot say they are healthy end to end

## Explicit Non-Claims

The current model does not claim:

- AWS health
- Azure health
- Keycloak auth success
- full FireFlow workflow health
- cross-node failover or replication health
- ActiveMQ service-consumer health
- `ms-metro` or `algosec-ms` internal health beyond local presence and route
  adjacency

## Current Degraded Bucket

The AWS and Azure provider-driver families are now explicitly upgraded to
`degraded` on both the CM and remote-agent nodes.

That is still intentionally fail-closed. The current imported distributed proof
shows node-local driver-runtime degradation, not cloud-provider failure.

## Operator Readout

The successor can now say:

- the AFF session edge on the CM node is healthy at the current bounded
  boundary
- the AFA-facing Metro bridge is reachable
- AWS and Azure driver families are now locally degraded on both the CM and
  the remote agent
- Keycloak is configured on the CM node but not yet health-validated
- provider-side success and cross-node integration directionality remain
  uncertain

## Next Step

Advance to `strengthen_cross_node_directionality_proof` and test whether the
same degraded provider-driver pattern on both nodes can be tied to any honest
cross-node role split, orchestration direction, or shared upstream dependency
without flattening the remaining uncertainty.
