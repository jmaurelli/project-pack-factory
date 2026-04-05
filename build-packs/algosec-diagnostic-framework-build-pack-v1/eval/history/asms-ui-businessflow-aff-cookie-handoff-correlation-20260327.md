# ASMS UI BusinessFlow AFF Cookie Handoff Correlation 2026-03-27

## Purpose

Record one bounded follow-up pass after the healthy
`BusinessFlow -> AFF connection` and FireFlow `UserSession` bridge work so the
playbook can separate the original cookie handoff from the later refresh loop.

The question for this pass was:

- what is the clearest preserved BusinessFlow-side cookie handoff into FireFlow
- and which runtime window best distinguishes that handoff from later
  `getAFASessionInfo` or `bridge/refresh` upkeep

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
- `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/delegated-codex-runs/businessflow-aff-cookie-handoff-v1/target-bundle/`

## Bounded Checks

1. accepted delegated observe-only bundle

   Bundle purpose: capture one bounded BusinessFlow-to-FireFlow handoff slice
   from allowed source and log targets only

   Result:

   - preserved source snippets showed:
     - `SSOLogin.php` sends `AFF_COOKIE=<utils::getFireflowCookie()>` into the
       FireFlow no-auth SSO endpoint
     - FireFlow returns `BFCookie`, which BusinessFlow then sets on
       `/BusinessFlow`
     - `SuiteLoginSessionValidation.php` is the fallback cleanup path, not the
       initiator, and it expires `PHPSESSID`, `RT_SID_FireFlow.443`, and the
       `/BusinessFlow/` plus `/aff/` `JSESSIONID` cookies when authentication is
       missing
     - `Environment.php::getAFASessionInfo()` returns `faSession`,
       `faDomain`, `phpSession`, `username`, and `authenticated` state from the
       local AlgoSec session

2. earlier live handoff window

   Window purpose: preserve the closest runtime handoff after FireFlow
   completes its AFA-side login

   Result:

   - Apache `ssl_access_log` on `2026-03-27 00:00:43-00:00:51 -0400` showed:
     - `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
     - `GET /FireFlow/api/session`
     - `POST /fa/server/connection/login`
     - `POST /fa/environment/getAFASessionInfo`
     - `POST /afa/external//bridge/storeFireflowCookie?...`
     - `POST /afa/external//session/extend?...`
   - matching FireFlow logs for the same window showed:
     - successful AFA login for `Backup_user`
     - `_issuePostToAfa will call /storeFireflowCookie`
     - `Issue metro call, url=[https://localhost:443/afa/external/bridge/storeFireflowCookie]`

3. later steady-state upkeep window

   Window purpose: preserve the later path that should not be mistaken for the
   original cookie bridge

   Result:

   - Apache `ssl_access_log` on `2026-03-27 05:59:57-06:00:00 -0400` showed:
     - `POST /afa/external//bridge/refresh?...`
     - repeated `POST /fa/environment/getAFASessionInfo`
     - `POST /afa/external//session/extend?...`
     - `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
     - `GET /FireFlow/api/session`
   - the accepted delegated reading treated this as post-handoff session upkeep
     rather than the original BusinessFlow cookie bridge

## What Became Clear

- The clearest preserved source-side handoff is now explicit:
  `SSOLogin.php` passes `AFF_COOKIE` into FireFlow and accepts `BFCookie` back
  for `/BusinessFlow`.
- `SuiteLoginSessionValidation.php` is not the initiator for this seam. It is
  a cleanup or fallback point that expires the same cookie families when the
  POST validation path is unauthenticated.
- The earliest preserved runtime handoff is stronger than the later refresh
  loop. The `00:00:43-00:00:51` window ties FireFlow `CommandsDispatcher` and
  `GET /FireFlow/api/session` to `POST /fa/server/connection/login`, then to
  `storeFireflowCookie`, which makes the original handoff more concrete than the
  later `bridge/refresh` cadence.
- The later `05:59:57-06:00:00` pattern is still useful, but it is a different
  branch: repeated `getAFASessionInfo`, AFA `session/extend`, and
  `bridge/refresh` after the session already exists.
- The remaining ambiguity is narrower now. The initiating caller is still
  localhost-bound in the preserved logs, so this pass did not prove the exact
  external BusinessFlow browser request that triggers the handoff.

## Current Reading

For `ASMS UI is down` support work:

- keep `BusinessFlow -> AFF connection` as the named child seam when deep
  health points there
- first prove `/FireFlow/api/session` parity against direct `1989`
- then check the FireFlow `UserSession` bridge and reused FA session context
- if the question is about the original session bootstrap rather than later
  upkeep, look for `storeFireflowCookie` immediately after AFA login instead of
  treating `bridge/refresh` as the first cookie bridge

The remaining gap is now specific: a tighter proof of which external
BusinessFlow browser action or caller path triggers the localhost-side
`CommandsDispatcher` and `storeFireflowCookie` handoff.
