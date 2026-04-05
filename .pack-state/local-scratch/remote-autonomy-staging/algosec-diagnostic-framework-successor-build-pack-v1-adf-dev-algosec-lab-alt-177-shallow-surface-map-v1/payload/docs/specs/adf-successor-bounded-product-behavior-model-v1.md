# ADF Successor Bounded Product Behavior Model v1

## Purpose

Tie the strongest current successor surfaces into one support-useful product
behavior readout without pretending the full suite is completely known.

This model is grounded in:

- route ownership
- session parity
- retained session and cookie-handoff packets
- thin multi-node topology
- bounded dependency edges
- bounded health states

## Evidence Base

- `docs/specs/adf-successor-thin-multi-node-topology-map-v1.md`
- `docs/specs/adf-successor-bounded-dependency-graph-v1.md`
- `docs/specs/adf-successor-health-validated-integration-model-v1.md`
- `eval/history/import-external-runtime-evidence-20260403t172733z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t110310z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t105216z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t105216z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`

## Strongest Proven Behavior Story

### 1. Front Door To AFF Session Boundary

The clearest proven product behavior on the CM node is:

- Apache receives the FireFlow or AFF-facing request
- `/FireFlow/api` and `/aff/api` route into `aff-boot` on local `1989`
- `/FireFlow/api/session` and the direct local
  `/aff/api/external/session` path behave the same at the current bounded edge
- the current returned body is the same `INVALID_SESSION_KEY` response on both
  paths
- BusinessFlow deep health still reports `AFF connection = true`

Behavior reading:

- the successor can now say the CM node’s Apache-to-AFF session boundary is
  coherent and healthy at its current edge
- it cannot yet say a full authenticated FireFlow workflow is healthy end to
  end

### 2. FireFlow Session Handling Reuses AFA Session Context

The strongest retained session-side behavior story is:

- FireFlow UserSession markers are visible behind the confirmed AFF edge
- the retained proof shows concrete `ff-session -> reused FA-session` pairs
- the same session family shows a bounded bootstrap anchor and then later
  shared polling behavior

Behavior reading:

- FireFlow session handling is not isolated from the AFA-side session context
- the current product behavior appears to reuse an existing FA-session rather
  than creating a brand-new isolated FireFlow-only session for every request

### 3. FireFlow Or AFF Carries Into The AFA Or Metro Bridge

The strongest bridge-side behavior story is:

- FireFlow session `bcbefc00d0` carries a token through
  `/afa/external//bridge/storeFireflowCookie`
- the same token family later appears on `/afa/external//session/extend`
- those bridge surfaces route into `ms-metro` on local `8080`

Behavior reading:

- the successor can now say the CM node’s FireFlow or AFF-side session behavior
  crosses into the AFA-facing Metro bridge
- it cannot yet say exactly which external browser action began that chain

## Strongest Distributed Behavior Story

The current multi-node behavior story is thinner but still useful:

- both nodes share a runtime spine around `httpd`, `ms-metro`, `algosec-ms`,
  `activemq`, and AWS or Azure driver families
- the CM node keeps the richer FireFlow, BusinessFlow, AFF, and
  identity-facing behavior surfaces
- the remote-agent node keeps the thinner configuration, device-management, and
  provider-driver-heavy behavior surfaces

Behavior reading:

- the current distributed architecture behaves like a CM-plus-remote-agent
  split, not two identical peer nodes
- provider-driver families are distributed across the pair
- FireFlow or AFF session behavior is still CM-local in the current proof

## Strongest Health-Backed Behavior Claims

The current proof safely supports these behavior-level health claims:

- the CM-side AFF session edge is healthy at its current boundary
- the AFA-facing Metro bridge is reachable
- AWS and Azure driver families are configured on both the CM and remote-agent
  nodes
- Keycloak is configured on the CM but not yet health-validated

## Support-Useful Takeaways

### If FireFlow Or AFF Looks Broken

Start on the CM node, not the remote agent.

Why:

- the strongest route, parity, session, and cookie-handoff surfaces are all
  CM-local

### If Provider Integrations Look Wrong

Treat both nodes as relevant and keep the first question narrow:

- is the family merely configured
- or is there any evidence of actual provider-side success

Why:

- the drivers are distributed across both nodes, but the current proof still
  does not promote them beyond configured placement

### If Identity Looks Wrong

Start with the CM-side Keycloak surface and do not assume the remote agent is a
full identity peer.

Why:

- Keycloak is visible on the CM and not retained in the RA proof

## Unknowns Kept Explicit

This behavior model still does not prove:

- the original external browser or caller action that created the FireFlow
  session
- exact east-west request ordering between CM and remote agent
- whether `ms-metro` or `algosec-ms` is the stronger internal orchestrator
- provider-side API success, credential correctness, or freshness
- full authenticated user-flow behavior through Keycloak
- a total product-behavior story for the entire suite

## Operator Readout

The current successor can now say:

- Apache on the CM fronts a healthy AFF session boundary
- FireFlow behavior reuses and carries AFA session context instead of staying
  isolated
- that carried session context crosses into the AFA-facing Metro bridge
- the distributed lab looks like a CM-plus-remote-agent split with shared
  provider-driver vocabulary and CM-local FireFlow or identity emphasis
- provider integrations are visibly placed and configured, but not yet
  health-validated end to end

## Next Step

No same-tier roadmap item remains inside the current bounded frontier.

The next useful move should be chosen explicitly from one of these widening
options:

- deeper provider-health proof
- stronger cross-node directionality proof
- a new distributed architecture such as LDU, HA, or DR
- refreshed live evidence after another lab change
