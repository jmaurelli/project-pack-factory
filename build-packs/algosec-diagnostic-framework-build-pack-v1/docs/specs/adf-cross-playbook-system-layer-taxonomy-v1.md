# ADF Cross-Playbook System Layer Taxonomy v1

## Purpose

Define the canonical ASMS-runtime-first taxonomy that future ADF playbooks
share.

This is the shared planning contract for ADF playbooks, not a per-playbook
style note. The current playbooks are seed traversals of the model, not the
limit of the model.

## Canonical Status

This taxonomy is the stable ADF layer map for frontline playbook design.

- it tells ADF where to start, what to inspect next, and where to stop
- it keeps one shared language across symptom-entry playbooks, boundary
  confirmation pages, and deep guides
- it is broader than the current proof-of-concept playbooks, but it must stay
  small enough to support live troubleshooting

Do not replace this taxonomy with ad hoc service lists, module trees, or host
checklists in the frontline path.

## Canonical Layers

1. ASMS entry and edge

The first ASMS-visible runtime layer:

- suite login entry, UI assets, listener ownership, TLS termination, and
  reverse-proxy route ownership for the ASMS-visible entry path
- whether the ASMS entry surface can still answer useful requests and route the
  customer journey into the right downstream application surfaces

2. ASMS authentication and session

The identity and session-handoff layer:

- login setup, session validation, redirects, cookies or server-side session
  state, BusinessFlow login handoff, and later Keycloak or FireFlow auth work
- the question here is whether authentication and session establishment can do
  useful work for the reproduced customer journey

3. ASMS application services

The named ASMS service layer:

- BusinessFlow, AFA, AFF, Metro, FireFlow, and other app-owned service seams
- the question here is not only whether a process exists, but whether the
  application service can still do its role in the user journey

4. Shared runtime and dependencies

The shared execution and dependency layer:

- JVM runtimes, Perl or PHP runtime behavior, databases, brokers, local
  filesystem-backed state, certificates, keystores, and similar supporting
  dependencies
- this layer should stay behind the closer customer-visible seams unless the
  reproduced evidence says the issue has already crossed into shared runtime or
  dependency behavior

5. Host integration and operating evidence

The host-facing evidence and integration layer:

- `systemd`, `journalctl`, socket and listener state, filesystems, temp space,
  log files, permissions, local files, and other Rocky 8 or Linux operating
  surfaces that help explain the ASMS runtime state
- this is a supporting evidence plane around ASMS, not the first architectural
  layer and not the primary product map

## Supporting-Surface Rule

Host integration and Linux operating evidence belong in the taxonomy as
supporting surfaces.

Use them to explain the state of the closer ASMS layers, not to define the
frontline path by default.

That means:

- start from customer-visible ASMS symptoms first
- move through the closer ASMS runtime layers before using host checks
- use Linux output as evidence for a broken ASMS boundary, not as the first
  abstract layer of the product model

If the issue is still explainable from ASMS entry, auth/session, application
services, or shared runtime, do not jump straight to host evidence.

## Decision Rule

`Useful work` is a stop rule, not a named layer.

The layer taxonomy tells the engineer where to troubleshoot. The useful-work
rule tells the engineer where to stop: stop at the first layer boundary where
the system can no longer do the customer-visible work that should happen next.

## Playbook Rule

Each playbook is a scenario-specific traversal of the shared ASMS runtime
taxonomy.

Examples:

- `ASMS UI is down` enters through ASMS entry and edge, then authentication and
  session, then application services, and only pulls shared runtime or host
  evidence when the closer ASMS runtime path stays ambiguous.
- FireFlow- or microservice-specific playbooks may enter at a later layer, but
  they still use the same underlying taxonomy and the same stop-at-the-first-
  broken-boundary rule.

## Direction

The current direction for ADF is:

- keep the cross-playbook taxonomy stable
- let individual playbooks define entry symptom, expected traversal, likely stop
  points, and safe restart surfaces
- keep ASMS-runtime-first and support-engineer-friendly language, while using
  Linux tooling as supporting evidence rather than the primary architecture map
- treat the current playbooks as seed examples, not as the architectural ceiling
  for ADF

## Planner Fit

This spec is the canonical home for the two taxonomy planning tasks:

- `codify_system_thinking_as_adf_theme`
- `formalize_linux_foundation_as_adf_theme`

It satisfies both by making the ASMS-runtime-first taxonomy explicit and by
placing host integration and Linux operating evidence in the supporting-surface
role instead of the first architectural layer.
