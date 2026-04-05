# ASMS UI Frontline Service Surfaces Observe-Only Delegation 2026-03-27

## Purpose

Record one bounded remote Codex delegation slice for the shallow frontline
`ASMS UI is down` path.

This pass intentionally stayed on the support surfaces that a frontline
engineer can verify quickly during a live customer session:

- host sanity
- Apache or HTTPD service and local UI reachability
- shallow core service status
- no deeper login-bootstrap, BusinessFlow, FireFlow, AFA SOAP, broker, or
  database tracing

## Control Path

This pass used both a local swarm and the official split-host delegated path:

- a local multi-agent swarm tightened the slice around shallow host, Apache,
  and service surfaces
- PackFactory root used the staged `adf-dev` build-pack copy
- the staged pack on `adf-dev` launched one target-local Codex worker on
  `algosec-lab`
- delegation tier: `observe_only`
- remote run root on `adf-dev`:
  `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/`
- delegation run id:
  `frontline-ui-down-service-surfaces-observe-only-v1-20260327t164953z`

## Scope Guardrails

The delegated request explicitly kept the slice shallow:

- check host pressure only at a quick sanity level
- check `httpd`, `keycloak`, `aff-boot`, wrapper state, and listeners
- check localhost UI reachability only
- review only recent Apache error clues
- do not widen into login-bootstrap, BusinessFlow, FireFlow, Metro post-home,
  AFA SOAP, ActiveMQ, database, or broad log mining unless the shallow checks
  pointed there
- no target-side mutations

One harmless remote shell quoting glitch dropped the literal phrase
`ASMS UI is down` from the request text, but the actual delegated scope stayed
bounded and shallow.

## Accepted Remote Result

The accepted delegated bundle reported:

- no shallow localhost Apache or UI outage on the host itself
- `https://127.0.0.1/` returned `200 OK`
- `http://127.0.0.1/` returned `302 Found` to HTTPS
- `https://127.0.0.1/algosec/` returned `200 OK`
- `httpd.service` was `active (running)`
- `keycloak.service` was `active (running)`
- `aff-boot.service` was `active (running)`
- `algosec-ms.service` was `active (exited)` as a wrapper-style unit
- listeners were present on `80`, `443`, `8080`, and `8443`
- `httpd -t` returned `Syntax OK`
- recent Apache error-log tail did not show a fresh web-tier crash or startup
  failure

The delegated worker also preserved three non-fatal Apache warnings:

- missing global `ServerName`
- useless `AllowOverride`
- worker-sharing proxy warnings

Those warnings matter as maintenance clues, but they did not explain a
frontline UI outage in this observed window.

## What Became Clear

- The shallow service and route surfaces are repeatable enough to use as the
  frontline default.
- A pure `ASMS UI is down` path should not jump straight to bootstrap or deeper
  auth analysis when Apache, localhost UI reachability, and the main shallow
  services are all healthy.
- If users still report the UI down while these shallow local checks are
  healthy, the next practical questions are external path, customer browser
  path, or a narrower login or app-shell issue, not a blind jump into deeper
  module theory.

## Preserved Remote Bundle

The accepted bundle lives on the staged `adf-dev` copy under the delegated run
root for `adf-autonomy-baseline-catch-up-checkpoint-v1`.

Remote bundle artifacts referenced by the delegated result:

- `artifacts/httpd-configtest.txt`
- `artifacts/httpd-error-tail.txt`
- `artifacts/listeners.txt`
- `artifacts/service-status.txt`
- `artifacts/ui-reachability.txt`
