# ASMS UI BusinessFlow AFF Bootstrap Trigger Correlation 2026-03-27

## Purpose

Record one bounded follow-up pass after the AFF cookie-handoff and shared
polling notes so the playbook can name the strongest browser-facing trigger for
the localhost bootstrap window.

The question for this pass was:

- what browser-facing request path most likely leads into the localhost AFF
  bootstrap window
- and how much of that attribution is direct evidence versus inference

## Control Path

This pass used both local and remote paths:

- PackFactory root used a local multi-agent swarm to inspect prior accepted
  auth-flow and AFF evidence
- PackFactory root then used the staged build pack on `adf-dev` to launch an
  accepted `observe_only` delegated target slice
- the delegated slice ran on `algosec-lab` at `10.167.2.150`
- the returned bundle was pulled back to `adf-dev`, reviewed as `accepted`,
  and synced into the local pack

Relevant surfaces:

- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `docs/remote-targets/algosec-lab/target-connection-profile.json`
- `.pack-state/remote-codex/asms-ui-auth-hop-pass-20260325.md`
- `.pack-state/remote-codex/asms-ui-authenticated-flow-pass-20260325.md`
- `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/delegated-codex-runs/businessflow-aff-bootstrap-trigger-v1/target-bundle/`

## Bounded Checks

1. accepted delegated observe-only bundle

   Bundle purpose: correlate the bootstrap windows with browser-facing suite
   source and Apache history

   Result:

   - the requested Apache bootstrap windows on `2026-03-26 10:20:05-10:20:17`
     EDT and `2026-03-27 00:00:43-00:00:51` EDT showed only localhost traffic
   - the preserved localhost bootstrap chain was:
     - `POST /fa/server/connection/login`
     - `POST /FireFlow/SelfService/CheckAuthentication`
     - `POST /BusinessFlow/rest/v1/login`
     - `POST /afa/external//bridge/storeFireflowCookie`
     - then `home.php`-adjacent AFA calls such as `getAFASessionInfo`,
       `config`, `ws.php`, and `session/extend`
   - the delegated slice also preserved:
     - Apache timeline artifacts for both bootstrap windows
     - AFF-side access-log confirmation that AFF received
       `POST /aff/api/external/authentication/authenticate`
     - a shipped `login.service.ts` snippet extracted from
       `/usr/share/fa/suite/client/app/suite-new-ui/main.js.map`

2. shipped suite login-shell source

   Source purpose: identify the most likely browser-facing caller when the
   exact bootstrap seconds are all localhost-only

   Result:

   - the login shell exports:
     - `sessionValidationUrl = '/afa/php/SuiteLoginSessionValidation.php'`
     - `SSOUrl = '/afa/php/SSOLogin.php'`
     - `bflowHealthUrl = '/BusinessFlow'`
     - `affHealthUrl = '/aff/api/internal/noauth/getStatus'`
   - `getSetup()` fetches `/seikan/login/setup`, then checks AFF health first
     and BusinessFlow health if ABF is also enabled
   - `calcLoginSystem()` prefers `aff` when AFF is enabled and version-clean,
     then falls back to `abf`, then `afa`
   - `submitLogin()` uses:
     - `aff -> /FireFlow/SelfService/CheckAuthentication/`
     - on AFF non-success and ABF enabled:
       `abf -> /BusinessFlow/rest/v1/login`
     - otherwise:
       `afa -> /fa/server/connection/login`

3. earlier accepted auth-flow notes

   Note purpose: keep the browser-facing inference grounded in previously
   accepted pack evidence

   Result:

   - the accepted auth-hop note already showed the suite shell path
     `/algosec/suite/login -> /algosec-ui/login -> /seikan/login/setup ->
     /afa/php/SuiteLoginSessionValidation.php`
   - the accepted authenticated-flow note already showed the later observed
     auth-chain members:
     `POST /BusinessFlow/rest/v1/login`,
     `GET /FireFlow/SelfService/CheckAuthentication/?login=1`,
     then `/afa/php/home.php`

## What Became Clear

- The exact bootstrap seconds do not expose a browser-client IP or a
  non-localhost request immediately before the bootstrap chain.
- Even so, the strongest supported browser-facing entrypoint is now clearer:
  the suite login shell at `/algosec-ui/login`.
- The strongest early browser-visible setup probe is `/seikan/login/setup`.
- The strongest supported trigger model is the Angular login shell driving an
  AFF-first cascade:
  `CheckAuthentication -> BusinessFlow login -> AFA login fallback` as needed,
  rather than a direct browser request to AFF or ABF endpoints.
- That attribution is still inference, but it is now a strong inference because
  it is backed by both the shipped login-shell source and the accepted Apache
  bootstrap windows.

## Current Reading

For `ASMS UI is down` support work:

- keep the browser-facing auth trigger on the suite shell:
  `/algosec-ui/login`
- treat `/seikan/login/setup` as the first visible setup probe after the shell
- treat `SuiteLoginSessionValidation.php` as the legacy validation hop that
  prepares the login shell state
- treat the later localhost bootstrap as a server-side or proxied cascade from
  that shell, not as a direct browser hit to AFF or ABF endpoints

The remaining gap is now very narrow: if stronger proof is needed, capture
request headers or proxy metadata such as `Referer` or `X-Forwarded-For` for a
fresh login so the suite shell can be tied to the localhost bootstrap window
without inference.
