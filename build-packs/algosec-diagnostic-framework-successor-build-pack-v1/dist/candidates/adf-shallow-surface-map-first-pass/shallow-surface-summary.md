# ADF Successor Shallow Surface Summary

## Scope

- Target: local-host
- Hostname: orch-lab-01
- Components recorded: 333
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## Fast Read

- No bounded route-owner chain is strong enough to headline yet.
- No failed high-signal services were highlighted in this bounded pass.
- Next best seam: `define_second_node_request_shape` from ms-metro, ms-bflow, activemq.

## What Appears To Be Running

- No clearly central components were identified in this first pass.
Top visible candidates from the bounded run:
- `polkit`: identity_or_access (confidence medium, score 3, ports none linked yet) Doc-pack hints: matched terms authorization
- `vgauth`: identity_or_access (confidence medium, score 3, ports none linked yet) Doc-pack hints: matched terms authentication

## Config And Log Surfaces

- `polkit`: configs `/usr/lib/systemd/system/polkit.service` (observed, systemd_fragment); logs `journalctl -u polkit.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `vgauth`: configs `/usr/lib/systemd/system/vgauth.service` (observed, systemd_fragment); logs `journalctl -u vgauth.service --no-pager -n 80` (candidate, systemd_journal_locator).

## Edge-To-Local Route Hints

- No Apache route hints were strong enough to summarize in this pass.

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

- No bounded provider-specific integration packet was strong enough to summarize in this pass.

## Distributed And External Knowledge Layers

- `distributed_and_external_knowledge_layers`: node scope `single_node_only` with cross-node envelope `not_activated`; component guidance `none`; observed local external surfaces `none`; vendor activation `dormant` with dormant inventory `Cisco, Arista, Check Point, F5 BIG-IP, Fortinet`. Next stop: `define_second_node_request_shape`.

## Visible Unknowns

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_fronted_probe could not be collected in this pass.
- aff_session_direct_probe could not be collected in this pass.

## Next Candidate Seams

- `define_second_node_request_shape`: The current node now has explicit activation boundaries for component guidance and external-system hints, so the next bounded move should stay at the control-plane edge instead of widening this one node into a suite graph or vendor-health story. Starting points: ms-metro, ms-bflow, activemq.
- `capture_provider_specific_integration_evidence`: Vendor-side terms are already present in the ASMS doc-pack hint inventory, but this node still lacks provider-specific local evidence. The next useful trigger is a bounded pass that captures config, route, or log markers strong enough to activate a real vendor packet later. Starting points: httpd, ms-metro, keycloak.

