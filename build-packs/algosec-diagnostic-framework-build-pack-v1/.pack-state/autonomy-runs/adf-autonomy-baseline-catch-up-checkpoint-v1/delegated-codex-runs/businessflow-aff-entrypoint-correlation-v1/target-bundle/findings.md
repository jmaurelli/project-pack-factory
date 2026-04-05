## Summary

Observed evidence does not support a distinct BusinessFlow cookie-driven handoff as the initiator of `GET /FireFlow/api/session`.

The strongest correlation is a shared suite polling path on localhost:

- `POST /fa/environment/getAFASessionInfo`
- `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
- `GET /FireFlow/api/session`
- repeated `POST /afa/php/ws.php`

This sequence appears in the same second on March 25, 2026 at `03:00:43-03:00:44`, `03:15:43-03:15:44`, and other repeating windows in `/var/log/httpd/ssl_access_log-20260325`.

## Key findings

1. `SuiteLoginSessionValidation.php` explicitly cannot read the BusinessFlow cookie and intentionally validates only AFA and FireFlow state.
   Source: `/usr/share/fa/php/SuiteLoginSessionValidation.php`

2. `getAFASessionInfo` is a read-only AFA session endpoint that returns `faSession`, `faDomain`, `phpSession`, `username`, and `authenticated`.
   Source: `/usr/share/fa/php/ci/application/controllers/Environment.php`

3. FireFlow validation on the AFA side is based on the FireFlow cookie alone via `checkFireFlowAuth()`, not on a BusinessFlow cookie branch.
   Source: `/usr/share/fa/php/utils.php`

4. BusinessFlow SSO does exist, but it is only visible in explicit SSO code paths where AFA sets a `/BusinessFlow` cookie.
   Source: `/usr/share/fa/php/SSOLogin.php`, `/usr/share/fa/php/BusinessFlowAPI.php`

5. The repeating access-log sequence around `/FireFlow/api/session` also includes `GET /BusinessFlow/shallow_health_check` and `GET /aff/api/internal/noauth/health/*`, which looks like appliance health/UI polling rather than a one-time BusinessFlow-auth redirect.

## Assessment

Most likely immediate caller for the observed AFF session checks is the shared suite UI/bridge polling loop, not a BusinessFlow-only cookie branch.

BusinessFlow is still present in the same windows via health checks, but the allowed-source evidence here does not isolate a BusinessFlow-side entrypoint that directly triggers `/FireFlow/api/session` before the shared bridge/poller does.

## Limits

- The baseline summary file referenced by the request was not present at the stated path.
- I did not find a readable local source file in the allowed PHP tree for `FireFlowAffApi/NoAuth/CommandsDispatcher`.
- I did not find per-request cookie dumps in the allowed logs, so the initiator claim is necessarily based on timing and local-source behavior, not raw cookie capture.
