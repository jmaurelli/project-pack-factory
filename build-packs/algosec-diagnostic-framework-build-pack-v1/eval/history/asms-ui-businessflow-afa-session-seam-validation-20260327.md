# ASMS UI BusinessFlow AFA Session Seam Validation 2026-03-27

## Purpose

Record one bounded live validation pass for the `BusinessFlow -> AFA connection`
seam after the local playbook update narrowed the next stop to:

- Apache `443`
- local PHP SOAP `/afa/php/ws.php`
- `/data/public_html/algosec/.ht-fa-history`
- PHP session backing files and `.ht-LastActionTime`

## Control Path

This pass used the current split-host ADF path:

- PackFactory root prepared and staged the build pack to `adf-dev`
- the staged build pack on `adf-dev` used the pack-local target helper commands
- the downstream target stayed the active profile `algosec-lab` at `10.167.2.150`

Relevant surfaces:

- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `docs/remote-targets/algosec-lab/target-connection-profile.json`
- `.pack-state/remote-autonomy-staging/algosec-diagnostic-framework-build-pack-v1-split-host-smoke-run-v1/target-manifest.json`

## Bounded Checks

1. `target-preflight`
   Result: pass
   Meaning: the non-login shell launcher on `adf-dev -> 10.167.2.150` still works.

2. `target-heartbeat`
   Result: pass
   Meaning: the active downstream target remained reachable through the bounded helper path.

3. `target-shell-command`
   Command shape:
   `systemctl is-active httpd.service ms-bflow.service`
   Result: both services returned `active`

4. `target-shell-command`
   Command shape:
   `curl -k -sS -D - -o /tmp/adf-wsdl.body https://localhost/afa/php/ws.php?wsdl`
   Result: `HTTP/1.1 200 OK` and WSDL XML content

5. `target-shell-command`
   Command shape:
   `curl -k -sS https://127.0.0.1/BusinessFlow/deep_health_check`
   Result: overall `status:true` with `Postgres connection`, `AFA connection`, and `AFF connection` all true

6. `target-shell-command`
   Command shape:
   `grep -n -E 'SOAP Web Service call|is_session_alive|SESSION:' /data/public_html/algosec/.ht-fa-history | tail -n 8`
   Result: fresh `SOAP Web Service call` and `is_session_alive - AlgosecSession is still active` lines with live session ids at `2026-03-27 06:03:43`

## What Became Clear

- The current `BusinessFlow -> AFA connection` seam is healthy on the active lab.
- `httpd.service` and `ms-bflow.service` are both active on `10.167.2.150`.
- The AFA WSDL path is healthy when checked with the same GET-style request the playbook uses.
- BusinessFlow deep health currently agrees that `AFA connection` is healthy.
- `.ht-fa-history` still provides the expected first readable seam behind `ws.php`, including live session ids and `is_session_alive` evidence.

## Important Nuance

- A shortcut `curl -I https://localhost/afa/php/ws.php?wsdl` returned `HTTP/1.1 500 Internal Server Error`.
- The actual playbook command uses a normal GET and returned `HTTP/1.1 200 OK` with valid WSDL XML.
- For this seam, treat GET as the supported probe and do not over-read a HEAD-only failure.

## Current Reading

This validation does not prove the `BusinessFlow -> AFA connection` seam is the
current failure point on the active lab. It proves the opposite: the seam is
healthy enough that the playbook should help an engineer stop cleanly when it is
healthy and move on to the next named branch instead of leaving the stop point
vague.

That makes the sibling `BusinessFlow -> AFF connection` seam the stronger next
live reduction target if the next cycle stays on the same dependency-aware
playbook task.
