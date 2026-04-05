---
title: "ASMS / Keycloak integration guide"
description: ""
sidebar:
  label: "ASMS / Keycloak integration guide"
  order: 2
---

# ASMS / Keycloak integration guide

## Current route contract

- Use this route when: Login page opens but sign-in fails.
- Current handoff target: `asms-runtime-taxonomy`

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

## Imported-module drilldown summary

- Classify the module first: service state, listener state, OIDC useful-work check, and proxy path.
- Keep the next support step on the smallest failing Keycloak boundary instead of widening back into Apache or later ASMS modules too early.
- If the boundary is still unresolved after the shallow checks, gather the escalation packet and only then branch into deeper module-specific interpretation.

## Proven runtime clues

- Apache can still serve `https://127.0.0.1/algosec-ui/login` while the proxied Keycloak OIDC path is unhealthy.
- Keycloak service state, listener `8443`, and the OIDC well-known probe together define whether the auth module can still do useful work.
- Use current appliance evidence first. In the validated March 30, 2026 slice on `10.167.2.150`, the login page stayed `200`, the Keycloak OIDC path returned `503`, `keycloak.service` was failed, `8443` was absent, and Metro still reported `isAlive: true`.

## Useful files and endpoints

- Apache Keycloak proxy config: `/etc/httpd/conf.d/keycloak.conf`
- Apache login rewrite config: `/etc/httpd/conf.d/zzz_fa.conf`
- Browser-facing login page: `https://127.0.0.1/algosec-ui/login`
- Browser-facing OIDC well-known probe: `https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration`
- Local Keycloak listener: `8443`

## Save these items

- service status
- listener output
- OIDC probe output

## Upstream references

- [Keycloak documentation](https://www.keycloak.org/documentation): Use this after the appliance evidence proves the Keycloak boundary and you need bounded interpretation of Keycloak server behavior.
- [Keycloak server configuration guide](https://www.keycloak.org/server/configuration): Use this for deeper configuration or startup interpretation only after the local service and listener checks narrow the failure class.

## Evidence

- `eval/history/asms-ui-login-bootstrap-observe-only-delegation-20260327.md`
- `eval/history/asms-ui-keycloak-simulation-and-metro-blocked-20260330.md`
- `eval/history/asms-ui-keycloak-and-metro-service-fault-simulation-attempt-20260330.md`

