# ADF Successor Runtime Cookbook Guide

## Purpose

- Preserve the richer product-learning view that sits behind the fast diagnostic playbook.
- Keep the explanation grounded in observed runtime packets instead of broad suite folklore.
- Help engineers translate product-facing paths into runtime-facing owners, seams, and evidence surfaces.

## Current Runtime Shape

- `httpd` currently reads as `edge_proxy` on ports `80, 443`.
- `logstash` currently reads as `application_service` on ports `9600`.
- `ms-hadr` currently reads as `application_service` on ports `9595`.
- `elastic-ssh-tunnel` currently reads as `application_service` on ports `9200, 9300`.
- `ssh-connections-monitor` currently reads as `application_service` on ports `9200, 9300`.
- `gssproxy` currently reads as `edge_proxy` on ports `none linked yet`.

## Product Language To Runtime Owners

- `/FireFlow/api` -> `httpd` via `http://localhost:1989/aff/api/external` from `/etc/httpd/conf.d/aff.conf:6`.
- `/aff/api` -> `httpd` via `http://localhost:1989/aff/api` from `/etc/httpd/conf.d/aff.conf:16`.

## Proven Packets And Why They Matter

### Provider packets

- Provider-Specific Integration Evidence Current Node is `local_provider_health_partially_classified`. This packet keeps AWS and Azure provider evidence fail-closed while sharpening local classification from merely configured toward bounded reachable or degraded states where the current node evidence actually supports that. Confirmed elements: The current node exposes bounded provider-driver surfaces for `AWS`, `Azure` through matching Apache family names, local service units, and listener ownership.; Recent local failure signals are now visible for `AWS`, `Azure`, so those provider-driver surfaces should be treated as degraded rather than merely present.

### Knowledge-layer packets

- Distributed And External Knowledge Layer Packet is `single_node_layering_ready`. This packet marks which outside knowledge layers the current node can honestly activate now, so the successor can stay evidence-first while preparing for later cross-node and provider-side expansion. Confirmed elements: The current proof is still a single-node readout for `algosec-dr-secondary-153`, so cross-node claims remain intentionally inactive.; Observed runtime lineage is now strong enough to layer bounded component guidance for `httpd`, `activemq`, `logstash` without treating that guidance as node-local fact.


## Config And Log Entry Points

- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php74-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `logstash`: configs `/usr/lib/systemd/system/logstash.service` (observed, systemd_fragment), `/etc/sysconfig/logstash` (observed, systemd_environment_file); logs `journalctl -u logstash.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/log/logstash/` (observed, process_command_path), `/data/log/logstash/` (observed, process_command_option).
- `ms-hadr`: configs `/etc/systemd/system/ms-hadr.service` (observed, systemd_fragment); logs `journalctl -u ms-hadr.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `elastic-ssh-tunnel`: configs `/etc/systemd/system/elastic-ssh-tunnel.service` (observed, systemd_fragment); logs `journalctl -u elastic-ssh-tunnel.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `ssh-connections-monitor`: configs `/etc/systemd/system/ssh-connections-monitor.service` (observed, systemd_fragment); logs `journalctl -u ssh-connections-monitor.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `gssproxy`: configs `/usr/lib/systemd/system/gssproxy.service` (observed, systemd_fragment); logs `journalctl -u gssproxy.service --no-pager -n 80` (candidate, systemd_journal_locator).

## What Is Still Not Proven

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_direct_probe could not be collected in this pass.
- No external API success or provider credential correctness is proven in this packet.
- No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.
- No cross-node role or suite-topology claim is made from this current-node packet.

## Best Follow-On Study Paths

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

