# ADF Successor Support Decision Support Under Pressure v1

## Purpose

Capture the operator discussion about what support engineers actually need from
the ADF successor line.

This is not a generic documentation note.
It is a support-facing framing artifact for a high-pressure ASMS environment
where engineers carry heavy case volume, weak customer problem statements,
weak product documentation, weak GUI error messaging, and a long manual
escalation path before R&D intervention.

The goal of this note is to preserve three core ideas from that discussion:

- support content should be treated as decision support under time pressure,
  not as documentation
- support engineers are usually starting from an ambiguity-conversion problem,
  not from a clean technical problem statement
- the ASMS doc pack should act as a guidance layer that helps shape
  investigation and data-flow understanding without overriding observed runtime
  evidence

## Two Primary Content Modes

The discussion also surfaced an important distinction:

support engineers may need two primary kinds of content from the successor.

### 1. Diagnostic Playbook

This is the fast-path content.

It is meant for active case handling under pressure and should help the
engineer:

- classify the problem quickly
- resolve the internal ASMS identity
- follow the right dependency chain
- choose the next evidence checkpoint
- decide whether the case can continue locally or needs escalation

In plain language:

- the diagnostic playbook helps the engineer work the case

### 2. Richer Cookbook

This is the slower-learning content.

It is meant to help engineers understand how the product behaves, how data
flows through it, how the observed runtime seams fit together, and what the
validated successor evidence is teaching about the product over time.

This should feel like:

- an enhancement of the technical documentation
- a lab-validated product-learning guide
- a way to capture and distribute hard-won understanding without forcing every
  engineer to rediscover it through painful cases

In plain language:

- the cookbook helps the engineer learn the product

### Why Both Modes Matter

The two modes serve different support needs:

- the playbook reduces time pressure during live case handling
- the cookbook reduces long-term dependence on tribal knowledge

The successor should therefore avoid collapsing all support content into one
format.

Some content should optimize for:

- speed
- triage
- first actions
- evidence collection

Other content should optimize for:

- product understanding
- data-flow understanding
- architecture understanding
- durable transfer of lab-validated knowledge

That distinction should shape future support-facing successor outputs.

## Operator Reality

The current support environment is high-volume and stressful.

Observed operator framing from the discussion:

- engineers may handle roughly `15` to `20` cases per day
- a typical day may include around `3` web sessions
- the team also carries a critical-case rotation, with a few critical cases per
  day
- the team includes support engineers of varying levels, from tier-two through
  escalation and strategic-account roles
- customer pressure is persistent and often pushes toward direct R&D
  escalation
- the official workflow is slower:
  support engineer -> escalation engineer -> Jira / R&D path
- weak documentation, weak training, and poor GUI error messaging force
  engineers to learn through painful case-by-case experience
- engineers spend most of their time in CLI and offline logs, with GUI time
  used mainly to gather context rather than to find trustworthy explanations

In plain language:

- support engineers are busy
- support engineers are under pressure
- support engineers are often forced to improvise
- the current system rewards tribal knowledge more than clear product guidance

This note treats that frustration as a real product problem, not as a soft
process complaint.

## Core Thesis

Do not think of support content as documentation.

Think of support content as decision support under time pressure.

Why that framing fits:

- engineers are not sitting down to study the product calmly
- they need to orient quickly, ask better questions, gather better evidence,
  and decide whether they can continue or need escalation
- the best support content reduces time to first useful hypothesis, time to
  first trustworthy evidence, and time to a justified escalation boundary

The successor should therefore aim to produce content that helps engineers:

- orient fast
- translate weak customer language into internal ASMS coordinates
- follow the right dependency chain
- identify the first broken link
- hand off evidence cleanly when escalation is required

## The Real Starting Point

Support engineers are usually not starting from a technical problem.

They are starting from an ambiguity-conversion problem.

The first hard job is turning weak customer language into ASMS-internal
coordinates such as:

- the exact feature or report component
- the exact firewall identity as ASMS names it
- the exact normalized object name, including concatenation or formatting rules
- the likely upstream prerequisites for the reported behavior
- the likely logs, CLI surfaces, or offline evidence needed next

This is especially important in ASMS because customer-facing names and
ASMS-internal names often diverge:

- spaces may become underscores
- IP addresses may be normalized into underscore-separated identifiers
- virtual systems, virtual routers, or related identity fragments may be
  concatenated into long internal names

That means the engineer often has to solve identity before they can even start
solving the product behavior.

## Support Mental Model

The strongest mental model from the discussion is:

- customer claim
- ASMS internal identity
- dependency chain
- evidence checkpoints
- first broken link

This should become a core successor framing surface for support-oriented
content.

Why this model matters:

- it matches how real cases start
- it prevents engineers from jumping straight into broad product guessing
- it turns vague symptoms into a bounded evidence path
- it helps the engineer explain the issue back to the customer in a more
  grounded way

## High-Volume Case Concentration

The operator discussion identified a large case concentration around:

- firewall monitoring
- firewall analysis
- log collection
- traffic log collection
- audit log collection

Those areas likely cover a large share of support volume.

That means support guidance should not begin with a flat feature catalog.
It should begin with the major dependency-heavy case families where engineers
lose the most time and confidence.

## Example: Policy Optimization Contradiction

The operator gave one representative case shape:

- customer says a firewall rule is used
- customer can show firewall-side hit counts
- ASMS says the rule is unused

This is exactly the kind of support problem that should not be handled by
tribal guesswork alone.

A support-oriented successor should help the engineer walk the case through a
bounded dependency chain such as:

1. correct firewall identity in ASMS
2. correct rule identity and mapping
3. traffic log collection for that firewall
4. traffic log parsing and retention
5. traffic-to-rule correlation
6. analysis and report generation
7. report wording and timing relative to firewall-side evidence

The useful support question is not:

- "who is right, the customer or ASMS?"

The useful support question is:

- "which dependency or evidence checkpoint is the first broken link between
  firewall-side truth and ASMS-side truth?"

That is the type of guidance the successor should aim to generate.

## The Role Of The ASMS Doc Pack

The ASMS doc pack should be treated as a guidance layer, not as the truth
layer.

That role is valuable because the doc pack can help with:

- terminology bridging
- workflow and data-flow hints
- likely prerequisite chains
- likely module or report relationships
- better investigative questions at intake time

The doc pack should therefore support the successor in these ways:

### Terminology Bridge

Help translate between:

- customer language
- support shorthand
- GUI labels
- report names
- module names
- ASMS internal identities

### Workflow And Data-Flow Hints

Help the successor form bounded hypotheses such as:

- this report component probably depends on traffic logs plus prior analysis
- this symptom likely belongs upstream of report generation
- this GUI surface probably maps to these service families or data stages

### Better Intake Questions

Help the successor ask for the right missing data early:

- which firewall object exactly
- which report or component exactly
- which timeframe
- which log type
- which VSYS / VR / virtual context
- whether the issue is live behavior, stale report state, or naming mismatch

### Contradiction Interpretation

Help the successor explain how two apparently conflicting truths can coexist,
for example:

- firewall hit counts show rule use
- ASMS still reports the rule as unused

The doc pack can help shape the likely dependency chain behind that
contradiction, but it must not silently overrule observed evidence.

## Evidence Order

The successor should preserve this support-facing evidence order:

1. observed runtime and case evidence
2. observed logs, CLI surfaces, normalized object identity, and imported lab
   proof
3. ASMS doc-pack guidance about likely flow, terminology, and prerequisites
4. cautious support-facing inference

In plain language:

- the doc pack can influence the next question
- the doc pack cannot overrule what the runtime actually shows

## Why This Matters For Support Engineers

This framing addresses several real frustrations at once:

- weak customer descriptions
- weak internal product documentation
- weak training
- weak GUI error messages
- cryptic logs
- language friction in both logs and team communication
- long manual escalation loops

If the successor can produce better support guidance, it can help engineers:

- waste less time on bad first guesses
- ask customers for better evidence sooner
- move faster from symptom to identity
- move faster from identity to dependency chain
- move faster from dependency chain to the first broken link
- provide better explanations to the customer before escalation
- escalate with stronger evidence when escalation is actually needed

## What The Successor Should Ultimately Enable

The successor should aim to make support engineers more effective without
pretending to replace their judgment.

The desired outcome is:

- the successor provides guidance to the support engineer
- the support engineer uses that guidance to provide better guidance to the
  customer

That is the right practical goal.

The first meaningful win is not perfect diagnosis.
The first meaningful win is better orientation, better evidence requests,
better dependency reasoning, and better communication under pressure.

## Current Relevance To The Successor Line

This discussion is now grounded by the successor's current lab-validated
evidence posture:

- bounded target-backed runtime mapping exists
- bounded route-owner and session-chain packets exist
- bounded ASMS architecture, failure-seam, support-pain, and configuration
  pattern reviews now exist
- the successor already treats imported doc-pack hints as subordinate to live
  runtime evidence

That means this support framing is no longer abstract.
It can now shape future successor work concretely.

## Practical Direction

Future successor work should keep asking:

- how do we reduce ambiguity at intake
- how do we resolve ASMS internal identity faster
- how do we expose dependency chains more clearly
- how do we help the engineer find the first broken link
- how do we use the doc pack as a guidance layer without turning it into
  folklore
- how do we produce guidance that helps support engineers help customers

## Summary

The key ideas preserved by this note are:

- support content should be treated as decision support under time pressure
- support engineers usually start from ambiguity conversion, not from clean
  technical problem statements
- the strongest support mental model is:
  customer claim -> ASMS internal identity -> dependency chain ->
  evidence checkpoints -> first broken link
- the ASMS doc pack should serve as a guidance layer that improves terms,
  workflow hints, intake questions, and contradiction reasoning while staying
  subordinate to observed evidence

This is the support-facing framing the successor should continue to build
toward.
