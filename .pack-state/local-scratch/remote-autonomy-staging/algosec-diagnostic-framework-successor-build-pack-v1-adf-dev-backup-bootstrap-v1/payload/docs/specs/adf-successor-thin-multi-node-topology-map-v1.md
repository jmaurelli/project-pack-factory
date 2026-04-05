# ADF Successor Thin Multi-Node Topology Map v1

## Purpose

Activate the first bounded multi-node topology surface for the successor from
real imported distributed-lab proof.

This artifact stays intentionally thin. It does not try to be a full suite
graph. It only records:

- what appears shared across the observed nodes
- what appears node-specific
- what role hints are now strong enough to say plainly
- what still remains unknown

## Evidence Base

- `eval/history/import-external-runtime-evidence-20260403t172733z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- `eval/history/import-external-runtime-evidence-20260403t172516z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- `docs/specs/adf-successor-first-distributed-role-separated-proof-review-v1.md`

## Observed Nodes

The current topology surface is grounded in two imported node-local proofs from
the first reviewed distributed architecture:

- CM-style node `10.167.2.150`
- remote-agent-style node `10.167.2.153`

Both nodes are currently on the same package line:

- `algosec-appliance-3300.10.260-34`
- `fa-3300.10.260-80`
- `fireflow-3300.10.260-80`
- `fa-platform-3300.10.260-80`

That version alignment matters because the role separation below is less likely
to be just package drift.

## Shared Runtime Base

The imported proofs show a meaningful shared runtime base across both nodes:

- `httpd`
- `ms-metro`
- `algosec-ms`
- `activemq`
- `ms-devicedriver-aws`
- `ms-devicedriver-azure`
- `ms-devicemanager`
- `ms-genericdevice`
- bounded AWS and Azure provider-driver activation packets

This means the current lab is not split into two unrelated products. The nodes
share an overlapping substrate and service vocabulary.

## CM-Strong Topology Signals

The CM-side node `10.167.2.150` retains stronger control-plane and
user-facing signals:

- Apache `aff.conf` routes for `/FireFlow/api` and `/aff/api`
- bounded owner confirmation for local `1989` via `aff-boot`
- bounded AFF session parity
- `ms-bflow` plus `/BusinessFlow` route ownership
- `keycloak`
- broader lineage visibility such as `kibana`, `elasticsearch`, and other
  CM-adjacent surfaces

Topology reading:

- this node currently looks like the stronger CM or primary application node
- it carries the clearest FireFlow, BusinessFlow, and identity-facing entry
  points in the observed pair

## Remote-Agent-Strong Topology Signals

The remote-agent-side node `10.167.2.153` retains a thinner management and
provider-service shape:

- `ms-configuration`
- `ms-devicemanager`
- `ms-genericdevice`
- `ms-devicedriver-aws`
- `ms-devicedriver-azure`
- adjacent provider families such as `ms-aad-azure-sensor`,
  `ms-aad-log-sensor`, and `ms-cloudflow-broker`

What is notably missing from the imported RA proof:

- no AFF owner packet
- no AFF session parity packet
- no `keycloak`-side identity packet

Topology reading:

- this node currently looks more like a thinner remote worker or remote-agent
  role than a full CM-style node
- provider-driver and device-management surfaces are more central here than
  FireFlow or identity-facing paths

## First Honest Topology Picture

The successor can now say the following thin topology picture is supported:

- there is a shared suite base across the observed nodes
- `10.167.2.150` is the stronger CM-like node in the current pair
- `10.167.2.153` is the thinner remote-agent-like node in the current pair
- FireFlow, BusinessFlow, AFF, and identity-facing control paths are stronger
  on the CM side
- provider-driver and device-management surfaces are clearly visible on both
  sides but remain more role-defining on the RA side

## Cross-Node Adjacency Hints

The current topology surface also supports a few bounded adjacency hints:

- provider-driver families are part of the shared distributed vocabulary, not
  a one-node anomaly
- `ms-metro` and `algosec-ms` appear as repeated cross-node runtime families,
  which makes them good candidates for later dependency-edge work
- AFF and session-routing evidence are still node-local to the CM-side proof,
  which makes them poor candidates for immediate cross-node generalization

## Unknowns Kept Explicit

This topology map does not currently prove:

- east-west traffic direction between the nodes
- exact RPC or message ordering across nodes
- cluster membership or failover behavior
- whether provider-driver work is initiated locally, remotely, or both
- whether `ms-metro` and `algosec-ms` play identical roles on both nodes
- complete placement for every package or service family in the distributed
  architecture

## Why This Matters

This is the first point where the successor can talk about a distributed
runtime shape without inventing a full graph.

That matters because the next layer can now focus on dependency edges between
already-observed repeated families instead of spending more time proving that
the topology exists at all.

## Next Step

Derive `derive_full_dependency_graph` from the repeated cross-node runtime
families, the CM-local route ownership, the provider-driver activations, and
the still-bounded unknowns above.
