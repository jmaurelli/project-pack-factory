# Project Pack Factory ADF Successor Creation Request Plan

## Status

Draft v1 bounded request-preparation note for the fresh ADF successor line.

## Purpose

Prepare the concrete PackFactory request surfaces needed to start the new ADF
successor line without overcommitting later layers.

## What Is Being Prepared

This planning slice prepares:

- one template-creation request for a fresh reusable ADF successor template
- one first-materialization request for the first bounded proving-ground
  build-pack derived from that template

These requests are prepared, not executed, in this planning step.

## Why A New Template Line

The current ADF build-pack already contains strong product and method learning,
but it also contains substantial line-specific state and active implementation
history. The cleaner path is:

- preserve the current line as evidence and inheritance input
- create a fresh successor template that starts with the newer bounded model
- materialize the first successor build-pack from that template

## Request Strategy

### Template creation

Create a new template line for the bounded agent-centered ADF successor model.

Recommended template id:

- `algosec-diagnostic-framework-successor-template-pack`

Recommended display name:

- `AlgoSec Diagnostic Framework Successor Template Pack`

### First materialization

Prepare the first proving-ground build-pack derived from that template.

Recommended build-pack id:

- `algosec-diagnostic-framework-successor-build-pack-v1`

Recommended display name:

- `AlgoSec Diagnostic Framework Successor Build Pack v1`

## Selected Control-Plane Inputs

### Agent-native profile

Use the tracker-backed agent-native profile from initialization:

- `packfactory_tracker_backed_agent_native`

Why:

- the successor line is explicitly meant to put the agent at the center from
  day one
- the line needs canonical objective, backlog, work-state, and restart-memory
  expectations from the start

### Personality selection

Use the catalog personality overlay:

- `calm-delivery-lead`

Why:

- the successor line needs plain, concise, operator-facing communication
- the target support audience is practical and not deeply specialized
- the line should stay direct and grounded rather than overly expansive

### Role/domain selection

The recommended initial ADF role/domain lens is:

- `diagnostic-systems-analyst`

But the current template-creation and materialization request schemas only
accept role/domain selections from the shared catalog. The chosen ADF lens is
currently line-specific and not yet a catalog entry.

So this request plan does **not** fake a catalog selection. Instead it records
the honest current boundary:

- no shared catalog role/domain overlay is selected in the request
- the line-specific ADF role/domain lens should be authored as a pack-local
  line contract immediately after creation/materialization
- a later PackFactory decision can determine whether that lens becomes a shared
  catalog entry

## First-Wave Scope Carried Into The Request

The first-wave objective is the shallow surface map slice defined in:

- [PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md)

That means the request should encode:

- live Rocky 8 and appliance observation as the main input
- incomplete but agent-optimized technical docs as valid supplemental input
- machine-readable shallow surface map as the first canonical artifact
- one operator-reviewable summary as the first derived review surface
- no deep dependency graph or predictive work in wave 1

## Evidence

This request plan is grounded in:

- bounded successor-line model:
  [PROJECT-PACK-FACTORY-BOUNDED-AGENT-CENTERED-ADF-SUCCESSOR-LINE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-BOUNDED-AGENT-CENTERED-ADF-SUCCESSOR-LINE-TECH-SPEC.md)
- first slice:
  [PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-ADF-SUCCESSOR-SHALLOW-SURFACE-MAP-FIRST-SLICE-TECH-SPEC.md)
- first role/domain test:
  [PROJECT-PACK-FACTORY-ADF-SUCCESSOR-INITIAL-ROLE-DOMAIN-LENS-FIRST-TEST.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-ADF-SUCCESSOR-INITIAL-ROLE-DOMAIN-LENS-FIRST-TEST.md)
- current ADF objective:
  [project-objective.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/contracts/project-objective.json)
- current ADF execution lessons:
  [work-state.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json)

## Request Artifacts

Prepared request files:

- [.pack-state/tmp/adf-successor-template-creation-request.json](/home/orchadmin/project-pack-factory/.pack-state/tmp/adf-successor-template-creation-request.json)
- [.pack-state/tmp/adf-successor-first-materialization-request.json](/home/orchadmin/project-pack-factory/.pack-state/tmp/adf-successor-first-materialization-request.json)

## Decision

The ADF successor line is now ready for the next action:

- execute the prepared template-creation request
- then materialize the first proving-ground successor build-pack from that new
  template

The only deliberate deferred item is the line-specific `diagnostic-systems-analyst`
role/domain lens, which should be authored after creation unless and until it
is promoted into the shared catalog.
