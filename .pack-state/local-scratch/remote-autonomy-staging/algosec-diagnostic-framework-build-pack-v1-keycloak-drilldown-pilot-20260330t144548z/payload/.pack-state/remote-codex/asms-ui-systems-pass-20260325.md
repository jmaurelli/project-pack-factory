## Observed Facts

- `httpd.service` is active and has been running since March 7, 2026, with listeners on `0.0.0.0:80` and `0.0.0.0:443`.
- Apache serves the ASMS UI entry content directly. `curl -k -I https://127.0.0.1/algosec-ui/login` returned `HTTP/1.1 200 OK` from `Server: Apache`.
- The legacy suite login path is still part of the practical UI edge. `curl -k -I https://127.0.0.1/algosec/suite/login` returned `HTTP/1.1 302 Found` with `Location: https://127.0.0.1/algosec-ui/login`.
- Apache proxies the auth branch through `/keycloak/` to local `https://localhost:8443/` according to `/etc/httpd/conf.d/keycloak.conf`.
- Apache proxies the app/API branch through `/afa/api/v1` to local `http://localhost:8080/afa/api/v1` according to `/etc/httpd/conf.d/zzz_fa.conf`.
- Local auth-path probing works through Apache. `curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration` returned `HTTP/1.1 200 OK`.
- Local app-path probing works through Metro. `curl -k -I https://127.0.0.1/afa/api/v1/config/all/noauth` returned `HTTP/1.1 200` from `Server: Apache-Coyote`.
- Direct Metro useful-work probing also works. `curl http://127.0.0.1:8080/afa/getStatus` returned JSON with `"isAlive" : true`.
- Metro access logs show recent successful local traffic for both `/afa/getStatus` and `/afa/api/v1/config/all/noauth?domain=0` with `200` responses.
- The recent `httpd` journal was thin for failures. The available Apache log surface mainly showed routine sudo-backed app activity and FireFlow bridge calls rather than a clear ASMS UI error.

## Dependency Links We Now Believe

- For the ASMS UI path, Apache is not only a reverse proxy. It is also the direct edge serving the current login page assets under `/algosec-ui/`.
- The practical Apache edge sequence on this appliance is:
  legacy suite login route -> Apache-served UI login page -> split to auth and app neighbors
- The immediate auth neighbor is Keycloak through Apache path `/keycloak/` -> local `8443`.
- The immediate app neighbor is Metro through Apache path `/afa/api/v1` -> local `8080`.
- The evidence supports host -> Apache edge -> parallel first-pass auth and app neighbors more strongly than a strict Apache -> Keycloak -> Metro serial chain.
- `ms-metro` still appears to be an important app neighbor, but the Apache edge can already prove useful work before Keycloak or Metro are tested because it serves `/algosec-ui/login` directly.

## Build-Pack Changes Made

- Tightened the ASMS UI Apache edge checkpoint in `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`.
- Replaced the generic edge curl example with the appliance-backed suite login redirect check at `/algosec/suite/login`.
- Added a separate Apache-served UI login page check at `/algosec-ui/login`.
- Tightened the Apache route inspection command and examples so they show the observed login redirect, UI alias, Keycloak proxy target, and Metro API proxy target.
- Kept the change bounded to the ASMS UI systems-thinking slice. No pack state, deployment state, manifest, or unrelated docs/tests were edited.

## Regenerated Artifacts

- Regenerated `dist/candidates/algosec-lab-baseline/runtime-evidence.json`.
- Regenerated `dist/candidates/algosec-lab-baseline/service-inventory.json`.
- Regenerated `dist/candidates/algosec-lab-baseline/support-baseline.json`.
- Regenerated `dist/candidates/algosec-lab-baseline/support-baseline.html`.
- Regenerated the Starlight source under `dist/candidates/algosec-lab-baseline/starlight-site`.
- Rebuilt the Starlight static output under `dist/candidates/algosec-lab-baseline/starlight-site/dist` with `pnpm`, because `npm` was not available in the appliance shell path.

## Verification

- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-support-baseline --project-root . --target-label algosec-lab --artifact-root dist/candidates/algosec-lab-baseline --output json` passed.
- `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-starlight-site --project-root . --artifact-root dist/candidates/algosec-lab-baseline --output json` passed.
- `pnpm install` and `pnpm run build` passed under `dist/candidates/algosec-lab-baseline/starlight-site`.
- The existing durable review server on port `18082` was already serving from the refreshed candidate `dist` tree, so no restart was needed.
- `curl -I http://127.0.0.1:18082/playbooks/asms-ui-is-down/` returned `HTTP/1.0 200 OK`.
- A content spot-check confirmed the regenerated baseline includes the new Apache edge labels and examples.

## Recommended Next Checks

- Test whether Apache can still serve the JS/CSS assets under `/algosec-ui/` when the login page is up, so the edge checkpoint moves one step closer to full browser-useful work.
- Check Apache access logs for `/algosec-ui/`, `/keycloak/`, and `/afa/api/v1` during an actual login attempt, so the first failing neighbor can be identified from one user journey instead of separate curls.
- Inspect whether any Apache rewrite or auth module gates sit in front of `/afa/api/v1/config/all/noauth` versus authenticated UI API calls, because the no-auth path may be healthier than the full signed-in UI path.
- Deepen the Keycloak and Metro branches only after correlating one real browser or curl login flow through Apache, so the next check reduces ambiguity fastest.
