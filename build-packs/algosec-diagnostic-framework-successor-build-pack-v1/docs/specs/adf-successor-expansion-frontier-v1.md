# ADF Successor Expansion Frontier v1

## Purpose

Record the larger successor capabilities that should remain visible in the
planner without collapsing the current bounded roadmap into premature suite
theory.

The current bounded seam set is now complete.
These expansion targets remain intentionally later-phase follow-ons, but the
first two have now advanced from planner-only intent into active successor
surfaces:

- the first distributed role-separated proof pair exists
- the first thin multi-node topology surface now exists
- the first bounded dependency graph now exists
- the first bounded integration-health model now exists
- the first bounded product-behavior model now exists
- two explicit post-frontier widening experiments now exist too:
  a deeper provider-health proof that refines AWS and Azure from
  placement-only into repeated local degradation signals on both the CM and
  remote-agent nodes, and a bounded cross-node directionality proof that adds
  one observed CM-to-RA ingress clue plus RA-side refresh or
  broadcast-consumer hints without claiming the full east-west graph
- one reviewed next-architecture proof now exists too:
  a first `standalone + LDU` imported role-separated proof that keeps the CM
  side as the stronger AFF, BusinessFlow, and identity-facing node while the
  LDU side stays thinner, edge-heavy, provider-heavy, and visibly adjacent to
  CM-hosted messaging on `10.167.2.150:61616`

## Expansion Order

The reviewed expansion order is:

1. multi-node topology map
2. fuller dependency graph
3. health-validated integration model
4. more complete product behavior model

This order is practical rather than absolute. It reflects the current belief
that cross-node evidence should precede broader system dependency claims, and
that both should precede stronger health and behavior modeling.

## Planned Expansion Targets

### 1. Multi-Node Topology Map

Goal:

- turn multiple imported node-local proofs into a bounded topology surface that
  can explain what appears local, remote, shared, or node-specific across the
  suite

Why it matters:

- this is the first step that lets the successor move from a strong
  single-node explainer into an honest distributed-runtime mapper

Boundary:

- topology should stay evidence-first and fail-closed
- do not invent unseen nodes, links, or roles

### 2. Fuller Dependency Graph

Goal:

- derive a stronger service-to-service and route-to-runtime dependency graph
  from repeated imported proofs, route evidence, listener ownership, config
  surfaces, and retained runtime hints

Why it matters:

- this is the layer that can start answering "what depends on what" with more
  than route packets and local adjacency clues

Boundary:

- keep direct evidence distinct from inferred dependency edges
- avoid claiming total graph completeness until the suite-wide evidence base
  can support it

### 3. Health-Validated Integration Model

Goal:

- advance beyond simple activation hints and local provider markers into a
  model that can say whether an integration appears configured, reachable,
  healthy, degraded, or uncertain

Why it matters:

- support and diagnostic value rises sharply when the successor can separate
  "integration exists" from "integration is actually working"

Boundary:

- do not claim health without bounded runtime, config, route, or log evidence
- keep unknown or weakly supported integrations explicit

### 4. More Complete Product Behavior Model

Goal:

- explain larger end-to-end product behavior across major request, session,
  service, and integration flows instead of only isolated seams

Why it matters:

- this is the layer that can eventually support stronger diagnostic reasoning,
  support navigation, and operator-facing behavior explanations

Boundary:

- behavior modeling must stay grounded in observed packets, imported proofs,
  and clearly-labeled inference
- do not flatten uncertainty into a clean but unsupported product story

## Relationship To The Current Roadmap

These expansion targets are planner-visible on purpose, but they are not the
current active work. The immediate successor path is now further refined by:

- `docs/specs/adf-successor-standalone-node-review-and-distributed-lab-activation-plan-v1.md`

That means the reviewed widening order is:

1. capture and compare standalone calibration nodes
2. capture real distributed-lab role-separated proof
3. activate a thin multi-node topology surface
4. then widen into the remaining expansion frontier in the reviewed order above

## Current Explicit Widening State

The original bounded frontier remains complete.

The next explicitly chosen widening experiment after that closure was:

- `capture_deeper_provider_health_proof`

That step is now complete and recorded in:

- `docs/specs/adf-successor-deeper-provider-health-proof-v1.md`

It matters because the successor can now say more than "AWS and Azure are
present on both nodes." The current proof says the driver families are locally
degraded on both nodes, while still keeping cloud-provider success,
credential-validity, and cross-node directionality unresolved.

The next honest widening seam is now:

- `strengthen_cross_node_directionality_proof`

That step is now complete and recorded in:

- `docs/specs/adf-successor-bounded-cross-node-directionality-proof-v1.md`

It matters because the successor can now separate:

- one directly observed CM-to-RA ingress clue
- RA-side refresh or broadcast-consumer hints for provider-adjacent runtime
  families
- shared local provider-driver degradation
- still-unresolved deeper orchestration direction

The next explicitly chosen reviewed architecture after that directionality step
was:

- `standalone + LDU`

That step is now complete and recorded in:

- `docs/specs/adf-successor-first-standalone-plus-ldu-proof-review-v1.md`

It matters because the successor can now separate:

- the CM-side AFF, FireFlow, BusinessFlow, and identity-facing control paths
- the LDU-side edge-heavy and provider-heavy role shape
- the shared runtime spine that still exists on both nodes
- one bounded LDU-side messaging adjacency back to CM `10.167.2.150:61616`

The next explicitly chosen reviewed architecture after that LDU step was:

- `disaster recovery`

That step is now complete and recorded in:

- `docs/specs/adf-successor-first-dr-primary-secondary-proof-review-v1.md`

It matters because the successor can now separate:

- an active-looking DR primary that retains the stronger AFF, FireFlow,
  BusinessFlow, and identity-facing packets
- a colder standby-style DR secondary that keeps Apache route shape but loses
  the deeper AFF route-owner and session-parity proof
- the difference between persistent route configuration and deeper runtime
  ownership on a standby-style node
- bounded DR-primary coordination clues versus more local-only DR-secondary
  provider evidence

The next widening move should now be chosen explicitly from the next stacked
or alternate reviewed architecture types rather than inferred from the old
frontier slice. The strongest follow-on is:

- `capture_disaster_recovery_plus_ldu_role_separated_node_proofs`
