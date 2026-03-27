# ASMS UI AFA SOAP Runtime Correlation Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- Apache proves when `/afa/php/ws.php` was hit, but Apache logs do not carry a
  usable request hash or session id for this seam.
- The nearest support-readable seam behind `ws.php` is
  `/data/public_html/algosec/.ht-fa-history`.
- `.ht-fa-history` records:
  - exact second-level timing
  - a per-request hash
  - the raw `IsSessionAliveRequest` payload
  - the `SESSION / TOKEN / COOKIE` triple
  - the result line from `ws.inc.php::is_session_alive`
- Behind that log seam, the PHP session layer is the next direct check:
  - `/var/lib/php/session/sess_<id>`
  - `/data/public_html/algosec/session-<id>/work/.ht-LastActionTime`

## Current Working Rule

For the BusinessFlow `AFA connection` seam behind `ASMS UI is down`:

- entrypoint:
  Apache `443` -> local PHP SOAP `/afa/php/ws.php`
- first support-readable seam:
  `/data/public_html/algosec/.ht-fa-history`
- next direct seam:
  PHP session file and pulse-file freshness for the same session id

## What This Replaces

- `display_log_data.cmd.php` is not the first useful follow-on seam for
  `ws.php`. It belongs to a later GUI-authenticated device/log-collection path.
- The first useful follow-on seam is now the SOAP request history plus the
  session backing files it references.

## Best Next Seam

If the AFA side needs another reduction step later, the next best seam is:

- same-minute correlation between one `.ht-fa-history` request hash and the
  exact session file / pulse-file state transition for that session id
