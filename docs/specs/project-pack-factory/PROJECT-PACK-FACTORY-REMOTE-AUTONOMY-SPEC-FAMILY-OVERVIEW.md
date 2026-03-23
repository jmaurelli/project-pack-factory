# Project Pack Factory Remote Autonomy Spec Family Overview

## Purpose

Define the relationship between the remote-autonomy specifications that extend
Project Pack Factory from local bounded autonomous build-pack work into an
initial reusable source-to-target remote roundtrip proof workflow.

This umbrella spec exists mainly to keep the remote-autonomy spec family easy
to traverse, sequence, and reference later.

This family is intentionally the initial bounded remote-autonomy proof suite,
not a general remote autonomy framework for arbitrary long-running remote work.

## Spec Link Tags

```json
{
  "spec_id": "remote-autonomy-spec-family-overview",
  "suite_members": [
    "remote-autonomy-target-workspace-and-staging",
    "portable-build-pack-autonomy-runtime-helpers",
    "remote-autonomous-build-pack-execution",
    "remote-autonomy-end-to-end-roundtrip"
  ],
  "integrates_with": [
    "autonomous-build-pack-handoff-and-work-state",
    "external-build-pack-runtime-evidence-export",
    "external-runtime-evidence-import",
    "build-pack-control-plane-dataplane-integrity"
  ]
}
```

## Why This Spec Family Exists

Project Pack Factory already had most of the important building blocks:

- canonical build-pack handoff state
- bounded autonomous starter-task execution
- runtime evidence export
- runtime evidence import

What was missing was the reusable remote suite that connects those pieces into
one clear source-to-target model:

- PackFactory remains the source control plane
- a remote target hosts the execution plane
- a staged build-pack becomes the autonomous work packet
- the staged build-pack also carries a local portability amendment so it stays
  executable outside the factory checkout
- exported runtime evidence returns to the factory as supplementary history

## Recommended Reading Order

The intended reading order for this spec family is:

1. [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-TARGET-WORKSPACE-AND-STAGING-TECH-SPEC.md)
   This defines the reusable source-to-target workspace, directory naming, and
   staging contract.
2. [PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PORTABLE-BUILD-PACK-AUTONOMY-RUNTIME-HELPERS-TECH-SPEC.md)
   This makes the staged build-pack self-sufficient enough to execute outside
   the factory repo.
3. [PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md)
   This defines the bounded remote agent execution contract.
4. [PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md)
   This defines the full remote roundtrip from local materialization through
   remote execution through evidence import.

This is a reading order, not a claim that implementation dependencies or
runtime sequence always follow the same numbering.

## Implementation Dependency Note

The family has two closely related setup layers:

- remote staging defines where and how the remote workspace is prepared
- portable runtime helpers define what the staged build-pack must carry to run
  outside the factory repo

Those two layers may be implemented together even though the recommended
reading order starts with staging.

In implementation terms, the portable helper layer is not optional connective
glue. It is the portability amendment that keeps the staged build-pack
executable after it leaves the factory checkout.

In plain language:

- read staging first to understand the source-target workspace model
- read portable helpers next to understand what must travel with the pack

## Runtime Sequence

The intended runtime sequence for the spec family is:

1. PackFactory materializes or selects a build-pack locally.
2. A remote target workspace is prepared.
3. The portable build-pack payload is staged to that target.
4. A remote agent executes the build-pack within its pack-local bounds.
5. The remote run exports a bounded runtime evidence bundle.
6. The bundle is pulled back to local non-canonical staging.
7. The bundle may then be imported through the bounded external runtime
   evidence importer.

## Outside This Family

The four suite members are the remote-autonomy family itself.

The following specs are adjacent boundary specs, not part of the four-document
family traversal:

- [PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMOUS-BUILD-PACK-HANDOFF-AND-WORK-STATE-TECH-SPEC.md)
  Read when implementing or reviewing the canonical pack-local handoff model.
- [PROJECT-PACK-FACTORY-EXTERNAL-BUILD-PACK-RUNTIME-EVIDENCE-EXPORT-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-EXTERNAL-BUILD-PACK-RUNTIME-EVIDENCE-EXPORT-TECH-SPEC.md)
  Read when implementing or reviewing portable runtime evidence export.
- [PROJECT-PACK-FACTORY-EXTERNAL-RUNTIME-EVIDENCE-IMPORT-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-EXTERNAL-RUNTIME-EVIDENCE-IMPORT-TECH-SPEC.md)
  Read when implementing or reviewing how remote evidence re-enters the
  factory.
- [PROJECT-PACK-FACTORY-BUILD-PACK-CONTROL-PLANE-AND-DATAPLANE-INTEGRITY-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-BUILD-PACK-CONTROL-PLANE-AND-DATAPLANE-INTEGRITY-TECH-SPEC.md)
  Read when implementing or reviewing the control-plane versus execution-plane
  boundary.

## Relationship To The Broader Project

This spec family is additive to the existing PackFactory model.

It does not replace:

- canonical local factory control-plane truth
- bounded promotion workflows
- bounded deployment workflows
- bounded external runtime evidence import

Instead, it extends the project in one specific direction:

- an initial bounded proof that a portable build-pack can be staged to a
  remote target, completed there to its pack-local boundary, and returned as
  supplementary runtime evidence while PackFactory still owns the authoritative
  local decision surfaces

## Mutation Authority And Re-Entry Boundary

The remote-autonomy family is only valid if the source-target split remains
strict.

Remote workflows may write only:

- the staged remote build-pack copy
- remote runtime artifacts under that staged copy
- local orchestration scratch used to stage, pull, or queue import requests

Remote workflows must not directly mutate local canonical PackFactory control
plane surfaces such as:

- `registry/*.json`
- `deployments/`
- canonical promotion history
- local `status/readiness.json`
- local `status/work-state.json`
- local `eval/latest/index.json`
- local release artifacts

Any readiness, work-state, or eval state observed on the remote side is
evidentiary only until a separate bounded factory workflow acts on it.

Staged remote file mutations do not reconcile back into the local source
build-pack by direct copy or sync.

The only allowed return path for remote execution output is:

1. pull the exported bundle into non-canonical local staging
2. optionally import it through the bounded external runtime evidence importer

No direct copy into canonical `eval/history/`, `status/*`, or other local
control-plane surfaces is allowed.

## Historical And Future Role

These specs are expected to remain useful even after implementation because
they explain:

- why the remote-autonomy workflow is split into these four layers
- which layer owns which concern
- where future integration or refinement work should attach

## Minimal Family Rule

Future remote-autonomy work should prefer amending one of the existing suite
members before creating a new adjacent spec unless the new work truly adds a
separate layer of responsibility.
