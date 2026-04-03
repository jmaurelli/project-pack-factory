# ADF Successor Shallow Surface Summary

## Scope

- Target: algosec-dr-secondary-153
- Hostname: algosec
- Components recorded: 326
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## Fast Read

- `/FireFlow/api` currently points toward `http://localhost:1989/aff/api/external` with likely owner `httpd`.
- Immediate pressure points: `activemq` (failed), `ms-bflow` (failed), `ms-metro` (failed).
- Next best seam: `strengthen_cross_node_directionality_proof` from ms-devicedriver-aws, ms-devicedriver-azure.

## What Appears To Be Running

- `httpd`: edge_proxy (confidence high, ports 80, 443)
- `logstash`: application_service (confidence low, ports 9600) Doc-pack hints: matched terms api
- `ms-hadr`: application_service (confidence medium, ports 9595) Doc-pack hints: matched terms algosec
- `elastic-ssh-tunnel`: application_service (confidence medium, ports 9200, 9300) Doc-pack hints: matched terms algosec
- `ssh-connections-monitor`: application_service (confidence medium, ports 9200, 9300) Doc-pack hints: matched terms algosec

## Config And Log Surfaces

- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `logstash`: configs `/usr/lib/systemd/system/logstash.service` (observed, systemd_fragment), `/etc/sysconfig/logstash` (observed, systemd_environment_file); logs `journalctl -u logstash.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/log/logstash/` (observed, process_command_path), `/data/log/logstash/` (observed, process_command_option).
- `ms-hadr`: configs `/etc/systemd/system/ms-hadr.service` (observed, systemd_fragment); logs `journalctl -u ms-hadr.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `elastic-ssh-tunnel`: configs `/etc/systemd/system/elastic-ssh-tunnel.service` (observed, systemd_fragment); logs `journalctl -u elastic-ssh-tunnel.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `ssh-connections-monitor`: configs `/etc/systemd/system/ssh-connections-monitor.service` (observed, systemd_fragment); logs `journalctl -u ssh-connections-monitor.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `activemq`: configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment); logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `ms-bflow`: configs `/etc/systemd/system/ms-bflow.service` (observed, systemd_fragment), `/etc/systemd/system/ms-bflow.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-bflow.service --no-pager -n 80` (candidate, systemd_journal_locator).

## Edge-To-Local Route Hints

- `/FireFlow/api` via `ProxyPass` in `/etc/httpd/conf.d/aff.conf:6` points toward `http://localhost:1989/aff/api/external`; likely owner `httpd` (name hint `httpd` is visible in Apache route config).
- `/FireFlow/api` via `ProxyPassReverse` in `/etc/httpd/conf.d/aff.conf:7` points toward `http://localhost:1989/aff/api/external`; likely owner `httpd` (name hint `httpd` is visible in Apache route config).
- `/aff/api` via `ProxyPass` in `/etc/httpd/conf.d/aff.conf:16` points toward `http://localhost:1989/aff/api`; likely owner `httpd` (name hint `httpd` is visible in Apache route config).
- `/aff/api` via `ProxyPassReverse` in `/etc/httpd/conf.d/aff.conf:17` points toward `http://localhost:1989/aff/api`; likely owner `httpd` (name hint `httpd` is visible in Apache route config).
- `/aff/api` via `RewriteRule` in `/etc/httpd/conf.d/aff.conf:52` points toward `no backend target`; likely owner `httpd` (name hint `httpd` is visible in Apache route config).

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

- `provider_specific_integration_evidence_current_node`: status `local_provider_health_partially_classified`; observed providers AWS via `ms-devicedriver-aws` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-aws.conf` to port `8104` with service `None` (health `degraded` ; local port `8104` not reachable), Azure via `ms-devicedriver-azure` from `/etc/httpd/conf.d/algosec-ms.ms-devicedriver-azure.conf` to port `8113` with service `None` (health `degraded` ; local port `8113` not reachable); adjacent surfaces `ms-aad-azure-sensor->8151, ms-aad-log-sensor->8183, ms-cloudflow-broker->8134`; coordination clues `none`; not proven: No external API success or provider credential correctness is proven in this packet.; No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.. Next stop: `strengthen_cross_node_directionality_proof`.

## Distributed And External Knowledge Layers

- `distributed_and_external_knowledge_layers`: node scope `single_node_only` with cross-node envelope `not_activated`; component guidance `httpd as `apache_httpd`, activemq as `apache_activemq`, logstash as `logstash``; observed local external surfaces `ms-aad-azure-sensor -> httpd, ms-aad-log-sensor -> httpd, ms-cloudflow-broker -> httpd, ms-cloudlicensing -> httpd`; vendor activation `provider_specific_local_evidence_visible` with dormant inventory `Cisco, Arista, Check Point, F5 BIG-IP, Fortinet`. Next stop: `strengthen_cross_node_directionality_proof`.

## Visible Unknowns

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_direct_probe could not be collected in this pass.

## Next Candidate Seams

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

