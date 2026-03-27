# ASMS UI BusinessFlow AFA SOAP Path Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- The BusinessFlow `AFA connection` deep-health check does not use
  `/afa/php/commands.php`.
- It resolves through the AFA SOAP endpoint:
  `https://localhost/afa/php/ws.php`
- The call type is SOAP `isSessionAlive`, not REST.
- `/afa/php/ws.php` is reached through Apache on `443`, but it is not an Apache
  proxy family. Apache serves the local PHP endpoint and the PHP SOAP service
  handles the request on-box.
- `/afa/php/commands.php` remains a real UI command-dispatcher path, but it is
  not the deep-health liveness path for BusinessFlow.

## Current Working Rule

For the BusinessFlow seam behind `ASMS UI is down`:

- `AFA connection` is now reduced to:
  Apache `443` -> local PHP SOAP endpoint `/afa/php/ws.php`
- `AFF connection` is now reduced to:
  Apache `443` -> `aff-boot` `1989` via `/FireFlow/api/session`
- That makes the BusinessFlow deep-health seam much more concrete for support:
  one SOAP PHP endpoint and one Apache-to-aff-boot REST session path, both
  behind Postgres.

## Best Next Seam

The next best BusinessFlow reduction is no longer “what endpoint does it hit?”
That part is now good enough.

The next seam is:

- same-minute request correlation for `/afa/php/ws.php`
- then the nearest PHP-side runtime surfaces behind that SOAP request
