# Project Context

This build pack was materialized from template `algosec-diagnostic-framework-successor-template-pack` and is the active runtime root for `AlgoSec Diagnostic Framework Successor Build Pack v1`.

The project goal carried forward from the template is:

- Create a bounded agent-centered ADF successor template that learns from incomplete technical documentation plus live Rocky 8 appliance discovery, builds machine-readable diagnostic content first, and proves value through an early shallow surface map slice before deeper dependency or predictive work.

## Priority

1. Keep the build-pack control plane authoritative.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack easy for a fresh agent to inspect and continue.

## Primary Runtime Surfaces

- `pack.json`
- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`
- `benchmarks/active-set.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
- optional feedback memory: `.pack-state/agent-memory/latest-memory.json`
- optional template lineage memory: `.pack-state/template-lineage-memory/latest-memory.json`

## Agent-Native Initialization

This build pack is operating with the PackFactory tracker-backed agent-native profile active.
This profile is descriptive only; canonical tracker discovery still comes from `pack.json.directory_contract` and `pack.json.post_bootstrap_read_order`.
Profile: `packfactory_tracker_backed_agent_native` (PackFactory Tracker-Backed Agent-Native).
Activation state: `build_pack_active`.
Work management model: `objective_backlog_work_state` / `tracker_backed_advisory_planning`.
Advisory planning does not override the canonical execution tracker.
This active mode was inherited from the template declaration during materialization.

## Template Lineage Note

The template remains the source-of-truth for reusable scaffold intent, but the build pack is the live control-plane instance.

## Runtime Ownership

The current reviewed operating model is:

- PackFactory root is the canonical build-pack home and control plane
- `adf-dev` is the operational runtime home
- the downstream Rocky 8 or appliance target at `10.167.2.150` is the observed runtime source
- `adf-dev` is currently reachable at `10.167.2.151` and also serves the
  support-facing diagnostic pages consumed by support engineers

Keep remote runtime work heavy and local return thin. The normal return path is
bounded exported runtime evidence plus intentional source or tracker changes,
not a full copy-back of the staged remote workspace.

## Lab Posture

The current successor lab posture is operator-provided and intentionally more
exploratory than a fragile customer environment:

- the current target lab at `10.167.2.150` is quickly redeployable
- bounded misconfiguration or temporary lab breakage is acceptable during
  discovery work
- later distributed-architecture labs are expected as future discovery targets

## Current Layering Frontier

The latest imported target-backed proof now says:

- cross-node topology is still intentionally inactive because only one
  node-local proof exists
- bounded component guidance is now activatable for visible families such as
  `httpd`, `ms-metro`, `ms-bflow`, `activemq`, and `keycloak`
- provider-specific local evidence is now visible for AWS and Azure-side
  surfaces on the target node, while broader vendor inventory from the ASMS
  doc pack remains mostly dormant until stronger local evidence appears

That previously made the next bounded successor seam
`define_second_node_request_shape` rather than reopening the single-node
route, session, or architecture work.

The latest imported target-backed proof now goes one step further:

- the successor carries a bounded `provider_specific_integration_evidence_current_node`
  packet for AWS and Azure
- that packet ties matching Apache family names, local listener ports, service
  units, jar paths, and journal entrypoints together without claiming provider
  health
- adjacent Azure and AWS-side families such as `ms-aad-azure-sensor`,
  `ms-aad-log-sensor`, `ms-cloudflow-broker`, and `ms-cloudlicensing` stay
  visible but separate from the core provider-driver entries

That work has now produced a first imported standalone calibration-node proof
from `algosec-lab-alt-192` (`10.167.2.192`).

That proof matters because it keeps the same `A33.10` family as the current
baseline node `10.167.2.150` while still changing the package patch train and
several provider-driver and adjacent service ports. It confirms that the
successor artifact shape travels beyond a single appliance without needing
target-local Codex on the second node.

That now makes the next bounded successor seam
`capture_standalone_node_calibration_set`, because the strongest remaining
ambiguity is no longer whether one extra standalone node can be imported
cleanly. It is which runtime families and provider surfaces repeat across a
small independent-node set before any distributed-topology claims activate.

## Future Expansion Frontier

The successor now also carries an explicit later-phase expansion frontier in:

- `docs/specs/adf-successor-expansion-frontier-v1.md`
- `docs/specs/adf-successor-standalone-node-review-and-distributed-lab-activation-plan-v1.md`

Those items are planner-visible but intentionally not active yet:

1. activate a multi-node topology map
2. derive a fuller dependency graph
3. capture a health-validated integration model
4. derive a more complete product behavior model

For now, those remain downstream of `capture_second_node_node_local_proof` so
the successor keeps widening from imported proof instead of jumping from a good
single-node map to a premature suite theory.

## Node Expansion Plan

The reviewed node-expansion plan now distinguishes:

- standalone-node review as a calibration and node-archetype program
- distributed-lab activation as the first real topology and cross-node
  behavior program

That distinction matters because the currently available extra nodes are
standalone and independent from each other, and they do not have target-local
Codex installed. The reviewed execution path therefore keeps `adf-dev` as the
runtime owner, uses per-node read-only target-connection profiles, and treats
the first additional standalone node proofs as calibration evidence rather than
as distributed-topology truth.

That calibration set now exists in a useful first form:

- baseline `10.167.2.150` on `A33.10.240`
- standalone sibling `10.167.2.192` on `A33.10.230`
- standalone line-jump node `10.167.2.177` on `A33.20.120`

The bounded archetype readout is recorded in:

- `docs/specs/adf-successor-standalone-node-archetype-comparison-v1.md`

That matters because the successor can now separate stable standalone-node
runtime roles from version-specific drift before any distributed-topology
claims begin.

The reviewed first distributed architecture to inspect is now also pinned:

- `standalone + remote agent`

with `10.167.2.150` retained as the primary standalone node for that first
distributed proof. The reasoning and rollout order are recorded in:

- `docs/specs/adf-successor-standalone-node-review-and-distributed-lab-activation-plan-v1.md`

That first distributed proof now exists in canonical imported form:

- CM node `10.167.2.150`
- remote-agent node `10.167.2.153`
- both currently on the upgraded `A33.10.260` line

The bounded role-separated readout is recorded in:

- `docs/specs/adf-successor-first-distributed-role-separated-proof-review-v1.md`

The first bounded topology readout is now also recorded in:

- `docs/specs/adf-successor-thin-multi-node-topology-map-v1.md`

The first bounded dependency readout is now also recorded in:

- `docs/specs/adf-successor-bounded-dependency-graph-v1.md`

The first bounded integration-health readout is now also recorded in:

- `docs/specs/adf-successor-health-validated-integration-model-v1.md`

The first bounded product-behavior readout is now also recorded in:

- `docs/specs/adf-successor-bounded-product-behavior-model-v1.md`

That matters because the successor has now crossed the boundary from
independent-node comparison into real distributed-lab evidence. The imported
pair shows that both nodes share a meaningful runtime base such as `httpd`,
`ms-metro`, `algosec-ms`, `activemq`, and bounded provider-driver surfaces,
while the CM side retains stronger AFF, BusinessFlow, and identity-facing
signals and the remote-agent side retains a thinner configuration,
device-management, and provider-driver-heavy shape.

That topology step is now complete, and the dependency step is now complete
too. The successor can now say, in a fail-closed way, that both nodes share a
meaningful runtime base, that the CM side keeps the stronger AFF, BusinessFlow,
and identity-facing paths, that the remote-agent side keeps the thinner
management and provider-driver-heavy shape, and that the clearest dependency
hub is Apache routing into `aff-boot`, `ms-bflow`, `ms-metro`, and
`algosec-ms`.

The graph still stays bounded. It treats FireFlow-to-Metro bridge activity and
provider-driver placement as strong inferred edges, while keeping cross-node
directionality, deeper `ms-metro` versus `algosec-ms` ordering, ActiveMQ
direction, and provider health unresolved.

That health step is now complete too. The successor can now say:

- the CM-side AFF session boundary is healthy at its current bounded edge
- the AFA-facing Metro bridge is reachable
- AWS and Azure driver families on both nodes are configured
- Keycloak on the CM is configured but not yet health-validated
- deeper provider-side and cross-node health remains uncertain

That behavior step is now complete as well. The successor can now say:

- the CM node fronts the clearest FireFlow or AFF session path
- FireFlow carries AFA session context into the Metro bridge
- the observed distributed architecture behaves like a CM-plus-remote-agent
  split rather than two identical peer nodes
- provider-driver families are distributed and configured, but not yet
  health-validated end to end

The current bounded roadmap frontier is therefore complete.

The next useful move should now be chosen explicitly rather than inferred from
the old planner slice. Good candidates include:

- deeper provider-health proof
- stronger cross-node directionality proof
- another distributed architecture such as LDU, HA, or DR

That explicit provider-health widening step has now been completed too.

The current successor can now say:

- the AWS and Azure driver families are still clearly present on both the CM
  and remote-agent nodes
- both nodes now also retain the same bounded local degradation pattern for
  those driver families: failed local loopback reachability plus repeated
  runtime-failure journal markers centered on
  `logging.file.maxHistory_IS_UNDEFINED`
- this is still local driver-runtime evidence, not proof of provider-side or
  credential-side failure

That sharpens the next move.

That cross-node directionality widening step has now been completed too.

The current successor can now say:

- one explicit CM-to-RA ingress clue is visible because the remote-agent node
  `10.167.2.153` retains an `httpd` connection on `443` from
  `10.167.2.150`
- the remote-agent side retains the stronger refresh or broadcast-consumer
  hints for `ms-devicemanager`, `ms-devicedriver-aws`, and
  `ms-devicedriver-azure`, with repeated `LegacyContextRefresher`,
  `ConfigurationChangeListener`, and `ActiveMQService` markers
- the CM side does not retain a reciprocal peer clue or comparable
  directionality markers in the same bounded window
- exact provider orchestration direction still remains unresolved

The bounded proof for that step is recorded in:

- `docs/specs/adf-successor-bounded-cross-node-directionality-proof-v1.md`

That reviewed `standalone + LDU` architecture has now been captured too.

The current successor can now say:

- `10.167.2.150` still retains the stronger CM-side `keycloak`, `aff-boot`,
  `/FireFlow/api`, `/aff/api`, and `/BusinessFlow` packets
- `10.167.2.153` now reads as the first bounded LDU-side proof rather than as
  the earlier remote-agent role
- the LDU still carries a meaningful runtime spine around `httpd`,
  `ms-metro`, `algosec-ms`, `activemq`, and degraded AWS and Azure driver
  families
- the LDU-side provider-adjacent families now retain bounded peer clues back
  to `10.167.2.150:61616`, which is enough to treat CM-hosted messaging
  adjacency as visible without claiming the full east-west graph

The bounded proof for that step is recorded in:

- `docs/specs/adf-successor-first-standalone-plus-ldu-proof-review-v1.md`

That reviewed DR-only architecture has now been captured too.

The current successor can now say:

- `10.167.2.150` reads as the active DR primary and still retains the
  stronger `keycloak`, `aff-boot`, `/FireFlow/api`, `/aff/api`,
  `/BusinessFlow`, and `aff_session_route_parity` packets
- `10.167.2.153` reads as the colder DR secondary and retains Apache route
  shape plus `ms-hadr` or `logstash`, but loses the deeper bounded AFF
  route-owner and AFF session-parity packets
- the DR-primary provider packet still retains bounded coordination clues,
  while the DR-secondary provider packet stays more local-only
- this is a cleaner active-versus-standby read than the earlier LDU split,
  but it still does not prove failover success, replication freshness, or the
  complete east-west graph

The bounded proof for that step is recorded in:

- `docs/specs/adf-successor-first-dr-primary-secondary-proof-review-v1.md`

The next widening move should now be chosen explicitly from the next reviewed
stacked or alternate architectures. The strongest follow-on is:

- add the LDU layer onto the current DR shape and capture
  `capture_disaster_recovery_plus_ldu_role_separated_node_proofs`
- then revisit stacked `standalone + LDU + remote agent` or move on to
  `high availability`

## Optional Overlays

Treat `pack.json.personality_template` and `pack.json.role_domain_template` as composable guidance layers. They shape tone and framing, not canonical lifecycle, readiness, deployment, or tracker truth.

## Line-Specific Role/Domain Lens

This build pack currently uses the line-specific `diagnostic-systems-analyst`
lens recorded in:

- `docs/specs/adf-successor-diagnostic-systems-analyst-role-domain-lens-v1.md`

Use it to keep the first wave focused on bounded live system mapping,
machine-readable diagnostic structure, and support-useful stop points.
For the current first wave, also use:

- `docs/specs/adf-successor-shallow-surface-map-first-slice-v1.md`
- `docs/specs/adf-successor-remote-owned-runtime-thin-local-canonical-return-contract-v1.md`

## Derived From

- Source template: `algosec-diagnostic-framework-successor-template-pack`
- Build pack: `algosec-diagnostic-framework-successor-build-pack-v1`
