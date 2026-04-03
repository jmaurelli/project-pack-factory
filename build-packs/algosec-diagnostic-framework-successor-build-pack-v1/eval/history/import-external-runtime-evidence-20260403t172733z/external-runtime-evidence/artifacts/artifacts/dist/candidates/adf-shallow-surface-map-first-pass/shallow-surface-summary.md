# ADF Successor Shallow Surface Summary

## Scope

- Target: algosec-lab-cm-150-distributed
- Hostname: algosec
- Components recorded: 344
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- `keycloak`: identity_or_access (confidence medium, ports 8443, 9000, 28897) Doc-pack hints: matched terms authentication, authorization; matched ports 8443
- `algosec-ms`: application_service (confidence medium, ports 8185) Doc-pack hints: matched terms afa, algosec
- `ms-metro`: application_service (confidence medium, ports 5701, 8080, 8082) Doc-pack hints: matched terms afa; matched ports 8082
- `activemq`: queue_or_messaging (confidence high, ports 61616) Doc-pack hints: matched terms algosec
- `httpd`: edge_proxy (confidence high, ports 80, 443)

## Config And Log Surfaces

- `keycloak`: configs `/usr/lib/systemd/system/keycloak.service` (observed, systemd_fragment), `/usr/share/keycloak/keycloak_service.conf` (observed, systemd_environment_file), `/usr/share/keycloak/bin/../conf` (observed, process_command_option); logs `journalctl -u keycloak.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `algosec-ms`: configs `/etc/systemd/system/algosec-ms.service` (observed, systemd_fragment), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u algosec-ms.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec-ms/logs/` (observed, process_command_option).
- `ms-metro`: configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-metro/logs/` (observed, process_command_option), `/data/ms-metro/logs` (candidate, derived_runtime_root).
- `activemq`: configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment), `/opt/apache-activemq-6.2.0/conf/jolokia-access.xml` (observed, process_command_path), `/opt/apache-activemq-6.2.0/conf/login.conf` (observed, process_command_path); logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec/work/` (observed, process_command_option).
- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
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

- `fireflow_usersession_bridge`: status `bridge_signals_thin`; Apache markers `/FireFlow/api/session` and FireFlow markers `none` are visible. Next stop: `keep_usersession_bridge_bounded`.

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

- `provider_specific_integration_evidence_current_node`: status `local_surfaces_visible_not_health_validated`; observed providers AWS via `ms-devicedriver-aws` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-aws.conf` to port `8104` with service `ms-devicedriver-aws.service`, Azure via `ms-devicedriver-azure` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-azure.conf` to port `8113` with service `ms-devicedriver-azure.service`; adjacent surfaces `ms-aad-azure-sensor->8151, ms-aad-log-sensor->8183, ms-cloudflow-broker->8134`; not proven: No external API success or provider credential correctness is proven in this packet.; No provider-side health, sync state, or inventory freshness is claimed from current node evidence.. Next stop: `capture_second_node_node_local_proof`.

## Distributed And External Knowledge Layers

- `distributed_and_external_knowledge_layers`: node scope `single_node_only` with cross-node envelope `not_activated`; component guidance `httpd as `apache_httpd`, activemq as `apache_activemq` v6.2.0, keycloak as `keycloak`, kibana as `kibana`, elasticsearch as `elasticsearch``; observed local external surfaces `ms-aad-azure-sensor -> algosec-ms, ms-aad-log-sensor -> algosec-ms, ms-cloudflow-broker -> algosec-ms, ms-cloudlicensing -> algosec-ms`; vendor activation `provider_specific_local_evidence_visible` with dormant inventory `Cisco, Arista, Check Point, F5 BIG-IP, Fortinet`. Next stop: `capture_second_node_node_local_proof`.

## Visible Unknowns

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `capture_second_node_node_local_proof`: The current node now has a bounded provider-evidence packet for AWS and Azure, so the next meaningful ambiguity is no longer what this node exposes but what changes on a second imported node-local proof. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

