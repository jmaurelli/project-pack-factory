---
title: "ASMS / Keycloak integration guide"
description: ""
sidebar:
  label: "ASMS / Keycloak integration guide"
  order: 1
---

# ASMS / Keycloak integration guide

## What Keycloak does in ASMS

- Keycloak is the auth service used in the ASMS login chain.
- Apache exposes Keycloak through `/keycloak/` and proxies that path to `https://localhost:8443/`.
- The UI login page can still load even when Keycloak is down. That means Keycloak failure is not always a top-level Apache failure.

## Proven integration points

1. Apache rewrites `/algosec/suite/login...` to `/algosec-ui/login` before the operator reaches the browser-facing login shell.
2. Apache proxies `/keycloak/` to local Keycloak on `8443` through `/etc/httpd/conf.d/keycloak.conf`.
3. The preserved login-bootstrap window on this lab was `/seikan/login/setup` -> `SuiteLoginSessionValidation.php` -> same-window Keycloak OIDC request.
4. In the clean Keycloak-down simulation, Apache still returned `HTTP 200` for `/algosec-ui/login` while the Keycloak OIDC well-known path returned `503`.

## What this means for support

- If the login page itself is down, stay on Apache or the UI edge.
- If the login page still loads but auth is failing, move to Keycloak.
- Do not treat Keycloak as the first browser-facing edge. Treat it as the auth branch behind Apache.

## Proven runtime clues

- Healthy baseline from March 29, 2026 around `19:59:50 EDT`: `httpd`, `keycloak`, and `ms-metro` were active, the login page returned `HTTP 200`, Keycloak OIDC returned `200`, and Metro heartbeat returned `isAlive: true`.
- Keycloak-down simulation from March 29, 2026: login page stayed `HTTP 200`, OIDC returned `503`, and Metro stayed healthy.
- Current failure clue from the same troubleshooting line: repeated `java.io.EOFException` in the Keycloak startup path can leave `keycloak.service` failed while Apache still serves the login page.

## Useful files and endpoints

- Apache Keycloak proxy config: `/etc/httpd/conf.d/keycloak.conf`
- Apache login rewrite config: `/etc/httpd/conf.d/zzz_fa.conf`
- Browser-facing login page: `https://127.0.0.1/algosec-ui/login`
- Browser-facing OIDC well-known probe: `https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration`
- Local Keycloak listener: `8443`

## Evidence

- `eval/history/asms-ui-login-bootstrap-observe-only-delegation-20260327.md`
- `eval/history/asms-ui-keycloak-simulation-and-metro-blocked-20260330.md`
- `eval/history/asms-ui-keycloak-and-metro-service-fault-simulation-attempt-20260330.md`

