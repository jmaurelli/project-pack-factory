# ADF Successor Diagnostic Playbook

## Use This For

- Live triage on `algosec-dr-secondary-153` when the engineer needs the fastest bounded owner, evidence, and escalation path.
- Decision support under pressure, not full product study.
- A fast route from symptom to local owner, first checks, and explicit stop rules.

## Fast Start

- Strongest current owner chain: `/FireFlow/api` currently points toward `http://localhost:1989/aff/api/external` with likely owner `httpd`.
- Provider warning: local degradation is visible for `ms-devicedriver-aws`, `ms-devicedriver-azure`, but provider-side success is still not proven.
- Failed or degraded-looking services worth checking early: `activemq`, `ms-bflow`, `ms-metro`.

## Route To Owner Shortlist

- `/FireFlow/api` -> `httpd` via `http://localhost:1989/aff/api/external` from `/etc/httpd/conf.d/aff.conf:6`.
- `/aff/api` -> `httpd` via `http://localhost:1989/aff/api` from `/etc/httpd/conf.d/aff.conf:16`.

## First Checks By Family

- `activemq`: state `failed`, listener ports `none linked yet`, configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment), logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `ms-bflow`: state `failed`, listener ports `none linked yet`, configs `/etc/systemd/system/ms-bflow.service` (observed, systemd_fragment), `/etc/systemd/system/ms-bflow.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory), logs `journalctl -u ms-bflow.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `ms-metro`: state `failed`, listener ports `none linked yet`, configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory), logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `httpd`: state `active`, listener ports `80, 443`, configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin), logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `logstash`: state `active`, listener ports `9600`, configs `/usr/lib/systemd/system/logstash.service` (observed, systemd_fragment), `/etc/sysconfig/logstash` (observed, systemd_environment_file), logs `journalctl -u logstash.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/log/logstash/` (observed, process_command_path), `/data/log/logstash/` (observed, process_command_option).

## Escalate Or Stop When

- No external API success or provider credential correctness is proven in this packet.
- No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.

## Known Boundaries

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_direct_probe could not be collected in this pass.

## Best Next Deepening Step

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

