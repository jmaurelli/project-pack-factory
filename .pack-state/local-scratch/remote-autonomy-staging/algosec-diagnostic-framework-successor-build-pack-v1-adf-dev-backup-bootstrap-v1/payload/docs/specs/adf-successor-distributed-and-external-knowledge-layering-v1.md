# ADF Successor Distributed And External Knowledge Layering v1

## Purpose

Define the next bounded extension beyond the current single-node ASMS successor
proof on `10.167.2.150`.

This note is a planning artifact, not a distributed topology claim and not a
license to mix external product folklore into the current runtime map.

Its job is to pin how future work should layer:

- observed node reality
- version-matched component knowledge
- external-system integration hints

without weakening the successor's evidence-first contract.

## Current Baseline

The successor already has bounded proof for:

- single-node runtime topology on `10.167.2.150`
- browser-edge to local-owner route hints
- the AFF and FireFlow session bridge chain
- central config and log inspection surfaces
- one bounded configuration-pattern readout

Canonical current proof:

- `eval/history/import-external-runtime-evidence-20260403t115837z/`
- `docs/specs/adf-successor-asms-runtime-architecture-review-v1.md`
- `docs/specs/adf-successor-configuration-patterns-and-tunable-behaviors-v1.md`
- `docs/specs/adf-successor-distributed-and-external-knowledge-activation-review-v1.md`

Important boundary:

- this is still an appliance-style single-node readout
- it is not yet a multi-node ASMS topology map
- it is not yet an external-integration behavior map
- the latest imported proof now carries a bounded activation packet for
  component-guidance layering plus observed AWS and Azure-side activation
  signals, but it still keeps cross-node topology inactive until a second
  imported node-local proof exists

## Layer Model

### Layer 0: Observed Node Reality

This stays authoritative.

Examples:

- host identity
- service families
- route ownership hints
- listener ownership
- config and log surface hints
- failed services
- retained runtime markers

Rule:

- future distributed or external reasoning must start from imported runtime
  evidence for a specific node or target, not from doc-pack memory alone

### Layer 1: Version-Matched Component Knowledge

This is allowed only when the node proof exposes a credible component family
or runtime lineage.

Current likely candidates:

- Apache httpd
- Tomcat-family application containers behind `ms-metro` and `ms-bflow`
- standalone Java services such as `algosec-ms` and `aff-boot`
- ActiveMQ
- Keycloak
- Elasticsearch and Logstash when later bounded evidence is needed

Rule:

- component knowledge must stay version-aware when possible and must be labeled
  as guidance layered onto observed runtime fact, not as observed fact itself

Examples of safe future use:

- interpreting a visible `catalina.base` as a Tomcat-family runtime-root clue
- interpreting `activemq.conf` and `jolokia-access.xml` as messaging-side
  control surfaces
- interpreting Keycloak environment-file or wrapper-start surfaces as
  identity-side control entrypoints

Examples of unsafe future use:

- assuming exact default file semantics without version match
- importing tuning advice from generic vendor docs and presenting it as lab fact
- using open-source defaults to overwrite observed target-local behavior

### Layer 2: External-System Integration Knowledge

This stays third in priority and activates only when the successor observes
credible integration-side evidence.

Current bounded local hint source:

- `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`

Visible external-system terms in that local hint bundle already include:

- Check Point
- Fortinet
- Juniper
- Palo Alto Networks
- Panorama

Rule:

- those names are currently hint inventory only
- they do not prove that the current target node is actively integrated with
  those systems
- future external-system reasoning must be gated by observed integration
  surfaces such as route names, provider config families, runtime logs,
  provider-specific environment files, or returned API markers

## Distributed-Node Mapping Plan

The successor should expand to multiple nodes in this order:

### 1. Keep One Canonical Map Per Node

Do not merge nodes into one suite graph first.

For each node:

- collect the same bounded shallow surface map
- keep node label, host identity, and imported proof bundle separate
- preserve which routes, listeners, configs, and failures belong to that node

Why:

- this keeps node-local truth from being flattened into a premature suite story

### 2. Add A Thin Cross-Node Envelope

Only after at least two node-local maps exist, add a separate envelope layer
that records:

- node labels and roles as observed or operator-supplied
- repeated service families across nodes
- clearly observed cross-node endpoints
- unresolved cross-node edges

Do not claim:

- full dependency order
- full east-west traffic truth
- cluster membership without observed evidence

### 3. Separate Shared Packaging From Shared Ownership

If multiple nodes show the same Tomcat-family or Java-family pattern, treat
that first as packaging similarity, not automatic proof of one cluster role.

Why:

- the current single-node proof already shows that shared packaging can still
  hide distinct service families

## External-Knowledge Layering Plan

### Open-Source Component Layering

When the successor has both a clear component family and credible version or
runtime lineage, it may layer:

- config-surface expectations
- log-entrypoint expectations
- common operational vocabulary

It must not layer:

- speculative bug claims
- unsupported tuning advice
- generic defaults presented as local truth

### External-System Layering

When the successor observes provider or integration-specific evidence, it may
add a bounded external hint packet with three bands:

- observed local integration evidence
- product-doc or version-matched terminology
- external-system behavior hints

That packet must stay fail-closed:

- if local evidence is weak, keep external-system reasoning weak
- if only docs mention a vendor, do not activate vendor-side behavior claims
- if the integration family is visible but version is unknown, keep the
  behavior guidance explicitly generic and low-confidence

## First Future Activation Triggers

The successor should only activate distributed or external layering after one
of these surfaces appears:

- a second imported node-local proof bundle
- provider-specific config families under Apache, AFA, or service-local config
  roots
- provider-specific runtime markers in bounded logs or journals
- observed integration-side route names or API paths
- version or package identity strong enough to attach open-source component
  guidance safely

## Fail-Closed Rules

- Observed node reality always wins over layered knowledge.
- Imported doc-pack hints remain hints until a node-local proof supports them.
- Version-matched open-source knowledge is guidance, not canonical truth.
- External-system reasoning must stay subordinate to observed local
  integration evidence.
- If future distributed evidence conflicts across nodes, preserve the conflict
  instead of normalizing it away.

## Best Next Implementation Slice

The best next bounded implementation is:

1. keep the current single-node shallow-surface flow unchanged
2. define a second-node request shape that reuses the same runtime-evidence
   roundtrip
3. add a separate thin node-envelope artifact instead of widening the current
   node-local map
4. only then add version-aware open-source or vendor-side hint packets when
   observed evidence activates them

In plain language:

- map each node honestly first
- compare nodes second
- layer outside knowledge third

That ordering protects the successor from becoming a folklore engine instead of
an evidence-first diagnostic line.
