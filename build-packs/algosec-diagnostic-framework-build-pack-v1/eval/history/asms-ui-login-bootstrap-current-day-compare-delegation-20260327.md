# ASMS UI Login Bootstrap Current-Day Compare Delegation 2026-03-27

## Purpose

Record one bounded remote Codex compare pass that tests whether the early
login-bootstrap ordering preserved from March 25, 2026 still reproduces on
March 27, 2026.

This slice stayed intentionally narrow:

- `/seikan/login/setup`
- `/afa/php/SuiteLoginSessionValidation.php`
- first same-window Apache downstream correlation

It did not widen into BusinessFlow, FireFlow, Metro, AFA SOAP, ActiveMQ,
database, or post-home routes.

## Control Path

This pass used:

- a local multi-agent swarm to define the current-day compare question and the
  narrowest sanctioned delegated scope
- the staged ADF build-pack copy on `adf-dev`
- one target-local Codex worker on `algosec-lab`
- delegation tier: `observe_only`
- remote run root on `adf-dev`:
  `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/`
- delegation run id:
  `login-bootstrap-compare-observe-only-v1-20260327t161407z`

## Compare Question

Does a fresh browser-like replay on March 27, 2026 still reproduce the same
early Apache ordering as the preserved March 25, 2026 bootstrap window?

Preserved baseline window:

- `25/Mar/2026 15:39:16 -0400`
- `GET /seikan/login/setup` -> `200 424`
- `GET /afa/php/SuiteLoginSessionValidation.php` -> `302 -`
- `GET /keycloak/realms/master/.well-known/openid-configuration` -> `200 6396`

## Accepted Remote Result

Yes. The delegated worker reported that the preserved ordering still reproduces
on the current-day compare pass:

- fresh compare window:
  `27/Mar/2026 12:18:40-12:18:41 -0400`
- `GET /seikan/login/setup` -> `200 424`
- `GET /afa/php/SuiteLoginSessionValidation.php` -> `302 -`
- `GET /keycloak/realms/master/.well-known/openid-configuration` -> `200 6396`

The worker also noted:

- no matching March 27 trio was already present in Apache logs before the fresh
  replay
- fresh response headers stayed consistent with the preserved interpretation
- `SuiteLoginSessionValidation.php` still returned `302 Found` with
  `Location: /algosec-ui/login?last_url=%2Fafa%2Fphp%2FSuiteLoginSessionValidation.php`
- the Keycloak OIDC well-known path still returned `200 OK` JSON

## What Became Clear

- The early login-bootstrap ordering is not just a preserved March 25 artifact.
- It still reproduces on March 27, 2026 in a fresh compare pass.
- That gives the canonical `ASMS UI is down` path a stronger early runtime
  anchor:
  `setup -> SuiteLoginSessionValidation -> Keycloak OIDC`
- BusinessFlow still does not need to be promoted as an assumed first UI
  dependency for this top-level slice.

## Preserved Remote Bundle

The accepted compare bundle on the staged `adf-dev` copy preserved these
artifacts:

- `artifacts/ssl_access_window_20260327_121840.txt`
- `artifacts/ssl_request_window_20260327_121840.txt`
- `artifacts/current_setup_headers.txt`
- `artifacts/current_suite_headers.txt`
- `artifacts/current_keycloak_headers.txt`
- `artifacts/compare-summary.txt`

## Next Bound

If stronger proof is needed later, the next bounded step is a true headless
browser pass from `/algosec-ui/login` to confirm the same trio appears without
manually pinning the three requests.
