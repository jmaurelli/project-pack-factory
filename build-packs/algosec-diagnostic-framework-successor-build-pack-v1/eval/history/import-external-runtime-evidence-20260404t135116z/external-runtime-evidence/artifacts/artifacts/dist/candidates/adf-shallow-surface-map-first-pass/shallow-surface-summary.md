# ADF Successor Shallow Surface Summary

## Scope

- Target: algosec-lab-alt-213
- Hostname: algosec
- Components recorded: 356
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## Fast Read

- routes /FireFlow/api, /aff/api currently land on `aff-boot` over local ports `1989`.
- No failed high-signal services were highlighted in this bounded pass.
- Session seam: `aff_session_route_parity` is `parity_confirmed` with status-code match `True` and body match `True`.
- Next best seam: `strengthen_cross_node_directionality_proof` from ms-devicedriver-aws, ms-devicedriver-azure.

## What Appears To Be Running

- `keycloak`: identity_or_access (confidence medium, ports 8443, 9000, 29195) Doc-pack hints: matched terms authentication, authorization; matched ports 8443
- `algosec-ms`: application_service (confidence medium, ports 8185) Doc-pack hints: matched terms afa, algosec
- `ms-metro`: application_service (confidence medium, ports 5701, 8080, 8082) Doc-pack hints: matched terms afa; matched ports 8082
- `activemq`: queue_or_messaging (confidence high, ports 61616) Doc-pack hints: matched terms algosec
- `httpd`: edge_proxy (confidence high, ports 80, 443)

## Config And Log Surfaces

- `keycloak`: configs `/usr/lib/systemd/system/keycloak.service` (observed, systemd_fragment), `/usr/share/keycloak/keycloak_service.conf` (observed, systemd_environment_file), `/usr/share/keycloak/bin/../conf` (observed, process_command_option); logs `journalctl -u keycloak.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `algosec-ms`: configs `/etc/systemd/system/algosec-ms.service` (observed, systemd_fragment), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u algosec-ms.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec-ms/logs/` (observed, process_command_option).
- `ms-metro`: configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-metro/logs/` (observed, process_command_option), `/data/ms-metro/logs` (candidate, derived_runtime_root).
- `activemq`: configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment), `/opt/apache-activemq-6.2.0/conf/jolokia-access.xml` (observed, process_command_path), `/opt/apache-activemq-6.2.0/conf/login.conf` (observed, process_command_path); logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec/work/` (observed, process_command_option).
- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php83-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
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

- `fireflow_usersession_bridge`: status `bridge_signals_thin`; Apache markers `/FireFlow/api/session, /FireFlow/api/session/validate, extendSession` and FireFlow markers `none` are visible. Next stop: `keep_usersession_bridge_bounded`.

## Reused FA Session Chain

- No bounded reused FA-session packet was strong enough to summarize in this pass.

## Session Origin Clues

- No bounded upstream session-origin packet was strong enough to summarize in this pass.

## Bootstrap Vs Polling

- No bounded bootstrap-versus-polling packet was strong enough to summarize in this pass.

## AFF Cookie Handoff

- No bounded AFF cookie-handoff packet was strong enough to summarize in this pass.

## Java Runtime Clusters

- No bounded Java runtime cluster packet was strong enough to summarize in this pass.

## Provider-Specific Integration Evidence

- `provider_specific_integration_evidence_current_node`: status `local_provider_health_partially_classified`; observed providers AWS via `ms-devicedriver-aws` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-aws.conf` to port `8174` with service `ms-devicedriver-aws.service` (health `degraded` ; local port `8174` not reachable ; journal signals `runtime_failure` x10), Azure via `ms-devicedriver-azure` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-azure.conf` to port `8115` with service `ms-devicedriver-azure.service` (health `degraded` ; local port `8115` not reachable ; journal signals `runtime_failure` x10); adjacent surfaces `ms-aad-azure-sensor->8149, ms-aad-log-sensor->8184, ms-cloudflow-broker->8180`; coordination clues `ms-devicemanager peers 10.178.4.231,10.178.4.231 journal polling`; not proven: No external API success or provider credential correctness is proven in this packet.; No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.. Next stop: `strengthen_cross_node_directionality_proof`.

## Distributed And External Knowledge Layers

- `distributed_and_external_knowledge_layers`: node scope `single_node_only` with cross-node envelope `not_activated`; component guidance `httpd as `apache_httpd`, activemq as `apache_activemq` v6.2.0, keycloak as `keycloak`, kibana as `kibana`, elasticsearch as `elasticsearch``; observed local external surfaces `ms-aad-azure-sensor -> algosec-ms, ms-aad-log-sensor -> algosec-ms, ms-cloudflow-broker -> algosec-ms, ms-cloudlicensing -> algosec-ms`; vendor activation `provider_specific_local_evidence_visible` with dormant inventory `Cisco, Arista, Check Point, F5 BIG-IP, Fortinet`. Next stop: `strengthen_cross_node_directionality_proof`.

## Visible Unknowns

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

