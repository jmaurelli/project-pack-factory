# ASMS UI Frontline Support Auth-Service-First Decision 2026-03-27

## Purpose

Record the decision to decommission the deep AFF cookie-bootstrap branch from
the active support playbook.

## Support Context

The intended operator model is:

- the support engineer joins the customer over Microsoft Teams or Zoom
- the customer presents the running ASMS GUI or CLI from their own environment
- the support engineer uses copy-paste commands and visible service checks to
  diagnose the running application and restart services when needed

That means the active playbook should optimize for support-useful system
boundaries, not for the deepest internal localhost handoffs.

## Decision

- Keep the frontline ASMS login path centered on customer-visible auth and
  service checkpoints:
  - `/algosec-ui/login`
  - `/seikan/login/setup`
  - `SuiteLoginSessionValidation.php`
  - BusinessFlow health
  - `BusinessFlow -> AFA connection`
  - `BusinessFlow -> AFF connection`
  - the later Keycloak or FireFlow auth handoff
  - service status and restartable daemons such as Apache, BusinessFlow,
    FireFlow, and related platform services
- Decommission the deep localhost cookie-bootstrap branch from the active
  support path.
- Keep the deeper AFF cookie, polling, and localhost-bootstrap notes only as
  archived engineering evidence under `eval/history/`.

## What This Means In Practice

- Do not ask a frontline support engineer to chase
  `storeFireflowCookie`, `getAFASessionInfo`, `bridge/refresh`, repeated
  `ws.php`, or similar localhost traces during a normal login failure case.
- If the user cannot log in, first classify the case as:
  - authentication failure
  - service down
  - proxy or route break
  - later workflow issue after login
- Only reopen the archived deep localhost traces when the frontline auth and
  service checks remain contradictory and engineering-level root-cause work is
  explicitly needed.

## Current Reading

System thinking for this pack now means:

- map the running customer-visible login and service boundaries first
- prefer checks that can be run safely in a live customer session
- stop at the first actionable auth or service boundary
- treat deep localhost bootstrap traces as historical background, not as active
  support stops
