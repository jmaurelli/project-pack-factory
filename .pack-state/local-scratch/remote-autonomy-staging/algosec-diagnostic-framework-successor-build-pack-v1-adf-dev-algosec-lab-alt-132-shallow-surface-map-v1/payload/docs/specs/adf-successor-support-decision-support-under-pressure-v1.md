# ADF Successor Support Decision Support Under Pressure v1

## Purpose

Capture the current reviewed support-facing framing for the ADF successor line.

This is not a generic documentation note.
It is a support-facing framing artifact for a high-pressure ASMS environment
where engineers carry heavy case volume, weak product documentation, weak GUI
error messaging, and a long manual escalation path before R&D intervention.

The goal of this note is to preserve four core ideas from the current operator
review:

- support content should be treated as decision support under time pressure,
  not as documentation
- the playbook should start from validated technical triage paths, not from
  weak customer phrasing
- the playbook should strengthen experienced support engineers instead of
  coaching or restricting them
- the ASMS doc pack should act as a guidance layer for cookbook depth and
  terminology without overriding observed runtime or lab evidence

## Operator Reality

The current support environment is high-volume and stressful.

Observed operator framing from the discussion:

- engineers may handle roughly `15` to `20` cases per day
- a typical day may include around `3` web sessions
- the team also carries a critical-case rotation, with a few critical cases per
  day
- the team includes experienced support engineers across multiple seniority
  bands
- most engineers already know Linux basics, networking basics, firewall
  basics, and normal support decision-making
- most engineers already know when to restart, when not to restart, when to go
  deeper, and when to pull in more people
- customer pressure is persistent and often pushes toward direct R&D
  escalation
- weak documentation, weak training, and poor GUI error messaging force
  engineers to learn through painful case-by-case experience
- engineers spend most of their time in CLI and offline logs, with GUI time
  used mainly to gather context rather than to find trustworthy explanations

In plain language:

- support engineers are busy
- support engineers are under pressure
- support engineers are already capable
- the product problem is not lack of basic support skill
- the product problem is lack of a strong diagnostic standard for ASMS

This note treats that gap as a real product problem, not as a soft process
complaint.

## Core Thesis

Do not think of support content as documentation.

Think of support content as decision support under time pressure.

Why that framing fits:

- engineers are not sitting down to study the product calmly while working a
  live case
- they need a stronger way to move from first observation to the next useful
  diagnostic step
- the best support content reduces time to first useful direction and increases
  confidence in that direction

The successor should therefore aim to produce content that helps engineers:

- orient fast
- triage the Linux appliance and ASMS runtime confidently
- move from the first visible surface to the next high-value surface
- branch cleanly into the next technical path
- reuse lab-validated understanding without having to rediscover the same
  failure points repeatedly

## Two Primary Content Modes

The successor should keep two distinct support-facing content modes.

### 1. Diagnostic Playbook

This is the fast-path content.

It is meant for active case handling under pressure and should help the
engineer:

- start from a validated technical path
- perform explicit triage steps
- branch to the next path cleanly
- stay confident during live customer sessions

In plain language:

- the diagnostic playbook helps the engineer work the case

### 2. Richer Cookbook

This is the slower-learning content.

It is meant to help engineers understand:

- how the product behaves
- where known failure points sit
- how node roles differ
- what the current lab-validated evidence is teaching about ASMS over time

This should feel like:

- an enhancement of the technical documentation
- a lab-validated product-learning guide
- a way to capture and distribute hard-won understanding without forcing every
  engineer to rediscover it through painful cases

In plain language:

- the cookbook helps the engineer learn the product

### Why Both Modes Matter

The two modes serve different support needs:

- the playbook supports live first-response triage
- the cookbook supports deeper understanding and later reuse

The successor should therefore avoid collapsing all support content into one
format.

Some content should optimize for:

- speed
- triage
- explicit next steps
- clear branch movement

Other content should optimize for:

- product understanding
- known failure points
- data-flow understanding
- durable transfer of lab-validated knowledge

That distinction should shape future support-facing successor outputs.

## Current Playbook Model

The current reviewed frontline playbook model is recorded in:

- `docs/specs/adf-successor-triage-playbook-path-model-v1.md`

The current working rule is:

- the playbook starts from validated technical paths, not customer-story pages
- the playbook should not coach experienced engineers about restart judgment,
  escalation judgment, reporting workflow, or basic evidence collection
- the playbook should tell the engineer what to check next and where to branch
  next

The current reviewed first-response starting-path set is:

- `Service State`
- `Host Health`
- `Logs`
- `Data Collection and Processing`
- `Distributed Node Role`

Those paths are the current bounded starting set that survived operator review.

## Special Rule For Service State

The CLI service dashboard is only a front-door filter.

It currently shows whether core `ms-*` services are:

- `up`
- `down`
- `not responding`

It does not provide richer diagnostic depth on its own.

Therefore:

- the `Service State` path should stay narrow
- it should sort the issue quickly
- real triage depth usually begins in `Logs`

That rule matters because it keeps the dashboard honest and prevents the
successor from pretending that the service-status view is a richer diagnostic
surface than it actually is.

## Page Shape

The current reviewed frontline playbook page shape is intentionally strict:

- page title only
- `Steps`
- `Branch to`
- `Related cookbook foundations`

Do not add support-page framing like:

- `Use this path when`
- `What this path helps confirm`
- `What these signals usually mean`
- `Evidence to capture`

Those sections add coaching language that the current operator review rejected.

## The Role Of The ASMS Doc Pack

The ASMS doc pack should be treated as a guidance layer, not as the truth
layer.

That role is valuable because the doc pack can help with:

- official names
- product subdivision
- high-level workflow and data-flow context
- config and log references
- module and report vocabulary

The doc pack should therefore support the successor in these ways:

### Cookbook Foundation

Help the cookbook explain:

- what a service, report, or subsystem is called
- where it sits in the official product structure
- which logs, config areas, and admin surfaces are documented at a high level

### Terminology Stability

Help the successor keep naming stable between:

- product labels
- support shorthand
- module names
- report names
- official documentation names

### High-Level Flow Context

Help the cookbook preserve cautious, high-level statements such as:

- this report family depends on traffic logs and prior analysis
- this admin area is associated with these product modules
- this documented feature belongs to this product slice

The doc pack can help shape understanding, but it must not silently overrule
observed runtime or lab evidence.

## Evidence Order

The successor should preserve this support-facing evidence order:

1. observed runtime and case evidence
2. observed logs, CLI surfaces, normalized object identity, and imported lab
   proof
3. ASMS doc-pack guidance about terminology, high-level flow, and documented
   surfaces
4. cautious support-facing inference

In plain language:

- the doc pack can guide naming and cookbook understanding
- the doc pack cannot overrule what the runtime or lab evidence actually shows

## What The Successor Should Not Do

The current operator review explicitly rejected these shapes for frontline
playbooks:

- customer-description-first playbook entry
- support-page coaching about when a senior engineer may or may not restart
  services
- support-page coaching about when to escalate
- support-page coaching about reporting workflow
- support-page coaching about what evidence experienced engineers already know
  to collect
- R&D-depth branch points such as listener ownership, route ownership, or
  backend handoff as frontline triage steps

Those items may still belong in the cookbook or deeper successor artifacts, but
not in the frontline playbook path layer.

## Why This Matters

This framing addresses several real frustrations at once:

- weak internal product documentation
- weak training
- weak GUI error messages
- cryptic logs
- language friction in both logs and team communication
- long manual escalation loops

If the successor can produce better support guidance, it can help engineers:

- waste less time on bad first diagnostic directions
- move faster from first observation to the next useful surface
- speak with more confidence on live customer sessions
- reuse proven system understanding instead of depending only on tribal memory
- carry a clearer diagnostic standard across the team

## Current Relevance To The Successor Line

This discussion is now grounded by the successor's current lab-validated
evidence posture:

- bounded target-backed runtime mapping exists
- bounded architecture, failure-seam, support-pain, and configuration pattern
  reviews exist
- distributed role-separated proofs now exist across standalone, remote-agent,
  LDU, and DR contexts
- the successor already treats imported doc-pack hints as subordinate to live
  runtime evidence

That means this support framing is no longer abstract.
It can now shape future successor work concretely.

## Summary

The key ideas preserved by this note are:

- support content should be treated as decision support under time pressure
- the playbook should start from validated technical paths, not weak customer
  phrasing
- the playbook should strengthen experienced support engineers instead of
  coaching or restricting them
- the cookbook should hold the deeper product, failure-point, and doc-pack
  context behind those playbook paths
- the ASMS doc pack should serve as a guidance layer that improves naming and
  high-level understanding while staying subordinate to observed evidence

This is the support-facing framing the successor should continue to build
toward.

## Current Derived Artifact Shape

The current implementation now expresses that framing through three derived
artifacts under
`dist/candidates/adf-shallow-surface-map-first-pass/`:

- `shallow-surface-summary.md`
- `diagnostic-playbook.md`
- `runtime-cookbook-guide.md`

That split matters because it preserves two different support needs:

- the playbook supports fast frontline triage
- the cookbook supports slower product-learning and knowledge transfer

All three remain downstream of the canonical `shallow-surface-map.json`
artifact, so the successor keeps one machine-readable truth layer while still
improving the engineer-facing look and feel.
