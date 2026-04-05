# ASMS UI keycloak simulation and metro blocked follow-up - 2026-03-30

## Purpose

Run bounded service-fault simulations against the live lab appliance to validate
whether the current `ASMS UI is down` playbook matches operational behavior for
`keycloak.service` and `ms-metro.service`.

## Baseline before mutation

At `2026-03-29 19:59:50 EDT` the lab showed:

- `httpd`, `keycloak`, and `ms-metro` all `active`
- `GET /algosec-ui/login` returned `HTTP 200`
- `GET /keycloak/realms/master/.well-known/openid-configuration` returned `200`
- `GET /afa/getStatus` returned `"isAlive" : true`

That is the accepted clean baseline for this simulation pass.

## Keycloak-down simulation

An intentional `keycloak.service` stop was followed by shallow probes.

Observed behavior:

- `httpd` remained `active`
- `ms-metro` remained `active`
- `GET /algosec-ui/login` still returned `HTTP 200`
- `GET /keycloak/realms/master/.well-known/openid-configuration` returned `503`
- `GET /afa/getStatus` still returned `"isAlive" : true`

Operational meaning:

- Apache still served the UI shell and login page
- the first broken boundary moved to the auth service, not the top-level UI
  edge
- this matches the current playbook rule that `keycloak.service` is the shallow
  stop point only when the login page still loads but auth is down

## Metro simulation status

The first `ms-metro.service` stop was launched in overlap with a concurrent
`keycloak.service` stop. Because the two mutations were not isolated, the
result is not accepted as a clean Metro-only simulation.

What can be said safely:

- the Metro-only conclusion from that overlapping run is not trustworthy enough
  to update the playbook
- the current playbook expectation remains only inferred for the clean
  Metro-down case: login page and Keycloak should still be reachable, while the
  app-side shell and Metro heartbeat should fail first

## Recovery outcome

After the overlapping mutation window, `keycloak.service` did not recover
cleanly.

Repeated bounded restart attempts showed:

- `systemctl is-active keycloak` returning `failed`
- Keycloak OIDC probe still returning `503`
- repeated `java.io.EOFException` in the Keycloak startup path
- Metro eventually returned to `active` and `GET /afa/getStatus` returned
  `"isAlive" : true`
- Apache continued serving the login page with `HTTP 200`

Representative Keycloak failure clue:

```text
Exception in thread "main" java.lang.reflect.UndeclaredThrowableException
Caused by: java.io.EOFException
... SerializedApplication.read(...)
... QuarkusEntryPoint.doRun(...)
keycloak.service: Main process exited, status=1/FAILURE
```

## Judgment

What is now proven:

- the current playbook is operationally correct for the `keycloak.service`
  shallow-fault case
- `keycloak.service` failure does not by itself mean Apache stops serving the
  login page
- the correct support stop point is the auth service boundary, not the top-level
  UI edge

What is still not proven:

- a clean isolated `ms-metro.service` fault simulation from a trustworthy
  healthy baseline

## Next step

Do not run more live service-mutation simulations until the lab returns to a
clean baseline with:

- `systemctl is-active httpd keycloak ms-metro` all healthy
- login page returning `HTTP 200`
- Keycloak OIDC probe returning `200`
- Metro heartbeat returning `"isAlive" : true`

Once the baseline is restored, rerun `ms-metro.service` as a single isolated
mutation and compare the observed behavior to the current Step 3 and Step 4
playbook guidance.
