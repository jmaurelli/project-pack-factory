# ADF Successor Triage Playbook Path Model v1

## Purpose

Capture the reviewed support-facing playbook model for the ADF successor line.

This note defines how the successor should structure frontline diagnostic
playbooks for experienced ASMS support engineers without turning those pages
into beginner coaching, reporting workflow repetition, or R&D-depth runtime
analysis.

## Core Working Rule

The playbook should start from validated technical paths, not from weak
customer wording.

The engineer is the expert.
The customer report says that something is wrong.
The playbook should help the engineer triage the Linux virtual appliance and
the ASMS runtime with confidence using known surfaces, lab-validated failure
points, and existing support judgment.

That means the playbook should not be shaped around:

- customer-story phrasing
- soft symptom storytelling
- restart permissioning
- escalation permissioning
- case-report coaching

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

## Role Split

### Playbook

The playbook is the first-responder surface.

It should tell the engineer:

- what to check now
- what to do next
- where to branch next

It should not try to explain the whole product while the engineer is working a
live case.

### Cookbook

The cookbook is the foundation layer behind the playbook.

It should carry:

- deeper ASMS service and node-role understanding
- lab-validated failure points
- known runtime patterns
- product and data-flow context from the doc pack

The cookbook can explain why a path exists.
The playbook should mostly tell the engineer what to do next.

## Current Starting-Path Model

The current reviewed first-response starting-path set is:

- `Service State`
- `Host Health`
- `Logs`
- `Data Collection and Processing`
- `Distributed Node Role`

This is the current bounded starting-point set that survived operator review.
Additional starting paths can be added later only if the evidence supports
them and the result still stays triage-first.

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
- the real diagnostic depth usually begins in `Logs`

The current reviewed `Service State` path logic is:

1. Open the CLI service-status dashboard.
2. Review the core `ms-*` services.
3. Put the result in one of these groups:
   - one core service down
   - multiple core services down
   - one or more core services not responding
   - core services up
4. If any service is down or not responding, open the first relevant logs for
   that service or service group.
5. If core services are up, leave this path and continue in `Logs`.

Current branch rule:

- `one core service down` -> service-focused logs
- `multiple core services down` -> host health or broader logs
- `one or more core services not responding` -> logs
- `core services up` -> logs

This rule matters because it keeps the dashboard honest.
It prevents the successor from pretending the CLI status view is a richer
diagnostic source than it actually is.

## Rejected Shapes

The operator review explicitly rejected these ideas for frontline playbooks:

- customer-description-first playbook entry
- separate `GUI and Access` starting path after service-state review
- support-page coaching about when a senior engineer may or may not restart
  services
- support-page coaching about reporting workflow
- support-page coaching about what evidence engineers already know to collect
- R&D-depth branch points such as listener ownership, route ownership, or
  backend handoff as frontline triage steps

Those items may still belong in the cookbook or deeper successor artifacts, but
not in the frontline playbook path layer.
