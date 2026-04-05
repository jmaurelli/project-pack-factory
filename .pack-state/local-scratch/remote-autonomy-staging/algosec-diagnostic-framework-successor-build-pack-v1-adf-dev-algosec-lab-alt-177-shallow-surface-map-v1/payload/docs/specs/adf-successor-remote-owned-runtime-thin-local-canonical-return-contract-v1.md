# ADF Successor Remote-Owned Runtime Thin Local Canonical Return Contract V1

## Purpose

Define the current reviewed operating model for the ADF successor line now that
`adf-dev` is the practical runtime home, the target Rocky 8 or appliance lab is
the downstream evidence source, and PackFactory root still owns canonical build-
pack truth.

This is not a remote-canonical pack transition.

The goal is narrower:

- let `adf-dev` carry the long-lived successor runtime and its second backup
  surface
- let the successor inspect the target lab from `adf-dev`
- keep PackFactory root as the canonical source, tracker, readiness, and import
  authority
- pull back only the bounded artifacts needed to judge the run

## Current Mode

Current reviewed mode for the successor is:

- PackFactory root = canonical control plane and canonical build-pack home
- `adf-dev` = operational runtime home and remote execution workspace
- Rocky 8 or appliance target = observed runtime source
- the `adf-dev` host also serves as the consumer-facing review surface for
  generated successor content

In plain language:

- PackFactory decides what is officially true
- `adf-dev` does the heavy runtime work
- the target lab supplies runtime facts

Current pinned topology for this line:

- current downstream lab target: `10.167.2.150`
- `adf-dev` host IP: `10.167.2.151`

These host identities are now part of the successor's reviewed operating
context rather than inherited ADF memory only.

This contract does not activate a remote-canonical successor mode. Repeated
staging, successful remote runs, or the existence of remote backups do not move
canonical pack ownership away from PackFactory root.

## Why This Contract Exists

The successor now has enough moving parts that the ownership boundary needs to
be explicit:

- `adf-dev` has more disk, host-local backup coverage, and better proximity to
  the target network
- PackFactory local disk is smaller and should not absorb every remote artifact
- the first-wave successor value still depends on PackFactory being able to
  judge returned evidence against local canonical state
- the support-engineer consumption path shares the `adf-dev` host rather than
  the target lab itself

Operator-provided lab posture for this line:

- quickly deployable labs are available
- breaking a lab through bounded misconfiguration or exploratory mutation is not
  a material concern
- later distributed-architecture labs are expected as additional discovery
  surfaces

That means the successor can stay evidence-first and bounded, while still being
more willing to explore appliance behavior than a fragile customer environment
would allow.

Without this contract, the line can drift into one of two bad modes:

- copying too much back into PackFactory and treating local scratch as durable
  evidence
- leaving too much only on `adf-dev` and losing canonical control of source,
  readiness, or accepted proof

## Ownership Split

### PackFactory Root Owns

PackFactory root remains authoritative for:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`
- accepted source changes
- accepted spec and doc changes
- runtime-evidence import
- readiness judgment and promotion-facing decisions

Local scratch and pulled roundtrip trees do not become canonical by themselves.
Durable imported runtime evidence must flow through the factory-root importer.

### `adf-dev` Owns

`adf-dev` is the successor's operational runtime home for:

- the staged remote build-pack workspace
- day-to-day target-backed runs
- remote-only intermediate logs and helper files
- the host-local second backup surface
- bounded target-facing investigation steps

Remote mutations stay remote until PackFactory root explicitly accepts the
relevant proof or source changes.

### Rocky 8 Or Appliance Target Owns

The downstream target owns runtime reality only:

- services
- processes
- listeners
- logs
- browser-visible behavior
- target-local Codex help when used

The target does not become canonical for build-pack source, tracker state, or
readiness state.

### `adf-dev` Publication Surface

The `adf-dev` host also serves successor-generated diagnostic content to
support engineers.

Current pinned host IP:

- `10.167.2.151`

That publication role is still a consumer surface, not the runtime evidence
source.

## Thin Local Canonical Return Rule

PackFactory should not pull the whole staged successor workspace back from
`adf-dev` after each run.

The reviewed return shape is:

- bounded exported runtime evidence bundles
- selected proof artifacts needed for readiness judgment
- intentional source, doc, or tracker changes that the operator wants accepted

The normal return does not include:

- whole-workspace tarballs
- remote caches and virtualenvs
- routine remote backup archives
- every intermediate log or exploratory note

In plain language:

- keep the heavy runtime surface remote
- bring back the proof, not the whole house

## Runtime Evidence Contract

The successor inherits the PackFactory remote-evidence rules:

- export from the pack through `pack.json.entrypoints.export_runtime_evidence_command`
- import only from PackFactory root through
  `python3 tools/import_external_runtime_evidence.py ...` or a higher-level
  wrapper that uses that import path
- exported bundles remain `supplementary_runtime_evidence`
- imported bundles are preserved audit evidence, not direct remote overwrites of
  canonical local state

For the successor's first target-backed shallow surface map loop, the minimum
return bundle should include:

- `run-summary.json`
- `loop-events.jsonl` when present
- the target-backed `shallow-surface-map.json`
- the derived `shallow-surface-summary.md`
- optional feedback memory when the run produced it

## Mirrored Return Artifacts

The successor's first-wave product artifacts normally live under:

- `dist/candidates/adf-shallow-surface-map-first-pass/`

That is the right operator-facing location on the remote runtime host, but it is
not by itself enough for PackFactory's bounded export surface.

The reviewed bridge is:

- when a target-backed run is tied to a PackFactory `run_id`, mirror the
  generated shallow-surface artifacts under
  `.pack-state/autonomy-runs/<run-id>/artifacts/`
- the exporter then includes those mirrored files automatically in the bounded
  runtime-evidence bundle

This keeps the pack's product artifact root stable while still giving PackFactory
an importable proof line.

## Operational Flow

The normal successor flow is:

1. Stage or refresh the successor pack on `adf-dev` through the PackFactory
   remote control plane.
2. Keep the `adf-dev` host-local backup job in place as operational resilience.
3. Run the successor on `adf-dev` against the downstream Rocky 8 or appliance
   target at `10.167.2.150`.
4. Generate the shallow surface artifacts in `dist/candidates/...`.
5. Mirror those generated artifacts into the matching
   `.pack-state/autonomy-runs/<run-id>/artifacts/...` path.
6. Export bounded runtime evidence from the staged pack.
7. Pull the exported bundle back through the PackFactory roundtrip workflow.
8. Import that bundle at the factory root and judge readiness from the imported
   proof.
9. Publish or refresh the derived diagnostic content on `adf-dev`
   (`10.167.2.151`) when operator review is needed.

## Target-Local Codex Use

If the downstream Rocky 8 or appliance host already has Codex, it may be used as
bounded target-local help for read-only observation work.

That does not change the ownership split:

- `adf-dev` still owns the successor runtime loop
- PackFactory root still owns canonical acceptance
- target-local Codex remains a helper, not a second control plane

## Backup Boundary

The `adf-dev` backup job is a safety measure for the staged successor runtime.
It is not a canonical evidence line and it is not a substitute for returning
bounded exported proof to PackFactory root.

In plain language:

- backup helps us recover remote work
- import is how PackFactory learns from remote work

## Current Decision

This contract is active now for the successor line.

Current reviewed decision:

- remote-owned runtime: yes
- thin local canonical return: yes
- remote-canonical build-pack home: no

Future agents should preserve that distinction unless a later reviewed mode
change explicitly moves canonical successor ownership away from PackFactory
root.
