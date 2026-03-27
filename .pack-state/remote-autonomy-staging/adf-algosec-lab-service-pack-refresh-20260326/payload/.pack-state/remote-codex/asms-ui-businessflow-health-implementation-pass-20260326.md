# ASMS UI BusinessFlow Health Implementation Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- BusinessFlow deep health is implemented in
  `com.algosec.bflow.service.BflowHealthCheckService`.
- The deep-health order is:
  - Postgres first
  - then `AFA connection`
  - then `AFF connection`
  - then optional CMDB
- `AFA connection` resolves to an AFA session-liveness check through the local
  HTTPS AFA surface, not a raw direct `8080` probe.
- `AFF connection` resolves to a FireFlow session-liveness check through the
  local HTTPS FireFlow surface, not a raw direct `1989` probe.
- Current BusinessFlow client properties point those checks at `localhost`,
  which keeps Apache and the local HTTPS application surfaces in the immediate
  path.

## Current Working Rule

For the BusinessFlow seam behind `ASMS UI is down`:

- Postgres still stays first.
- `AFA connection` and `AFF connection` are not generic service-presence checks.
  They are session-liveness checks against local HTTPS surfaces.
- That keeps the next immediate support seam closer to Apache and the local AFA
  and FireFlow application routes than to raw `8080` or `1989` targets.
- ActiveMQ still does not belong in the immediate BusinessFlow deep-health path
  on current evidence.

## Best Next Seam

If this path needs deeper reduction next, inspect Apache route ownership for:

- the local HTTPS AFA surface used by the AFA SOAP client
- `https://localhost/FireFlow/api/session`

That should tell the next agent whether the closest handoff is Apache itself, a
local Java service on `8443`, or a later proxy hop behind those HTTPS surfaces.
