# ADF Successor Diagnostic Playbook

## Use This For

- Live triage on `local-host` when the engineer needs the fastest bounded owner, evidence, and escalation path.
- Decision support under pressure, not full product study.
- A fast route from symptom to local owner, first checks, and explicit stop rules.

## Fast Start

- This bounded pass has not yet produced a strong pressure-path headline.

## Route To Owner Shortlist

- No bounded route-owner shortlist is ready yet.

## First Checks By Family

- `polkit`: state `active`, listener ports `none linked yet`, configs `/usr/lib/systemd/system/polkit.service` (observed, systemd_fragment), logs `journalctl -u polkit.service --no-pager -n 80` (candidate, systemd_journal_locator).
- `vgauth`: state `active`, listener ports `none linked yet`, configs `/usr/lib/systemd/system/vgauth.service` (observed, systemd_fragment), logs `journalctl -u vgauth.service --no-pager -n 80` (candidate, systemd_journal_locator).

## Escalate Or Stop When

- Stop when the current packet chain stops proving ownership and would require broad product guessing.

## Known Boundaries

- The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.
- aff_session_fronted_probe could not be collected in this pass.
- aff_session_direct_probe could not be collected in this pass.

## Best Next Deepening Step

- `define_second_node_request_shape`: The current node now has explicit activation boundaries for component guidance and external-system hints, so the next bounded move should stay at the control-plane edge instead of widening this one node into a suite graph or vendor-health story. Starting points: ms-metro, ms-bflow, activemq.
- `capture_provider_specific_integration_evidence`: Vendor-side terms are already present in the ASMS doc-pack hint inventory, but this node still lacks provider-specific local evidence. The next useful trigger is a bounded pass that captures config, route, or log markers strong enough to activate a real vendor packet later. Starting points: httpd, ms-metro, keycloak.

