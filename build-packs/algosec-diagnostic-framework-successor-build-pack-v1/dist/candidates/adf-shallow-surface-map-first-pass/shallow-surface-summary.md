# ADF Successor Shallow Surface Summary

## Scope

- Target: local-host
- Hostname: orch-lab-01
- Components recorded: 336
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- No clearly central components were identified in this first pass.
Top visible candidates from the bounded run:
- `polkit`: identity_or_access (confidence medium, score 3, ports none linked yet) Doc-pack hints: matched terms authorization
- `ssh`: system_service (confidence low, score 3, ports 18081, 18083)
- `vgauth`: identity_or_access (confidence medium, score 3, ports none linked yet) Doc-pack hints: matched terms authentication

## Visible Unknowns

- The first pass does not yet parse config files, unit fragments, or logs.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `trace_edge_to_local_service_routes`: Several visible listeners suggest a bounded next pass through proxy-to-local-service ownership. Starting points: ssh.

