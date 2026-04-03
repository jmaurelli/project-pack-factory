# ADF Successor Shallow Surface Summary

## Scope

- Target: 10.167.2.150
- Hostname: algosec
- Components recorded: 360
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- `algosec-ms`: application_service (confidence medium, ports 8185) Doc-pack hints: matched terms afa, algosec
- `ms-metro`: application_service (confidence medium, ports 5701, 8080, 8082) Doc-pack hints: matched terms afa; matched ports 8082
- `httpd`: edge_proxy (confidence high, ports 80, 443)
- `logstash`: application_service (confidence low, ports 9600) Doc-pack hints: matched terms api
- `ms-bflow`: application_service (confidence medium, ports 8081, 8083) Doc-pack hints: matched terms afa

## Config And Log Surfaces

- `algosec-ms`: configs `/etc/systemd/system/algosec-ms.service` (observed, systemd_fragment), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u algosec-ms.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec-ms/logs/` (observed, process_command_option).
- `ms-metro`: configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-metro/logs/` (observed, process_command_option), `/data/ms-metro/logs` (candidate, derived_runtime_root).
- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `logstash`: configs `/usr/lib/systemd/system/logstash.service` (observed, systemd_fragment), `/etc/sysconfig/logstash` (observed, systemd_environment_file); logs `journalctl -u logstash.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/log/logstash/` (observed, process_command_path), `/data/log/logstash/` (observed, process_command_option).
- `ms-bflow`: configs `/etc/systemd/system/ms-bflow.service` (observed, systemd_fragment), `/etc/systemd/system/ms-bflow.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-bflow.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-bflow/logs/` (observed, process_command_option), `/data/ms-bflow/logs` (candidate, derived_runtime_root).
- `activemq`: configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment), `/opt/apache-activemq-6.1.7/conf/jolokia-access.xml` (observed, process_command_path), `/opt/apache-activemq-6.1.7/conf` (observed, process_command_option); logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `aff-boot`: configs `/etc/systemd/system/aff-boot.service` (observed, systemd_fragment); logs `journalctl -u aff-boot.service --no-pager -n 80` (candidate, systemd_journal_locator).

## Edge-To-Local Route Hints

- `/FireFlow/api` via `ProxyPass` in `/etc/httpd/conf.d/aff.conf:6` points toward `http://localhost:1989/aff/api/external`; likely owner `aff-boot` (listener port 1989 matches exact PID ownership).
- `/FireFlow/api` via `ProxyPassReverse` in `/etc/httpd/conf.d/aff.conf:7` points toward `http://localhost:1989/aff/api/external`; likely owner `aff-boot` (listener port 1989 matches exact PID ownership).
- `/aff/api` via `ProxyPass` in `/etc/httpd/conf.d/aff.conf:16` points toward `http://localhost:1989/aff/api`; likely owner `aff-boot` (listener port 1989 matches exact PID ownership).
- `/aff/api` via `ProxyPassReverse` in `/etc/httpd/conf.d/aff.conf:17` points toward `http://localhost:1989/aff/api`; likely owner `aff-boot` (listener port 1989 matches exact PID ownership).
- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:3` points toward `http://127.0.0.1:8081/BusinessFlow/$1`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).

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

## Java Runtime Clusters

- `java_runtime_clusters`: status `cluster_boundaries_visible`; visible families ms-metro as `tomcat_service_family` via `/data/ms-metro` on ports `5701, 8080, 8082` with routes `/afa/external, /afa/api/v1`, ms-bflow as `tomcat_service_family` via `/data/ms-bflow` on ports `8081, 8083` with routes `/BusinessFlow`, algosec-ms as `standalone_jar_service` via `/usr/share/fa/mslib/ms-configuration.jar` on ports `8185` with routes `/algosec/swagger/service, /algosec/swagger/swagger-ui.html`, aff-boot as `standalone_jar_service` via `/usr/share/aff/lib/aff-boot.jar` on ports `1989` with routes `/FireFlow/api, /aff/api`. Shared substrates: `activemq`. Next stop: `review_asms_runtime_architecture`.

## Distributed And External Knowledge Layers

- `distributed_and_external_knowledge_layers`: node scope `single_node_only` with cross-node envelope `not_activated`; component guidance `httpd as `apache_httpd`, ms-metro as `apache_tomcat_family`, ms-bflow as `apache_tomcat_family`, activemq as `apache_activemq` v6.1.7, keycloak as `keycloak``; observed local external surfaces `/FireFlow/api -> aff-boot, /aff/api -> aff-boot, /BusinessFlow -> ms-bflow, /afa/external -> ms-metro`; vendor activation `provider_specific_local_evidence_visible` with dormant inventory `Cisco, Arista, Check Point, F5 BIG-IP, Fortinet`. Next stop: `define_second_node_request_shape`.

## Visible Unknowns

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `define_second_node_request_shape`: The current node now has explicit activation boundaries for component guidance and external-system hints, so the next bounded move is defining the second-node request and thin cross-node envelope instead of widening this one node into a suite graph. Starting points: httpd, ms-metro, ms-bflow, activemq.

