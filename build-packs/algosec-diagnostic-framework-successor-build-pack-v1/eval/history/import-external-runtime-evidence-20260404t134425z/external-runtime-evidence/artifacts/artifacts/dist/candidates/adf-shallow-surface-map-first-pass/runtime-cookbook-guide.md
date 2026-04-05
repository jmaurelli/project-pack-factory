# ADF Successor Runtime Cookbook Guide

## Purpose

- Preserve the richer product-learning view that sits behind the fast diagnostic playbook.
- Keep the explanation grounded in observed runtime packets instead of broad suite folklore.
- Help engineers translate product-facing paths into runtime-facing owners, seams, and evidence surfaces.

## Current Runtime Shape

- `keycloak` currently reads as `identity_or_access` on ports `8443, 9000, 29377`.
- `opsec_collect_c` currently reads as `application_service` on ports `1989, 5701, 8080, 8081`.
- `algosec-ms` currently reads as `application_service` on ports `8185`.
- `ms-metro` currently reads as `application_service` on ports `5701, 8080, 8082`.
- `activemq` currently reads as `queue_or_messaging` on ports `61616`.
- `httpd` currently reads as `edge_proxy` on ports `80, 443`.

## Product Language To Runtime Owners

- `/FireFlow/api` -> `aff-boot` on local ports `1989`.
- `/aff/api` -> `aff-boot` on local ports `1989`.
- `(route path not explicit)` -> `ms-bflow` via `http://127.0.0.1:8081/BusinessFlow/$1` from `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:3`.
- `/BusinessFlow` -> `ms-bflow` via `http://127.0.0.1:8081/BusinessFlow` from `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:12`.

## Proven Packets And Why They Matter

### Boundary packets

- AFF or FireFlow 1989 Route Owner Packet is `bounded_owner_confirmed`. This packet keeps Apache route ownership, the local 1989 listener, and the owning service family in one bounded proof surface. Confirmed elements: Apache aff.conf points `/FireFlow/api` and `/aff/api` at local port 1989.; The local 1989 listener is attached to the aff-boot service family through descendant PID ownership.

### Session parity packets

- AFF Session Route Parity Packet is `parity_confirmed`. This packet checks whether the fronted Apache AFF session path and the direct aff-boot local session path still behave the same before widening into later FireFlow behavior. Confirmed elements: httpd.service, ms-bflow.service, and aff-boot.service all report active.; The Apache-fronted `/FireFlow/api/session` probe and the direct aff-boot `/aff/api/external/session` probe returned the same observable response.

### UserSession bridge packets

- FireFlow UserSession Bridge Packet is `bridge_signals_visible`. This packet uses bounded retained evidence to show whether the next support-useful stop behind the confirmed AFF session route is the FireFlow UserSession bridge. Confirmed elements: Apache retained markers still show `/FireFlow/api/session`-family activity.; Retained FireFlow logs show UserSession-style markers such as `UserSession::getUserSession`, `isUserSessionValid`, `ff-session`, or reused FA session hints.

### Provider packets

- Provider-Specific Integration Evidence Current Node is `local_provider_health_partially_classified`. This packet keeps AWS and Azure provider evidence fail-closed while sharpening local classification from merely configured toward bounded reachable or degraded states where the current node evidence actually supports that. Confirmed elements: The current node exposes bounded provider-driver surfaces for `AWS`, `Azure` through matching Apache family names, local service units, and listener ownership.; Recent local failure signals are now visible for `AWS`, `Azure`, so those provider-driver surfaces should be treated as degraded rather than merely present.

### Knowledge-layer packets

- Distributed And External Knowledge Layer Packet is `single_node_layering_ready`. This packet marks which outside knowledge layers the current node can honestly activate now, so the successor can stay evidence-first while preparing for later cross-node and provider-side expansion. Confirmed elements: The current proof is still a single-node readout for `algosec-lab-alt-177`, so cross-node claims remain intentionally inactive.; Observed runtime lineage is now strong enough to layer bounded component guidance for `httpd`, `activemq`, `keycloak`, `kibana`, `elasticsearch`, `logstash` without treating that guidance as node-local fact.


## Config And Log Entry Points

- `keycloak`: configs `/usr/lib/systemd/system/keycloak.service` (observed, systemd_fragment), `/usr/share/keycloak/keycloak_service.conf` (observed, systemd_environment_file), `/usr/share/keycloak/bin/../conf` (observed, process_command_option); logs `journalctl -u keycloak.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `opsec_collect_c`: configs none visible; logs none visible.
- `algosec-ms`: configs `/etc/systemd/system/algosec-ms.service` (observed, systemd_fragment), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u algosec-ms.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec-ms/logs/` (observed, process_command_option).
- `ms-metro`: configs `/etc/systemd/system/ms-metro.service` (observed, systemd_fragment), `/etc/systemd/system/ms-metro.service.d/limits.conf` (observed, systemd_dropin), `/home/afa` (candidate, systemd_working_directory); logs `journalctl -u ms-metro.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/ms-metro/logs/` (observed, process_command_option), `/data/ms-metro/logs` (candidate, derived_runtime_root).
- `activemq`: configs `/etc/systemd/system/activemq.service` (observed, systemd_fragment), `/opt/apache-activemq-6.2.0/conf/jolokia-access.xml` (observed, process_command_path), `/opt/apache-activemq-6.2.0/conf/login.conf` (observed, process_command_path); logs `journalctl -u activemq.service --no-pager -n 80` (candidate, systemd_journal_locator), `/data/algosec/work/` (observed, process_command_option).
- `httpd`: configs `/usr/lib/systemd/system/httpd.service` (observed, systemd_fragment), `/etc/systemd/system/httpd.service.d/algosec.conf` (observed, systemd_dropin), `/etc/systemd/system/httpd.service.d/php83-php-fpm.conf` (observed, systemd_dropin); logs `journalctl -u httpd.service --no-pager -n 80` (candidate, systemd_journal_locator).

## What Is Still Not Proven

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- No external API success or provider credential correctness is proven in this packet.
- No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.
- No cross-node role or suite-topology claim is made from this current-node packet.

## Best Follow-On Study Paths

- `strengthen_cross_node_directionality_proof`: The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair. Starting points: ms-devicedriver-aws, ms-devicedriver-azure.

