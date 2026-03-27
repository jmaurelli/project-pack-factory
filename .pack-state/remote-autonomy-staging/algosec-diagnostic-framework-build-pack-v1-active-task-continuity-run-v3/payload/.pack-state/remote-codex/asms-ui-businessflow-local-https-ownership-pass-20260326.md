# ASMS UI BusinessFlow Local HTTPS Ownership Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- The BusinessFlow `AFF connection` deep-health check resolves through
  `https://localhost/FireFlow/api/session`.
- Apache owns that local HTTPS route first on `443`.
- Apache immediately proxies that route through `/etc/httpd/conf.d/aff.conf` to
  `http://localhost:1989/aff/api/external/session`.
- The direct `1989` request returns the same session JSON as the Apache-fronted
  HTTPS request.
- The route does not pass through Keycloak `8443` first.

## AFA Side

- The BusinessFlow `AFA connection` check is still best understood as a local
  HTTPS AFA session-liveness surface.
- The strongest current read is still Apache-owned `/afa/...` family traffic
  toward Metro-backed handling.
- The exact preserved AFA path string is still unresolved in the current
  accessible notes, so that part stays inference rather than a direct quoted
  ownership proof.

## Current Working Rule

For the BusinessFlow seam behind `ASMS UI is down`:

- `AFF connection` now has a concrete local HTTPS ownership map:
  Apache `443` -> `aff-boot` `1989`.
- `AFA connection` stays one step less reduced:
  most likely Apache `443` -> AFA `/afa/...` route family -> Metro-backed
  handling.
- This keeps the next support-relevant seams closer to Apache route ownership
  and local application surfaces than to generic port-open checks.

## Best Next Seam

If BusinessFlow needs one more reduction step, the best next seam is:

- exact local HTTPS ownership for the AFA SOAP/session-liveness path
- then same-minute Apache and Metro correlation for that specific AFA request
