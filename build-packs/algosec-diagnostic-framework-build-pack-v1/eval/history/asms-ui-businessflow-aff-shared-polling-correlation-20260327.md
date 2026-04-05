# ASMS UI BusinessFlow AFF Shared Polling Correlation 2026-03-27

## Purpose

Record one bounded follow-up pass after the AFF cookie-handoff note so the
playbook can distinguish the original bootstrap window from later recurring
`/FireFlow/api/session` polling windows.

The question for this pass was:

- do the later repeated AFF session windows support a distinct
  BusinessFlow-only initiator
- or do they better match a shared suite localhost polling loop

## Control Path

This pass used both local and remote paths:

- PackFactory root used a local multi-agent swarm to inspect the preserved AFF
  source and runtime evidence
- PackFactory root then used the staged build pack on `adf-dev` to launch an
  accepted `observe_only` delegated target slice
- the delegated slice ran on `algosec-lab` at `10.167.2.150`
- the returned bundle was pulled back to `adf-dev`, reviewed as `accepted`,
  and synced into the local pack

Relevant surfaces:

- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `docs/remote-targets/algosec-lab/target-connection-profile.json`
- `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/delegated-codex-runs/businessflow-aff-entrypoint-correlation-v1/target-bundle/`

## Bounded Checks

1. accepted delegated observe-only bundle

   Bundle purpose: capture one bounded later AFF session window from allowed
   PHP and log targets only

   Result:

   - the accepted delegated reading did not isolate a distinct
     BusinessFlow-cookie branch as the direct initiator of
     `GET /FireFlow/api/session`
   - the strongest recurring windows came from
     `/var/log/httpd/ssl_access_log-20260325`
   - the clearest preserved cadence was `2026-03-25 03:15:43-03:15:44 -0400`,
     with the same-second sequence:
     - repeated `POST /afa/php/ws.php`
     - `GET /BusinessFlow/shallow_health_check`
     - `GET /aff/api/internal/noauth/health/shallow`
     - `GET /aff/api/internal/noauth/health/deep`
     - `POST /fa/environment/getAFASessionInfo`
     - `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
     - `GET /FireFlow/api/session`
     - `GET /BusinessFlow/deep_health_check`
     - then another `POST /fa/environment/getAFASessionInfo`,
       AFA `session/extend`, more `POST /afa/php/ws.php`,
       `CommandsDispatcher`, and `GET /FireFlow/api/session`
   - an earlier preserved cadence at `2026-03-25 03:15:05-03:15:10 -0400`
     already showed the same shared-family pattern with
     `isSessionAlive`, `CommandsDispatcher`,
     `GET /FireFlow/api/session/validate`, and
     `POST /fa/environment/getAFASessionInfo`
   - preserved source excerpts also showed:
     - `SuiteLoginSessionValidation.php` cannot read the BusinessFlow cookie
       because its path is `/BusinessFlow`, so it validates AFA plus FireFlow
       state instead
     - `Environment.php::getAFASessionInfo()` is a read-only AFA session
       endpoint that returns `faSession`, `faDomain`, `phpSession`,
       `username`, and `authenticated`
     - `utils.php::getFireflowCookie()` extracts only `AFF_COOKIE`, while
       `checkFireFlowAuth()` validates against the FireFlow cookie
     - explicit SSO paths still exist in `SSOLogin.php`, but the delegated
       reading treated those as different from the recurring March 25 polling
       pattern

## What Became Clear

- The cookie-handoff note still owns the original bootstrap window.
- The later recurring March 25 windows are better treated as shared suite
  polling than as a distinct BusinessFlow-only cookie handoff.
- In those recurring windows, the closest same-second initiators visible in the
  allowed logs are `CommandsDispatcher` plus the shared localhost calls around
  `getAFASessionInfo`, repeated `/afa/php/ws.php`, and BusinessFlow or AFF
  health checks.
- That means a reproduced `/FireFlow/api/session` window is not automatically
  the original bootstrap just because BusinessFlow appears nearby.
- The remaining ambiguity is narrower now: which external browser action or
  caller path leads into the localhost-side bootstrap window, as opposed to the
  later shared suite polling cadence.

## Current Reading

For `ASMS UI is down` support work:

- keep `BusinessFlow -> AFF connection` as the named child seam when deep
  health points there
- first prove `/FireFlow/api/session` parity against direct `1989`
- if the reproduced window shows `fa/server/connection/login` followed by
  `storeFireflowCookie`, treat it as the original bootstrap handoff
- if the reproduced window instead shows repeated `/afa/php/ws.php`,
  `getAFASessionInfo`, `CommandsDispatcher`, and BusinessFlow or AFF health
  checks in the same second, treat it as later shared suite polling rather than
  as the original cookie bridge

The remaining gap is now specific: a tighter proof of which external
BusinessFlow browser action or caller path triggers the localhost-side
bootstrap rather than the recurring polling loop.
