# ADF Successor Parallel Standalone Deepening Autonomy-Loop Plan v1

## Purpose

Keep enriching standalone-node system knowledge while the operator is busy
building the next distributed architectures.

This plan exists so the successor can keep learning without waiting for the
next `DR + LDU`, `HA`, or later stacked lab to finish building.

## Why This Matters Now

The successor already has useful architecture-level proof for:

- standalone + remote agent
- standalone + LDU
- DR primary + DR secondary

That means the best parallel use of time is no longer "invent another
architecture story early." It is:

- deepen the standalone runtime map
- improve reusable per-node knowledge packets
- make the support-facing playbook and cookbook layers richer
- keep the autonomy handoff path strong while the operator keeps changing lab
  topology elsewhere

## Boundary

This plan does not replace the current main distributed next step:

- `capture_disaster_recovery_plus_ldu_role_separated_node_proofs`

Instead, it adds a second lane that can run in parallel whenever one or more
stable standalone targets are available.

## Operating Model

- PackFactory root stays canonical for source, tracker, readiness, and import.
- `adf-dev` stays the runtime owner.
- stable standalone targets stay read-only observed nodes reached from
  `adf-dev`.
- canonical proof still returns through bounded export and import.

## Standalone Target Strategy

Prefer stable standalone nodes that are not currently being reused for active
distributed-architecture rebuilds.

The practical order is:

1. use any operator-provided standalone node that is expected to stay up for a
   while
2. otherwise reuse already-known standalone siblings such as `10.167.2.192`
   and `10.167.2.177`
3. treat `10.167.2.150` as a standalone deepening target only when it is not
   in the middle of a distributed rebuild

## Loop 1: Live Knowledge-Capture Loop

This is the main successor work loop.

Use the current build-pack, the current `adf-dev` runtime home, and the
official node-local request surfaces:

1. create or refresh a standalone target-connection profile
2. create the matching `adf-dev` run and test request files
3. run `python3 tools/run_remote_autonomy_test.py ...`
4. import the returned proof bundle into the successor pack
5. update bounded knowledge artifacts, not broad suite theory

This loop should enrich:

- service-family and role classification
- package or version drift readouts
- config and log locator coverage
- failed-service and degraded-service packet quality
- provider-driver local health evidence
- route-owner and route-residue coverage
- engineer playbook and cookbook depth

## Loop 2: Active-Task Continuity Loop

Use the current long-lived successor pack only when the tracker is at a
compatible active-task boundary.

Preferred control-plane tools:

- `python3 tools/run_local_mid_backlog_checkpoint.py ...`
- `python3 tools/run_remote_active_task_continuity_test.py ...`

Use this loop when:

- the next standalone-deepening task is clear
- a pause or restart is likely
- we want the remote `adf-dev` worker to continue a bounded standalone task
  without losing canonical state

## Loop 3: Ready-Boundary Continuity Loop

Use this only if the long-lived successor pack legitimately reaches the
required ready boundary.

Tool:

- `python3 tools/run_remote_memory_continuity_test.py ...`

This is not the main standalone-learning loop. It is a bounded continuity
check for a pack that has genuinely reached the ready boundary.

## Loop 4: Proving-Ground Autonomy Hardening Loop

Use fresh proving-ground packs when we want to stress autonomy itself rather
than to claim new standalone runtime truth.

Useful factory tools:

- `python3 tools/run_longer_backlog_autonomy_exercise.py ...`
- `python3 tools/run_branching_autonomy_exercise.py ...`
- `python3 tools/run_degraded_connectivity_autonomy_exercise.py ...`
- `python3 tools/run_semantic_branch_choice_exercise.py ...`
- `python3 tools/run_operator_hint_branch_choice_exercise.py ...`

Those proving-ground results can justify reusable autonomy improvements, but
they do not count as standalone target-system knowledge by themselves.

## Practical Standalone Deepening Backlog

While distributed architectures are in flux, the best standalone deepening
targets are:

1. richer failed-service and degraded-service packets
2. stronger version-drift and package-line mapping across standalone nodes
3. deeper config-root and log-root discovery for major service families
4. cleaner provider-driver packet separation and local health evidence
5. richer route-residue and route-family coverage for Apache-fronted paths
6. richer support-facing playbook and cookbook derivation from the canonical
   JSON map

## Expected Outputs

If this plan works, the successor should accumulate:

- more imported standalone proof bundles
- stronger reusable node-archetype comparisons
- better bounded service, route, config, and health packets
- richer diagnostic-playbook and runtime-cookbook content
- better restart and remote-continuation resilience on the long-lived pack

## Explicit Non-Claims

This plan does not claim:

- new distributed topology truth
- failover truth
- full east-west directionality
- provider-side success
- promotion-ready certification for the current long-lived pack

Fresh-pack certification still belongs to the official rehearsal workflows on
fresh proving-ground packs, not to this evolving successor instance.

## Recommended Parallel Priority

While the operator keeps building the next distributed architecture, the
successor should prefer this parallel order:

1. run another stable standalone knowledge-capture pass
2. update standalone-facing packets and engineer-facing derived artifacts
3. checkpoint and prove active-task continuity when a bounded standalone task
   is in flight
4. use proving-ground autonomy exercises only when the autonomy workflow
   itself needs hardening

## Immediate Guidance

Keep the main roadmap honest:

- main distributed next step: `capture_disaster_recovery_plus_ldu_role_separated_node_proofs`

Keep the parallel lane productive:

- use stable standalone nodes plus official `adf-dev` request wrappers to keep
  enriching standalone runtime knowledge while the operator is still building
  the next DA type
