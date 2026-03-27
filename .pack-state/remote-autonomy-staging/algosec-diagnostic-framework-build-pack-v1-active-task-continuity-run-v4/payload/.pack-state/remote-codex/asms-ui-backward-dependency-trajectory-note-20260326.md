# ASMS UI Backward Dependency Trajectory Note 2026-03-26

## Why This Exists

The current `ASMS UI is down` work is no longer only about proving the first
usable shell.

The next systems-thinking slice is to walk backward from the customer-visible
ASMS path through the operational modules that can make a case look like `GUI
down`, while keeping the playbook classification boundary clean.

## Current Operator Boundary

For support classification, stop calling the case `ASMS UI is down` once the
customer can:

- navigate the devices tree
- open `REPORTS` and view a report
- optionally reach the `Analyze` surface

After that, branch into the more specific failing workflow instead.

## Current Backward Dependency Working Model

Keep this as the current working model unless stronger lab evidence proves a
better path:

- Apache edge
- legacy setup and session-validation hop
- BusinessFlow as the first named operational checkpoint
- later Keycloak and FireFlow auth-coupled handoff
- `/afa/php/home.php`
- dashboard and issue-center hydration
- later device-content and workflow branches

## New Trajectory

The next ADF trajectory is to walk backward through the ASMS path this way:

1. keep the core `ASMS UI is down` playbook bounded around first usable GUI
   availability
2. treat BusinessFlow as the earlier support-relevant stop point inside the
   greater ASMS path
3. treat FireFlow as a later auth-coupled stop point that can still present to
   support like a GUI-down or login-stall case
4. only then inspect supporting dependencies behind those module checkpoints
5. keep ActiveMQ, JMS, and similar broker dependencies out of the first-pass
   path unless the live flow proves they are directly involved

## What The Latest Evidence Supports

- BusinessFlow is directly proxied through Apache to local `8081`.
- FireFlow API traffic is directly proxied through Apache to local `1989`.
- The observed authenticated ASMS journey reaches BusinessFlow before the later
  FireFlow auth signals.
- ActiveMQ is clearly configured for the broader `algosec-ms` microservice
  layer on this appliance, but it is not yet proven as a first-pass ASMS
  GUI-down gate.
- The strongest current interpretation is:
  - BusinessFlow = earlier operational checkpoint
  - FireFlow = later auth-coupled checkpoint
  - ActiveMQ = supporting or edge-case dependency unless the live flow proves a
    broker or JMS tie

## Next Dependency Seams

The next seams to inspect are the immediate backend dependency surfaces behind:

- `ms-bflow.service` on `8081`
- `aff-boot.service` on `1989`

Specifically:

- identify the direct neighbors that can stop BusinessFlow before the customer
  reaches the authenticated shell
- identify the direct neighbors that can stop FireFlow during the later
  authenticated handoff
- watch for evidence that `ms-metro`, `aff-boot`, or a broker client actually
  opens a JMS or ActiveMQ dependency during the failing path

## Working Rule For ActiveMQ

Do not promote ActiveMQ into the first-pass `ASMS UI is down` path just because
it exists or is running.

Promote it only if:

- the failing ASMS flow shows broker or JMS-related errors in the same minute,
  or
- the direct module under inspection clearly depends on the broker in the
  failing path

