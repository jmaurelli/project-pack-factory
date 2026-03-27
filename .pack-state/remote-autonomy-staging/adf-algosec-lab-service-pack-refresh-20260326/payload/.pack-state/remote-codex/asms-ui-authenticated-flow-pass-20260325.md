## Observed Authenticated Request Order

- A real headless Chromium login to `https://127.0.0.1/algosec-ui/login` succeeded and landed on `https://127.0.0.1/afa/php/home.php` with page title `AlgoSec - Home`.
- On the reproduced login minute, the first clear post-shell requests in Apache were:
  - `GET /afa/php/commands.php?cmd=IS_SESSION_ACTIVE&extended=true`
  - `GET /seikan/login/setup`
  - `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` returning `401`
  - `POST /afa/php/SuiteLoginSessionValidation.php?clean=false`
- The later authenticated auth handoff then reached:
  - `POST //keycloak/realms/master/protocol/openid-connect/token?`
  - `POST /BusinessFlow/rest/v1/login`
  - `GET /FireFlow/SelfService/CheckAuthentication/?login=1`
  - `GET /afa/php/home.php`
- Metro-backed authenticated app traffic appeared after that handoff, including:
  - `GET /afa/api/v1/config?...` `200`
  - `POST /afa/api/v1/session/extend?...` `200`
  - other authenticated `/afa/...` requests in Metro access logs

## Proven Vs Inferred

- Proven first post-shell JS-triggered request on this lab: `/seikan/login/setup`
- Proven first auth-triggering legacy session hop on this lab: `POST /afa/php/SuiteLoginSessionValidation.php?clean=false`
- Proven observed auth-chain members after the legacy hop: Keycloak token path, BusinessFlow login, FireFlow auth check, then `/afa/php/home.php`
- Proven Metro role on this lab: meaningful authenticated `/afa/api/v1/...` traffic after the home-page handoff, not the first authenticated hop
- Keycloak is no longer only inferred. It is in the observed authenticated chain, but it is not the first post-shell request.

## Build-Pack Changes Made

- Updated `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py` to make the ASMS UI auth model match the authenticated evidence.
- Added a dedicated Apache correlation check for the authenticated auth handoff.
- Reframed the auth step so the playbook states the legacy pre-auth and session-validation paths happen before the later BusinessFlow and Keycloak handoff on this lab.
- Reframed the Metro step so it explicitly focuses on authenticated post-login app traffic after `/afa/php/home.php`.
- Updated `src/algosec_diagnostic_framework_template_pack/starlight_site.py` so the generated notes explain the authenticated auth handoff and the later Metro role clearly.

## Regeneration And Verification

- `generate-support-baseline` passed.
- `generate-starlight-site` passed.
- `pnpm run build` passed.
- `curl -I http://127.0.0.1:18082/playbooks/asms-ui-is-down/` returned `HTTP/1.0 200 OK` with refreshed page content and a new `Last-Modified` timestamp.

## Recommended Next Move

- Keep the authenticated ordering in the ASMS UI playbook as the current lab-backed model.
- Next, decide whether to treat `BusinessFlow` and `FireFlow` as explicit named neighbors in the ASMS UI system map or keep them as sub-checks inside the broader auth chain.
