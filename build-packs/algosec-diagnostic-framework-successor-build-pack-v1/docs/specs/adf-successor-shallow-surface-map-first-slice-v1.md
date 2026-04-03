# ADF Successor Shallow Surface Map First Slice v1

## Purpose

Define the first real product slice for the ADF successor build pack and lock
the first artifact contract before deeper discovery work begins.

## Slice Question

What is observably running on the Rocky 8 host and the virtual appliance at the
first useful support layer, and what are the first visible relationships among
those processes, services, ports, configs, logs, and JVM surfaces?

## Inputs

- process table
- systemd services and unit files
- listening ports and owning processes
- command lines and executable paths
- visible config and log paths
- JVM process metadata where safely observable
- incomplete but agent-optimized technical documentation already available for
  this product family

## Optional Supplementary Hint Import

The first slice may use one supplementary local hint artifact at:

- `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`

That artifact may be distilled from the remote ASMS doc pack and used only to:

- recognize product-family terms or module names more reliably
- notice documented third-party integration surfaces such as ports
- rank likely product-relevant components above generic host noise

That hint layer must stay subordinate to live runtime observation:

- imported doc-pack hints may improve naming, ranking, and summary wording
- imported doc-pack hints must not override observed service state, process
  ownership, port ownership, or dependency claims
- imported doc-pack hints must remain inference support, not promoted observed
  fact

## Required Artifacts

### Artifact A

One machine-readable shallow surface map at:

- `dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`

The JSON artifact is the canonical first-wave output. It records, at minimum:

- `schema_version`, `generated_at`, `target`, and `collection_policy`
- `runtime_identity`
- `docpack_hint_ref` when a supplementary hint artifact was loaded
- `component_records`
- `unknowns`
- `next_candidate_seams`

Each `component_records[]` entry must keep observed fact, tentative
classification, and visible unknowns distinct. Each record must include, at
minimum:

- service or process name
- first observed category
- whether the record came from a systemd unit, a standalone process, or both
- executable or main command line when visible
- service-unit relationship when available
- listening ports when available
- likely config path candidates when visible
- likely log path candidates when visible
- JVM visibility notes when applicable
- source command ids that produced the record
- explicit unknowns

Observed values must stay under `observed`.
Tentative labels or bounded importance hints must stay under `inference`.
Missing or not-yet-proven details must stay under `unknowns`.

### Artifact B

One operator-reviewable summary at:

- `dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`

The summary must be derived from the JSON map and must state:

- what appears to be running
- which components look central
- which areas remain unknown
- which one or two next deeper seams are most worth investigating

The summary is a view, not a second source of truth. It should avoid broad
architecture narration and instead stay tied to the recorded component facts.

## Initial Collection Scope

The first pass may use bounded read-only commands against:

- runtime identity
- process table
- systemd unit and unit-file inventory
- listening TCP ports and owning processes when visible
- command-line path hints for config and log files
- JVM-adjacent command-line visibility

The first pass should not require config-file parsing, log parsing, package
inventory mining, remote mutation, or deep service-to-service dependency
reconstruction.

## Initial Classification Rules

- Prefer simple first observed categories such as `system_service`,
  `application_service`, `edge_proxy`, `data_store`, `queue_or_messaging`,
  `identity_or_access`, `java_process`, or `standalone_process`.
- Use low or medium confidence when the category is inferred from names,
  ports, command-line hints, or supplementary doc-pack hints rather than
  directly confirmed.
- Keep unknowns visible instead of forcing every component into a clean
  product story.

## Stop Conditions

Stop the slice when:

- the first useful host/appliance surface map exists at the declared path
- the derived Markdown summary exists at the declared path
- likely major categories and obvious unknowns are visible
- one or two candidate next seams are named

Do not continue the slice into:

- deep dependency reasoning
- subsystem root-cause analysis
- predictive analytics
- broad playbook generation
