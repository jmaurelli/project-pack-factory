This delegated slice stayed observe-only within the allowed targets.

The clearest source-side handoff is in `SSOLogin.php`: AFA sends `AFF_COOKIE=<RT_SID_FireFlow.443>` into FireFlow's no-auth SSO endpoint, then accepts `BFCookie` back and plants it on `/BusinessFlow`. That is the direct BusinessFlow-to-FireFlow cookie bridge in source.

`SuiteLoginSessionValidation.php` is the fallback cleanup point, not the initiator. If authentication is missing on the POST validation path, it explicitly expires `PHPSESSID`, `RT_SID_FireFlow.443`, and both `/BusinessFlow/` and `/aff/` `JSESSIONID` cookies.

The closest preserved runtime handoff window I found is on March 27, 2026 at `00:00:43-00:00:51 -0400`:

- `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
- `GET /FireFlow/api/session`
- `POST /fa/server/connection/login`
- `POST /fa/environment/getAFASessionInfo`
- `POST /afa/external//bridge/storeFireflowCookie?...`
- `POST /afa/external//session/extend?...`

The matching FireFlow log ties that exact window to a successful AFA login for `Backup_user`, followed immediately by `_issuePostToAfa will call /storeFireflowCookie`. That strongly suggests the cookie handoff happens immediately after FireFlow completes its AFA-side login, before the later periodic `refresh` loop.

The later steady-state pattern is distinct. By March 27, 2026 `05:59:57-06:00:00 -0400`, the logs show `bridge/refresh`, repeated `getAFASessionInfo`, AFA `session/extend`, and `GET /FireFlow/api/session` in the same second. This looks like post-handoff session upkeep, not the original BusinessFlow cookie bridge.

Two useful anomalies remain visible:

- FireFlow logs and some AFA-side requests preserve duplicated query material such as `...?domain=0&session=... ?domain=0&session=...` or `...?session=...&domain=0?session=...&domain=0`.
- The initiating caller in the preserved windows is still internal and localhost-bound (`FireFlowAffApi/NoAuth/CommandsDispatcher`, `FireFlow/XML/CommandsDispatcher`, `/afa/php/ws.php`, `/afa/php/commands.php`). I did not find an external BusinessFlow browser request in the allowed logs that directly precedes the handoff.

Artifacts:

- `artifacts/source-snippets.txt`
- `artifacts/log-windows.txt`
