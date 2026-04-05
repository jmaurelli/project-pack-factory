# Project Pack Factory ADF Successor Shallow Surface Map First Slice Tech Spec

## Status

Draft v1 first-slice definition for the bounded, agent-centered ADF successor
line.

## Purpose

Define the first concrete slice for the new ADF successor line so the project
starts with a bounded, early-reviewable artifact instead of a long open-ended
discovery phase.

## Why This Slice First

The current ADF line and the operator feedback point to the same rule:

- delayed tangible proof is a major failure mode
- live target observability is already strong
- broad subsystem theory arrives too early unless the first slice stays shallow

The shallow surface map is the right first slice because it is:

- evidence-first
- directly available from the target host
- useful before deeper interpretation is perfect
- a strong precursor to dependency mapping and playbook generation

## Slice Question

What is observably running on the Rocky 8 host and the virtual appliance at the
first useful support layer, and what are the first visible relationships among
those processes, services, ports, configs, logs, and JVM surfaces?

## Intended Inputs

### Live target inputs

- process table
- systemd services and unit files
- listening ports and owning processes
- command lines and executable paths
- config paths visible from service units, process arguments, or standard
  layout
- log paths visible from service units, package layout, or standard layout
- JVM process metadata where safely observable

### Documentation inputs

- incomplete but agent-optimized technical documentation already available to
  the operator
- existing ADF notes that help classify obvious appliance-specific names

### Inherited PackFactory inputs

- the successor-line planning model in
  [PROJECT-PACK-FACTORY-BOUNDED-AGENT-CENTERED-ADF-SUCCESSOR-LINE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-BOUNDED-AGENT-CENTERED-ADF-SUCCESSOR-LINE-TECH-SPEC.md)
- the current ADF lessons in
  [project-objective.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/contracts/project-objective.json)
  and
  [work-state.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json)

## Out Of Scope

This slice does not attempt to:

- fully explain every subsystem
- produce a complete dependency graph
- reverse engineer all Java internals
- predict failures
- generate a full support site
- fully classify every unknown process on the first pass

## Commands And Evidence Class

Representative command classes for this slice include:

- `ps`
- `systemctl`
- socket and port inspection
- service unit inspection
- process executable and cwd inspection where safe
- package or file location checks when needed to name a surface
- JVM-adjacent inspection tools where safely available on the host

The important boundary is not the exact command list. The boundary is that the
slice remains:

- read-only
- shallow
- host-and-runtime observable
- first-layer only

## Required Output Artifacts

This slice should produce two artifacts and stop.

### Artifact A: machine-readable shallow surface map

A structured artifact that records, at minimum:

- service or process name
- first observed category
- executable or main command line
- service-unit relationship when available
- listening ports when available
- likely config path candidates when visible
- likely log path candidates when visible
- JVM visibility notes when applicable
- confidence or uncertainty notes when classification is thin

### Artifact B: operator-reviewable summary

A plain-language review surface derived from the machine-readable map that lets
the operator quickly inspect:

- what appears to be running
- which components look central
- which areas remain unknown
- which next deeper seam is most worth investigating

## Acceptance Criteria

- one machine-readable shallow surface map exists
- one operator-reviewable summary exists and is derived from that map
- the output distinguishes observed facts from tentative classification
- the slice identifies at least one sensible next deeper seam without claiming
  total understanding
- the slice is small enough that the operator can judge usefulness early

## Stop Conditions

Stop the slice when:

- the first useful host/appliance surface map is produced
- the agent can name likely major categories and obvious unknowns
- one or two candidate next seams are visible

Do not continue the slice into:

- deep dependency reasoning
- subsystem root-cause analysis
- broad Java interpretation
- full playbook authoring

Those belong to later slices.

## Good Outcome Shape

A good first-slice result should let the operator say something like:

- "Yes, this is a useful first map of the appliance."
- "These are clearly the next two places worth going deeper."
- "This already feels more concrete than prior attempts."

That is enough for success. The slice does not need to be complete to be
valuable.

## Evidence From Current ADF

The current ADF line already supports the logic behind this slice.

### Evidence A: shallow-first support usefulness is already a proven lesson

The current ADF work-state records:

- healthy-path trial first
- symptom-classification second
- shallow-fault validation third

See
[work-state.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json).

### Evidence B: useful outputs should appear early

The current ADF line already produces reviewable artifact candidates under
[dist/candidates](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/dist/candidates),
which reinforces that the successor line should generate inspectable outputs
quickly instead of waiting for deep architecture convergence.

### Evidence C: machine-readable truth should stay primary

The current ADF objective already emphasizes machine-readable truth first and
derived support surfaces second:
[project-objective.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/contracts/project-objective.json)

## Recommended Successor-Line Follow-On

If this slice is accepted, the next slice should likely be one of:

- first dependency seam map for one central service boundary
- first machine-readable service-boundary record for one JVM-backed component
- first derived support playbook fragment from the shallow map

## Decision

The shallow surface map is the recommended first implementation slice for the
new ADF successor line because it is the smallest high-value artifact that uses
the target's strong observability without forcing premature deep interpretation.
