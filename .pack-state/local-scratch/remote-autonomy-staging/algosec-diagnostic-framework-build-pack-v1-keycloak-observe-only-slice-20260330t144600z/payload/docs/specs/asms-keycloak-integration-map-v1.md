# ASMS / Keycloak integration map v1

## Purpose

Capture the current evidence-backed view of how Keycloak integrates into the
ASMS login and auth path on the AlgoSec lab appliance.

## What Keycloak is in this appliance

Keycloak is the auth service used by ASMS in the observed login chain.

What that means in operational terms:

- Apache is still the browser-facing UI edge.
- Keycloak sits behind Apache as the auth branch.
- A Keycloak failure does not automatically mean Apache stops serving the login
  page.

## Proven integration surfaces

### Browser-facing login path

Apache rewrites the suite login route into the current UI login route:

- `/algosec/suite/login...` -> `/algosec-ui/login`

### Apache-to-Keycloak proxy path

Apache proxies `/keycloak/` to local Keycloak on `8443`.

Observed config clue:

- `/etc/httpd/conf.d/keycloak.conf`
- `<Location /keycloak/>`
- `ProxyPass https://localhost:8443/ timeout=300`
- `ProxyPassReverse https://localhost:8443/`

### Early observed login bootstrap order

The preserved login-bootstrap window on this lab was:

1. `/seikan/login/setup`
2. `/afa/php/SuiteLoginSessionValidation.php`
3. same-window Keycloak OIDC request to
   `/keycloak/realms/master/.well-known/openid-configuration`

That means Keycloak is in the early auth chain, but it is not the top-level UI
edge and not the first browser-facing stop point.

## Proven failure behavior

### Clean baseline before Keycloak mutation

Observed around March 29, 2026 at `19:59:50 EDT`:

- `httpd`, `keycloak`, and `ms-metro` were all active
- `/algosec-ui/login` returned `HTTP 200`
- Keycloak OIDC well-known returned `200`
- Metro heartbeat returned `"isAlive" : true`

### Keycloak-down behavior

After an intentional `keycloak.service` stop:

- `httpd` remained active
- `ms-metro` remained active
- `/algosec-ui/login` still returned `HTTP 200`
- Keycloak OIDC well-known returned `503`
- Metro heartbeat still returned `"isAlive" : true`

Operational meaning:

- the UI shell can still load while auth is broken
- the correct support stop point is `keycloak.service`, not Apache

### Current startup failure clue

Repeated restart attempts later showed a Keycloak startup failure with:

- `java.lang.reflect.UndeclaredThrowableException`
- `java.io.EOFException`
- `SerializedApplication.read(...)`
- `QuarkusEntryPoint.doRun(...)`

This is a proven example of a case where Keycloak can stay failed while Apache
still serves the login page.

## Support interpretation

- If `/algosec-ui/login` is down, stay on Apache and the UI edge first.
- If `/algosec-ui/login` still works but the Keycloak OIDC path fails, move to
  Keycloak.
- Do not describe Keycloak as the top-level UI edge.
- Do not claim Metro behavior from the overlapping Metro simulation; that proof
  is still incomplete.

## Still open

What is not yet fully proven:

- a clean isolated `ms-metro` mutation from a healthy baseline after the
  Keycloak work

That gap does not weaken the Keycloak result. It only means the Keycloak and
Metro branches should not be merged into one conclusion.

## Evidence

- `eval/history/asms-ui-login-bootstrap-observe-only-delegation-20260327.md`
- `eval/history/asms-ui-keycloak-simulation-and-metro-blocked-20260330.md`
- `eval/history/asms-ui-keycloak-and-metro-service-fault-simulation-attempt-20260330.md`
