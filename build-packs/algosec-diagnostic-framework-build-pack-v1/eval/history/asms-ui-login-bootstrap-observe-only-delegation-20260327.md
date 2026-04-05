# ASMS UI Login Bootstrap Observe-Only Delegation 2026-03-27

## Purpose

Record one bounded remote Codex delegation slice for the canonical
`ASMS UI is down` proving ground after the playbook was tightened to stay
fail-closed around the login-bootstrap surfaces.

This slice intentionally excluded downstream modules unless the same reproduced
journey clearly reached them.

## Control Path

This pass used both a local swarm and the official split-host delegated path:

- a local multi-agent swarm narrowed the slice to `/seikan/login/setup`,
  `/afa/php/SuiteLoginSessionValidation.php`, and the first correlated Apache
  request window
- PackFactory root used the staged `adf-dev` build-pack copy
- the staged pack on `adf-dev` launched one target-local Codex worker on
  `algosec-lab`
- delegation tier: `observe_only`
- remote run root on `adf-dev`:
  `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/`
- delegation run id:
  `login-bootstrap-observe-only-v1-20260327t153143z`

## Scope Guardrails

The delegated request explicitly kept the slice bounded:

- reproduce only `/seikan/login/setup`
- reproduce only `/afa/php/SuiteLoginSessionValidation.php`
- correlate the same Apache request window
- do not widen into BusinessFlow, Keycloak, FireFlow, Metro, AFA SOAP,
  ActiveMQ, database, or post-home routes unless the same reproduced journey
  clearly reached them
- no target-side mutations

## Accepted Remote Result

The accepted delegated bundle reported this observed login-bootstrap window:

- Apache window: `25/Mar/2026 15:39:16 -0400`
- `GET /seikan/login/setup` -> `200`
- `GET /afa/php/SuiteLoginSessionValidation.php` -> `302`
- first correlated same-window Apache request:
  `GET /keycloak/realms/master/.well-known/openid-configuration` -> `200`

The delegated findings also preserved two useful config clues:

- `/etc/httpd/conf.d/zzz_fa.conf` rewrites `/algosec/suite/login...` to
  `/algosec-ui/login` and forces HTTPS
- `/etc/httpd/conf.d/keycloak.conf` proxies `/keycloak/` to
  `https://localhost:8443/` and only allows loopback clients

## What Became Clear

- The current fail-closed UI-down slice can be executed through the official
  delegated remote path without widening into deeper app theory.
- The earliest observed bootstrap path on this appliance is now sharper:
  `/seikan/login/setup` first, then `SuiteLoginSessionValidation`, then a
  same-window Keycloak OIDC request.
- That means Keycloak is not the first post-shell request, but it is already in
  the early bootstrap chain for the preserved window.
- BusinessFlow did not need to be promoted to explain this login-bootstrap
  window.

## Preserved Remote Bundle

The accepted bundle lives on the staged `adf-dev` copy under the delegated run
root for `adf-autonomy-baseline-catch-up-checkpoint-v1`, and the local pack now
preserves this summary note as the canonical reminder of what the remote
observe-only slice proved.

Remote bundle artifacts referenced by the delegated result:

- `artifacts/ssl_access_window_20260325_153916.txt`
- `artifacts/ssl_request_window_20260325_153916.txt`
- `artifacts/zzz_fa_login_rewrite_excerpt.txt`
- `artifacts/keycloak_proxy_excerpt.txt`

## Gap Noted

The delegated worker noted one remote workspace gap:

- `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/run-summary.json`
  was missing from the staged workspace even though the run root itself was
  present and usable for delegation

That did not block the slice, but it is worth fixing if later remote
correlation depends on the run summary.
