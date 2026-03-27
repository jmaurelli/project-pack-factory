# ASMS UI BusinessFlow AFF UserSession Bridge Correlation 2026-03-27

## Purpose

Record one bounded follow-up pass after the healthy
`BusinessFlow -> AFF connection` seam so the next readable stop is sharper than
generic FireFlow.

The question for this pass was:

- what sits immediately behind the healthy `/FireFlow/api/session` parity check
- and what clues show that FireFlow is reusing an FA session before the later
  workflow branches begin

## Control Path

This pass kept the same split-host helper route:

- PackFactory root used the staged build pack on `adf-dev`
- the staged ADF runtime on `adf-dev` ran pack-local target helpers
- the downstream target remained `algosec-lab` on `10.167.2.150`

Relevant surfaces:

- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `docs/remote-targets/algosec-lab/target-connection-profile.json`
- `.pack-state/remote-autonomy-staging/algosec-diagnostic-framework-build-pack-v1-split-host-smoke-run-v1/target-manifest.json`
- accepted delegated bundle:
  `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/delegated-codex-runs/businessflow-aff-usersession-bridge-v1/target-bundle/`

An earlier `observe_only` delegated launch for the same question under
`.pack-state/delegated-codex-runs/businessflow-aff-session-context-trace-v1`
did not produce the clean result surface needed at the time. Treat that earlier
launch as supplementary debugging only. The accepted `businessflow-aff-usersession-bridge-v1`
bundle is the canonical delegated evidence for this pass.

## Bounded Checks

1. staged helper correlation from `adf-dev`

   Command purpose: correlate the nearby Apache minute for BusinessFlow and the
   FireFlow AFF side on `algosec-lab`

   Result:

   - `GET /BusinessFlow/deep_health_check` appeared at
     `2026-03-27 06:25:43 -0400`
   - the same Apache window also showed:
     - `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
     - `GET /FireFlow/api/session`
     - `GET /FireFlow/api/session/validate?fireflowSessionOnly=true`
     - `POST /FireFlow/api/session/extendSession?...`

2. accepted delegated observe-only bundle

   Bundle purpose: reproduce the same seam with preserved Apache, FireFlow, and
   BusinessFlow-side PHP context artifacts

   Result:

   - Apache `ssl_request_log` showed repeatable windows at `06:20` and again at
     `06:25` EDT where BusinessFlow health checks continued while FireFlow
     performed:
     - `GET /FireFlow/api/session/validate`
     - `POST /FireFlow/api/session/extendSession`
     - `POST /fa/environment/getAFASessionInfo`
     - `POST /afa/external//bridge/refresh`
   - FireFlow logs on those same windows showed:
     - `UserSessionPersistenceEventHandler.java::requestUserDetails`
     - `ff-session: ...`
     - `LegacyRestRepository.java::sendRequest`
     - `Calling to perl code [UserSession::getUserSession]`
     - `Calling to perl code [UserSession::isUserSessionValid]`
     - `Using existing FASessionId: uimmr6u9e8`
   - a second FireFlow session branch around `06:20:43` and `06:25:43` called
     `POST /fa/environment/getAFASessionInfo` before resolving
     `Using existing FASessionId: n575jpek15`, then extended the AFA session
   - preserved BusinessFlow-side PHP context also showed:
     - `SSOLogin.php` sends `AFF_COOKIE=<utils::getFireflowCookie()>` into the
       FireFlow SSO bootstrap
     - FireFlow can return `BFCookie`, which BusinessFlow then sets on
       `/BusinessFlow`
     - `SuiteLoginSessionValidation.php` explains that suite login cannot read
       that BusinessFlow cookie because the cookie path is `/BusinessFlow`, so
       it validates against AFA plus FireFlow instead
     - `AlgosecSessionManager.php` notes that AFF separation changed suite login
       to use AFA REST login semantics
     - `ExtUtils.php` preserves `Could not find AlgosecSession` because FireFlow
       searches for it in `VerifyGetFASessionIdValid`

## What Became Clear

- The next readable stop behind a healthy `BusinessFlow -> AFF connection`
  seam is not generic FireFlow and not only `aff-boot.service`.
- The sharper stop is the FireFlow `UserSession` bridge:
  `CommandsDispatcher` or `/FireFlow/api/session` ->
  `UserSessionPersistenceEventHandler.java::requestUserDetails` ->
  `LegacyRestRepository.java::sendRequest` ->
  `UserSession::getUserSession` or `isUserSessionValid` ->
  reused `FASessionId`
- The accepted delegated bundle sharpened the branch further:
  FireFlow can call `getAFASessionInfo` and `/afa/external//bridge/refresh`
  before resolving a usable FA session, which suggests FireFlow sometimes
  reconstructs or refreshes AFA context before serving `/FireFlow/api/session`.
- The preserved PHP context makes the BusinessFlow side less abstract too:
  `AFF_COOKIE` is passed into FireFlow SSO bootstrap, BusinessFlow can receive a
  cookie back on `/BusinessFlow`, and suite login intentionally falls back to
  AFA plus FireFlow validation because that BusinessFlow cookie path is not
  visible in that context.
- That keeps the support stop closer to session bridging and reused FA session
  context than to later config-broadcast, ticket-progression, or ActiveMQ
  theories.

## Current Reading

For `ASMS UI is down` support work:

- keep `BusinessFlow -> AFF connection` as the named child seam when deep
  health points there
- first prove `/FireFlow/api/session` parity against direct `1989`
- then stop on the FireFlow `UserSession` bridge, reused FA session context,
  and `getAFASessionInfo` or `bridge/refresh` fallback branch before widening
  into later FireFlow workflow or broker branches

The remaining gap is still the same one: a tighter proof of the exact
BusinessFlow-side caller that initiates this AFF path before FireFlow reuses the
FA session or falls back through `getAFASessionInfo`.
