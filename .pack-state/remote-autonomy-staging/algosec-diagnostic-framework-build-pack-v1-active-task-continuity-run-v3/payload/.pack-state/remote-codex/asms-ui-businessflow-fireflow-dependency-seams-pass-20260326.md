# ASMS UI BusinessFlow / FireFlow Dependency Seams Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

### BusinessFlow on `8081`

- `ms-bflow.service` owns `8081`.
- Apache fronts `/BusinessFlow` to `127.0.0.1:8081/BusinessFlow`.
- BusinessFlow deep health names its closest readable dependencies:
  - `Postgres connection`
  - `AFA connection`
  - `AFF connection`
- Those dependencies are closer for this seam than Keycloak or ActiveMQ.

### FireFlow on `1989`

- `aff-boot.service` owns `1989`.
- Apache fronts `/FireFlow/api` and `/aff/api` to `1989`.
- Readable FireFlow evidence points most strongly to:
  - Apache proxying as the front seam
  - PostgreSQL as the strongest readable backend dependency
  - Metro as a later supporting neighbor
- ActiveMQ did not surface as the closest readable dependency for this seam.

## Current Working Rule

For the backward dependency map behind `ASMS UI is down`:

- BusinessFlow = earlier direct checkpoint
- closest readable dependencies behind BusinessFlow = Postgres, AFA, AFF
- FireFlow = later auth-coupled checkpoint
- closest readable dependencies behind FireFlow = Apache proxying, FireFlow
  backend, database, then Metro
- ActiveMQ = supporting or edge-case dependency unless a broker or JMS tie is
  proven in the live failing path

## Best Next Seams

- inspect how BusinessFlow implements `AFA connection` and `AFF connection`
- inspect whether those calls land directly on `ms-metro` and `aff-boot`
- inspect whether `aff-boot.jar` or nearby runtime evidence proves any broker
  or JMS client behavior before promoting ActiveMQ higher in the ASMS map

