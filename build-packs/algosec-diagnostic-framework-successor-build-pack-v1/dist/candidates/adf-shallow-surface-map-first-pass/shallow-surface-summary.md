# ADF Successor Shallow Surface Summary

## Scope

- Target: 10.167.2.150
- Hostname: algosec
- Components recorded: 351
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- `algosec-ms`: application_service (confidence medium, ports 8185) Doc-pack hints: matched terms afa, algosec
- `ms-metro`: application_service (confidence medium, ports 5701, 8080, 8082) Doc-pack hints: matched terms afa; matched ports 8082
- `httpd`: edge_proxy (confidence high, ports 80, 443)
- `logstash`: application_service (confidence low, ports 9600) Doc-pack hints: matched terms api
- `ms-bflow`: application_service (confidence medium, ports 8081, 8083) Doc-pack hints: matched terms afa

## Edge-To-Local Route Hints

- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:3` points toward `http://127.0.0.1:8081/BusinessFlow/$1`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).
- `/BusinessFlow` via `ProxyPass` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:12` points toward `http://127.0.0.1:8081/BusinessFlow`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).
- `/BusinessFlow` via `ProxyPassReverse` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:13` points toward `http://127.0.0.1:8081/BusinessFlow`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).
- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-configuration.conf:3` points toward `http://127.0.0.1:8185/$1`; likely owner `algosec-ms` (listener port 8185 matches exact PID ownership).
- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-metro.conf:3` points toward `http://127.0.0.1:8080/afa/$1`; likely owner `ms-metro` (listener port 8080 matches exact PID ownership).

## Boundary Packets

- `aff_fireflow_1989_route_owner`: AFF or FireFlow 1989 Route Owner Packet confirms routes /FireFlow/api, /aff/api through owner `aff-boot` on local ports 1989.

## Session Parity Packets

- `aff_session_route_parity`: status `parity_confirmed`; fronted `/FireFlow/api/session` returned `200`, direct aff-boot session returned `200`, body match `True`, invalid-session code match `True`. Next stop: `fireflow_usersession_bridge`.

## UserSession Bridge

- `fireflow_usersession_bridge`: status `bridge_signals_visible`; Apache markers `/FireFlow/api/session, /FireFlow/api/session/validate, extendSession` and FireFlow markers `UserSession::getUserSession, isUserSessionValid, Using existing FASessionId, ff-session:` are visible. Next stop: `trace_usersession_fa_session_reuse`.

## Reused FA Session Chain

- `usersession_fa_session_reuse`: status `reuse_chain_visible`; retained pairs `e0974e9f0e -> n575jpek15 x7, 0135ec87f0 -> 0o43kjh144 x2, 652116c1ae -> 0o43kjh144 x2`. Next stop: `trace_businessflow_session_origin`.

## Visible Unknowns

- The first pass does not yet parse config files, unit fragments, or logs.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `trace_businessflow_session_origin`: The retained FireFlow window now shows concrete `ff-session -> reused FA-session` pairs, so the next bounded question is which upstream BusinessFlow or AFA-side caller fed that session context into the confirmed FireFlow bridge. Starting points: ms-bflow, aff-boot, httpd.
- `trace_edge_to_local_service_routes`: Apache route hints now expose candidate local handoffs, so the next bounded pass can confirm which service owns each browser-facing route. Starting points: ms-bflow, algosec-ms, ms-metro.

