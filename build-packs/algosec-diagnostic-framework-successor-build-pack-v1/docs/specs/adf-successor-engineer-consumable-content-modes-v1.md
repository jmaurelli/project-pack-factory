# ADF Successor Engineer-Consumable Content Modes v1

## Purpose

Define the first bounded engineer-consumable content modes for the ADF
successor line without weakening the machine-readable-first product contract.

The successor still treats the machine-readable shallow surface map as the
canonical product layer.
The engineer-facing Markdown artifacts remain derived outputs.

## Content Modes

### 1. Shallow Surface Summary

Artifact:

- `dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`

Role:

- one short overview for quick operator review
- highlights scope, strongest current owner signals, major packet status, and
  next bounded seam

### 2. Diagnostic Playbook

Artifact:

- `dist/candidates/adf-shallow-surface-map-first-pass/diagnostic-playbook.md`

Role:

- live-case decision support under pressure
- turns bounded successor evidence into:
  symptom-to-owner hints,
  first checks,
  stop rules,
  and the next justified escalation or deepening seam

This mode should optimize for:

- speed
- triage
- explicit next steps
- clear branch movement

This mode should not turn into:

- generic documentation
- open-ended architecture theory
- broad suite claims beyond the current packet chain
- beginner coaching about restart or reporting judgment

### 3. Runtime Cookbook Guide

Artifact:

- `dist/candidates/adf-shallow-surface-map-first-pass/runtime-cookbook-guide.md`

Role:

- slower product-learning support for engineers who need to understand how the
  observed runtime seams fit together
- preserves product-language to runtime-owner translation
- preserves packet-backed interpretation and important non-claims

This mode should optimize for:

- durable transfer of runtime understanding
- architecture and data-flow learning
- packet-backed explanation instead of tribal memory

This mode is also the right home for bounded operational behavior notes such as:

- when reusable lab deployments swap node roles but reuse the same IP address,
  the central manager may need explicit cleanup of the earlier node identity
  before the reused IP attaches cleanly again
- keep those notes clearly labeled as observed practice, operator theory, or
  proven behavior so the cookbook does not overstate what the current evidence
  actually shows

## Shared Contract

All engineer-consumable derived artifacts should:

- stay explicitly downstream of `shallow-surface-map.json`
- preserve the boundary between observed facts, bounded inference, and unknowns
- reuse the current packet layer instead of inventing a second truth source
- stay support-facing and operator-usable
- follow the current frontline playbook shape in
  `docs/specs/adf-successor-triage-playbook-path-model-v1.md` when shaping the
  support-facing playbook layer

## Why This Matters

The ADF successor is now producing more useful bounded runtime packets than the
original first-pass summary format can present well on its own.

Separating a fast playbook from a slower cookbook matters because support
engineers often need two different things:

- immediate decision support during live case handling
- durable runtime understanding they can reuse later

Keeping both modes derived from the same machine-readable layer lets the line
improve look and feel for engineers without giving up the canonical product
artifact.
