# ASMS UI AFA Local Ownership Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- `/afa/php/...` is not an Apache proxy family on this appliance.
- Apache owns `/afa` first through a local alias, then executes local PHP from
  `/usr/share/fa/php`.
- The local PHP layer then fans out internally, including direct calls to Metro
  at `127.0.0.1:8080`.
- The strongest proven AFA family on the appliance is:
  - Apache `443` -> `/afa/external//config/all/noauth?domain=0`
  - Apache `443` -> `/afa/api/v1/config/all/noauth?domain=0`
  - both proxying to Metro `8080`
- Those proven `/afa` requests did not cross Keycloak `8443` first.

## What Is Still One Step Ambiguous

- The exact single endpoint used by the BusinessFlow `AFA connection`
  session-liveness call is still not directly preserved in the current
  read-only evidence.
- The strongest current read is still:
  local `https://localhost` AFA SOAP or session-liveness family,
  with the provable Apache-owned `/afa/external` and `/afa/api/v1` config
  family reducing the seam most clearly.

## Current Working Rule

For the AFA side behind `ASMS UI is down`:

- Do not treat `/afa/php/...` as if Apache proxies it somewhere else. Apache
  receives it and local PHP executes it.
- For Apache-owned browser-facing AFA routes, the strongest proven family is
  `/afa/external` and `/afa/api/v1`, both toward Metro `8080`.
- Keep the exact BusinessFlow `AFA connection` endpoint slightly cautious until
  a future runtime trace pins it more precisely.

## Best Next Seam

If the AFA side needs one more reduction step, the next best seam is:

- one runtime trace or same-minute correlation that captures the exact AFA
  session-liveness request BusinessFlow emits
- then tie that request to either the local PHP family or the Metro-backed
  Apache proxy family with the same quality of evidence as the AFF side
