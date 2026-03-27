# ASMS UI BusinessFlow AFF Session Seam Validation 2026-03-27

## Scope

Validate the sibling `BusinessFlow -> AFF connection` seam through the current
split-host helper path:

- PackFactory root stages the pack on `adf-dev`
- the staged ADF runtime on `adf-dev` uses the pack-local target helpers
- the downstream target remains `algosec-lab` on `10.167.2.150`

This note preserves bounded live evidence only. It does not claim a full
FireFlow workflow or ticket-progression proof.

## Command Path

The live checks used the existing staged pack on `adf-dev` with:

- `target-preflight`
- `target-heartbeat`
- `target-shell-command`

The remote control-plane request remained:

- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`

The downstream connection profile remained:

- `docs/remote-targets/algosec-lab/target-connection-profile.json`

## What Was Checked

1. `target-preflight`
   Result: pass

2. `target-heartbeat`
   Result: pass

3. `target-shell-command`
   Command shape:
   `systemctl is-active httpd.service ms-bflow.service aff-boot.service`
   Result:
   all three services returned `active`

4. `target-shell-command`
   Command shape:
   `curl -k -sS -D - https://localhost/FireFlow/api/session`
   and
   `curl -sS -D - http://localhost:1989/aff/api/external/session`
   Result:
   both paths returned `HTTP/1.1 200` and the same invalid-session JSON body:
   `{"valid":false,"message":{"code":"INVALID_SESSION_KEY","message":"The session key provided is invalid"}}`

5. `target-shell-command`
   Command shape:
   `curl -k -sS https://127.0.0.1/BusinessFlow/deep_health_check`
   Result:
   overall `status:true` with `Postgres connection`, `AFA connection`, and
   `AFF connection` all true

6. `target-shell-command`
   Command shape:
   `grep -E '/FireFlow/api/session|/FireFlow/api/session/validate|extendSession' /var/log/httpd/ssl_access_log`
   plus
   `grep -E 'UserSession::getUserSession|isUserSessionValid|Using existing FASessionId|ff-session:' /usr/share/fireflow/var/log/fireflow.log*`
   Result:
   Apache showed current `/FireFlow/api/session` activity on `2026-03-27
   06:15-06:16 EDT`, and retained FireFlow logs showed the closer backend seam
   as `UserSession::getUserSession`, `isUserSessionValid`, `ff-session`, and
   `Using existing FASessionId`

## What Became Clear

- The current `BusinessFlow -> AFF connection` seam is healthy on the active
  lab through the bounded `adf-dev -> algosec-lab` helper path.
- The local HTTPS AFF path is still correctly reduced to:
  Apache `443` -> `aff-boot` `1989` -> `/aff/api/external/session`
- The next readable stop behind that route is now support-useful:
  FireFlow `UserSession` validation or lookup plus the reused FA session id
- The backend log proof here is retained FireFlow evidence, not the same-minute
  pair for the helper probe, so treat it as seam identification rather than as
  a same-minute workflow correlation

## Practical Rule

For the generated ASMS auth-handoff playbook:

- if `https://localhost/FireFlow/api/session` and
  `http://localhost:1989/aff/api/external/session` disagree, stop at the
  Apache-to-`aff-boot` route seam
- if those two paths agree but the AFF side still looks unhealthy, the next
  named stop should be the FireFlow `UserSession` bridge rather than generic
  FireFlow, Keycloak, or ActiveMQ
