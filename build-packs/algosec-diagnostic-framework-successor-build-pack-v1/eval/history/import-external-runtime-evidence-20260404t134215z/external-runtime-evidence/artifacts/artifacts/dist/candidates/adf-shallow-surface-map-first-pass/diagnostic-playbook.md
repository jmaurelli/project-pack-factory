# ADF Successor Diagnostic Playbook

## Use This For

- Live triage on `algosec-lab-alt-192` when the engineer needs the fastest bounded owner, evidence, and escalation path.
- Decision support under pressure, not full product study.
- A fast route from symptom to local owner, first checks, and explicit stop rules.

## Fast Start

- Strongest current owner chain: routes /FireFlow/api, /aff/api currently land on `aff-boot` over local ports `1989`.
- Session check: `AFF Session Route Parity Packet` is `parity_confirmed`. The fronted `/FireFlow/api/session` path and the direct aff-boot session path currently agree at the bounded edge.
- Provider warning: local degradation is visible for `ms-devicedriver-aws`, `ms-devicedriver-azure`, but provider-side success is still not proven.

## Route To Owner Shortlist

- `/FireFlow/api` -> `aff-boot` on local ports `1989`.
- `/aff/api` -> `aff-boot` on local ports `1989`.
- `(route path not explicit)` -> `ms-bflow` via `http://127.0.0.1:8081/BusinessFlow/$1` from `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:3`.
- `/BusinessFlow` -> `ms-bflow` via `http://127.0.0.1:8081/BusinessFlow` from `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:12`.

## First Checks By Family

- `keycloak`: state `active`, listener ports `8443, 9000, 24565`, configs `/usr/lib/systemd/system/keycloak.service` (observed, systemd_fragment), `/usr/share/keycloak/keycloak_service.conf` (observed, systemd_environment_file), `/usr/share/keycloak/bin/../conf` (observed, process_command_option), logs `journalctl -u keycloak.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `algosec-ms`: state `active`, listener ports `8185`, configs `/etc/systemd/system/algosec-ms.service` (observed, systemd_fragment), `/home/afa` (candidate, systemd_working_directory), logs `journalctl -u algosec-ms.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec-ms/logs/` (observed, process_command_option).
- `ms-metro`: state `active`, listener ports `5701, 8080, 8082`, configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory), logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-metro/logs/` (observed, process_command_option), `/data/ms-metro/logs` (candidate, derived_runtime_root).
- `httpd`: state `active`, listener ports `80, 443`, configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin), logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `logstash`: state `active`, listener ports `9600`, configs `/usr/lib/systemd/system/logstash.service` (observed, systemd_fragment), `/etc/sysconfig/logstash` (observed, systemd_environment_file), logs `journalctl -u logstash.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/log/logstash/` (observed, process_command_path), `/data/log/logstash/` (observed, process_command_option).

## Escalate Or Stop When

- The packet does not yet prove the full downstream FireFlow workflow behind aff-boot.
- The packet does not yet replay requests or prove post-handoff business logic behavior.
- No external API success or provider credential correctness is proven in this packet.
- No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.

## Known Boundaries

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Best Next Deepening Step

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

