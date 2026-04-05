# ADF Successor Standalone-Node Archetype Comparison v1

## Purpose

Record what the successor learned from the first independent-node calibration
set before any distributed-topology claims activate.

This comparison uses three imported node-local proofs:

1. baseline node `10.167.2.150`
2. standalone calibration node `algosec-lab-alt-192` (`10.167.2.192`)
3. standalone calibration node `algosec-lab-alt-177` (`10.167.2.177`)

## Version Spread

The calibration set now spans:

- `10.167.2.150`
  `algosec-appliance 3300.10.240-31`, `fa 3300.10.240-66`,
  `fireflow 3300.10.240-66`, `fa-platform 3300.10.240-66`
- `10.167.2.192`
  `algosec-appliance 3300.10.230-28`, `fa 3300.10.230-54`,
  `fireflow 3300.10.230-52`, `fa-platform 3300.10.230-54`
- `10.167.2.177`
  `algosec-appliance 3300.20.120-4`, `fa 3300.20.120-12`,
  `fireflow 3300.20.120-12`, `fa-platform 3300.20.120-12`

That means the successor is no longer calibrated only against one appliance or
one patch train. It now spans:

- one current `A33.10` baseline
- one older `A33.10` sibling
- one `A33.20` line jump

## What Stayed Stable

These families and seams repeated strongly across the calibration set:

- Apache edge ownership through `httpd`
- AFF or FireFlow route ownership on local port `1989` through `aff-boot`
- AFF session parity on `/FireFlow/api/session`
- `ms-metro` as the strongest AFA-side Tomcat-family anchor
- `algosec-ms` as a stable standalone service family
- bounded AWS and Azure provider-driver activation through Apache-family plus
  service-unit plus local-listener evidence
- read-only target capture from `adf-dev` without target-local Codex

In plain language: the successor's current artifact shape survived node,
package, and version drift well enough to trust it as a reusable
independent-node capture shape.

## What Drifted

The calibration set also shows useful variation:

- provider-driver ports moved across nodes
  `150`: AWS `8087`, Azure `8157`
  `192`: AWS `8116`, Azure `8102`
  `177`: AWS `8157`, Azure `8131`
- adjacent provider-facing service ports also drifted
- kernel releases drifted within Rocky `8.10`
  `150`: `4.18.0-553.89.1`
  `192`: `4.18.0-553.85.1`
  `177`: `4.18.0-553.105.1`
- Apache drop-in surfaces drifted
  `150` and `192`: `php74-php-fpm`
  `177`: `php83-php-fpm`
- ActiveMQ version drift is visible
  `150`: `apache_activemq` `6.1.7`
  `177`: `apache_activemq` `6.2.0`

This is the useful calibration result: the successor can now distinguish
stable runtime roles from version-specific local details.

## Archetype Reading

### Shared Single-Node ASMS Archetype

All three nodes support one bounded shared archetype:

- Apache-fronted single-node ASMS runtime
- AFA-side `ms-metro`
- FireFlow-side `aff-boot`
- `algosec-ms` service family
- bounded provider-driver and adjacent cloud-facing surfaces

This is not a distributed-role claim. It is a repeated standalone-node pattern.

### Richer Versus Thinner Evidence Variants

Within that shared archetype, two useful evidence variants appeared:

- richer seam-continuity variant:
  `10.167.2.150` and `10.167.2.177`
  retained deeper packets such as UserSession bridge, FA-session reuse,
  bootstrap-versus-polling, AFF cookie handoff, and Java runtime clusters
- thinner but still structurally valid variant:
  `10.167.2.192`
  preserved AFF route-owner, parity, and provider surfaces, but did not retain
  the stronger deeper packets in the same way

That means the successor should treat:

- repeated route and service-family evidence as highly portable
- deeper session and behavior packets as version-sensitive or runtime-activity
  sensitive

## What This Proves

The calibration set now honestly proves:

- the node-local successor map is reusable across multiple independent ASMS
  nodes
- repeated service-family and route-family signals can be compared across
  standalone appliances
- provider-driver activation remains visible even when ports drift
- the successor can now talk about standalone node archetypes without
  overclaiming topology

## What This Still Does Not Prove

The calibration set still does not prove:

- distributed role separation
- east-west traffic truth
- cluster membership
- suite-wide dependency order
- integration health

Those still belong to the distributed-lab and later expansion phases.

## Recommended Next Step

The best next step is now:

- `capture_distributed_lab_role_separated_node_proofs`

Reason:

- the standalone calibration set is already broad enough to show what is
  shared and what drifts across independent nodes
- the next useful knowledge is not "one more standalone node"
- it is the first real role-separated distributed evidence
