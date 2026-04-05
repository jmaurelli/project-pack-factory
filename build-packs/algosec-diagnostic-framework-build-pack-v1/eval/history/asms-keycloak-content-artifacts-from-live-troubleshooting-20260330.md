# ASMS Keycloak content artifacts from live troubleshooting - 2026-03-30

## Purpose

Record the evidence line used to build dedicated Keycloak content artifacts for
the ADF pack.

## What was built

- dedicated operator playbook:
  `playbooks/asms-keycloak-auth-is-down`
- dedicated integration guide:
  `guides/asms-keycloak-integration-guide`
- dedicated junior operator guide:
  `guides/asms-keycloak-junior-operator-guide`
- durable integration spec:
  `docs/specs/asms-keycloak-integration-map-v1.md`

## Evidence used

### Login bootstrap evidence

The preserved bootstrap slice showed:

1. `/seikan/login/setup`
2. `SuiteLoginSessionValidation.php`
3. same-window Keycloak OIDC request

That proved Keycloak is in the early auth chain but behind the Apache-served
login shell.

### Clean Keycloak-down behavior

The clean service-fault simulation showed:

- login page still returned `HTTP 200`
- Keycloak OIDC returned `503`
- Metro stayed healthy

That proved the correct support stop point is Keycloak when auth is down but
the login page still loads.

### Keycloak startup failure clue

The later bounded recovery attempts preserved a real failure clue:

- `java.io.EOFException`
- `SerializedApplication.read(...)`
- `QuarkusEntryPoint.doRun(...)`

That made the operator guide concrete instead of generic.

## Content rule used

The Keycloak pages were written in the newer operator language standard:

- short check names
- `Run`
- `Expected result`
- `Check output for`
- `If result is different`

## Known limit

The Metro-only mutation proof is still not clean. These Keycloak artifacts only
claim what the current Keycloak evidence actually proves.
