Observed result: the AFF cookie-bootstrap sequence at `27/Mar/2026 00:00:43-00:00:51 -0400` does not have an immediately preceding non-`127.0.0.1` request in the Apache slice that contains it.

What the logs show:
- [`artifacts/march27-midnight-ssl-slice.txt`](/root/.pack-state/delegated-codex-runs/businessflow-aff-bootstrap-trigger-v1/artifacts/march27-midnight-ssl-slice.txt) contains the exact Apache sequence. Every request in the relevant window is `127.0.0.1`.
- The sequence is: `GET /`, repeated `POST /afa/php/ws.php`, `GET /BusinessFlow/shallow_health_check`, `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`, `GET /FireFlow/api/session`, `POST /fa/server/connection/login`, then at `00:00:50-00:00:51` `POST /fa/environment/getAFASessionInfo`, `POST /afa/external//bridge/storeFireflowCookie`, `POST /FireFlow/XML/CommandsDispatcher`, and `POST /BusinessFlow/rest/v1/login`.
- [`artifacts/march27-fireflow-bootstrap-slice.txt`](/root/.pack-state/delegated-codex-runs/businessflow-aff-bootstrap-trigger-v1/artifacts/march27-fireflow-bootstrap-slice.txt) shows FireFlow logging the same handoff internally. At `00:00:50.607-00:00:50.608`, `FABridge.pm` issues `/storeFireflowCookie` to `https://localhost:443/afa/external/bridge/storeFireflowCookie`.

What the PHP sources imply:
- [`Login.php`](/usr/share/fa/php/Login.php#L24) redirects suite login requests to `/algosec-ui/login`.
- [`SuiteLoginSessionValidation.php`](/usr/share/fa/php/SuiteLoginSessionValidation.php#L206) sends unauthenticated users to `/algosec-ui/login`, and on valid sessions redirects to `/afa/php/home.php`, `FireFlow`, or the BusinessFlow URL depending on landing-page logic.
- [`BusinessFlowAPI.php`](/usr/share/fa/php/BusinessFlowAPI.php#L24) performs BusinessFlow login server-side by calling `rest/v1/login`.
- [`SSOLogin.php`](/usr/share/fa/php/SSOLogin.php#L295) also calls `BusinessFlowAPI::login`, then sets the `JSESSIONID` cookie for `/BusinessFlow`.
- [`utils.php`](/usr/share/fa/php/utils.php#L3204) validates FireFlow authentication through `/FireFlow/SelfService/CheckAuthentication/?login=1`.

Closest browser-visible precursor found:
- The March 27 midnight logs do not contain `/algosec-ui/login`, `/seikan/login/setup`, `/afa/php/SuiteLoginSessionValidation.php`, or `/afa/php/home.php`.
- A representative browser-visible sequence exists elsewhere in the same Apache log and is saved in [`artifacts/browser-visible-login-examples.txt`](/root/.pack-state/delegated-codex-runs/businessflow-aff-bootstrap-trigger-v1/artifacts/browser-visible-login-examples.txt): `GET /algosec-ui/login`, `GET /seikan/login/setup`, `GET /BusinessFlow` -> `302`, `GET /BusinessFlow/login` -> `302`, then `POST /afa/php/SuiteLoginSessionValidation.php?clean=false`.

Operator conclusion:
- The target midnight bootstrap window appears to be a server-local bootstrap/refresh path, not a browser-initiated request path.
- The browser-visible suite path exists, but it is evidenced by code and by other access-log examples, not by a non-localhost request immediately preceding the March 27 midnight `storeFireflowCookie` window.
