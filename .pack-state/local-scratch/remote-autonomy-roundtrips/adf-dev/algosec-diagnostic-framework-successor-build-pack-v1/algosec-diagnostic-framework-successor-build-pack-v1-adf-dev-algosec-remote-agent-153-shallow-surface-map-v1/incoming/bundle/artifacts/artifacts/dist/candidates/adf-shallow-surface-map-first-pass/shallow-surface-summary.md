# ADF Successor Shallow Surface Summary

## Scope

- Target: algosec-remote-agent-153
- Hostname: algosec
- Components recorded: 336
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- `algosec-ms`: application_service (confidence medium, ports 8185) Doc-pack hints: matched terms afa, algosec
- `ms-metro`: application_service (confidence medium, ports 5701, 8080, 8082) Doc-pack hints: matched terms afa; matched ports 8082
- `activemq`: queue_or_messaging (confidence high, ports 61616) Doc-pack hints: matched terms algosec
- `httpd`: edge_proxy (confidence high, ports 80, 443)
- `systemd`: application_service (confidence low, ports 22, 80, 111, 443, 5432, 5701, 8080, 8082, 8086, 8099, 8143, 8166, 8175, 8185, 61616) Doc-pack hints: matched ports 8082

## Config And Log Surfaces

- `algosec-ms`: configs `/etc/systemd/system/algosec-ms.service` (observed, systemd_fragment), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u algosec-ms.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec-ms/logs/` (observed, process_command_option).
- `ms-metro`: configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-metro/logs/` (observed, process_command_option), `/data/ms-metro/logs` (candidate, derived_runtime_root).
- `activemq`: configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment), `/opt/apache-activemq-6.2.0/conf/jolokia-access.xml` (observed, process_command_path), `/opt/apache-activemq-6.2.0/conf/login.conf` (observed, process_command_path); logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec/work/` (observed, process_command_option).
- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `ms-bflow`: configs `/etc/systemd/system/ms-bflow.service` (observed, systemd_fragment), `/etc/systemd/system/ms-bflow.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-bflow.service --no-pager -n 80` (candidate, systemd_journal_locator).

## Edge-To-Local Route Hints

- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-configuration.conf:3` points toward `http://127.0.0.1:8185/$1`; likely owner `algosec-ms` (listener port 8185 matches exact PID ownership).
- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-metro.conf:3` points toward `http://127.0.0.1:8080/afa/$1`; likely owner `ms-metro` (listener port 8080 matches exact PID ownership).
- `/afa/external` via `ProxyPass` in `/etc/httpd/conf.d/zzz_fa.conf:131` points toward `http://localhost:8080/afa/api/v1`; likely owner `ms-metro` (listener port 8080 matches exact PID ownership).
- `/afa/external` via `ProxyPassReverse` in `/etc/httpd/conf.d/zzz_fa.conf:132` points toward `http://localhost:8080/afa/api/v1`; likely owner `ms-metro` (listener port 8080 matches exact PID ownership).
- `/afa/api/v1` via `ProxyPass` in `/etc/httpd/conf.d/zzz_fa.conf:140` points toward `http://localhost:8080/afa/api/v1`; likely owner `ms-metro` (listener port 8080 matches exact PID ownership).

## Boundary Packets

- No bounded boundary packet was strong enough to summarize in this pass.

## Session Parity Packets

- No bounded AFF session parity packet was strong enough to summarize in this pass.

## UserSession Bridge

- No bounded UserSession bridge packet was strong enough to summarize in this pass.

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

- `provider_specific_integration_evidence_current_node`: status `local_provider_health_partially_classified`; observed providers AWS via `ms-devicedriver-aws` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-aws.conf` to port `8143` with service `ms-devicedriver-aws.service` (health `degraded` ; local port `8143` not reachable ; journal signals `runtime_failure` x10), Azure via `ms-devicedriver-azure` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-azure.conf` to port `8086` with service `ms-devicedriver-azure.service` (health `degraded` ; local port `8086` not reachable ; journal signals `runtime_failure` x10); adjacent surfaces `ms-aad-azure-sensor->8118, ms-aad-log-sensor->8126, ms-cloudflow-broker->8134`; coordination clues `ms-devicemanager journal polling`; not proven: No external API success or provider credential correctness is proven in this packet.; No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.. Next stop: `strengthen_cross_node_directionality_proof`.

## Distributed And External Knowledge Layers

- `distributed_and_external_knowledge_layers`: node scope `single_node_only` with cross-node envelope `not_activated`; component guidance `httpd as `apache_httpd`, activemq as `apache_activemq` v6.2.0`; observed local external surfaces `ms-aad-azure-sensor -> algosec-ms, ms-aad-log-sensor -> algosec-ms, ms-cloudflow-broker -> algosec-ms, ms-cloudlicensing -> algosec-ms`; vendor activation `provider_specific_local_evidence_visible` with dormant inventory `Cisco, Arista, Check Point, F5 BIG-IP, Fortinet`. Next stop: `strengthen_cross_node_directionality_proof`.

## Visible Unknowns

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_direct_probe could not be collected in this pass.

## Next Candidate Seams

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

