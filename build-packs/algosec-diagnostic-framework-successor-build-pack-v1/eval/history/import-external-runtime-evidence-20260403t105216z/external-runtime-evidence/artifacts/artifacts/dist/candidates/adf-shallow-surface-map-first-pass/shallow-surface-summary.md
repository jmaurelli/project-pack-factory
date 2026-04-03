# ADF Successor Shallow Surface Summary

## Scope

- Target: 10.167.2.150
- Hostname: algosec
- Components recorded: 353
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

- `usersession_fa_session_reuse`: status `reuse_chain_visible`; retained pairs `bcbefc00d0 -> et7nlq7ird x3, 14943c0d54 -> 6far9qrvdn x2, 333bba3359 -> 6far9qrvdn x2`. Next stop: `trace_businessflow_session_origin`.

## Session Origin Clues

- `businessflow_session_origin_clue`: status `shared_polling_origin_clues_visible` with distinction `polling_dominant_without_httpd_bootstrap_pair` and reading `later_shared_polling`; Apache-side markers `getAFASessionInfo, bridge/refresh, CommandsDispatcher, /afa/php/ws.php, BusinessFlow/shallow_health_check` and source-side markers `BFCookie, getAFASessionInfo, VerifyGetFASessionIdValid, Could not find AlgosecSession, storeFireflowCookie` are visible, while missing Apache bootstrap terms are `/fa/server/connection/login, storeFireflowCookie`. Next stop: `distinguish_bootstrap_from_shared_polling`.

## Bootstrap Vs Polling

- `bootstrap_polling_distinction`: status `polling_dominant_with_bootstrap_anchor` with reading `bootstrap_anchor_then_shared_polling`; bootstrap anchors `bcbefc00d0 store->1s then ~300s cadence` and polling-only sessions `e0974e9f0e x20` are visible. Next stop: `inspect_aff_cookie_handoff`.

## AFF Cookie Handoff

- `aff_cookie_handoff`: status `cookie_handoff_visible`; bootstrap anchor `bcbefc00d0` carries token `et7nlq7ird78aueurcmblulov6` through `/afa/external//bridge/storeFireflowCookie` toward owner `ms-metro`, with later extend path `/afa/external//session/extend`. Next stop: `inspect_java_runtime_clusters`.

## Visible Unknowns

- The first pass does not yet parse config files, unit fragments, or logs.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `inspect_java_runtime_clusters`: The bounded bootstrap anchor now crosses a visible AFF bridge handoff, so the next ambiguity shifts from session-origin classification to the local owners and runtime boundaries behind that bridge. Starting points: ms-metro, ms-bflow, aff-boot.
- `trace_edge_to_local_service_routes`: Apache route hints now expose candidate local handoffs, so the next bounded pass can confirm which service owns each browser-facing route. Starting points: ms-bflow, algosec-ms, ms-metro.

