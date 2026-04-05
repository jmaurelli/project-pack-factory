# ADF Successor Runtime Cookbook Guide

## Purpose

- Preserve the richer product-learning view that sits behind the fast diagnostic playbook.
- Keep the explanation grounded in observed runtime packets instead of broad suite folklore.
- Help engineers translate product-facing paths into runtime-facing owners, seams, and evidence surfaces.

## Current Runtime Shape

- `polkit` is a top visible candidate for `identity_or_access` in this bounded pass.
- `vgauth` is a top visible candidate for `identity_or_access` in this bounded pass.

## Product Language To Runtime Owners

- Product-facing route ownership is still too thin to summarize cleanly.

## Proven Packets And Why They Matter

### Knowledge-layer packets

- Distributed And External Knowledge Layer Packet is `single_node_layering_ready`. This packet marks which outside knowledge layers the current node can honestly activate now, so the successor can stay evidence-first while preparing for later cross-node and provider-side expansion. Confirmed elements: The current proof is still a single-node readout for `local-host`, so cross-node claims remain intentionally inactive.; Vendor-side terms `Cisco`, `Arista`, `Check Point`, `F5 BIG-IP`, `Fortinet` are present in the doc-pack hint inventory, but they remain dormant until provider-specific local evidence appears on the node.


## Config And Log Entry Points

- `polkit`: configs `/usr/lib/systemd/system/polkit.service` (observed, systemd_fragment); logs `journalctl -u polkit.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `vgauth`: configs `/usr/lib/systemd/system/vgauth.service` (observed, systemd_fragment); logs `journalctl -u vgauth.service --no-pager -n 80` (candidate, systemd_journal_locator).

## What Is Still Not Proven

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_fronted_probe could not be collected in this pass.
- aff_session_direct_probe could not be collected in this pass.
- No bounded Apache route hints were linked to local services in this pass.

## Best Follow-On Study Paths

- `define_second_node_request_shape`: The current node now has explicit activation boundaries for component guidance and external-system hints, so the next bounded move should stay at the control-plane edge instead of widening this one node into a suite graph or vendor-health story. Starting points: ms-metro, ms-bflow, activemq.
- `capture_provider_specific_integration_evidence`: Vendor-side terms are already present in the ASMS doc-pack hint inventory, but this node still lacks provider-specific local evidence. The next useful trigger is a bounded pass that captures config, route, or log markers strong enough to activate a real vendor packet later. Starting points: httpd, ms-metro, keycloak.

