# ASMS UI keycloak and Metro service-fault simulation attempt - 2026-03-30

## Purpose

Run bounded lab simulations to compare the current `ASMS UI is down` playbook
against real service behavior for:

- `httpd`
- `keycloak`
- `ms-metro`

This note preserves the `keycloak` and `ms-metro` attempt from March 29, 2026
through the official ADF target helper path.

## Helper Path

- PackFactory root
- ADF build-pack local helper commands
- target profile: `algosec-lab`
- target host: `10.167.2.150`

## Clean Baseline Before The Attempt

Observed around `2026-03-29 19:59:50 EDT`:

- `systemctl is-active httpd keycloak ms-metro` returned `active`, `active`,
  `active`
- `curl -k -I https://127.0.0.1/algosec-ui/login` returned `HTTP/1.1 200 OK`
- `curl -k -o /dev/null -w '%{http_code}\n' https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration`
  returned `200`
- `curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10` returned
  `"isAlive" : true`

## Attempt Shape

The operator question was:

- if `ms-metro` is disabled, does Apache still load the page
- if `keycloak` is disabled, does Apache still load the page and where should
  support stop

The first mutation attempt overlapped the `ms-metro` and `keycloak` service
stops, so it does not count as a clean isolated proof for Metro-only behavior.

## Observed Degraded State After Recovery Attempt

Observed around `2026-03-29 20:02-20:03 EDT` after a clean restart of
`keycloak.service` and `ms-metro.service`:

- `httpd.service` remained `active`
- `keycloak.service` became `failed`
- `ms-metro.service` returned to `active`
- listeners remained present on `80`, `443`, and `8080`
- `curl -k -I https://127.0.0.1/algosec-ui/login` still returned
  `HTTP/1.1 200 OK`
- `curl -k -o /dev/null -w '%{http_code}\n' https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration`
  returned `503`
- `curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10` timed out
- `systemctl status keycloak` showed `failed (Result: exit-code)`
- recent Keycloak output included `java.io.EOFException`

## What This Proves

### Proven tonight

- Apache can keep serving the login page even while auth is unhealthy.
- A broken `keycloak` state does not automatically become an Apache or top-level
  UI-edge outage.
- The current playbook stop rule matches that behavior:
  - keep Apache as the first stop only when the login page itself fails
  - stop on `keycloak.service` when the login page still loads but auth looks
    down

### Not cleanly proven tonight

- The Metro-only service-down behavior was not isolated cleanly because the
  first mutation pass overlapped with `keycloak` work and the post-recovery
  state remained degraded.
- The current observed `ms-metro` heartbeat timeout is useful evidence of an
  unhealthy app-side state, but it is not a clean mutation-backed proof of
  Metro-only failure.

## Playbook Match

The current playbook matches the cleanest observed behavior from this attempt:

- Apache or login-page failure should stop at `httpd`
- login page still healthy plus auth failure should stop at `keycloak`
- blank or partly usable shell plus Metro heartbeat trouble should stop on the
  Metro-backed shell path

Relevant playbook references:

- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`

## Operational Next Step

Do not treat the Metro-only scenario as closed from this note.

The next valid proof step is:

- restore a fully healthy baseline first
- run `ms-metro` stop and restore in isolation
- confirm whether Apache still serves the login page, whether auth stays up,
  and whether the failure moves to the shell or app-side path exactly where the
  playbook says it should
