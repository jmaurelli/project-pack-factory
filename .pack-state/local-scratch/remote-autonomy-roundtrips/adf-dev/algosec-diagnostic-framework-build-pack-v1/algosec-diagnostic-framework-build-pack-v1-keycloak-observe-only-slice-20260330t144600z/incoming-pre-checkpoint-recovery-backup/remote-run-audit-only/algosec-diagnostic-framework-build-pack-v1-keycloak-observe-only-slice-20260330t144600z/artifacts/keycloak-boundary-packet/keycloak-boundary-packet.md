# Keycloak Boundary Packet

## Run
- run_id: `algosec-diagnostic-framework-build-pack-v1-keycloak-observe-only-slice-20260330t144600z`
- target: `10.167.2.150`
- generated_at: `2026-03-30T14:55:50Z`
- observed_minute: `2026-03-30 10:10:55 EDT`

## Observed Boundary On This Appliance
- `target-preflight` returned `adf-target-shell-ok`.
- `target-heartbeat` returned `adf-target-heartbeat`.
- `systemctl show keycloak.service` reported `Result=exit-code; ExecMainCode=1; ExecMainStatus=1; ActiveState=failed; SubState=failed`.
- `systemctl status keycloak.service` showed `Active: failed (Result: exit-code)` and the startup failure minute `2026-03-30 10:10:55 EDT`.
- Listener check for `8443` returned only the `ss` header, which means no active listener was exposed on that port during this slice.
- `curl https://127.0.0.1/algosec-ui/login` returned `login_http=200`.
- `curl https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration` returned `keycloak_oidc_http=503`.
- Metro still answered `metro_status={  "isAlive" : true}`.
- Apache still maps `/keycloak/` through local Keycloak on `8443`: `1:<Location /keycloak/>; 2:        ProxyPass https://localhost:8443/ timeout=300; 3:        ProxyPassReverse https://localhost:8443/`.

## What That Boundary Means In ASMS
- The top-level UI edge is not the failing boundary in this slice because the login page still returns `200`.
- The failing stop point is the imported auth module boundary: Apache can still serve the login surface, but the proxied Keycloak OIDC path is broken.
- This confirms the support stop rule from the current Keycloak integration map: move from Apache to Keycloak only when `/algosec-ui/login` is still reachable but `/keycloak/.../.well-known/openid-configuration` fails.

## Generic Failure Classes
- `startup_failure`: supported by `ActiveState=failed`, `Result=exit-code`, and the repeated Quarkus startup trace.
- `listener_absent`: supported by the empty `8443` listener check.
- `useful_work_path_failed`: supported by `keycloak_oidc_http=503` while the surrounding UI edge still serves the login page.
- `dependency_or_resource_unknown`: not proven in this slice. The current evidence packet does not isolate database, filesystem, or host-pressure causes.

## Bounded Next Checks
- Keep the next support step on `keycloak.service` restartability and startup clues, not on Apache rewrite logic.
- If a deeper module drilldown is needed, inspect the Keycloak service wrapper and local runtime inputs that feed Quarkus startup before widening into unrelated ASMS services.
- Keep Metro as a supporting separation clue only; this slice does not need a Metro fault story because Metro still reports `isAlive: true`.

## Escalation-Ready Evidence Packet
- Service state: `artifacts/keycloak-boundary-packet/keycloak-service-show.json`
- Service status and startup trace: `artifacts/keycloak-boundary-packet/keycloak-service-status.json`
- Listener check: `artifacts/keycloak-boundary-packet/keycloak-listener-8443.json`
- Browser-facing login check: `artifacts/keycloak-boundary-packet/login-http.json`
- Keycloak OIDC boundary check: `artifacts/keycloak-boundary-packet/keycloak-oidc-http.json`
- Metro separation check: `artifacts/keycloak-boundary-packet/metro-heartbeat.json`
- Recent journal clues: `artifacts/keycloak-boundary-packet/keycloak-journal-tail.json`
- Apache integration clue: `artifacts/keycloak-boundary-packet/apache-keycloak-proxy.json`

## Pilot Judgment
- Result: `proves_reusable_module_boundary_packet`
- Why: this packet is small, support-useful, and reusable. It does not try to enumerate every Keycloak fix. It classifies the module boundary into service state, listener state, useful-work-path failure, and escalation-ready evidence.
- Falsifier for the pilot: if future imported-module slices require many module-specific branches before they become support-useful, the method should be abandoned quickly.
