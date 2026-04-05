# ADF Successor Standalone-Node Review And Distributed-Lab Activation Plan v1

## Purpose

Turn the successor's next node-expansion work into a concrete reviewed plan.

This note separates two different goals that should not be mixed together:

- standalone-node review, which is primarily a calibration and comparison
  program
- distributed-lab activation, which is the first real topology and
  cross-node-behavior program

## Current Reality

Today:

- `10.167.2.150` is the current node-local proof source
- `adf-dev` at `10.167.2.151` remains the operational runtime home and the
  support-facing publication host
- the currently available additional nodes are standalone and independent from
  each other
- Codex is not installed on those additional nodes
- later distributed-architecture labs are operator-available when deeper
  discovery is worth the cost

That means the next node work should stay honest:

- standalone nodes do not yet prove distributed topology
- they do help harden the successor's node-local model
- distributed labs are where topology, dependency, and broader behavior
  modeling start becoming evidence-rich

## Execution Model

The remote-owned runtime model does not change.

- PackFactory root stays canonical for source, tracker, readiness, and import
- `adf-dev` stays the runtime owner
- additional nodes are read-only observed targets reached from `adf-dev`
- returned proof stays bounded export plus import

Because target-local Codex is absent on the additional nodes, the reviewed
execution path stays:

1. create one target-connection profile per node
2. instantiate the existing second-node request templates from `adf-dev`
3. run the same bounded `generate-shallow-surface-map` command from `adf-dev`
4. mirror artifacts into the run root
5. import the returned bundle back into PackFactory

No target-local Codex installation is required for this phase.

## Phase 1: Standalone-Node Review

### Goal

Capture two or more additional node-local proofs from standalone nodes to test
whether the successor's current evidence model generalizes beyond
`10.167.2.150`.

### Use Cases

- check whether the current node looks typical or unusual
- identify repeated service families across independent nodes
- identify node-specific families or packaging differences
- test whether current route, session, Java-cluster, and provider heuristics
  still hold on other installs
- identify likely node archetypes for later support and deployment reasoning

### Additional Verification Gained

Standalone-node review can verify:

- which service families are consistently present
- which listener, config, and packaging patterns repeat
- which current-node assumptions break on other nodes
- whether the successor can classify nodes reliably without relying on one
  special-case lab

### Knowledge Gained

Standalone-node review should produce:

- a small set of imported node-local proofs
- an initial node archetype comparison
- better confidence in what is common, optional, or unusual across installs

### Explicit Non-Claims

Standalone-node review should not claim:

- real east-west traffic truth
- cluster membership
- cross-node request flow
- real distributed failover or topology order

## Phase 2: Distributed-Lab Activation

### Goal

Use one or more intentionally distributed labs to move from independent
node-local comparisons into real role-separated multi-node evidence.

### Use Cases

- identify what moves off-box in a distributed deployment
- validate which service families are local-only versus cross-node adjacent
- capture real cross-node endpoint hints
- test whether integration surfaces live on one node, many nodes, or shared
  role families
- activate the first honest thin cross-node envelope

### Additional Verification Gained

Distributed-lab review can verify:

- real role separation across nodes
- repeated versus distributed packaging patterns
- first bounded cross-node endpoint hints
- whether the successor's node archetypes map cleanly onto real distributed
  roles

### Knowledge Gained

Distributed-lab activation should produce:

- one or more imported distributed node-local proof bundles
- a thin cross-node envelope grounded in real multi-node evidence
- the first credible base for a topology map, fuller dependency graph,
  stronger integration-health modeling, and broader product behavior modeling

## Distributed Architecture Menu

The currently reviewed distributed node types are:

- remote agent
- load distribution unit
- disaster recovery node
- high availability node
- standalone

Those can be composed into architecture types such as:

- high availability
- disaster recovery with a remote agent
- an LDU only
- standalone with a remote agent
- standalone with an LDU

The operator also expects later stacked combinations where multiple roles are
combined into richer distributed shapes.

## Reviewed Starting Point

The reviewed first distributed proof should be:

- standalone + remote agent

with the current standalone primary remaining:

- `10.167.2.150`

### Why This Is First

This is the best first distributed proof because:

- it creates real role separation without the full complexity of HA or DR
- it is easier to explain and compare than a redundancy-first architecture
- it should reveal what truly moves off-box when a remote role exists
- it gives the successor its first honest multi-node role boundary before more
  complex stacked architectures arrive

### Why Other Architectures Come Later

- `standalone + LDU` is a strong second distributed proof because it teaches
  front-door and distribution behavior, but it is slightly less direct than a
  remote-agent split for initial role separation
- `high availability` should come after that because the first problem there
  is symmetry and failover, not simple role separation
- `disaster recovery with a remote agent` should come later still because it
  combines continuity, remote behavior, and recovery semantics at once
- stacked architectures should come last because they are most useful after
  the simpler distributed roles are already legible

## Reviewed Distributed Rollout Order

The reviewed order for distributed architectures is:

1. standalone + remote agent
2. standalone + LDU
3. high availability
4. disaster recovery with a remote agent
5. later stacked or mixed architectures

This order sets expectations on purpose:

- first learn what a second real role looks like
- then learn what a distribution/front-door role changes
- then learn what redundancy changes
- then learn what recovery and remote continuity change
- only then widen into multi-role stacked systems

## Build Responsibility

For the first distributed proof, the reviewed preference is:

- operator deploys the distributed lab manually
- successor then maps it through the bounded `adf-dev`-owned workflow

This is preferred over asking the successor to build the architecture itself
from incomplete doc-pack guidance, because the highest-value next proof is the
mapping and comparison of a real deployed distributed lab, not install-time
guesswork.

Later, once one or two distributed architectures are already mapped cleanly,
it may become worthwhile to attempt a separate "doc-pack-guided build" learning
exercise.

## Recommended Order

The reviewed order is:

1. complete `capture_second_node_node_local_proof` using one standalone node
2. capture additional standalone-node proofs as a calibration set
3. derive a bounded node archetype comparison from those independent nodes
4. deploy and inspect a distributed lab with role-separated nodes
5. activate the thin cross-node envelope
6. then widen into topology, fuller dependency mapping, integration-health
   modeling, and broader product behavior modeling

## Why This Order Matters

- it keeps the successor honest about what standalone nodes can and cannot
  prove
- it improves trust in the node-local model before widening into topology
- it lets distributed-lab work produce qualitatively new knowledge rather than
  just "more nodes"

## Immediate Next Step

The next active distributed step now remains
`capture_distributed_lab_role_separated_node_proofs`.

Given the reviewed distributed rollout order, the best immediate use of that
task is:

- wait for the operator to finish deploying the first distributed architecture
  as `standalone + remote agent`
- keep `10.167.2.150` as the primary standalone node
- obtain the new remote-agent node IP and credentials or SSH pattern
- create node-specific read-only target profiles
- capture one node-local proof for each distributed role from `adf-dev`
- only then activate the first thin cross-node envelope
