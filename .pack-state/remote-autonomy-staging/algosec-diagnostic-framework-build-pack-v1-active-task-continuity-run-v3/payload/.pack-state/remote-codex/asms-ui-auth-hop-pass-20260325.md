## Observed Auth-Trigger Path

- `curl -k https://127.0.0.1/algosec/suite/login` returned `HTTP/1.1 302 Found` from `Server: Apache` with `Location: https://127.0.0.1/algosec-ui/login`.
- Following that redirect with browser-like headers returned `HTTP/1.1 200 OK` from `Server: Apache` for `/algosec-ui/login`.
- The Apache-served shell contains `<base href="/algosec-ui/">` and ships `runtime.js`, `main.js`, and `styles.css` from `/algosec-ui/`.
- The shipped UI source map for `./src/app/login/services/login.service.ts` shows the login flow calls `fetch("/seikan/login/setup")` and `POST /afa/php/SuiteLoginSessionValidation.php` before any credential submission flow.
- `curl -k https://127.0.0.1/seikan/login/setup` returned JSON with `"isSSOEnabled" : false`, `"needsFirstTimeSetup" : false`, and both AFF and ABF enabled.
- `curl -k https://127.0.0.1/afa/php/SuiteLoginSessionValidation.php` returned `HTTP/1.1 302 Found`, set `PHPSESSID`, and redirected back to `/algosec-ui/login?last_url=%2Fafa%2Fphp%2FSuiteLoginSessionValidation.php`.

## Proven Useful Work

- Apache still performs useful edge work for the ASMS UI path:
  - serves the legacy suite login redirect
  - serves the current static login shell
  - serves representative static assets under `/algosec-ui/`
- The shipped login service can still reach the login setup endpoint:
  - `/seikan/login/setup` returned valid JSON from `Server: Apache-Coyote`
- The legacy suite session-validation endpoint still responds and creates a PHP session cookie:
  - `/afa/php/SuiteLoginSessionValidation.php` returned a redirect and `Set-Cookie: PHPSESSID=...`
- Keycloak is reachable through Apache for its OIDC metadata path:
  - `/keycloak/realms/master/.well-known/openid-configuration` returned `HTTP/1.1 200 OK`
- Metro remains reachable on known useful-work paths:
  - `/afa/external//config/all/noauth?domain=0` returned `200`
  - previous bounded local checks still show `/afa/getStatus` healthy

## First Real Downstream Hop

- Static edge proof:
  - Proven: `/algosec/suite/login` -> `/algosec-ui/login`
  - Proven: `/algosec-ui/` HTML and representative assets are Apache-served
- Auth-trigger proof after the static shell:
  - Strongest observed first auth-triggering hop on this run is the legacy suite path, not Keycloak:
    - `/seikan/login/setup`
    - `/afa/php/SuiteLoginSessionValidation.php`
- Keycloak status:
  - Reachable and healthy enough to answer OIDC metadata locally
  - Not proven as the first real downstream hop after the static shell on this reproduced journey
- Metro status:
  - Reachable on no-auth config and prior heartbeat checks
  - Not proven as the first auth-triggering downstream hop after the static shell

## Still Unproven Or Ambiguous

- Without a fuller browser session or credentials, this run did not prove which exact browser request comes immediately after the static shell in a real interactive login startup.
- The reproduced Apache minute for the shell load itself lit up:
  - `/algosec/suite/login`
  - `/algosec-ui/login`
  - no `/keycloak/`
  - no `/afa/api/v1`
- Keycloak remains a real reachable auth neighbor, but on this evidence it is inferred as a downstream auth component rather than observed as the first post-shell auth-trigger.
- Metro remains a real reachable app neighbor, but not the first proven downstream hop after the shell.
- A strict `Apache -> Keycloak -> Metro` serial chain remains unproven on this lab.

## Build-Pack Changes Made

- Updated `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py` in the ASMS UI systems-thinking slice only.
- Changed the auth-branch wording so the playbook no longer implies Keycloak is already proven as the first auth hop on this lab.
- Added an explicit `seikan/login/setup` check.
- Added an explicit cookie-jar check for `/afa/php/SuiteLoginSessionValidation.php`.
- Added a browser-like replay command with cookies and realistic headers for one reproduced journey.
- Tightened Apache log-correlation guidance so the page distinguishes:
  - static shell proof
  - legacy suite auth-trigger proof
  - inferred Keycloak or Metro neighbors
- Updated `src/algosec_diagnostic_framework_template_pack/starlight_site.py` note text so the new commands render with clear Linux-note guidance.

## Regenerated Artifacts

- Regenerated:
  - `dist/candidates/algosec-lab-baseline/runtime-evidence.json`
  - `dist/candidates/algosec-lab-baseline/service-inventory.json`
  - `dist/candidates/algosec-lab-baseline/support-baseline.json`
  - `dist/candidates/algosec-lab-baseline/support-baseline.html`
- Regenerated the Starlight source under:
  - `dist/candidates/algosec-lab-baseline/starlight-site`
- Rebuilt the Starlight static site with:
  - `pnpm install`
  - `pnpm run build`

## Verification

- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-support-baseline --project-root . --target-label algosec-lab --artifact-root dist/candidates/algosec-lab-baseline --output json` passed.
- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-starlight-site --project-root . --artifact-root dist/candidates/algosec-lab-baseline --output json` passed.
- `pnpm run build` passed under `dist/candidates/algosec-lab-baseline/starlight-site`.
- `curl -I http://127.0.0.1:18082/playbooks/asms-ui-is-down/` returned `HTTP/1.0 200 OK`.
- The live review surface on port `18082` shows the refreshed page text, including:
  - `Check the first auth-triggering hop after the static shell`
  - `seikan/login/setup`
  - `SuiteLoginSessionValidation.php`

## Recommended Next Checks

- Reproduce one fuller browser session with DevTools or equivalent request capture, so the first JS-triggered request after `/algosec-ui/login` is observed directly instead of inferred from shipped code.
- Correlate that same reproduced minute across:
  - Apache `ssl_access_log`
  - Keycloak request/activity logs if they light up
  - Metro access logs if they light up
- If credentials can be used safely in the lab, stop at the first post-shell request that actually carries the flow forward and record whether it reaches:
  - `/seikan/login/setup`
  - `/afa/php/SuiteLoginSessionValidation.php`
  - `/keycloak/...`
  - another path
- Keep Keycloak and Metro as parallel reachable neighbors in the playbook until one reproduced authenticated journey proves a stricter order.
