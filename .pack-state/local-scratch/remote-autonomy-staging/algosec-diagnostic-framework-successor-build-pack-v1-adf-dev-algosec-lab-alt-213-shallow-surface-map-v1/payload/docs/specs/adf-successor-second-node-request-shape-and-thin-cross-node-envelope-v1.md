# ADF Successor Second-Node Request Shape And Thin Cross-Node Envelope v1

## Purpose

Define the first reusable request shape for a second node-local ADF successor
pass and pin the boundary between:

- one node-local shallow surface map
- the later thin cross-node envelope

This note keeps the successor honest. It does not authorize a synthetic suite
graph, and it does not assume a second lab target already exists.

## Evidence Base

- Knowledge-layer activation proof:
  `eval/history/import-external-runtime-evidence-20260403t115837z/`
- Activation review:
  `docs/specs/adf-successor-distributed-and-external-knowledge-activation-review-v1.md`
- Layering plan:
  `docs/specs/adf-successor-distributed-and-external-knowledge-layering-v1.md`

## Why This Slice Exists

The current imported proof already says the next bounded seam is
`define_second_node_request_shape`.

That is the right next step because:

- the current blocker on distributed understanding is no longer theory
- it is the absence of a second imported node-local proof bundle
- the successor should solve that by standardizing the next node request and
  the later comparison envelope, not by widening the current node-local map

## Reusable Second-Node Request Shape

The second-node pass should reuse the same remote-owned runtime pattern:

- PackFactory root stays canonical
- `adf-dev` stays the operational runtime home
- the second target node becomes a new observed runtime source
- the return path stays bounded export plus import, not a workspace copy-back

### Request Inputs

The second-node run request should fill these fields explicitly:

- `run_id`
  format: `algosec-diagnostic-framework-successor-build-pack-v1-adf-dev-<node-label>-shallow-surface-map-v1`
- `remote_host`
  keep `adf-dev`
- `remote_user`
  keep `adf`
- `remote_target_label`
  keep `adf-dev`
- `target_label`
  set to the second observed node label or IP
- `target_connection_profile`
  point to a node-specific read-only profile under `docs/remote-targets/<node-label-or-pack-label>/`
- `mirror_into_run_id`
  match the same `run_id`
- `remote_reason`
  state plainly that this is a second node-local proof, not a suite-graph run

### Required Runner Shape

The reviewed runner remains:

```bash
set -euo pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack generate-shallow-surface-map \
  --project-root . \
  --target-label <second-node-label> \
  --target-connection-profile docs/remote-targets/<second-node-profile-dir>/target-connection-profile.json \
  --mirror-into-run-id <run-id> \
  --output json
```

This keeps the second node on the same bounded CLI surface as the first node.

### Required Wrapper Shape

The roundtrip wrapper should stay the same class of request used today:

- `pull_bundle: true`
- `import_bundle: true`
- canonical local scratch staging under
  `.pack-state/local-scratch/remote-autonomy-roundtrips/.../<run-id>/incoming`
- import reason that says the bundle is a second node-local proof for later
  cross-node comparison

## Node-Local Map Vs Cross-Node Envelope

### Keep In The Node-Local Map

Each node-local map should continue to keep:

- `target`
- `target_connection`
- `runtime_identity`
- `component_records`
- `edge_route_hints`
- all bounded packets such as route, session, Java-cluster, and knowledge-layer
  packets
- `unknowns`
- `next_candidate_seams`

Rule:

- do not flatten these fields into one suite-wide merged map

### Add Later In The Thin Cross-Node Envelope

Only after at least two imported node-local bundles exist, add a separate
envelope artifact with fields like:

- `node_map_refs`
  imported bundle ids or paths for each node-local proof
- `nodes`
  node label, hostname, and operator-supplied or observed role labels
- `repeated_runtime_families`
  repeated Tomcat, wrapper, messaging, identity, or substrate families
- `cross_node_endpoint_hints`
  only clearly observed cross-node endpoints
- `shared_packaging_patterns`
  where node-local packaging looks similar
- `unresolved_cross_node_edges`
  edges still visible only as ambiguity
- `conflicts`
  disagreements between node-local proofs that should be preserved

Rule:

- the envelope compares nodes; it does not replace the node-local maps

## Explicit Non-Claims

The second-node request shape does not authorize:

- full dependency order
- cluster membership claims
- a merged suite graph
- east-west traffic truth
- vendor-integration health claims

## Implementation Surface

The concrete reusable artifacts for this slice are:

- `docs/specs/adf-successor-second-node-request-shape-and-thin-cross-node-envelope-v1.md`
- `docs/remote-targets/adf-dev/remote-autonomy-second-node-shallow-surface-map-run-request.template.json`
- `docs/remote-targets/adf-dev/remote-autonomy-second-node-test-request.template.json`

## Best Next Step

With the request shape now pinned and the provider-evidence packet now
captured, the next grounded seam is `capture_second_node_node_local_proof`.

That is the better near-term follow-up because the current node no longer
lacks bounded AWS and Azure-side activation evidence. The strongest remaining
ambiguity is now what a second imported node-local proof changes, preserves, or
disproves before any thin cross-node envelope activates.
